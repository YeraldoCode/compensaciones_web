from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import pandas as pd
import os
import secrets
from datetime import datetime
from config import PERCEPCIONES_MAP, DEDUCCIONES_MAP
import sqlite3
from contextlib import contextmanager

app = Flask(__name__)

# Configuración de la base de datos
DATABASE_PATH = os.path.join('data', 'compensaciones.db')

# Configuración para la carga de archivos
UPLOAD_FOLDER = os.path.join('data')
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de la clave secreta para sesiones
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Ruta del archivo de última actualización
ULTIMA_ACTUALIZACION_PATH = os.path.join('data', 'ultima_actualizacion.txt')

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Inicializa la base de datos con las tablas necesarias."""
    # Asegurar que el directorio data existe
    os.makedirs('data', exist_ok=True)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tabla de compensaciones
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS compensaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomina TEXT NOT NULL,
            nombre TEXT NOT NULL,
            concepto TEXT NOT NULL,
            valor REAL NOT NULL,
            semana TEXT,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Tabla de nomina
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS nomina (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomina TEXT NOT NULL,
            nombre TEXT NOT NULL,
            concepto TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL,  -- 'PERCEPCION' o 'DEDUCCION'
            semana TEXT,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Índices para búsquedas rápidas
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_compensaciones_nomina ON compensaciones(nomina)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_compensaciones_nombre ON compensaciones(nombre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nomina_nomina ON nomina(nomina)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nomina_nombre ON nomina(nombre)')
        
        conn.commit()

def procesar_valor(valor):
    """Procesa un valor y lo convierte a float."""
    if valor is None or valor == '' or str(valor).lower() == 'nan':
        return 0.0
    try:
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            # Limpiar el valor de caracteres no numéricos excepto el punto decimal
            v_clean = valor.replace(',', '').replace('$', '').replace(' ', '')
            # Verificar si es un número válido
            if v_clean.replace('.', '', 1).replace('-', '', 1).isdigit():
                return float(v_clean)
            return 0.0
        return 0.0
    except Exception as e:
        print(f"Error procesando valor '{valor}': {str(e)}")
        return 0.0

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cargar_datos_excel(file_path, semana):
    """Carga los datos del Excel en la base de datos."""
    try:
        print(f"Cargando archivo: {file_path}")  # Debug log
        print(f"Semana: {semana}")  # Debug log
        
        # Leer el Excel
        df_compensaciones = pd.read_excel(file_path, sheet_name='BD_COMPENSACIONES', dtype={'NOMINA': str})
        df_nomina = pd.read_excel(file_path, sheet_name='BD', dtype={'clave.': str})
        
        print(f"Registros en BD_COMPENSACIONES: {len(df_compensaciones)}")  # Debug log
        print(f"Registros en BD: {len(df_nomina)}")  # Debug log
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Limpiar datos anteriores de la semana
            cursor.execute('DELETE FROM compensaciones WHERE semana = ?', (semana,))
            cursor.execute('DELETE FROM nomina WHERE semana = ?', (semana,))
            
            # Procesar compensaciones
            compensaciones_insertadas = 0
            for _, row in df_compensaciones.iterrows():
                nomina = str(row['NOMINA']).strip()
                nombre = str(row['NOMBRE']).strip()
                
                for col in df_compensaciones.columns:
                    if col not in ['NOMINA', 'NOMBRE']:
                        valor = procesar_valor(row[col])
                        if valor != 0:  # Solo guardar valores no cero
                            cursor.execute('''
                                INSERT INTO compensaciones (nomina, nombre, concepto, valor, semana)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (nomina, nombre, col, valor, semana))
                            compensaciones_insertadas += 1
            
            print(f"Compensaciones insertadas: {compensaciones_insertadas}")  # Debug log
            
            # Procesar nómina
            nomina_insertada = 0
            for _, row in df_nomina.iterrows():
                nomina = str(row['clave.']).strip()
                nombre = str(row['nombre completo.']).strip()
                
                # Procesar percepciones
                for col, nombre_concepto in PERCEPCIONES_MAP.items():
                    if col in row:
                        valor = procesar_valor(row[col])
                        if valor != 0:
                            cursor.execute('''
                                INSERT INTO nomina (nomina, nombre, concepto, valor, tipo, semana)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (nomina, nombre, nombre_concepto, valor, 'PERCEPCION', semana))
                            nomina_insertada += 1
                
                # Procesar deducciones
                for col, nombre_concepto in DEDUCCIONES_MAP.items():
                    if col in row:
                        valor = procesar_valor(row[col])
                        if nombre_concepto == 'IMSS':  # Log específico para IMSS
                            print(f"IMSS para {nomina} ({nombre}): {valor}")
                        if valor != 0:
                            cursor.execute('''
                                INSERT INTO nomina (nomina, nombre, concepto, valor, tipo, semana)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (nomina, nombre, nombre_concepto, valor, 'DEDUCCION', semana))
                            nomina_insertada += 1
            
            print(f"Registros de nómina insertados: {nomina_insertada}")  # Debug log
            
            conn.commit()
            
            # Verificar datos insertados
            cursor.execute("SELECT COUNT(*) FROM compensaciones WHERE semana = ?", (semana,))
            total_compensaciones = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM nomina WHERE semana = ?", (semana,))
            total_nomina = cursor.fetchone()[0]
            
            print(f"Total de compensaciones en la base de datos para la semana {semana}: {total_compensaciones}")
            print(f"Total de registros de nómina en la base de datos para la semana {semana}: {total_nomina}")
            
            return True
    except Exception as e:
        print(f"Error cargando datos: {str(e)}")
        return False

@app.route('/')
def login():
    return render_template('login_alert.html')

@app.route('/compensaciones', methods=['POST'])
def compensaciones():
    nomina = request.form.get('nomina')
    nombre = request.form.get('nombre')
    semana = None
    
    # Obtener semana actual
    if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
        try:
            with open(ULTIMA_ACTUALIZACION_PATH, 'r', encoding='utf-8') as f:
                line = f.read().strip()
                if line:
                    partes = line.split('|')
                    if len(partes) == 2:
                        _, semana = partes
                        print(f"Semana actual: {semana}")  # Debug log
        except Exception as e:
            print(f"Error leyendo archivo de última actualización: {str(e)}")
            semana = None

    if not nomina and not nombre:
        return render_template('login_alert.html', error="Por favor, proporciona un número de nómina o un nombre completo para realizar la búsqueda.")

    try:
        # Leer directamente el archivo PLANTILLA_DESGLOSE.xlsx
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'PLANTILLA_DESGLOSE.xlsx')
        if not os.path.exists(file_path):
            return render_template('login_alert.html', error="No se encontró el archivo de datos.")

        # Cargar datos del Excel
        df_compensaciones = pd.read_excel(file_path, sheet_name='BD_COMPENSACIONES', dtype={'NOMINA': str})
        df_nomina = pd.read_excel(file_path, sheet_name='BD', dtype={'clave.': str})

        # Buscar en compensaciones
        if nomina:
            df_comp = df_compensaciones[df_compensaciones['NOMINA'] == nomina.strip()]
        else:
            df_comp = df_compensaciones[df_compensaciones['NOMBRE'].str.contains(nombre.strip(), case=False, na=False)]

        if df_comp.empty:
            return render_template('login_alert.html', 
                                error="No se encontraron datos para el número de nómina o el nombre proporcionado.",
                                nomina=nomina, nombre=nombre)

        # Procesar datos de compensaciones
        row_comp = df_comp.iloc[0]
        datos = {
            'NOMINA': str(row_comp['NOMINA']),
            'NOMBRE': str(row_comp['NOMBRE'])
        }

        total_compensaciones = 0
        for col in df_compensaciones.columns:
            if col not in ['NOMINA', 'NOMBRE']:
                valor = procesar_valor(row_comp[col])
                if valor != 0:
                    datos[col] = valor
                    total_compensaciones += valor

        datos['TOTAL'] = f"${total_compensaciones:,.2f}"

        # Buscar en nómina
        if nomina:
            df_nom = df_nomina[df_nomina['clave.'] == nomina.strip()]
        else:
            df_nom = df_nomina[df_nomina['nombre completo.'].str.contains(nombre.strip(), case=False, na=False)]

        nomina_obj = None
        if not df_nom.empty:
            row_nom = df_nom.iloc[0]
            percepciones = {}
            deducciones = {}
            total_percepciones = 0
            total_deducciones = 0

            # Procesar percepciones
            for col, nombre_concepto in PERCEPCIONES_MAP.items():
                if col in row_nom:
                    valor = procesar_valor(row_nom[col])
                    if valor != 0:
                        percepciones[nombre_concepto] = valor
                        total_percepciones += valor

            # Procesar deducciones
            for col, nombre_concepto in DEDUCCIONES_MAP.items():
                if col in row_nom:
                    valor = procesar_valor(row_nom[col])
                    if nombre_concepto == 'IMSS':  # Log específico para IMSS
                        print(f"IMSS para {datos['NOMINA']} ({datos['NOMBRE']}): {valor}")
                    if valor != 0:
                        deducciones[nombre_concepto] = valor
                        total_deducciones += valor

            # Solo agregar totales si hay valores
            if percepciones:
                nomina_obj = type('Nomina', (), {})()
                nomina_obj.percepciones = percepciones
                nomina_obj.total_percepciones = total_percepciones

            if deducciones:
                if not nomina_obj:
                    nomina_obj = type('Nomina', (), {})()
                nomina_obj.deducciones = deducciones
                nomina_obj.total_deducciones = total_deducciones

            if nomina_obj:
                nomina_obj.neto_a_pagar = total_percepciones - total_deducciones

    except Exception as e:
        print(f"Error en la ruta compensaciones: {str(e)}")  # Debug log
        return render_template('login_alert.html', error=f"Error al procesar los datos: {str(e)}")

    return render_template('compensaciones.html', 
                         datos=datos, 
                         semana=semana, 
                         nomina=nomina_obj, 
                         now=datetime.now())

@app.route('/modificar', methods=['GET', 'POST'])
def modificar_archivo():
    ultimo_archivo = None
    ultima_semana = None
    
    # Leer última actualización si existe
    if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
        try:
            with open(ULTIMA_ACTUALIZACION_PATH, 'r', encoding='utf-8') as f:
                line = f.read().strip()
                if line:
                    partes = line.split('|')
                    if len(partes) == 2:
                        ultimo_archivo, ultima_semana = partes
        except Exception:
            pass
            
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo')
            return redirect(request.url)
        
        file = request.files['file']
        semana = request.form.get('semana')
        
        # Validaciones básicas
        if file.filename == '':
            flash('No se seleccionó ningún archivo')
            return redirect(request.url)
        if not semana:
            flash('Debes seleccionar una semana')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('Solo se permiten archivos Excel (.xlsx)')
            return redirect(request.url)
            
        try:
            # Validar que el archivo sea un Excel válido y tenga las hojas correctas
            df = pd.read_excel(file, sheet_name=None)
            required_sheets = ['BD_COMPENSACIONES', 'BD']
            missing_sheets = [sheet for sheet in required_sheets if sheet not in df]
            
            if missing_sheets:
                flash(f'El archivo debe contener las siguientes hojas: {", ".join(required_sheets)}')
                return redirect(request.url)
                
            # Validar que las hojas tengan datos
            for sheet in required_sheets:
                if df[sheet].empty:
                    flash(f'La hoja {sheet} está vacía')
                    return redirect(request.url)
            
            # Guardar el archivo con nombre único por semana
            unique_filename = f"PLANTILLA_DESGLOSE_SEMANA_{semana}.xlsx"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Guardar el archivo
            file.seek(0)
            file.save(file_path)
            
            # Cargar datos en la base de datos
            if cargar_datos_excel(file_path, semana):
                # Guardar la información de la última actualización
                with open(ULTIMA_ACTUALIZACION_PATH, 'w', encoding='utf-8') as f:
                    f.write(f"{unique_filename}|{semana}")
                    
                flash('Archivo actualizado correctamente')
            else:
                flash('Error al cargar los datos en la base de datos')
            
            return redirect(url_for('modificar_archivo'))
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}')
            return redirect(request.url)
            
    return render_template('modificar.html', ultimo_archivo=ultimo_archivo, ultima_semana=ultima_semana)

# Inicializar la base de datos al iniciar la aplicación
init_db()

if __name__ == '__main__':
    if os.getenv('FLASK_ENV') == 'production':
        from waitress import serve
        serve(app, host='0.0.0.0', port=8080)
    else:
        app.run(host='0.0.0.0', port=8080, debug=True)
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import pandas as pd
import os
import secrets
from datetime import datetime
from config import PERCEPCIONES_MAP, DEDUCCIONES_MAP
import sqlite3

app = Flask(__name__)

# Ruta del archivo Excel
EXCEL_PATH = os.path.join('data', 'PLANTILLA_DESGLOSE.xlsx')

# Configuración para la carga de archivos
UPLOAD_FOLDER = os.path.join('data')
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de la clave secreta para sesiones
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Variable global para almacenar los DataFrames en memoria
compensaciones_df = None
nomina_desglose_df = None

def procesar_valor(valor):
    """Procesa un valor y lo convierte a float."""
    if valor is None or valor == '' or str(valor).lower() == 'nan':
        return 0.0
    try:
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            v_clean = valor.replace(',', '').replace('$', '').replace(' ', '')
            return float(v_clean) if v_clean.replace('.', '', 1).replace('-', '', 1).isdigit() else 0.0
        return 0.0
    except Exception:
        return 0.0

def init_db():
    """Initialize the database schema."""
    conn = sqlite3.connect('data/compensaciones.db')
    cursor = conn.cursor()
    # Create compensaciones table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS compensaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomina INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            concepto TEXT NOT NULL,
            valor REAL NOT NULL,
            semana INTEGER NOT NULL
        )
        """
    )
    # Create nomina table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS nomina (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomina INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            concepto TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL,
            semana INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

# Enhance cargar_excel to handle missing required values
def cargar_excel():
    global compensaciones_df, nomina_desglose_df
    ULTIMA_ACTUALIZACION_PATH = os.path.join('data', 'ultima_actualizacion.txt')
    if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
        try:
            with open(ULTIMA_ACTUALIZACION_PATH, 'r', encoding='utf-8') as f:
                line = f.read().strip()
                if line:
                    partes = line.split('|')
                    if len(partes) == 2:
                        archivo_reciente, semana = partes
                        excel_path = os.path.join('data', archivo_reciente)
                        if os.path.exists(excel_path):
                            compensaciones_df = pd.read_excel(excel_path, sheet_name='BD_COMPENSACIONES').fillna('')
                            nomina_desglose_df = pd.read_excel(excel_path, sheet_name='BD').fillna('')
                            
                            # Verificar que las columnas requeridas estén presentes
                            columnas_requeridas = [
                                'NOMBRE', 'TEAM LEADER', 'COORDINADOR', 'BONO DELEGADO',
                                'BONO DE ARRA. E INDIC.', 'RUTA LARGA-LIDER CERO', 'ESTANCIAS',
                                'BONO FIJO PLANTAS CRITICAS', 'BONO FORANEO', 'BONO CONTRATACION',
                                'BONO DE RECOMENDADO', 'BONO KPIS', 'APOYO A PLANTAS CRITICAS',
                                'PAGO PENDIENTE/BONO GUARDIA/BONO CELESTICA',
                                'VUELTAS NO REGISTRADAS EN BUSTRAX',
                                'MONTO VUELTAS NO REGISTRADAS EN BUSTRAX'
                            ]
                            for columna in columnas_requeridas:
                                if columna not in compensaciones_df.columns:
                                    raise ValueError(f"La columna requerida '{columna}' no está presente en la hoja BD_COMPENSACIONES.")
                            
                            # Actualizar la base de datos
                            conn = sqlite3.connect('data/compensaciones.db')
                            cursor = conn.cursor()
                            # Limpiar datos existentes para la semana
                            cursor.execute("DELETE FROM compensaciones WHERE semana = ?", (semana,))
                            # Insertar datos de compensaciones
                            for _, row in compensaciones_df.iterrows():
                                for columna in columnas_requeridas:
                                    valor = procesar_valor(row.get(columna, 0.0))
                                    cursor.execute(
                                        "INSERT INTO compensaciones (nomina, nombre, concepto, valor, semana) VALUES (?, ?, ?, ?, ?)",
                                        (
                                            row.get('NOMBRE', 'Desconocido'),
                                            columna,
                                            valor,
                                            semana
                                        )
                                    )
                            conn.commit()
                            conn.close()
                            return
        except Exception as e:
            print(f"Error al cargar el Excel: {str(e)}")

# Cargar el Excel al iniciar la app
cargar_excel()

# Verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def login():
    return render_template('login_alert.html')

@app.route('/compensaciones', methods=['POST'])
def compensaciones():
    nomina = request.form.get('nomina')
    nombre = request.form.get('nombre')
    semana = None

    # Obtener semana actual
    ULTIMA_ACTUALIZACION_PATH = os.path.join('data', 'ultima_actualizacion.txt')
    if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
        try:
            with open(ULTIMA_ACTUALIZACION_PATH, 'r', encoding='utf-8') as f:
                line = f.read().strip()
                if line:
                    partes = line.split('|')
                    if len(partes) == 2:
                        _, semana = partes
        except Exception:
            semana = None

    if not nomina and not nombre:
        return render_template('login_alert.html', error="Por favor, proporciona un número de nómina o un nombre completo para realizar la búsqueda.")

    try:
        # Procesar datos de compensaciones
        df = compensaciones_df
        if nomina:
            try:
                nomina_int = int(nomina)
                fila = df[df['NOMINA'] == nomina_int]
            except ValueError:
                return render_template('login_alert.html', error="El número de nómina debe ser un valor numérico.", nomina=nomina)
        elif nombre:
            fila = df[df['NOMBRE'].str.contains(nombre, case=False, na=False)]

        # --- MODIFICACIÓN: Permitir mostrar nómina aunque no tenga compensaciones ---
        if fila.empty:
            # Buscar en el desglose de nómina
            df_desglose = nomina_desglose_df
            if nomina:
                try:
                    nomina_int = int(nomina)
                    fila_desglose = df_desglose[df_desglose['clave.'] == nomina_int]
                except ValueError:
                    fila_desglose = pd.DataFrame()
            elif nombre:
                fila_desglose = df_desglose[df_desglose['nombre completo.'].str.contains(nombre, case=False, na=False)]
            else:
                fila_desglose = pd.DataFrame()

            if not fila_desglose.empty:
                datos = {}
                datos['NOMINA'] = int(nomina) if nomina else None
                datos['TOTAL'] = "$0.00"
            else:
                return render_template('login_alert.html', error="No se encontraron datos para el número de nómina o el nombre proporcionado.", nomina=nomina, nombre=nombre)
        else:
            datos = fila.to_dict(orient='records')[0]
            datos['NOMINA'] = int(datos['NOMINA'])
            total = sum(valor for clave, valor in datos.items() if isinstance(valor, (int, float)) and clave != 'NOMINA')
            datos['TOTAL'] = f"${total:,.2f}"
        # --- FIN MODIFICACIÓN ---

        # Procesar datos de nómina
        nomina_obj = None
        try:
            df_desglose = nomina_desglose_df
            if nomina:
                fila_desglose = df_desglose[df_desglose['clave.'] == int(nomina)]
            elif nombre:
                fila_desglose = df_desglose[df_desglose['nombre completo.'].str.contains(nombre, case=False, na=False)]

            if not fila_desglose.empty:
                fila_desglose = fila_desglose.iloc[0]

                # Procesar percepciones
                percepciones = {}
                for col, nombre in PERCEPCIONES_MAP.items():
                    valor = procesar_valor(fila_desglose.get(col, 0.0))
                    percepciones[nombre] = valor

                # Procesar deducciones
                deducciones = {}
                for col, nombre in DEDUCCIONES_MAP.items():
                    valor = procesar_valor(fila_desglose.get(col, 0.0))
                    deducciones[nombre] = valor

                # Calcular totales
                total_percepciones = sum(percepciones.values())
                total_deducciones = sum(deducciones.values())

                # Obtener neto a pagar
                neto_a_pagar = procesar_valor(fila_desglose.get('NETO A PAGAR', 0.0))
                if neto_a_pagar == 0.0:
                    neto_a_pagar = total_percepciones - total_deducciones

                nomina_obj = type('Nomina', (), {})()
                nomina_obj.percepciones = percepciones
                nomina_obj.deducciones = deducciones
                nomina_obj.total_percepciones = total_percepciones
                nomina_obj.total_deducciones = total_deducciones
                nomina_obj.neto_a_pagar = neto_a_pagar

        except Exception as e:
            print(f"Error procesando nómina: {str(e)}")
            nomina_obj = None

    except Exception as e:
        return f"Error al leer el archivo: {str(e)}", 500

    return render_template(
        'compensaciones.html',
        datos=datos,
        semana=semana,
        nomina=nomina_obj,
        now=datetime.now()
    )

ULTIMA_ACTUALIZACION_PATH = os.path.join('data', 'ultima_actualizacion.txt')

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
        if file.filename == '':
            flash('No se seleccionó ningún archivo')
            return redirect(request.url)
        if not semana:
            flash('Debes seleccionar una semana')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Guardar el archivo con nombre único por semana
            unique_filename = f"PLANTILLA_DESGLOSE_SEMANA_{semana}.xlsx"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            # Sobrescribir el archivo principal para que siempre se lea el último
            file.seek(0)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'PLANTILLA_DESGLOSE.xlsx'))
            # Guardar la información de la última actualización
            with open(ULTIMA_ACTUALIZACION_PATH, 'w', encoding='utf-8') as f:
                f.write(f"{unique_filename}|{semana}")
            flash('Archivo actualizado correctamente')
            # Recargar el Excel en memoria
            cargar_excel()
            return redirect(url_for('modificar_archivo'))
    return render_template('modificar.html', ultimo_archivo=ultimo_archivo, ultima_semana=ultima_semana)

@app.route('/nomina/<int:nomina>', methods=['GET'])
def obtener_nomina(nomina):
    try:
        nomina_desglose_df = pd.read_excel(EXCEL_PATH, sheet_name='BD').fillna('')
        fila_desglose = nomina_desglose_df[nomina_desglose_df['clave.'] == nomina]
        if not fila_desglose.empty:
            fila_desglose = fila_desglose.iloc[0]
            
            # Aplicar mapeo de percepciones
            percepciones = {nombre: fila_desglose[col] if col in fila_desglose else 0.0 for col, nombre in PERCEPCIONES_MAP.items()}
            
            # Aplicar mapeo de deducciones
            deducciones = {nombre: fila_desglose[col] if col in fila_desglose else 0.0 for col, nombre in DEDUCCIONES_MAP.items()}
            
            return jsonify({
                "percepciones": percepciones,
                "deducciones": deducciones
            }), 200
        else:
            return jsonify({"error": f"No se encontraron datos para la nómina {nomina}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if os.getenv('FLASK_ENV') == 'production':
        from waitress import serve
        serve(app, host='0.0.0.0', port=8080)
    else:
        app.run(host='0.0.0.0', port=8080, debug=True)
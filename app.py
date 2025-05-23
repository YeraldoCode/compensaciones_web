from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import pandas as pd
import os
import secrets

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

def cargar_excel():
    global compensaciones_df, nomina_desglose_df
    compensaciones_df = pd.read_excel(EXCEL_PATH, sheet_name='BD_COMPENSACIONES').fillna('')
    try:
        nomina_desglose_df = pd.read_excel(EXCEL_PATH, sheet_name='DESGLOSE').fillna('')
    except Exception:
        nomina_desglose_df = None

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
        df = compensaciones_df  # Usar el DataFrame en memoria
        if nomina:
            try:
                nomina_int = int(nomina)
                fila = df[df['NOMINA'] == nomina_int]
            except ValueError:
                return render_template('login_alert.html', error="El número de nómina debe ser un valor numérico.", nomina=nomina)
        elif nombre:
            fila = df[df['NOMBRE'].str.contains(nombre, case=False, na=False)]
        if fila.empty:
            return render_template('login_alert.html', error="No se encontraron datos para el número de nómina o el nombre proporcionado.", nomina=nomina, nombre=nombre)
        datos = fila.to_dict(orient='records')[0]
        datos['NOMINA'] = int(datos['NOMINA'])
        total = 0
        for clave, valor in datos.items():
            if isinstance(valor, (int, float)) and clave != 'NOMINA':
                total += valor
                datos[clave] = f"${valor:,.2f}"
        datos['TOTAL'] = f"${total:,.2f}"
        # --- Detalle de nómina desde hoja BD ---
        nomina_obj = None
        try:
            # Usar DataFrame en memoria si existe
            global nomina_desglose_df
            if nomina_desglose_df is None:
                nomina_desglose_df = pd.read_excel(EXCEL_PATH, sheet_name='BD').fillna('')
            df_desglose = nomina_desglose_df
            if nomina:
                try:
                    nomina_int = int(nomina)
                    fila_desglose = df_desglose[df_desglose['clave.'] == nomina_int]
                except ValueError:
                    fila_desglose = None
            elif nombre:
                fila_desglose = df_desglose[df_desglose['nombre completo.'].str.contains(nombre, case=False, na=False)]
            if fila_desglose is not None and not fila_desglose.empty:
                fila_desglose = fila_desglose.iloc[0]
                # Mapeo de columnas a nombres amigables para mostrar en la tabla
                mapeo_percepciones = {
                    'SUELDO': 'SUELDO',
                    'VALES DESPENSA': 'VALES DE DESPENSA',
                    'VACACIONES': 'VACACIONES',
                    'PRIMA VAC.': 'PRIMA VACACIONAL',
                    'SUELDO ADEUDADO': 'SUELDO ADEUDADO',
                    'PRIMA DOMINICAL': 'PRIMA DOMINICAL',
                    'FEST DESC LABOR': 'FESTIVO LABORADO',
                    'DOMINGO LABORAD': 'DOMINGO LABORADO',
                    'VIAJES ADICIONA': 'VIAJES ADICIONALES',
                    'SERVICIOS ESPEC': 'SERVICIOS ESPECIALES',
                    'SERVICIOS FIJOS': 'SERVICIOS FIJOS',
                    'BONO DE RENDIMI': 'BONO RENDIMIENTO',
                    'COMPENSACION': 'COMPENSACION',
                    'BONO DESEMPEÑO': 'BONO DESEMPEÑO',
                    'AYUDA FUNERARIA': 'AYUDA FUNERARIA',
                    'AYUDA ESCOLAR': 'AYUDA ESCOLAR',
                    'TOTAL PERCEP': 'TOTAL PERCEPCIONES',
                }
                mapeo_deducciones = {
                    'FALTAS': 'FALTAS o PERMISOS SIN GOCE',
                    'I.S.P.T.': 'ISPT',
                    'I.M.S.S.': 'IMSS',
                    'CUOTA SINDICAL': 'CUOTA SINDICAL',
                    'DESC. INFONAVIT': 'INFONAVIT',
                    'SEG.DAÑOS VIV': 'SEGURO INFONAVIT',
                    'DIF. INFONAVIT': 'DIF INFONAVIT',
                    'PENSION ALIMENT': 'PENSION ALIMENTICIA',
                    'DESCTO. FONACOT': 'FONACOT',
                    'PRESTAMO PERSON': 'PRESTAMO PERSONAL',
                    'ANOMALIAS': 'ANOMALIAS',
                    'COMBUSTIBLE': 'COMBUSTIBLE',
                    'TELEFONIA': 'TELEFONIA',
                    'SINIESTROS': 'SINIESTROS',
                    'PRESTAMO DE LIC': 'PRESTAMO LICENCIA',
                    'DESC. DE LENTES': 'DESC. DE LENTES',
                    'TAXIS': 'TAXIS',
                    'REP. TARJETA': 'REP. TARJETA',
                    'TOTAL DEDUCC': 'TOTAL DEDUCCIONES',
                }
                percepciones = {}
                deducciones = {}
                total_percepciones = 0
                total_deducciones = 0
                for col, nombre in mapeo_percepciones.items():
                    if col in fila_desglose:
                        valor = fila_desglose[col]
                        if col == 'TOTAL PERCEP':
                            total_percepciones = valor
                        if isinstance(valor, (int, float)):
                            percepciones[nombre] = valor
                for col, nombre in mapeo_deducciones.items():
                    if col in fila_desglose:
                        valor = fila_desglose[col]
                        if col == 'TOTAL DEDUCC':
                            total_deducciones = valor
                        if isinstance(valor, (int, float)):
                            deducciones[nombre] = valor
                if 'NETO A PAGAR' in fila_desglose:
                    neto_a_pagar = fila_desglose['NETO A PAGAR']
                else:
                    neto_a_pagar = total_percepciones - total_deducciones
                nomina_obj = type('Nomina', (), {})()
                nomina_obj.percepciones = percepciones
                nomina_obj.deducciones = deducciones
                nomina_obj.total_percepciones = total_percepciones
                nomina_obj.total_deducciones = total_deducciones
                nomina_obj.neto_a_pagar = neto_a_pagar
        except Exception:
            nomina_obj = None
    except Exception as e:
        return f"Error al leer el archivo: {str(e)}", 500
    return render_template('compensaciones.html', datos=datos, semana=semana, nomina=nomina_obj)

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
            # Guardar SIEMPRE con el nombre que usa el backend para leer
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'PLANTILLA_DESGLOSE.xlsx'))
            # Guardar la información de la última actualización
            with open(ULTIMA_ACTUALIZACION_PATH, 'w', encoding='utf-8') as f:
                f.write(f"PLANTILLA_DESGLOSE.xlsx|{semana}")
            flash('Archivo actualizado correctamente')
            # Recargar el Excel en memoria
            cargar_excel()
            return redirect(url_for('modificar_archivo'))
    return render_template('modificar.html', ultimo_archivo=ultimo_archivo, ultima_semana=ultima_semana)

if __name__ == '__main__':
    if os.getenv('FLASK_ENV') == 'production':
        from waitress import serve
        serve(app, host='0.0.0.0', port=8080)
    else:
        app.run(host='0.0.0.0', port=8080, debug=True)
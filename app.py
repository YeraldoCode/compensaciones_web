from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import os
import secrets
from datetime import datetime
import unicodedata

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join('data')
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Variables globales para los DataFrames
compensaciones_df = None
nomina_desglose_df = None
ULTIMA_ACTUALIZACION_PATH = os.path.join('data', 'ultima_actualizacion.txt')

# Encabezados para mapeo por nombre (ajusta si cambian en tu Excel)
PERCEPCIONES = [
    'SUELDO', 'VALES DESPENSA', 'SUELDO ADEUDADO', 'VACACIONES', 'PRIMA VAC.', 'PRIMA DOMINICAL',
    'VIAJES ADICIONA', 'SERVICIOS ESPEC', 'SERVICIOS FIJOS', 'BONO DE RENDIMIENTO', 'COMPENSACION',
    'BONO DESEMPEÑO', 'AYUDA ESCOLAR', 'AYUDA FUNERARIA', 'DOMINGO LABORADO'
]
DEDUCCIONES = [
    'FALTAS', 'I.S.P.T.', 'I.M.S.S.', 'CUOTA SINDICAL', 'DESC. INFONAVIT', 'SEG.DAÑOS VIV',
    'DIF. INFONAVIT', 'PENSION ALIMENT', 'DESCTO. FONACOT', 'PRESTAMO PERSON', 'ANOMALIAS',
    'COMBUSTIBLE', 'TELEFONIA', 'SINIESTROS', 'PRESTAMO DE LIC', 'DESCUENTO TAXI', 'REP. TARJETA'
]
# Otros campos clave
CAMPOS_CLAVE = ['clave.', 'nombre completo.', 'nombre del puesto', 'TOTAL PERCEP', 'TOTAL DEDUCC', 'NETO A PAGAR']

# Encabezados de BD_COMPENSACIONES
COMPENSACIONES = [
    'NOMINA', 'NOMBRE', 'TEAM LEADER', 'COORDINADOR', 'BONO DELEGADO', 'RUTA LARGA-LIDER CERO',
    'ESTANCIAS', 'BONO FIJO PLANTAS CRITICAS', 'BONO FORANEO', 'BONO DE RECOMENDADO', 'BONO KPIS',
    'APOYO A PLANTAS CRITICAS', 'PAGO PENDIENTE/BONO GUARDIA/BONO CELESTICA',
    'VUELTAS NO REGISTRADAS EN BUSTRAX', 'MONTO VUELTAS NO REGISTRADAS EN BUSTRAX'
]

def normalizar_columna(nombre):
    # Quita espacios, tildes y convierte a minúsculas
    if not isinstance(nombre, str):
        return ''
    nombre = nombre.lower().replace(' ', '').replace('.', '').replace('$', '')
    nombre = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode('utf-8')
    return nombre

# --- Mapeo directo por nombre de columna, con comentarios de columna Excel ---
PERCEPCIONES_MAP = {
    'SUELDO': ['SUELDO'],                        # Q
    'VALES DESPENSA': ['VALES DESPENSA'],        # R
    'SUELDO ADEUDADO': ['SUELDO ADEUDADO'],      # S
    'VACACIONES': ['VACACIONES'],                # T
    'PRIMA VAC.': ['PRIMA VAC.'],                # U
    'PRIMA DOMINICAL': ['PRIMA DOMINICAL'],      # V
    'DOMINGO LABORAD': ['DOMINGO LABORAD'],      # W
    'VIAJES ADICIONA': ['VIAJES ADICIONA'],      # X
    'SERVICIOS ESPEC': ['SERVICIOS ESPEC'],      # Y
    'SERVICIOS FIJOS': ['SERVICIOS FIJOS'],      # Z
    'BONO DE RENDIMI': ['BONO DE RENDIMI'],      # AA
    'COMPENSACION': ['COMPENSACION'],            # AB
    'BONO DESEMPEÑO': ['BONO DESEMPEÑO'],        # AC
    'AYUDA ESCOLAR': ['AYUDA ESCOLAR'],          # AD
    'AYUDA FUNERARIA': ['AYUDA FUNERARIA'],      # AE
    'TOTAL PERCEP': ['TOTAL PERCEP']             # AF
}

DEDUCCIONES_MAP = {
    'FALTAS': ['FALTAS'],                        # AG
    'I.S.P.T.': ['I.S.P.T.'],                    # AH
    'I.M.S.S.': ['I.M.S.S.'],                    # AI
    'CUOTA SINDICAL': ['CUOTA SINDICAL'],        # AJ
    'DESC. INFONAVIT': ['DESC. INFONAVIT'],      # AK
    'SEG.DAÑOS VIV': ['SEG.DAÑOS VIV'],          # AL
    'DIF. INFONAVIT': ['DIF. INFONAVIT'],        # AM
    'PENSION ALIMENT': ['PENSION ALIMENT'],      # AN
    'DESCTO. FONACOT': ['DESCTO. FONACOT'],      # AO
    'PRESTAMO PERSON': ['PRESTAMO PERSON'],      # AP
    'ANOMALIAS': ['ANOMALIAS'],                  # AQ
    'COMBUSTIBLE': ['COMBUSTIBLE'],              # AR
    'TELEFONIA': ['TELEFONIA'],                  # AS
    'SINIESTROS': ['SINIESTROS'],                # AT
    'PRESTAMO DE LIC': ['PRESTAMO DE LIC'],      # AU
    'DESCUENTO TAXI': ['DESCUENTO TAXI'],        # AV
    'REP. TARJETA': ['REP. TARJETA'],            # AW
    'TOTAL DEDUCC': ['TOTAL DEDUCC'],            # AX
    'NETO A PAGAR': ['NETO A PAGAR']             # AY
}

def procesar_valor(valor):
    if valor is None or valor == '' or str(valor).lower() == 'nan':
        return 0.0
    try:
        # Si es un número (int, float, numpy int/float), conviértelo directo
        if isinstance(valor, (int, float)):
            return float(valor)
        # Si es string, limpia y convierte
        if isinstance(valor, str):
            v_clean = valor.replace(',', '').replace('$', '').replace(' ', '')
            try:
                return float(v_clean)
            except Exception:
                return 0.0
        # Si es otro tipo (por ejemplo, numpy types), intenta forzar a float
        try:
            return float(valor)
        except Exception:
            return 0.0
    except Exception:
        return 0.0

def get_valor_columna(fila, posibles_nombres):
    for nombre in posibles_nombres:
        if nombre in fila.index:
            return procesar_valor(fila[nombre])
    return 0.0

def cargar_excel():
    global compensaciones_df, nomina_desglose_df
    if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
        try:
            with open(ULTIMA_ACTUALIZACION_PATH, 'r', encoding='utf-8') as f:
                archivo = f.read().strip()
                if archivo:
                    excel_path = os.path.join('data', archivo)
                    if os.path.exists(excel_path):
                        compensaciones_df = pd.read_excel(excel_path, sheet_name='BD_COMPENSACIONES').fillna('')
                        nomina_desglose_df = pd.read_excel(excel_path, sheet_name='BD').fillna('')
                        compensaciones_df.columns = compensaciones_df.columns.str.strip()
                        nomina_desglose_df.columns = nomina_desglose_df.columns.str.strip()
        except Exception as e:
            print(f"Error al cargar el Excel: {str(e)}")
cargar_excel()

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
    if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
        with open(ULTIMA_ACTUALIZACION_PATH, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
            if '|' in contenido:
                semana = contenido.split('|')[-1]
            else:
                semana = None
    if not nomina and not nombre:
        return render_template('login_alert.html', error="Por favor, proporciona un número de nómina o un nombre completo para realizar la búsqueda.")
    # Buscar en compensaciones
    datos = None
    if nomina:
        try:
            nomina_int = int(nomina)
            fila = compensaciones_df[compensaciones_df['NOMINA'] == nomina_int]
        except Exception:
            fila = pd.DataFrame()
    elif nombre:
        fila = compensaciones_df[compensaciones_df['NOMBRE'].str.contains(nombre, case=False, na=False)]
    else:
        fila = pd.DataFrame()
    if not fila.empty:
        datos = fila.iloc[0].to_dict()
        # Calcular el total de compensaciones (excluyendo campos no numéricos ni el propio TOTAL)
        total_comp = sum(
            procesar_valor(v) for k, v in datos.items()
            if k not in ['NOMINA', 'NOMBRE', 'TOTAL'] and isinstance(v, (int, float, str)) and str(v).strip() not in ['', 'nan', 'None']
        )
        datos['TOTAL'] = total_comp
    else:
        datos = {'NOMINA': int(nomina) if nomina else None}
    # Buscar en nomina_desglose_df para percepciones y deducciones
    nomina_obj = None
    if nomina:
        try:
            nomina_int = int(nomina)
            fila_desglose = nomina_desglose_df[nomina_desglose_df['clave.'] == nomina_int]
        except Exception:
            fila_desglose = pd.DataFrame()
    elif nombre:
        fila_desglose = nomina_desglose_df[nomina_desglose_df['nombre completo.'].str.contains(nombre, case=False, na=False)]
    else:
        fila_desglose = pd.DataFrame()
    if not fila_desglose.empty:
        fila_desglose = fila_desglose.iloc[0]
        # Debug: mostrar valores crudos de cada columna relevante para la nómina seleccionada
        print('--- VALORES CRUDOS DE LA FILA DE NOMINA ---')
        for col in fila_desglose.index:
            print(f"{col}: {fila_desglose[col]}")
        print('--- VALORES QUE SE ENVIAN AL FRONTEND ---')
        percepciones = {k: get_valor_columna(fila_desglose, v) for k, v in PERCEPCIONES_MAP.items()}
        deducciones = {k: get_valor_columna(fila_desglose, v) for k, v in DEDUCCIONES_MAP.items()}
        for k, v in percepciones.items():
            print(f"Percepcion {k}: {v}")
        for k, v in deducciones.items():
            print(f"Deduccion {k}: {v}")
        print('------------------------------------------')
        total_percepciones = percepciones.get('TOTAL PERCEPCIONES', 0.0)
        total_deducciones = deducciones.get('TOTAL DEDUCCIONES', 0.0)
        neto_a_pagar = deducciones.get('NETO A PAGAR', 0.0)
        nomina_obj = type('Nomina', (), {})()
        nomina_obj.percepciones = percepciones
        nomina_obj.deducciones = deducciones
        nomina_obj.total_percepciones = total_percepciones
        nomina_obj.total_deducciones = total_deducciones
        nomina_obj.neto_a_pagar = neto_a_pagar
    return render_template(
        'compensaciones.html',
        datos=datos,
        semana=semana,
        nomina=nomina_obj,
        now=datetime.now()
    )

@app.route('/modificar', methods=['GET', 'POST'])
def modificar_archivo():
    ultimo_archivo = None
    ultima_semana = None
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
            # Guardar el archivo con nombre único
            unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            # Registrar el último archivo subido junto con la semana
            with open(ULTIMA_ACTUALIZACION_PATH, 'w', encoding='utf-8') as f:
                f.write(f"{unique_filename}|{semana}")
            flash('Archivo actualizado correctamente')
            cargar_excel()
            return redirect(url_for('modificar_archivo'))
    # Mostrar el último archivo y semana
    if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
        try:
            with open(ULTIMA_ACTUALIZACION_PATH, 'r', encoding='utf-8') as f:
                contenido = f.read().strip()
                if '|' in contenido:
                    ultimo_archivo, ultima_semana = contenido.split('|', 1)
                else:
                    ultimo_archivo = contenido
        except Exception:
            pass
    return render_template('modificar.html', ultimo_archivo=ultimo_archivo, ultima_semana=ultima_semana)


@app.route('/compensaciones_json', methods=['POST'])
def compensaciones_json():
    nomina = request.form.get('nomina')
    nombre = request.form.get('nombre')
    semana = None
    if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
        with open(ULTIMA_ACTUALIZACION_PATH, 'r', encoding='utf-8') as f:
            semana = f.read().strip().split('|')[-1] if '|' in f.read() else None
    if not nomina and not nombre:
        return jsonify({"error": "Por favor, proporciona un número de nómina o un nombre completo para realizar la búsqueda."}), 400
    datos = None
    if nomina:
        try:
            nomina_int = int(nomina)
            fila = compensaciones_df[compensaciones_df['NOMINA'] == nomina_int]
        except Exception:
            fila = pd.DataFrame()
    elif nombre:
        fila = compensaciones_df[compensaciones_df['NOMBRE'].str.contains(nombre, case=False, na=False)]
    else:
        fila = pd.DataFrame()
    if not fila.empty:
        datos = fila.iloc[0].to_dict()
        total_comp = sum(
            procesar_valor(v) for k, v in datos.items()
            if k not in ['NOMINA', 'NOMBRE', 'TOTAL'] and isinstance(v, (int, float, str)) and str(v).strip() not in ['', 'nan', 'None']
        )
        datos['TOTAL'] = total_comp
    else:
        datos = {'NOMINA': int(nomina) if nomina else None}
    nomina_obj = None
    if nomina:
        try:
            nomina_int = int(nomina)
            fila_desglose = nomina_desglose_df[nomina_desglose_df['clave.'] == nomina_int]
        except Exception:
            fila_desglose = pd.DataFrame()
    elif nombre:
        fila_desglose = nomina_desglose_df[nomina_desglose_df['nombre completo.'].str.contains(nombre, case=False, na=False)]
    else:
        fila_desglose = pd.DataFrame()
    if not fila_desglose.empty:
        fila_desglose = fila_desglose.iloc[0]
        percepciones = {k: get_valor_columna(fila_desglose, v) for k, v in PERCEPCIONES_MAP.items()}
        deducciones = {k: get_valor_columna(fila_desglose, v) for k, v in DEDUCCIONES_MAP.items()}
        total_percepciones = percepciones.get('TOTAL PERCEPCIONES', 0.0)
        total_deducciones = deducciones.get('TOTAL DEDUCCIONES', 0.0)
        neto_a_pagar = deducciones.get('NETO A PAGAR', 0.0)
        nomina_obj = {
            "percepciones": percepciones,
            "deducciones": deducciones,
            "total_percepciones": total_percepciones,
            "total_deducciones": total_deducciones,
            "neto_a_pagar": neto_a_pagar
        }
    return jsonify({
        "datos": datos,
        "semana": semana,
        "nomina": nomina_obj
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
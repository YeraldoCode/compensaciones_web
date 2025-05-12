from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import pandas as pd
import os

app = Flask(__name__)

# Ruta del archivo Excel
EXCEL_PATH = os.path.join('data', 'Plantilla_compensaciones.xlsx')

UPLOAD_FOLDER = os.path.join('data')
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

    if not nomina and not nombre:
        return "Por favor, proporciona un número de nómina o un nombre completo para realizar la búsqueda.", 400

    # Leer el archivo Excel
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name='COMPENSACIONES')
        df = df.fillna('')

        if nomina:
            try:
                nomina = int(nomina)
                fila = df[df['NOMINA'] == nomina]
            except ValueError:
                return render_template('login_alert.html', error="El número de nómina debe ser un valor numérico.")
        elif nombre:
            fila = df[df['NOMBRE'].str.contains(nombre, case=False, na=False)]

        if fila.empty:
            return "No se encontraron datos para el número de nómina o el nombre proporcionado.", 404

        datos = fila.to_dict(orient='records')[0]

        # Asegurar que la nómina sea un entero
        datos['NOMINA'] = int(datos['NOMINA'])

        # Calcular el total como la suma de los valores numéricos
        total = 0
        for clave, valor in datos.items():
            if isinstance(valor, (int, float)) and clave != 'NOMINA':
                total += valor
                datos[clave] = f"${valor:,.2f}"
        datos['TOTAL'] = f"${total:,.2f}"

    except Exception as e:
        return f"Error al leer el archivo: {str(e)}", 500

    return render_template('compensaciones.html', datos=datos)

@app.route('/modificar', methods=['GET', 'POST'])
def modificar_archivo():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No se seleccionó ningún archivo')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'Plantilla_compensaciones.xlsx'))
            flash('Archivo actualizado correctamente')
            return redirect(url_for('modificar_archivo'))
    return render_template('modificar.html')

if __name__ == '__main__':
    app.run(debug=True)
import sqlite3
import pandas as pd

def cargar_excel_a_bd(excel_path, semana):
    # Leer hojas del Excel
    df_bd = pd.read_excel(excel_path, sheet_name='BD').fillna('')
    df_comp = pd.read_excel(excel_path, sheet_name='BD_COMPENSACIONES').fillna('')
    conn = sqlite3.connect('data/compensaciones.db')
    cursor = conn.cursor()

    # Limpiar datos previos de la semana
    cursor.execute("DELETE FROM BD WHERE semana = ?", (semana,))
    cursor.execute("DELETE FROM BD_COMPENSACIONES WHERE semana = ?", (semana,))

    # Conceptos a mapear (ajusta si necesitas más)
    percepciones = [
        ('SUELDO', 'PERCEPCION'),
        ('VALES DESPENSA', 'PERCEPCION'),
        ('VACACIONES', 'PERCEPCION'),
        ('PRIMA VAC.', 'PERCEPCION'),
        ('SUELDO ADEUDADO', 'PERCEPCION'),
        ('PRIMA DOMINICAL', 'PERCEPCION'),
        ('FEST DESC LABOR', 'PERCEPCION'),
        ('DOMINGO LABORAD', 'PERCEPCION'),
        ('VIAJES ADICIONA.1', 'PERCEPCION'),
        ('SERVICIOS ESPEC', 'PERCEPCION'),
        ('SERVICIOS FIJOS', 'PERCEPCION'),
        ('BONO DE RENDIMI', 'PERCEPCION'),
        ('COMPENSACION', 'PERCEPCION'),
        ('BONO DESEMPEÑO', 'PERCEPCION'),
        ('AYUDA FUNERARIA', 'PERCEPCION'),
        ('AYUDA ESCOLAR', 'PERCEPCION'),
    ]
    deducciones = [
        ('FALTAS', 'DEDUCCION'),
        ('I.S.P.T.', 'DEDUCCION'),
        ('I.M.S.S.', 'DEDUCCION'),
        ('CUOTA SINDICAL', 'DEDUCCION'),
        ('DESC. INFONAVIT', 'DEDUCCION'),
        ('SEG.DAÑOS VIV', 'DEDUCCION'),
        ('DIF. INFONAVIT', 'DEDUCCION'),
        ('PENSION ALIMENT', 'DEDUCCION'),
        ('DESCTO. FONACOT', 'DEDUCCION'),
        ('PRESTAMO PERSON', 'DEDUCCION'),
        ('ANOMALIAS', 'DEDUCCION'),
        ('COMBUSTIBLE', 'DEDUCCION'),
        ('TELEFONIA', 'DEDUCCION'),
        ('SINIESTROS', 'DEDUCCION'),
        ('PRESTAMO DE LIC', 'DEDUCCION'),
        ('DESCUENTO TAXI', 'DEDUCCION'),
        ('REP. TARJETA', 'DEDUCCION'),
    ]

    # Insertar en BD
    for _, row in df_bd.iterrows():
        nomina = row.get('clave.', '')
        nombre = row.get('nombre completo.', '')
        for concepto, tipo in percepciones + deducciones:
            valor = row.get(concepto, 0)
            cursor.execute(
                "INSERT INTO BD (nomina, nombre, concepto, valor, tipo, semana) VALUES (?, ?, ?, ?, ?, ?)",
                (nomina, nombre, concepto, valor, tipo, semana)
            )

    # Insertar en BD_COMPENSACIONES
    for _, row in df_comp.iterrows():
        nomina = row.get('NOMINA', '')
        nombre = row.get('NOMBRE', '')
        for concepto in row.index:
            if concepto not in ['NOMINA', 'NOMBRE']:
                valor = row.get(concepto, 0)
                cursor.execute(
                    "INSERT INTO BD_COMPENSACIONES (nomina, nombre, concepto, valor, semana) VALUES (?, ?, ?, ?, ?)",
                    (nomina, nombre, concepto, valor, semana)
                )
    conn.commit()
    conn.close()
    print('Datos cargados en BD y BD_COMPENSACIONES para la semana', semana)

# Conexión a la base de datos (se crea si no existe)
conn = sqlite3.connect('data/compensaciones.db')
cursor = conn.cursor()

# Tabla BD (nómina, percepciones y deducciones)
cursor.execute('''
CREATE TABLE IF NOT EXISTS BD (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomina INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    concepto TEXT NOT NULL,
    valor REAL NOT NULL,
    tipo TEXT NOT NULL, -- 'PERCEPCION' o 'DEDUCCION'
    semana INTEGER NOT NULL
)
''')

# Tabla BD_COMPENSACIONES
cursor.execute('''
CREATE TABLE IF NOT EXISTS BD_COMPENSACIONES (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomina INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    concepto TEXT NOT NULL,
    valor REAL NOT NULL,
    semana INTEGER NOT NULL
)
''')

conn.commit()
conn.close()
print('Base de datos y tablas BD y BD_COMPENSACIONES creadas correctamente.')

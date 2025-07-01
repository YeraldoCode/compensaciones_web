import pandas as pd
import sys

# Cambia la ruta al archivo Excel y la nómina a consultar
EXCEL_PATH = 'data/20250630_134712_PLANTILLA_DESGLOSE_S26.xlsx'  # O el archivo actual
SHEET_NAME = 'BD'

if len(sys.argv) > 1:
    nomina = sys.argv[1]
else:
    nomina = input('Introduce el número de nómina: ')

# Lee el archivo Excel
df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

# Busca la fila por clave.
fila = df[df['clave.'] == int(nomina)]

if fila.empty:
    print(f'No se encontró la nómina {nomina}')
else:
    fila = fila.iloc[0]
    print(f'--- Todos los datos de la nómina {nomina} ---')
    for col in fila.index:
        print(f'{col}: {fila[col]}')
    print('-------------------------------------------')

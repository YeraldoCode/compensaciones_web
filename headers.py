import pandas as pd

# Ruta del archivo Excel
EXCEL_PATH = 'data/PLANTILLA_DESGLOSE.xlsx'

# Leer las columnas de las hojas BD_COMPENSACIONES y BD
try:
    compensaciones_columns = pd.read_excel(EXCEL_PATH, sheet_name='BD_COMPENSACIONES').columns.tolist()
    desglose_columns = pd.read_excel(EXCEL_PATH, sheet_name='BD').columns.tolist()
    print("Columnas en BD_COMPENSACIONES:", compensaciones_columns)
    print("Columnas en BD:", desglose_columns)
except Exception as e:
    print(f"Error al leer el archivo: {e}")
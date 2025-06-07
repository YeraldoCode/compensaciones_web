import pandas as pd

# Ruta del archivo Excel
EXCEL_PATH = 'data/PLANTILLA_DESGLOSE_SEMANA_22.xlsx'

try:
    # Leer todas las hojas del Excel
    excel_file = pd.ExcelFile(EXCEL_PATH)
    print("\nHojas disponibles:", excel_file.sheet_names)
    
    # Examinar la hoja BD_COMPENSACIONES
    print("\n=== EXAMINANDO HOJA BD_COMPENSACIONES ===")
    df_comp = pd.read_excel(EXCEL_PATH, sheet_name='BD_COMPENSACIONES')
    print("\nColumnas en BD_COMPENSACIONES:")
    print(df_comp.columns.tolist())
    print("\nPrimeras 5 filas de BD_COMPENSACIONES:")
    print(df_comp.head())
    
    # Examinar la hoja BD
    print("\n=== EXAMINANDO HOJA BD ===")
    df_nom = pd.read_excel(EXCEL_PATH, sheet_name='BD')
    print("\nColumnas en BD:")
    print(df_nom.columns.tolist())
    print("\nPrimeras 5 filas de BD:")
    print(df_nom.head())
    
except Exception as e:
    print(f"Error al leer el archivo: {str(e)}") 
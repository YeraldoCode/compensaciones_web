import pandas as pd
import os

# Ruta del archivo de última actualización
ULTIMA_ACTUALIZACION_PATH = 'data/ultima_actualizacion.txt'

# Obtener la semana actual desde el archivo de última actualización
if os.path.exists(ULTIMA_ACTUALIZACION_PATH):
    with open(ULTIMA_ACTUALIZACION_PATH, 'r') as f:
        line = f.read().strip()
        if line:
            partes = line.split('|')
            if len(partes) == 2:
                EXCEL_PATH = f"data/{partes[0]}"
else:
    EXCEL_PATH = 'data/PLANTILLA_DESGLOSE_SEMANA_22.xlsx'

def verificar_excel():
    try:
        print("\n=== VERIFICANDO ARCHIVO EXCEL ===")
        print(f"Archivo: {EXCEL_PATH}")
        
        # Verificar que el archivo existe
        if not os.path.exists(EXCEL_PATH):
            print(f"Error: El archivo {EXCEL_PATH} no existe")
            return
            
        # Leer todas las hojas
        excel_file = pd.ExcelFile(EXCEL_PATH)
        print("\nHojas disponibles:", excel_file.sheet_names)
        
        # Verificar hoja BD_COMPENSACIONES
        print("\n=== HOJA BD_COMPENSACIONES ===")
        df_comp = pd.read_excel(EXCEL_PATH, sheet_name='BD_COMPENSACIONES')
        print("\nColumnas:")
        print(df_comp.columns.tolist())
        print("\nPrimeras 5 filas:")
        print(df_comp.head())
        print("\nTotal de filas:", len(df_comp))
        
        # Verificar hoja BD
        print("\n=== HOJA BD ===")
        df_nom = pd.read_excel(EXCEL_PATH, sheet_name='BD')
        print("\nColumnas:")
        print(df_nom.columns.tolist())
        print("\nPrimeras 5 filas:")
        print(df_nom.head())
        print("\nTotal de filas:", len(df_nom))
        
    except Exception as e:
        print(f"Error al verificar el archivo Excel: {str(e)}")

if __name__ == "__main__":
    verificar_excel()
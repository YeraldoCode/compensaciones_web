import pandas as pd

EXCEL_PATH = "data/PLANTILLA_DESGLOSE.xlsx"  # Ajusta la ruta si es necesario

df = pd.read_excel(EXCEL_PATH, sheet_name="BD")
for idx, col in enumerate(df.columns):
    print(f"{idx}: {col}")
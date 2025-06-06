import pandas as pd
from config import PERCEPCIONES_MAP, DEDUCCIONES_MAP

# Ruta del archivo Excel
EXCEL_PATH = 'data/PLANTILLA_DESGLOSE.xlsx'

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

# Leer la hoja BD
try:
    nomina_desglose_df = pd.read_excel(EXCEL_PATH, sheet_name='BD').fillna('')
    # Filtrar por la nómina específica (puedes cambiar este número)
    nomina_int = 19102470
    fila_desglose = nomina_desglose_df[nomina_desglose_df['clave.'] == nomina_int]
    
    if not fila_desglose.empty:
        fila_desglose = fila_desglose.iloc[0]
        print(f"\nDatos para nómina: {nomina_int}")
        print(f"Nombre: {fila_desglose['nombre completo.']}")
        
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
        neto_a_pagar = procesar_valor(fila_desglose.get('NETO A PAGAR', 0.0))
        if neto_a_pagar == 0.0:
            neto_a_pagar = total_percepciones - total_deducciones

        print("\nPERCEPCIONES:")
        print("-" * 50)
        for concepto, valor in percepciones.items():
            print(f"{concepto:30} ${valor:,.2f}")
        print("-" * 50)
        print(f"TOTAL PERCEPCIONES: ${total_percepciones:,.2f}")

        print("\nDEDUCCIONES:")
        print("-" * 50)
        for concepto, valor in deducciones.items():
            print(f"{concepto:30} ${valor:,.2f}")
        print("-" * 50)
        print(f"TOTAL DEDUCCIONES: ${total_deducciones:,.2f}")
        
        print("\nNETO A PAGAR:")
        print("-" * 50)
        print(f"NETO A PAGAR: ${neto_a_pagar:,.2f}")

        # Mostrar datos originales del Excel
        print("\nDATOS ORIGINALES DEL EXCEL:")
        print("-" * 50)
        for col in fila_desglose.index:
            if col in PERCEPCIONES_MAP or col in DEDUCCIONES_MAP:
                print(f"{col:50} {fila_desglose[col]}")
        
    else:
        print(f"No se encontraron datos para la nómina {nomina_int}.")
except Exception as e:
    print(f"Error al leer el archivo: {e}")
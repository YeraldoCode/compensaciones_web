import pandas as pd
import os
from app import cargar_excel, compensaciones_df, nomina_desglose_df, mapear_percepciones_deducciones_por_indice

# Cargar los DataFrames en memoria
cargar_excel()

nomina = 19108331

# Buscar en compensaciones_df
fila = compensaciones_df[compensaciones_df['NOMINA'] == nomina]
if not fila.empty:
    datos = fila.iloc[0].to_dict()
    print('Datos de BD_COMPENSACIONES:')
    for k, v in datos.items():
        print(f'{k}: {v}')
else:
    print('No se encontró la nómina en BD_COMPENSACIONES')

# Buscar en nomina_desglose_df
fila_desglose = nomina_desglose_df[nomina_desglose_df['clave.'] == nomina]
if not fila_desglose.empty:
    fila_desglose = fila_desglose.iloc[0]
    percepciones, deducciones = mapear_percepciones_deducciones_por_indice(fila_desglose)
    print('\nPercepciones:')
    for k, v in percepciones.items():
        print(f'{k}: {v}')
    print('\nDeducciones:')
    for k, v in deducciones.items():
        print(f'{k}: {v}')
else:
    print('No se encontró la nómina en BD')

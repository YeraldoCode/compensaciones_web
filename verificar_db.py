import sqlite3
import os

# Ruta de la base de datos
DATABASE_PATH = os.path.join('data', 'compensaciones.db')

def verificar_base_datos():
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Verificar tablas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = cursor.fetchall()
        print("\nTablas en la base de datos:")
        for tabla in tablas:
            print(f"- {tabla['name']}")

        # Verificar datos en compensaciones
        print("\n=== DATOS EN COMPENSACIONES ===")
        cursor.execute("SELECT COUNT(*) as total FROM compensaciones")
        total_comp = cursor.fetchone()['total']
        print(f"Total de registros en compensaciones: {total_comp}")

        if total_comp > 0:
            print("\nPrimeros 5 registros de compensaciones:")
            cursor.execute("""
                SELECT nomina, nombre, concepto, valor, semana 
                FROM compensaciones 
                ORDER BY nomina 
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"Nómina: {row['nomina']}, Nombre: {row['nombre']}, Concepto: {row['concepto']}, Valor: {row['valor']}, Semana: {row['semana']}")

        # Verificar datos en nomina
        print("\n=== DATOS EN NÓMINA ===")
        cursor.execute("SELECT COUNT(*) as total FROM nomina")
        total_nom = cursor.fetchone()['total']
        print(f"Total de registros en nómina: {total_nom}")

        if total_nom > 0:
            print("\nPrimeros 5 registros de nómina:")
            cursor.execute("""
                SELECT nomina, nombre, concepto, valor, tipo, semana 
                FROM nomina 
                ORDER BY nomina 
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"Nómina: {row['nomina']}, Nombre: {row['nombre']}, Concepto: {row['concepto']}, Valor: {row['valor']}, Tipo: {row['tipo']}, Semana: {row['semana']}")

        # Verificar semana actual
        print("\n=== SEMANA ACTUAL ===")
        if os.path.exists('data/ultima_actualizacion.txt'):
            with open('data/ultima_actualizacion.txt', 'r') as f:
                contenido = f.read().strip()
                print(f"Contenido del archivo de última actualización: {contenido}")

        conn.close()

    except Exception as e:
        print(f"Error al verificar la base de datos: {str(e)}")

if __name__ == "__main__":
    verificar_base_datos() 
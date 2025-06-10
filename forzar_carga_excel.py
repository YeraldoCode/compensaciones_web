from app import cargar_excel, init_db
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Función principal para forzar la carga de datos"""
    try:
        # Inicializar la base de datos
        init_db()
        logger.info("Base de datos inicializada")

        # Cargar datos del Excel
        cargar_excel()
        logger.info("Datos cargados y base de datos actualizada")
    except Exception as e:
        logger.error(f"Error en el proceso de carga: {str(e)}")

if __name__ == '__main__':
    main()
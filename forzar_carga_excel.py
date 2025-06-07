from app import cargar_datos_excel, init_db
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
        datos = cargar_datos_excel()
        if datos:
            logger.info(f"Datos cargados exitosamente para la semana {datos['semana']}")
            logger.info(f"Compensaciones procesadas: {len(datos['compensaciones'])}")
            logger.info(f"Registros de nómina procesados: {len(datos['nomina'])}")
        else:
            logger.error("Error al cargar los datos del Excel")
    except Exception as e:
        logger.error(f"Error en el proceso de carga: {str(e)}")

if __name__ == '__main__':
    main() 
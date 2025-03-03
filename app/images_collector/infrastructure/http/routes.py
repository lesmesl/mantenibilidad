from fastapi import FastAPI, Depends
import os
from pathlib import Path

from ..settings.config import settings
from .controllers.image_controller import ImageController
from ..messaging.pulsar_publisher import PulsarMessagePublisher


def setup_routes() -> FastAPI:
    """Configura y retorna la aplicación FastAPI con todas las rutas."""
    app = FastAPI(title="Image Collector API", version="0.1.0")
    
    # Asegurar que los directorios necesarios existen
    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Asegurar que el directorio para la base de datos existe
    db_dir = os.path.dirname(settings.sqlite_db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    # Variable para almacenar el publicador en la aplicación
    app.state.message_publisher = None
    
    @app.on_event("startup")
    async def startup_event():
        # Inicializar el publicador de Pulsar si está habilitado
        if settings.pulsar_enabled:
            try:
                from ..messaging.pulsar_publisher import PulsarMessagePublisher
                app.state.message_publisher = PulsarMessagePublisher()
                # Pre-inicializar el cliente para asegurarnos que funciona
                await app.state.message_publisher._get_client()
                print(f"Pulsar publisher initialized. URL: {settings.pulsar_service_url}")
            except Exception as e:
                print(f"Error initializing Pulsar publisher: {e}")
                app.state.message_publisher = None

    @app.on_event("shutdown")
    async def shutdown_event():
        # Cerrar el publicador de Pulsar si está disponible
        if app.state.message_publisher:
            try:
                await app.state.message_publisher.close()
                print("Pulsar publisher closed")
            except Exception as e:
                print(f"Error closing Pulsar publisher: {e}")
    
    # Instancia del controlador
    image_controller = ImageController()
    
    # Registro de rutas para imágenes
    app.post("/images/", tags=["images"])(
        image_controller.collect_image
    )
    app.get("/images/", tags=["images"])(
        image_controller.get_all_images
    )
    app.get("/images/{image_id}", tags=["images"])(
        image_controller.get_image_by_id
    )
    
    # Ruta de salud
    @app.get("/health", tags=["health"])
    async def health_check():
        # Verifica si la base de datos existe
        db_exists = os.path.isfile(settings.sqlite_db_path)
        
        # Verifica estado de Pulsar
        pulsar_status = "enabled" if settings.pulsar_enabled else "disabled"
        
        return {
            "status": "ok", 
            "storage_type": settings.storage_type,
            "db_path": settings.sqlite_db_path,
            "db_exists": db_exists,
            "pulsar": {
                "status": pulsar_status,
                "service_url": settings.pulsar_service_url,
                "topic": settings.pulsar_image_topic
            }
        }
    
    @app.get("/health/pulsar", tags=["health"])
    async def pulsar_health():
        """Verifica la conexión con Pulsar."""
        import socket
        
        # Extraer host y puerto de la URL de Pulsar
        pulsar_url = settings.pulsar_service_url
        if pulsar_url.startswith("pulsar://"):
            pulsar_url = pulsar_url[9:]  # Quitar 'pulsar://'
        
        host, port_str = pulsar_url.split(":")
        port = int(port_str)
        
        # Probar conectividad TCP
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            reachable = result == 0
            sock.close()
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "pulsar_url": settings.pulsar_service_url,
            }
        
        # Si podemos alcanzar Pulsar, intentar crear un cliente
        if reachable and settings.pulsar_enabled:
            try:
                # Intenta crear un cliente Pulsar temporal
                import pulsar
                client = pulsar.Client(settings.pulsar_service_url)
                # Intenta listar los tópicos para verificar que funciona
                admin = pulsar.admin.AdminClient(f"http://{host}:8080")
                topics = []
                try:
                    topics = admin.topics().get_list("public/default")
                except:
                    pass
                client.close()
                
                return {
                    "status": "ok",
                    "reachable": True,
                    "pulsar_url": settings.pulsar_service_url,
                    "topics": topics
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reachable": True,
                    "client_error": str(e),
                    "pulsar_url": settings.pulsar_service_url
                }
        
        return {
            "status": "error" if not reachable else "warning",
            "reachable": reachable,
            "message": "No se pudo conectar a Pulsar" if not reachable else "Pulsar alcanzable pero no probado completamente",
            "pulsar_url": settings.pulsar_service_url
        }

    return app
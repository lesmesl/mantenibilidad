from fastapi import FastAPI
import os
from pathlib import Path

from ..settings.config import settings
from .controllers.image_controller import ImageController


def setup_routes() -> FastAPI:
    """Configura y retorna la aplicación FastAPI con todas las rutas."""
    app = FastAPI(title="Image Collector API", version="0.1.0")
    
    # Asegurar que los directorios necesarios existen
    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Asegurar que el directorio para la base de datos existe
    db_dir = os.path.dirname(settings.sqlite_db_path)
    os.makedirs(db_dir, exist_ok=True)
    
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
        return {
            "status": "ok", 
            "storage_type": settings.storage_type,
            "db_path": settings.sqlite_db_path,
            "db_exists": db_exists
        }
    
    return app
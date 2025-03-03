from fastapi import Depends

from ...application.use_cases.image_collector import ImageCollectorUseCase
from ..repositories.file_image_repository import FileImageRepository
from ..repositories.sqlite_image_repository import SQLiteImageRepository
from ..repositories.postgres_image_repository import PostgresImageRepository
from ..messaging.pulsar_publisher import PulsarMessagePublisher
from ..settings.config import settings

# Instancia singleton para reutilización
_pulsar_publisher = None

def get_image_repository():
    """Proporciona una instancia del repositorio de imágenes según la configuración."""
    if settings.storage_type == "sqlite":
        return SQLiteImageRepository()
    elif settings.storage_type == "postgres":
        return PostgresImageRepository()
    else:
        return FileImageRepository()


async def get_message_publisher():
    """Proporciona una instancia del publicador de mensajes si está habilitado."""
    global _pulsar_publisher
    
    if settings.pulsar_enabled:
        if _pulsar_publisher is None:
            _pulsar_publisher = PulsarMessagePublisher()
            # Pre-inicializar el cliente para evitar problemas
            try:
                client = await _pulsar_publisher._get_client()
                print(f"Cliente Pulsar inicializado: {client}")
            except Exception as e:
                print(f"Error inicializando cliente Pulsar: {e}")
                return None
        return _pulsar_publisher
    return None


async def get_image_use_case(
    repository = Depends(get_image_repository),
    message_publisher = Depends(get_message_publisher)
) -> ImageCollectorUseCase:
    """Proporciona una instancia del caso de uso de imágenes."""
    return ImageCollectorUseCase(repository, message_publisher)
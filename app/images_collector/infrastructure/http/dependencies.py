from fastapi import Depends

from ...application.use_cases.image_collector import ImageCollectorUseCase
from ..repositories.file_image_repository import FileImageRepository
from ..repositories.sqlite_image_repository import SQLiteImageRepository
from ..repositories.postgres_image_repository import PostgresImageRepository
from ..settings.config import settings


def get_image_repository():
    """Proporciona una instancia del repositorio de imágenes según la configuración."""
    if settings.storage_type == "sqlite":
        return SQLiteImageRepository()
    elif settings.storage_type == "postgres":
        return PostgresImageRepository()
    else:
        return FileImageRepository()


def get_image_use_case(
    repository = Depends(get_image_repository)
) -> ImageCollectorUseCase:
    """Proporciona una instancia del caso de uso de imágenes."""
    return ImageCollectorUseCase(repository)
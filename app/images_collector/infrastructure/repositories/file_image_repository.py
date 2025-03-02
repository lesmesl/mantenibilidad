import asyncio
import httpx
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ...domain.models.image import Image
from ...domain.ports.image_repository import ImageRepository
from ..settings.config import settings


class FileImageRepository(ImageRepository):
    """Implementación del repositorio que guarda imágenes en el sistema de archivos."""
    
    def __init__(self):
        self.storage_path = Path(settings.storage_path)
        self._ensure_storage_dir()
        self.images_metadata = {}  # Guarda metadatos en memoria por simplicidad
    
    def _ensure_storage_dir(self):
        """Asegura que el directorio de almacenamiento exista."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save(self, image: Image) -> Image:
        """Descarga y guarda una imagen desde la URL proporcionada."""
        # Generar nombre de archivo si no se proporciona
        file_name = image.file_name or f"{uuid.uuid4()}.jpg"
        file_path = self.storage_path / file_name
        
        # Descargar la imagen
        async with httpx.AsyncClient() as client:
            response = await client.get(image.url)
            response.raise_for_status()
            
            # Obtener el tipo de contenido
            content_type = response.headers.get("content-type", "image/jpeg")
            
            # Guardar la imagen en disco
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Obtener el tamaño del archivo
            size = len(response.content)
        
        # Crear una nueva instancia con los datos actualizados
        saved_image = Image(
            id=image.id,
            url=image.url,
            file_name=file_name,
            content_type=content_type,
            size=size,
            created_at=image.created_at
        )
        
        # Guardar metadatos en memoria
        self.images_metadata[saved_image.id] = saved_image
        
        return saved_image
    
    async def get_by_id(self, image_id: str) -> Optional[Image]:
        """Obtiene una imagen por su ID."""
        return self.images_metadata.get(image_id)
    
    async def get_all(self) -> List[Image]:
        """Obtiene todas las imágenes."""
        return list(self.images_metadata.values())
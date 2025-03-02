from abc import ABC, abstractmethod
from typing import List, Optional

from ..models.image import Image


class ImageRepository(ABC):
    """Puerto para el repositorio de imágenes."""
    
    @abstractmethod
    async def save(self, image: Image) -> Image:
        """Guarda una imagen en el repositorio."""
        pass
    
    @abstractmethod
    async def get_by_id(self, image_id: str) -> Optional[Image]:
        """Obtiene una imagen por su ID."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[Image]:
        """Obtiene todas las imágenes."""
        pass
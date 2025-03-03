import uuid
from typing import List, Optional

from ...domain.models.image import Image
from ...domain.ports.image_repository import ImageRepository
from ...domain.ports.message_publisher import MessagePublisher
from ..dto.image_dto import ImageDTO


class ImageCollectorUseCase:
    """Caso de uso para recolectar imágenes."""
    
    def __init__(
        self, 
        image_repository: ImageRepository, 
        message_publisher: Optional[MessagePublisher] = None
    ):
        self.image_repository = image_repository
        self.message_publisher = message_publisher
    
    async def collect_image(self, image_dto: ImageDTO) -> ImageDTO:
        """Recolecta y almacena una imagen desde la URL proporcionada."""
        # Crear modelo de dominio desde el DTO
        image = Image(
            id=image_dto.id or str(uuid.uuid4()),
            url=str(image_dto.url),
            file_name=image_dto.file_name,
            content_type=image_dto.content_type,
            size=image_dto.size
        )
        
        # Guardar en el repositorio
        saved_image = await self.image_repository.save(image)
        
        # Convertir de nuevo a DTO
        result_dto = ImageDTO(
            id=saved_image.id,
            url=saved_image.url,
            file_name=saved_image.file_name,
            content_type=saved_image.content_type,
            size=saved_image.size,
            created_at=saved_image.created_at
        )
        
        # Publicar evento si hay un publicador disponible
        if self.message_publisher:
            from ...infrastructure.settings.config import settings
            
            # Creamos un payload para el evento
            event_data = {
                "event_type": "image_created",
                "image": {
                    "id": result_dto.id,
                    "url": str(result_dto.url),
                    "file_name": result_dto.file_name,
                    "content_type": result_dto.content_type,
                    "size": result_dto.size,
                    "created_at": result_dto.created_at.isoformat() if result_dto.created_at else None
                }
            }
            
            # Publicar de forma asíncrona
            await self.message_publisher.publish(
                settings.pulsar_image_topic,
                event_data
            )
        
        return result_dto
    
    async def get_all_images(self) -> List[ImageDTO]:
        """Obtiene todas las imágenes almacenadas."""
        images = await self.image_repository.get_all()
        return [
            ImageDTO(
                id=img.id,
                url=img.url,
                file_name=img.file_name,
                content_type=img.content_type,
                size=img.size,
                created_at=img.created_at
            )
            for img in images
        ]
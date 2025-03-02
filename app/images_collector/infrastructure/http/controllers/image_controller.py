from fastapi import Depends, HTTPException, status
from typing import List
import traceback
import sys

from ....application.dto.image_dto import ImageDTO
from ....application.use_cases.image_collector import ImageCollectorUseCase
from ...repositories.sqlite_image_repository import SQLiteImageRepository
from ..dependencies import get_image_use_case


class ImageController:
    """Controlador para los endpoints relacionados con imágenes."""
    
    async def collect_image(
        self,
        image_data: ImageDTO,
        use_case: ImageCollectorUseCase = Depends(get_image_use_case)
    ) -> ImageDTO:
        """
        Recolecta una imagen desde la URL proporcionada.
        """
        try:
            print(f"Procesando imagen desde URL: {image_data.url}")
            return await use_case.collect_image(image_data)
        except Exception as e:
            print(f"Error al procesar la imagen: {e}")
            traceback.print_exc(file=sys.stdout)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al procesar la imagen: {str(e)}"
            )
    
    async def get_all_images(
        self,
        use_case: ImageCollectorUseCase = Depends(get_image_use_case)
    ) -> List[ImageDTO]:
        """
        Obtiene todas las imágenes almacenadas.
        """
        try:
            print("Obteniendo todas las imágenes")
            return await use_case.get_all_images()
        except Exception as e:
            print(f"Error al obtener las imágenes: {e}")
            traceback.print_exc(file=sys.stdout)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener las imágenes: {str(e)}"
            )
    
    async def get_image_by_id(
        self,
        image_id: str,
        use_case: ImageCollectorUseCase = Depends(get_image_use_case)
    ) -> ImageDTO:
        """
        Obtiene una imagen específica por su ID.
        """
        try:
            print(f"Buscando imagen con ID: {image_id}")
            repository = SQLiteImageRepository()
            image = await repository.get_by_id(image_id)
            if not image:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Image with id {image_id} not found"
                )
            
            return ImageDTO(
                id=image.id,
                url=image.url,
                file_name=image.file_name,
                content_type=image.content_type,
                size=image.size,
                created_at=image.created_at
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error al obtener la imagen: {e}")
            traceback.print_exc(file=sys.stdout)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener la imagen: {str(e)}"
            )
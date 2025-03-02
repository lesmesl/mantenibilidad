import asyncio
import grpc
from concurrent import futures
from typing import Optional

from ...application.dto.image_dto import ImageDTO
from ...application.use_cases.image_collector import ImageCollectorUseCase
from ..repositories.file_image_repository import FileImageRepository
from ..repositories.sqlite_image_repository import SQLiteImageRepository
from ..settings.config import settings
from .protos import images_pb2, images_pb2_grpc


class ImageCollectorServicer(images_pb2_grpc.ImageCollectorServicer):
    """Implementación del servicio gRPC para la recolección de imágenes."""
    
    def __init__(self):
        # Seleccionamos el tipo de repositorio según la configuración
        if settings.storage_type == "sqlite":
            self.repository = SQLiteImageRepository()
        else:
            self.repository = FileImageRepository()
        
        self.use_case = ImageCollectorUseCase(self.repository)
    
    async def CollectImage(self, request, context):
        """Recolecta una imagen desde la URL proporcionada."""
        try:
            # Convertir el request a DTO
            image_dto = ImageDTO(
                url=request.url,
                file_name=request.file_name
            )
            
            # Llamar al caso de uso
            result = await self.use_case.collect_image(image_dto)
            
            # Convertir el resultado a response de protobuf
            return images_pb2.ImageResponse(
                id=result.id,
                url=str(result.url),
                file_name=result.file_name,
                content_type=result.content_type,
                size=result.size if result.size else 0,
                created_at=result.created_at.isoformat() if result.created_at else ""
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error procesando imagen: {str(e)}")
            return images_pb2.ImageResponse()
    
    async def GetAllImages(self, request, context):
        """Obtiene todas las imágenes almacenadas."""
        try:
            images = await self.use_case.get_all_images()
            
            # Convertir la lista de DTOs a response de protobuf
            return images_pb2.ImagesResponse(
                images=[
                    images_pb2.ImageResponse(
                        id=img.id,
                        url=str(img.url),
                        file_name=img.file_name,
                        content_type=img.content_type,
                        size=img.size if img.size else 0,
                        created_at=img.created_at.isoformat() if img.created_at else ""
                    )
                    for img in images
                ]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error obteniendo imágenes: {str(e)}")
            return images_pb2.ImagesResponse()
    
    async def GetImageById(self, request, context):
        """Obtiene una imagen específica por su ID."""
        try:
            image = await self.repository.get_by_id(request.id)
            
            if not image:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Image with id {request.id} not found")
                return images_pb2.ImageResponse()
                
            return images_pb2.ImageResponse(
                id=image.id,
                url=str(image.url),
                file_name=image.file_name,
                content_type=image.content_type,
                size=image.size if image.size else 0,
                created_at=image.created_at.isoformat() if image.created_at else ""
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error obteniendo imagen: {str(e)}")
            return images_pb2.ImageResponse()


async def serve():
    """Inicia el servidor gRPC."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    images_pb2_grpc.add_ImageCollectorServicer_to_server(
        ImageCollectorServicer(), server
    )
    server_address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(server_address)
    
    print(f"Starting gRPC server on {server_address}")
    await server.start()
    await server.wait_for_termination()
import grpc
from concurrent import futures
from ...application.dto.image_dto import ImageDTO
from ...application.use_cases.image_collector import ImageCollectorUseCase
from ..repositories.file_image_repository import FileImageRepository
from ..repositories.sqlite_image_repository import SQLiteImageRepository
from ..repositories.postgres_image_repository import PostgresImageRepository
from ..messaging.pulsar_publisher import PulsarMessagePublisher
from ..settings.config import settings
from .protos import images_pb2, images_pb2_grpc


class ImageCollectorServicer(images_pb2_grpc.ImageCollectorServicer):
    """Implementación del servicio gRPC para la recolección de imágenes."""
    
    def __init__(self):
        # Seleccionar el repositorio según la configuración
        if settings.storage_type == "sqlite":
            self.repository = SQLiteImageRepository()
        elif settings.storage_type == "postgres":
            self.repository = PostgresImageRepository()
        else:
            self.repository = FileImageRepository()
        
        # Crear publicador de mensajes si está habilitado
        self.message_publisher = None
        if settings.pulsar_enabled:
            self.message_publisher = PulsarMessagePublisher()
        
        # Crear el caso de uso
        self.use_case = ImageCollectorUseCase(self.repository, self.message_publisher)
        
    async def initialize(self):
        """Inicializa los componentes asíncronos."""
        if self.message_publisher:
            try:
                await self.message_publisher._get_client()
            except Exception as e:
                print(f"Error initializing Pulsar publisher: {e}")
                self.message_publisher = None

    
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
    
    # El resto de los métodos permanecen igual...


async def serve():
    """Inicia el servidor gRPC."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Inicializar el servicio
    servicer = ImageCollectorServicer()
    await servicer.initialize()  # Inicializar componentes asíncronos
    
    images_pb2_grpc.add_ImageCollectorServicer_to_server(servicer, server)
    server_address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(server_address)
    
    print(f"Starting gRPC server on {server_address}")
    
    # Iniciar el servidor
    await server.start()
    
    # Esperar hasta la terminación
    try:
        await server.wait_for_termination()
    finally:
        # Asegurarse de cerrar el cliente de Pulsar al terminar
        if servicer.message_publisher:
            await servicer.message_publisher.close()
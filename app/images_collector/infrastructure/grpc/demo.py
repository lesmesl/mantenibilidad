import asyncio
import grpc

from ..settings.config import settings
from .protos import images_pb2, images_pb2_grpc


async def run_client():
    """Cliente gRPC para pruebas."""
    # Usa localhost en lugar de 0.0.0.0 para conexiones de cliente
    server_address = f"{settings.grpc_host}:{settings.grpc_port}"
    
    print(f"Conectando a servidor gRPC en {server_address}")
    
    async with grpc.aio.insecure_channel(server_address) as channel:
        stub = images_pb2_grpc.ImageCollectorStub(channel)
        
        # Ejemplo: Recolectar una imagen usando una URL que funcione
        request = images_pb2.ImageRequest(
            url="https://httpbin.org/image/jpeg",  # Esta URL devuelve una imagen de ejemplo
            file_name="test_image.jpg"
        )
        
        try:
            print("Enviando solicitud para recolectar imagen...")
            response = await stub.CollectImage(request)
            print(f"Imagen recolectada: {response}")
            
            print("Solicitando lista de imágenes...")
            response = await stub.GetAllImages(images_pb2.EmptyRequest())
            print(f"Imágenes obtenidas: {response}")
            
            if response.images:
                # Intentar obtener la primera imagen por ID
                first_image_id = response.images[0].id
                print(f"Solicitando imagen con ID: {first_image_id}")
                image_response = await stub.GetImageById(
                    images_pb2.ImageIdRequest(id=first_image_id)
                )
                print(f"Imagen obtenida por ID: {image_response}")
        except grpc.aio.AioRpcError as e:
            print(f"Error gRPC: {e.code()}")
            print(f"Detalles: {e.details()}")
        except Exception as e:
            print(f"Error general: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("Cliente detenido")
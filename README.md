# Mantenibilidad Domain-Driven Design y Arquitectura Hexagonal

## Visión General

Este proyecto implementa un microservicio de recolección de imágenes que permite obtener imágenes desde URLs, almacenarlas en disco y registrar sus metadatos en una base de datos SQLite. El sistema está diseñado siguiendo los principios de Domain-Driven Design (DDD) y Arquitectura Hexagonal (también conocida como Ports and Adapters).

## Cumplimiento con Domain-Driven Design (DDD)

La arquitectura DDD se refleja en las siguientes características:

### 1. Modelo de Dominio Claramente Definido

El núcleo del sistema está en el modelo de dominio `Image` en image.py:

```python
@dataclass(frozen=True)
class Image:
    """Entidad principal que representa una imagen."""
    id: str
    url: str
    file_name: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    created_at: datetime = datetime.now()
```

Este modelo encapsula el concepto central del negocio (imágenes) y sus propiedades esenciales como entidad inmutable.

### 2. Lenguaje Ubicuo

El código utiliza un lenguaje consistente y coherente con el dominio del problema:
- `Image` para la entidad principal
- `ImageRepository` para el repositorio
- `ImageCollectorUseCase` para los casos de uso
- `ImageDTO` para transferencia de datos

### 3. Capas Delimitadas

El proyecto separa claramente:
- **Dominio**: Contiene las entidades del negocio y reglas
- **Aplicación**: Orquesta los casos de uso
- **Infraestructura**: Implementa los adaptadores concretos

### 4. Servicios de Dominio

El caso de uso `ImageCollectorUseCase` encapsula la lógica específica del dominio para recopilar y gestionar imágenes.

## Cumplimiento con Arquitectura Hexagonal

### 1. Separación del Núcleo de Negocio de la Infraestructura

El código está estructurado para mantener la lógica de negocio (dominio) completamente independiente de los mecanismos de entrada/salida:

```
app/
├── images_collector/
    ├── domain/          # Núcleo de negocio
    ├── application/     # Casos de uso
    └── infrastructure/  # Adaptadores de entrada/salida
```

### 2. Puertos Claramente Definidos

El proyecto define puertos a través de interfaces abstractas que representan capacidades requeridas por el dominio:

```python
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
```

Este puerto define lo que el dominio necesita sin especificar cómo se implementará.

### 3. Adaptadores

Los adaptadores implementan los puertos definidos:

- **Adaptadores Primarios** (controlados por el usuario):
  - HTTP con FastAPI en http
  - gRPC en grpc

- **Adaptadores Secundarios** (controlados por la aplicación):
  - `SQLiteImageRepository` para persistencia de datos
  - `FileImageRepository` como alternativa

### 4. Inyección de Dependencias

El sistema utiliza inyección de dependencias para desacoplar componentes:

```python
def get_image_use_case(
    repository = Depends(get_image_repository)
) -> ImageCollectorUseCase:
    """Proporciona una instancia del caso de uso de imágenes."""
    return ImageCollectorUseCase(repository)
```

Esto permite que la aplicación funcione sin conocer las implementaciones concretas.

## Funcionamiento del Código

### Flujo de Ejecución Principal

1. **Punto de Entrada**: main.py permite elegir entre servidor HTTP o gRPC:
   ```python
   if args.mode == "http":
       asyncio.run(start_http_server())
   else:
       asyncio.run(start_grpc_server())
   ```

2. **Recepción de Solicitudes**: 
   - HTTP a través de FastAPI
   - gRPC mediante servicios definidos en protobuf

3. **Procesamiento**:
   - Las solicitudes son transformadas a DTOs
   - Se invocan los casos de uso apropiados
   - Los casos de uso utilizan el modelo de dominio

4. **Persistencia**:
   - Se guarda la imagen en disco
   - Se registran los metadatos en SQLite

### Funcionamiento de gRPC

El sistema gRPC funciona mediante:

1. **Definición de Protobuf**: 
   En `images.proto` se definen los servicios y mensajes:
   ```protobuf
   service ImageCollector {
     rpc CollectImage (ImageRequest) returns (ImageResponse);
     rpc GetAllImages (EmptyRequest) returns (ImagesResponse);
     rpc GetImageById (ImageIdRequest) returns (ImageResponse);
   }
   ```

2. **Servicer de gRPC**: 
   La clase `ImageCollectorServicer` implementa estos servicios:
   ```python
   class ImageCollectorServicer(images_pb2_grpc.ImageCollectorServicer):
       def __init__(self):
           if settings.storage_type == "sqlite":
               self.repository = SQLiteImageRepository()
           else:
               self.repository = FileImageRepository()
           self.use_case = ImageCollectorUseCase(self.repository)
   ```

3. **Cliente gRPC**: 
   En `client.py` se implementa un cliente para pruebas:
   ```python
   async with grpc.aio.insecure_channel(server_address) as channel:
       stub = images_pb2_grpc.ImageCollectorStub(channel)
       # Envío de solicitudes al servidor
   ```

4. **Flujo de Comunicación**:
   - El cliente envía mensajes protobuf al servidor
   - El servidor deserializa, procesa mediante casos de uso y responde
   - La comunicación es asíncrona usando `grpc.aio`

## Ventajas de la Arquitectura Implementada

1. **Independencia tecnológica**: Se puede cambiar entre HTTP y gRPC sin modificar la lógica de negocio.

2. **Facilidad de pruebas**: Los componentes están desacoplados, lo que facilita las pruebas unitarias.

3. **Flexibilidad de almacenamiento**: Se puede cambiar entre almacenamiento en archivo y SQLite sin afectar las capas superiores.

4. **Mantenibilidad**: El código está organizado por responsabilidad, haciendo más fácil entenderlo y modificarlo.

5. **Escalabilidad**: La arquitectura permite añadir nuevos adaptadores (como nuevos protocolos o fuentes de datos) sin modificar el núcleo.

## Conclusión

El proyecto implementa exitosamente los principios de DDD y Arquitectura Hexagonal. La separación clara entre el dominio de negocio y los detalles de implementación hace que el sistema sea flexible, mantenible y adaptable a cambios tecnológicos futuros. El uso de gRPC como protocolo alternativo a HTTP demuestra cómo los adaptadores pueden ser intercambiados sin afectar la lógica central del sistema.
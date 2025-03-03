import asyncio
import json
import pulsar
from typing import Any, Dict, Optional

from ...domain.ports.message_publisher import MessagePublisher
from ..settings.config import settings


class PulsarMessagePublisher(MessagePublisher):
    """Implementación de publicación de mensajes usando Apache Pulsar."""
    
    def __init__(self):
        self._client = None
        self._producers = {}
        self._connection_lock = asyncio.Lock()
        self._max_retries = 3
        self._retry_delay = 1.0  # segundos
    
    def _get_running_loop(self):
        """Obtiene el bucle de eventos actual o crea uno nuevo si no existe."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    async def _get_client(self):
        """Obtiene o crea un cliente Pulsar con un mecanismo de bloqueo para evitar conexiones múltiples."""
        # Usar un lock para prevenir múltiples conexiones simultáneas
        async with self._connection_lock:
            if self._client is None:
                try:
                    # Configuración del cliente sin el parámetro incompatible
                    self._client = pulsar.Client(
                        settings.pulsar_service_url,
                        operation_timeout_seconds=5,
                        # Eliminar: connection_timeout_seconds=5
                        io_threads=2,
                        message_listener_threads=1
                    )
                    print(f"Cliente Pulsar creado y conectado a {settings.pulsar_service_url}")
                except Exception as e:
                    print(f"Error al crear cliente Pulsar: {e}")
                    self._client = None
                    raise
        return self._client
    
    async def _get_producer(self, topic: str):
        """Obtiene o crea un productor para un tópico específico con configuración optimizada."""
        if topic not in self._producers:
            try:
                client = await self._get_client()
                
                # Crear productor directamente (sin asyncio.run_in_executor)
                # Esto previene problemas de bloqueo y mejora la fiabilidad
                self._producers[topic] = client.create_producer(
                    topic,
                    schema=pulsar.schema.BytesSchema(),
                    send_timeout_millis=3000,           # Timeout más corto para detectar errores rápido
                    block_if_queue_full=False,          # No bloquear para evitar deadlocks
                    batching_enabled=True,              # Habilitar batching para mejor throughput
                    batching_max_publish_delay_ms=10,   # Delay corto para envío rápido
                    max_pending_messages=1000,          # Limitar mensajes pendientes
                    max_pending_messages_across_partitions=50000
                )
                print(f"Productor creado para topic: {topic}")
            except Exception as e:
                print(f"Error al crear productor para {topic}: {e}")
                if topic in self._producers:
                    del self._producers[topic]
                raise
                
        return self._producers[topic]
    
    async def publish(self, topic: str, message: Any) -> bool:
        """Publica un mensaje en un tópico de Pulsar con reintentos limitados."""
        retries = 0
        last_exception = None
        
        while retries <= self._max_retries:
            try:
                # Preparar los datos
                if isinstance(message, dict):
                    data_to_send = message
                elif hasattr(message, "to_dict") and callable(message.to_dict):
                    data_to_send = message.to_dict()
                elif hasattr(message, "model_dump") and callable(message.model_dump):
                    data_to_send = message.model_dump()
                else:
                    data_to_send = dict(message)
                
                # Serializar a JSON
                json_bytes = json.dumps(data_to_send).encode('utf-8')
                
                # Obtener productor (o crear uno nuevo)
                producer = await self._get_producer(topic)
                
                # Enviar mensaje de forma síncrona con timeout
                # Esto garantiza confirmación inmediata o error rápido
                producer.send(json_bytes)
                
                print(f"Mensaje publicado en {topic}: {json.dumps(data_to_send)[:100]}...")
                return True
                
            except pulsar.ConnectError as e:
                # Error de conexión, intentar reconectar
                print(f"Error de conexión al publicar en {topic} (intento {retries+1}/{self._max_retries+1}): {e}")
                last_exception = e
                
                # Cerrar cliente para forzar reconexión
                await self._reset_connection()
                
            except Exception as e:
                # Otros errores (problema con el broker)
                print(f"Error publicando mensaje en {topic} (intento {retries+1}/{self._max_retries+1}): {e}")
                print(f"Detalles: {type(e).__name__}")
                
                # Si el error es de Bookkeeper, puede ser problema del broker
                if "bookies" in str(e).lower() or "ManagedLedgerException" in str(e):
                    print("Error de BookKeeper detectado, esperando a que el broker se estabilice")
                    # Esperar más tiempo para permitir que el sistema se recupere
                    await asyncio.sleep(self._retry_delay * 2)
                    await self._reset_connection()
                
                last_exception = e
            
            # Incrementar contador de reintentos y esperar antes de reintentar
            retries += 1
            if retries <= self._max_retries:
                await asyncio.sleep(self._retry_delay)
        
        # Si llegamos aquí, todos los reintentos han fallado
        print(f"Fallaron todos los intentos de publicar en {topic}. Último error: {last_exception}")
        return False
    
    async def _reset_connection(self):
        """Reinicia la conexión cerrando el cliente y productores."""
        async with self._connection_lock:
            # Cerrar productores
            for topic, producer in self._producers.items():
                try:
                    producer.close()
                except:
                    pass  # Ignorar errores al cerrar
            
            # Cerrar cliente
            if self._client:
                try:
                    self._client.close()
                except:
                    pass  # Ignorar errores al cerrar
            
            # Resetear variables
            self._producers = {}
            self._client = None
    
    async def close(self) -> None:
        """Cierra todos los productores y el cliente."""
        await self._reset_connection()
        print("Cliente y productores de Pulsar cerrados correctamente")
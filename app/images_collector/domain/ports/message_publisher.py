from abc import ABC, abstractmethod
from typing import Any


class MessagePublisher(ABC):
    """Puerto para publicar mensajes."""
    
    @abstractmethod
    async def publish(self, topic: str, message: Any) -> bool:
        """
        Publica un mensaje en el tópico especificado.
        
        Args:
            topic: El tópico donde publicar el mensaje
            message: El contenido del mensaje a publicar
            
        Returns:
            bool: True si el mensaje fue publicado correctamente, False en caso contrario
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Cierra las conexiones del publicador."""
        pass
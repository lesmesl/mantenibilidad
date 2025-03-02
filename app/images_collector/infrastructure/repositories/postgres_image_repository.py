import asyncpg
import httpx
import uuid
from pathlib import Path
from typing import List, Optional

from ...domain.models.image import Image
from ...domain.ports.image_repository import ImageRepository
from ..settings.config import settings


class PostgresImageRepository(ImageRepository):
    """Implementación del repositorio que guarda imágenes usando PostgreSQL."""
    
    def __init__(self):
        self.storage_path = Path(settings.storage_path)
        self._ensure_storage_dir()
        self._pool = None
        print(f"Nuevo repositorio PostgreSQL creado: {id(self)}")
    
    def _ensure_storage_dir(self):
        """Asegura que el directorio de almacenamiento exista."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def _get_pool(self):
        """Obtiene o crea el pool de conexiones."""
        if self._pool is None:
            # Crear el pool de conexiones
            self._pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db
            )
            
            # Inicializar la tabla si no existe
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS images (
                        id TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        file_name TEXT,
                        content_type TEXT,
                        size INTEGER,
                        created_at TIMESTAMP WITH TIME ZONE,
                        file_path TEXT
                    )
                """)
        
        return self._pool
    
    async def _get_connection(self):
        """Obtiene una conexión del pool y la registra."""
        pool = await self._get_pool()
        connection = await pool.acquire()
        conn_id = id(connection)
        return connection, conn_id
    
    async def save(self, image: Image) -> Image:
        """Descarga y guarda una imagen desde la URL proporcionada."""
        try:
            # Generar nombre de archivo si no se proporciona
            file_name = image.file_name or f"{uuid.uuid4()}.jpg"
            file_path = str(self.storage_path / file_name)
            
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
            
            # Guardar en la base de datos
            conn, conn_id = await self._get_connection()

            await conn.execute("""
                INSERT INTO images (id, url, file_name, content_type, size, created_at, file_path)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE 
                SET url = $2, file_name = $3, content_type = $4, size = $5, created_at = $6, file_path = $7
            """, 
                saved_image.id,
                saved_image.url,
                saved_image.file_name,
                saved_image.content_type,
                saved_image.size,
                saved_image.created_at,
                file_path
            )
            
            print(f"Imagen guardada en PostgreSQL: {saved_image.id}")
            return saved_image
            
        except Exception as e:
            print(f"Error guardando imagen en PostgreSQL: {e}")
            raise
    
    async def get_by_id(self, image_id: str) -> Optional[Image]:
        """Obtiene una imagen por su ID."""
        try:
            conn, conn_id = await self._get_connection()
            row = await conn.fetchrow("SELECT * FROM images WHERE id = $1", image_id)
            
            if not row:
                return None
            
            return Image(
                id=row['id'],
                url=row['url'],
                file_name=row['file_name'],
                content_type=row['content_type'],
                size=row['size'],
                created_at=row['created_at']
            )
        except Exception as e:
            print(f"Error obteniendo imagen por ID desde PostgreSQL: {e}")
            raise
    
    async def get_all(self) -> List[Image]:
        """Obtiene todas las imágenes."""
        try:
            conn, conn_id = await self._get_connection()
            rows = await conn.fetch("SELECT * FROM images ORDER BY created_at DESC")
            
            return [
                Image(
                    id=row['id'],
                    url=row['url'],
                    file_name=row['file_name'],
                    content_type=row['content_type'],
                    size=row['size'],
                    created_at=row['created_at']
                )
                for row in rows
            ]
        except Exception as e:
            print(f"Error obteniendo todas las imágenes desde PostgreSQL: {e}")
            raise

    async def close(self):
        """Cierra el pool de conexiones."""
        if self._pool:
            await self._pool.close()
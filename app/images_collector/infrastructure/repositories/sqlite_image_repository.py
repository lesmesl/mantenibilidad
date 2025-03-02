import aiosqlite
import httpx
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import contextlib

from ...domain.models.image import Image
from ...domain.ports.image_repository import ImageRepository
from ..settings.config import settings

class SQLiteImageRepository(ImageRepository):
    """Implementación del repositorio que guarda imágenes en SQLite."""
    
    def __init__(self):
        self.db_path = settings.sqlite_db_path
        self.storage_path = Path(settings.storage_path)
        self._ensure_storage_dir()
        self._init_db_sync()
        print(f"Nuevo repositorio SQLite creado: {id(self)}")
        
    @contextlib.asynccontextmanager
    async def _get_db_connection(self):
        """Obtiene una conexión a la base de datos y la registra."""
        connection = await aiosqlite.connect(self.db_path)
        connection.row_factory = aiosqlite.Row
        conn_id = id(connection)
        
        try:
            yield connection
        finally:
            await connection.close()
    
    def _ensure_storage_dir(self):
        """Asegura que el directorio de almacenamiento exista."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_db_sync(self):
        """Inicializa la base de datos de forma síncrona."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    file_name TEXT,
                    content_type TEXT,
                    size INTEGER,
                    created_at TEXT,
                    file_path TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()
        
        print(f"Base de datos SQLite inicializada en: {self.db_path}")
    
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
            
            # Guardar en la base de datos usando el connection manager
            async with self._get_db_connection() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO images (id, url, file_name, content_type, size, created_at, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        saved_image.id,
                        saved_image.url,
                        saved_image.file_name,
                        saved_image.content_type,
                        saved_image.size,
                        saved_image.created_at.isoformat(),
                        file_path
                    )
                )
                await db.commit()
            
            print(f"Imagen guardada: {saved_image.id}")
            return saved_image
            
        except Exception as e:
            print(f"Error guardando imagen: {e}")
            raise
    
    async def get_by_id(self, image_id: str) -> Optional[Image]:
        """Obtiene una imagen por su ID."""
        try:
            async with self._get_db_connection() as db:
                cursor = await db.execute("SELECT * FROM images WHERE id = ?", (image_id,))
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return Image(
                    id=row['id'],
                    url=row['url'],
                    file_name=row['file_name'],
                    content_type=row['content_type'],
                    size=row['size'],
                    created_at=datetime.fromisoformat(row['created_at'])
                )
        except Exception as e:
            print(f"Error obteniendo imagen por ID: {e}")
            raise
    
    async def get_all(self) -> List[Image]:
        """Obtiene todas las imágenes."""
        try:
            async with self._get_db_connection() as db:
                cursor = await db.execute("SELECT * FROM images ORDER BY created_at DESC")
                rows = await cursor.fetchall()
                
                return [
                    Image(
                        id=row['id'],
                        url=row['url'],
                        file_name=row['file_name'],
                        content_type=row['content_type'],
                        size=row['size'],
                        created_at=datetime.fromisoformat(row['created_at'])
                    )
                    for row in rows
                ]
        except Exception as e:
            print(f"Error obteniendo todas las imágenes: {e}")
            raise
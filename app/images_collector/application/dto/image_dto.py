from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class ImageDTO(BaseModel):
    """DTO para transferir datos de imágenes."""
    id: Optional[str] = None
    url: HttpUrl
    file_name: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    created_at: Optional[datetime] = None
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Image:
    """Entidad principal que representa una imagen."""
    id: str
    url: str
    file_name: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    created_at: datetime = datetime.now()
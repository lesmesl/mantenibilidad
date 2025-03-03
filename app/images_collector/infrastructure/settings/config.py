import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Configuraciones de la aplicación."""
    app_name: str = "Image Collector Service"
    debug: bool = False
    
    # HTTP Settings
    http_port: int = 8000
    http_host: str = "0.0.0.0"
    
    # GRPC Settings
    grpc_port: int = 8001
    grpc_host: str = "127.0.0.1"
    
    # Storage Settings
    storage_type: Literal["file", "sqlite", "postgres"] = "sqlite"
    storage_path: str = "./storage"
    
    # SQLite Settings
    sqlite_db_path: str = "./storage/images.db"
    
    # PostgreSQL Settings
    postgres_host: str = "localhost"
    postgres_port: int = 5450
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "images_db"
    
    # Pulsar Settings
    pulsar_service_url: str = "pulsar://localhost:6650"
    pulsar_enabled: bool = True
    pulsar_image_topic: str = "persistent://public/default/eventos-suscripcion"
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Convertir rutas relativas a absolutas
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        
        if not os.path.isabs(self.storage_path):
            self.storage_path = os.path.join(base_dir, self.storage_path)
        
        if not os.path.isabs(self.sqlite_db_path):
            self.sqlite_db_path = os.path.join(base_dir, self.sqlite_db_path)


settings = Settings()
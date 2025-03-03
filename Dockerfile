FROM python:3.12-slim

WORKDIR /app

# Instalar Poetry
RUN pip install poetry==1.8.2

# Copiar archivos de proyecto
COPY pyproject.toml poetry.lock ./

# Configurar Poetry para que no use entorno virtual
RUN poetry config virtualenvs.create false

# Instalar dependencias
RUN poetry install --no-interaction --no-ansi --no-dev

# Copiar código fuente
COPY . .

# Crear directorio para almacenar imágenes
RUN mkdir -p ./storage

# Puerto para HTTP y gRPC
EXPOSE 8000 8001

# Comando por defecto (se sobreescribe en docker-compose)
CMD ["python", "-m", "app.main"]
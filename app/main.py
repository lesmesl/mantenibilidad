"""
Punto de entrada principal de la aplicación. 
Permite seleccionar entre infraestructura HTTP o gRPC sin modificar
el servicio ni el dominio.
"""
import argparse
import asyncio
import sys

from app.images_collector.infrastructure.settings.config import settings


async def start_http_server():
    # Importación condicional para no cargar módulos innecesarios
    from app.images_collector.infrastructure.http.routes import setup_routes
    import uvicorn
    
    app = setup_routes()
    config = uvicorn.Config(
        app=app,
        host=settings.http_host,
        port=settings.http_port,
        reload=settings.debug
    )
    server = uvicorn.Server(config)
    await server.serve()


async def start_grpc_server():
    # Importación condicional para no cargar módulos innecesarios
    from app.images_collector.infrastructure.grpc.server import serve
    await serve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image Collector Service")
    parser.add_argument(
        "--mode", 
        choices=["http", "grpc"], 
        default="http",
        help="Execution mode: http for REST API, grpc for gRPC server"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "http":
            asyncio.run(start_http_server())
        else:
            asyncio.run(start_grpc_server())
    except KeyboardInterrupt:
        print("Service stopped")
        sys.exit(0)
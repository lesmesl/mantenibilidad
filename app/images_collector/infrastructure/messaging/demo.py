import asyncio
import json
import pulsar
import sys
import os

# Configuración de Pulsar
PULSAR_URL = os.environ.get("PULSAR_SERVICE_URL", "pulsar://localhost:6650")
TOPIC = "persistent://public/default/eventos-suscripcion"
SUBSCRIPTION = "test-subscription"

async def run_consumer():
    print(f"Conectando a Pulsar: {PULSAR_URL}")
    print(f"Escuchando en tópico: {TOPIC}")
    
    # Crear cliente y consumidor
    client = pulsar.Client(PULSAR_URL)
    
    # Si usas StringSchema:
    consumer = client.subscribe(
        TOPIC,
        subscription_name=SUBSCRIPTION,
        consumer_type=pulsar.ConsumerType.Shared,
        schema=pulsar.schema.StringSchema()  # Debe coincidir con el productor
    )
    
    # Si usas BytesSchema:
    # consumer = client.subscribe(
    #     TOPIC,
    #     subscription_name=SUBSCRIPTION,
    #     consumer_type=pulsar.ConsumerType.Shared,
    #     schema=pulsar.schema.BytesSchema()
    # )
    
    print("Consumidor iniciado. Esperando mensajes...")
    
    try:
        while True:
            try:
                # Recibir mensaje con timeout
                msg = consumer.receive(timeout_millis=5000)
                
                try:
                    # Decodificar payload según el esquema
                    
                    # Para StringSchema:
                    data_str = msg.value()  # Ya es un string
                    data = json.loads(data_str)
                    
                    # Para BytesSchema:
                    # data_bytes = msg.value()
                    # data = json.loads(data_bytes.decode('utf-8'))
                    
                    # Para JsonSchema con GenericMessage:
                    # generic_msg = msg.value()
                    # data = json.loads(generic_msg.data)
                    
                    print("\n--- Mensaje recibido ---")
                    print(f"ID: {msg.message_id()}")
                    print(f"Contenido: {json.dumps(data, indent=2)}")
                    print("------------------------")
                    
                    # Confirmar procesamiento
                    consumer.acknowledge(msg)
                except Exception as e:
                    print(f"Error procesando mensaje: {e}")
                    consumer.negative_acknowledge(msg)
                    
            except pulsar.exceptions.Timeout:
                print(".", end="", flush=True)  # Punto para indicar espera
                continue
                
    except KeyboardInterrupt:
        print("\nDeteniendo consumidor...")
    except Exception as e:
        print(f"Error general: {e}")
    finally:
        # Cerrar recursos
        consumer.close()
        client.close()
        print("Consumidor cerrado")

if __name__ == "__main__":
    try:
        asyncio.run(run_consumer())
    except KeyboardInterrupt:
        print("Consumidor detenido por el usuario")
        sys.exit(0)
import pulsar
import json
import time
import os

# Configuración
service_url = os.environ.get("PULSAR_SERVICE_URL", "pulsar://broker:6650")
topic = "persistent://public/default/eventos-suscripcion"

print(f"Conectando a Pulsar en {service_url}...")
client = pulsar.Client(service_url)

# Crear productor
producer = client.create_producer(topic)
print("✅ Productor creado correctamente")

# Enviar 5 mensajes
for i in range(5):
    mensaje = {"mensaje": f"Prueba #{i}", "timestamp": time.time()}
    producer.send(json.dumps(mensaje).encode('utf-8'))
    print(f"✅ Mensaje enviado: {mensaje}")
    time.sleep(1)

producer.close()

# Crear consumidor
consumer = client.subscribe(
    topic,
    "test-subscription",
    consumer_type=pulsar.ConsumerType.Shared
)
print("✅ Consumidor creado correctamente")

# Recibir mensajes
print("\n📨 Recibiendo mensajes:")
for i in range(5):
    try:
        msg = consumer.receive(timeout_millis=5000)
        data = json.loads(msg.data().decode('utf-8'))
        print(f"📩 Recibido: {data}")
        consumer.acknowledge(msg)
    except pulsar.Timeout:
        print("⚠️ Timeout esperando mensajes")
        break

consumer.close()
client.close()
print("✅ Prueba completada")
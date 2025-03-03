#!/usr/bin/env python3
import pulsar
import json
import sys
import time
import os
import requests

def create_topic(admin_url, topic_path):
    """Crea un tópico usando la API REST de Pulsar Admin."""
    print(f"Intentando crear tópico {topic_path} vía API Admin...")
    
    try:
        # Verificar si el tópico ya existe (no particionado)
        response = requests.get(f"{admin_url}/admin/v2/persistent/{topic_path}/stats")
        if response.status_code == 200:
            print(f"✅ El tópico {topic_path} ya existe.")
            return True
        
        # Verificar si existe como tópico particionado
        partition_check = requests.get(f"{admin_url}/admin/v2/persistent/{topic_path}/partitions")
        if partition_check.status_code == 200:
            print(f"✅ El tópico particionado {topic_path} ya existe.")
            return True
            
        # Primero intentar crear el namespace si no existe
        namespace = topic_path.split('/')[0] + '/' + topic_path.split('/')[1]
        ensure_namespace(admin_url, namespace)
        
        # Crear el tópico no particionado
        print(f"Creando tópico no particionado: {topic_path}")
        response = requests.put(f"{admin_url}/admin/v2/persistent/{topic_path}")
        if response.status_code == 204 or response.status_code == 200:
            print(f"✅ Tópico {topic_path} creado correctamente")
            return True
        elif response.status_code == 409:
            print(f"ℹ️ El tópico {topic_path} ya existe (código 409)")
            return True
        else:
            print(f"❌ Error al crear tópico: Código HTTP {response.status_code}")
            print(f"Respuesta: {response.text}")
            
            # Probar un enfoque alternativo usando CLI interna del broker
            print("Intentando crear tópico vía comando admin interno...")
            try:
                import subprocess
                # Este comando debe ejecutarse dentro del contenedor del broker
                cmd = [
                    "docker", "exec", "broker", 
                    "bin/pulsar-admin", "topics", "create", 
                    f"persistent://{topic_path}"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ Tópico creado correctamente via CLI")
                    return True
                else:
                    print(f"❌ Error al crear tópico vía CLI: {result.stderr}")
            except Exception as cli_error:
                print(f"❌ Error al ejecutar CLI: {cli_error}")
            
            return False
    except Exception as e:
        print(f"❌ Error al comunicarse con la API Admin: {e}")
        return False

def ensure_namespace(admin_url, namespace):
    """Asegura que el namespace exista."""
    try:
        # Verificar si el namespace existe
        ns_response = requests.get(f"{admin_url}/admin/v2/namespaces/{namespace}")
        if ns_response.status_code == 200:
            print(f"✅ Namespace {namespace} ya existe")
            return True
            
        # Si no existe, crearlo
        create_ns_response = requests.put(f"{admin_url}/admin/v2/namespaces/{namespace}")
        if create_ns_response.status_code == 204 or create_ns_response.status_code == 200:
            print(f"✅ Namespace {namespace} creado correctamente")
            
            # Configurar retención
            set_retention_policy(admin_url, namespace)
            return True
        else:
            print(f"❌ Error al crear namespace: Código HTTP {create_ns_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error al verificar namespace: {e}")
        return False

def create_topic_via_cli(topic_path):
    """Crea un tópico usando la CLI de Pulsar."""
    try:
        import subprocess
        print(f"Intentando crear tópico {topic_path} vía CLI...")
        
        # Este comando debe ejecutarse desde el host donde se ejecuta este script
        cmd = [
            "docker", "exec", "broker", 
            "bin/pulsar-admin", "topics", "create", 
            f"persistent://{topic_path}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Tópico {topic_path} creado correctamente via CLI")
            return True
        else:
            if "409 Conflict" in result.stderr:
                print(f"ℹ️ El tópico {topic_path} ya existe (CLI reportó conflicto)")
                return True
            else:
                print(f"❌ Error al crear tópico vía CLI: {result.stderr}")
                return False
    except Exception as e:
        print(f"❌ Error al ejecutar comando CLI: {e}")
        return False
    
def set_retention_policy(admin_url, namespace):
    """Configura la política de retención para el namespace."""
    try:
        print(f"Configurando política de retención para {namespace}...")
        response = requests.post(
            f"{admin_url}/admin/v2/namespaces/{namespace}/retention",
            json={"retentionTimeInMinutes": 60, "retentionSizeInMB": 512}
        )
        if response.status_code == 204 or response.status_code == 200:
            print(f"✅ Política de retención configurada correctamente")
            return True
        else:
            print(f"⚠️ No se pudo configurar la política de retención: Código HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error al configurar política de retención: {e}")
        return False

def verify_pulsar():
    """Verifica la disponibilidad del broker Pulsar y el tópico."""
    # Configuración
    service_url = os.environ.get("PULSAR_SERVICE_URL", "pulsar://broker:6650")
    admin_url = os.environ.get("PULSAR_ADMIN_URL", "http://broker:8080")
    topic = "persistent://public/default/eventos-suscripcion"
    topic_path = "public/default/eventos-suscripcion"
    namespace = "public/default"
    
    print(f"Verificando conexión a {service_url}...")
    print(f"URL Admin: {admin_url}")
    
    # Verificar si el broker está disponible
    try:
        cluster_response = requests.get(f"{admin_url}/admin/v2/clusters/cluster-a", timeout=5)
        if cluster_response.status_code == 200:
            print("✅ Broker Admin API está disponible")
        else:
            print(f"⚠️ Broker Admin API respondió con código: {cluster_response.status_code}")
    except Exception as e:
        print(f"❌ Error al conectar con Broker Admin API: {e}")
        print("Esperando 5 segundos antes de continuar...")
        time.sleep(5)
    
    # Asegurar que el namespace existe
    try:
        ns_response = requests.get(f"{admin_url}/admin/v2/namespaces/public")
        if ns_response.status_code == 200:
            namespaces = ns_response.json()
            if namespace in namespaces:
                print(f"✅ Namespace {namespace} existe")
            else:
                print(f"⚠️ Namespace {namespace} no encontrado, creándolo...")
                create_ns_response = requests.put(f"{admin_url}/admin/v2/namespaces/{namespace}")
                if create_ns_response.status_code == 204 or create_ns_response.status_code == 200:
                    print(f"✅ Namespace {namespace} creado correctamente")
                    # Configurar retención
                    set_retention_policy(admin_url, namespace)
                else:
                    print(f"❌ Error al crear namespace: Código HTTP {create_ns_response.status_code}")
    except Exception as e:
        print(f"❌ Error al verificar namespace: {e}")
    
    # Crear el tópico si no existe
    create_topic(admin_url, topic_path)
    
    # Verificar conexión mediante cliente Pulsar
    try:
        # Crear cliente
        client = pulsar.Client(service_url)
        print("✅ Cliente creado correctamente")
        
        # Verificar si podemos producir mensajes
        try:
            producer = client.create_producer(topic)
            print("✅ Productor creado correctamente")
            
            # Enviar un mensaje de prueba
            test_msg = {"test": "verification", "timestamp": time.time()}
            producer.send(json.dumps(test_msg).encode('utf-8'))
            print("✅ Mensaje de prueba enviado correctamente")
            
            producer.close()
        except Exception as e:
            print(f"❌ Error al crear productor o enviar mensaje: {e}")
            
        # Verificar si podemos consumir mensajes
        try:
            consumer = client.subscribe(
                topic,
                "verification-consumer",
                consumer_type=pulsar.ConsumerType.Shared
            )
            print("✅ Consumidor creado correctamente")
            
            # Intentar recibir un mensaje con timeout
            try:
                msg = consumer.receive(timeout_millis=5000)
                print(f"✅ Mensaje recibido: {msg.data().decode('utf-8')}")
                consumer.acknowledge(msg)
            except pulsar.Timeout:
                print("⚠️ No se recibieron mensajes en 5 segundos (esto puede ser normal)")
            
            consumer.close()
        except Exception as e:
            print(f"❌ Error al crear consumidor: {e}")
            
        # Cerrar cliente
        client.close()
        
    except Exception as e:
        print(f"❌ Error al conectar con Pulsar: {e}")
        return 1
        
    return 0

def list_available_topics(admin_url, namespace):
    """Lista todos los tópicos disponibles en el namespace."""
    try:
        response = requests.get(f"{admin_url}/admin/v2/persistent/{namespace}")
        if response.status_code == 200:
            topics = response.json()
            print("\n=== TÓPICOS DISPONIBLES ===")
            for topic in topics:
                print(f"- {topic}")
            print("==========================\n")
            return topics
        else:
            print(f"❌ Error al listar tópicos: Código HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error al listar tópicos: {e}")
        return []

if __name__ == "__main__":
    print("\n=== VERIFICACIÓN Y CONFIGURACIÓN DE PULSAR ===\n")
    
    # Variables de entorno o valores por defecto
    admin_url = os.environ.get("PULSAR_ADMIN_URL", "http://broker:8080")
    namespace = "public/default"
    
    # Listar tópicos disponibles
    list_available_topics(admin_url, namespace)
    
    # Ejecutar verificación
    result = verify_pulsar()
    
    # Mostrar tópicos después de la verificación
    list_available_topics(admin_url, namespace)
    
    print("\n=== VERIFICACIÓN COMPLETADA ===\n")
    sys.exit(result)
#!/usr/bin/env python3
"""
Script para verificar el estado y existencia del tópico de Pulsar.
Intenta varias estrategias para asegurar que el tópico exista.
"""
import requests
import subprocess
import sys
import time
import os
import json

# Configuración
ADMIN_URL = os.environ.get("PULSAR_ADMIN_URL", "http://127.0.0.1:8080")
SERVICE_URL = os.environ.get("PULSAR_SERVICE_URL", "pulsar://127.0.0.1:6650")
TOPIC_PATH = "public/default/eventos-suscripcion"
FULL_TOPIC_PATH = f"persistent://{TOPIC_PATH}"
NAMESPACE = "public/default"
CREATE_TEST_MESSAGE = True  # Crear un mensaje de prueba si se crea el tópico

def print_section(title):
    """Imprime un título de sección formateado."""
    print(f"\n{'=' * 10} {title} {'=' * 10}")

def check_broker_health():
    """Verifica si el broker está activo y respondiendo."""
    print("Verificando estado del broker...")
    try:
        response = requests.get(f"{ADMIN_URL}/admin/v2/clusters/cluster-a", timeout=5)
        if response.status_code == 200:
            print("✅ Broker está activo y respondiendo")
            return True
        else:
            print(f"⚠️ Broker respondió con código HTTP: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error al verificar estado del broker: {e}")
        return False

def ensure_namespace_exists():
    """Asegura que el namespace exista."""
    print(f"Verificando namespace {NAMESPACE}...")
    try:
        response = requests.get(f"{ADMIN_URL}/admin/v2/namespaces/public")
        if response.status_code == 200:
            namespaces = response.json()
            if NAMESPACE in namespaces:
                print(f"✅ Namespace {NAMESPACE} existe")
                return True
        
        # Crear namespace si no existe
        print(f"Creando namespace {NAMESPACE}...")
        create_response = requests.put(f"{ADMIN_URL}/admin/v2/namespaces/{NAMESPACE}")
        
        if create_response.status_code in [200, 204, 409]:  # 409 = ya existe
            print(f"✅ Namespace {NAMESPACE} creado/verificado correctamente")
            
            # Configurar política de retención
            print("Configurando política de retención...")
            retention_response = requests.post(
                f"{ADMIN_URL}/admin/v2/namespaces/{NAMESPACE}/retention",
                json={"retentionTimeInMinutes": 60, "retentionSizeInMB": 512}
            )
            
            if retention_response.status_code in [200, 204]:
                print("✅ Política de retención configurada")
            else:
                print(f"⚠️ No se pudo configurar la retención: {retention_response.status_code}")
                
            return True
        else:
            print(f"❌ Error al crear namespace: {create_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error al verificar/crear namespace: {e}")
        return False

def check_topic_exists():
    """Verifica si el tópico existe mediante la API REST."""
    print(f"Verificando si el tópico {TOPIC_PATH} existe...")
    try:
        # Intentar múltiples endpoints para verificar el tópico
        endpoints = [
            f"{ADMIN_URL}/admin/v2/persistent/{TOPIC_PATH}/stats",
            f"{ADMIN_URL}/admin/v2/persistent/{TOPIC_PATH}/partitions"
        ]
        
        for endpoint in endpoints:
            response = requests.get(endpoint)
            if response.status_code == 200:
                print(f"✅ El tópico {TOPIC_PATH} existe (verificado vía {endpoint})")
                return True
        
        # Verificar también en la lista de tópicos
        list_response = requests.get(f"{ADMIN_URL}/admin/v2/persistent/{NAMESPACE}")
        if list_response.status_code == 200:
            topics = list_response.json()
            for topic in topics:
                if TOPIC_PATH in topic or FULL_TOPIC_PATH in topic:
                    print(f"✅ El tópico {TOPIC_PATH} existe (encontrado en lista)")
                    return True
        
        print(f"ℹ️ El tópico {TOPIC_PATH} no existe")
        return False
    except Exception as e:
        print(f"❌ Error al verificar existencia del tópico: {e}")
        return False

def create_topic_via_rest():
    """Intenta crear un tópico usando la API REST."""
    print(f"Creando tópico {TOPIC_PATH} vía API REST...")
    try:
        response = requests.put(f"{ADMIN_URL}/admin/v2/persistent/{TOPIC_PATH}")
        if response.status_code in [200, 204]:
            print(f"✅ Tópico {TOPIC_PATH} creado correctamente")
            return True
        elif response.status_code == 409:
            print(f"ℹ️ El tópico {TOPIC_PATH} ya existe (409 Conflict)")
            return True
        else:
            print(f"❌ Error al crear tópico: Código HTTP {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error al crear tópico vía REST: {e}")
        return False

def create_topic_via_cli():
    """Intenta crear un tópico usando la CLI de Pulsar."""
    print(f"Creando tópico {TOPIC_PATH} vía CLI de Pulsar...")
    try:
        # Determinar si estamos dentro del contenedor o no
        in_container = os.path.exists("/.dockerenv")
        
        if in_container:
            # Si estamos dentro de un contenedor, usar el comando directo
            cmd = [
                "bin/pulsar-admin", "--admin-url", ADMIN_URL,
                "topics", "create", FULL_TOPIC_PATH
            ]
        else:
            # Si estamos fuera, usar docker exec
            cmd = [
                "docker", "exec", "broker", 
                "bin/pulsar-admin", "topics", "create", FULL_TOPIC_PATH
            ]
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Tópico {TOPIC_PATH} creado correctamente vía CLI")
            return True
        else:
            if "409 Conflict" in result.stderr:
                print(f"ℹ️ El tópico {TOPIC_PATH} ya existe (CLI reportó conflicto)")
                return True
            else:
                print(f"❌ Error al crear tópico vía CLI: {result.stderr}")
                return False
    except Exception as e:
        print(f"❌ Error al ejecutar comando CLI: {e}")
        return False

def send_test_message():
    """Envía un mensaje de prueba al tópico."""
    try:
        import pulsar
        
        print(f"Enviando mensaje de prueba al tópico {FULL_TOPIC_PATH}...")
        client = pulsar.Client(SERVICE_URL, operation_timeout_seconds=5)
        producer = client.create_producer(FULL_TOPIC_PATH)
        
        # Crear un mensaje de prueba
        test_msg = {
            "type": "test-message",
            "timestamp": time.time(),
            "message": "Este es un mensaje de prueba para verificar el tópico",
            "created_by": "check_topic.py"
        }
        
        # Enviar el mensaje
        producer.send(json.dumps(test_msg).encode('utf-8'))
        print("✅ Mensaje de prueba enviado correctamente")
        
        # Cerrar recursos
        producer.close()
        client.close()
        return True
    except Exception as e:
        print(f"❌ Error al enviar mensaje de prueba: {e}")
        return False

def list_topics():
    """Lista todos los tópicos disponibles en el namespace."""
    print(f"Listando tópicos en namespace {NAMESPACE}...")
    try:
        response = requests.get(f"{ADMIN_URL}/admin/v2/persistent/{NAMESPACE}")
        if response.status_code == 200:
            topics = response.json()
            if topics:
                print("Tópicos disponibles:")
                for topic in topics:
                    print(f"  - {topic}")
            else:
                print("No hay tópicos disponibles en este namespace")
            return topics
        else:
            print(f"❌ Error al listar tópicos: Código HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error al listar tópicos: {e}")
        return []

def main():
    print_section("VERIFICACIÓN DEL TÓPICO DE PULSAR")
    
    # Paso 1: Verificar que el broker esté activo
    if not check_broker_health():
        print("⚠️ El broker no está respondiendo correctamente. Esperando 10 segundos...")
        time.sleep(10)
        if not check_broker_health():
            print("❌ No se pudo conectar con el broker después de esperar.")
            return 1
    
    # Paso 2: Asegurar que el namespace existe
    if not ensure_namespace_exists():
        print("❌ Error al verificar/crear el namespace necesario.")
        return 1
    
    # Paso 3: Verificar si el tópico ya existe
    topic_exists = check_topic_exists()
    
    # Paso 4: Si no existe, intentar crearlo
    if not topic_exists:
        print("El tópico no existe. Intentando crearlo...")
        
        # Intento 1: Crear vía REST API
        created_rest = create_topic_via_rest()
        
        # Intento 2: Si REST falla, crear vía CLI
        if not created_rest:
            created_cli = create_topic_via_cli()
            if not created_cli:
                print("❌ No se pudo crear el tópico después de múltiples intentos.")
                return 1
    
    # Paso 5: Verificar una vez más para confirmar
    if not check_topic_exists():
        print("❌ No se pudo confirmar la existencia del tópico después de intentar crearlo.")
        return 1
    
    # Paso 6: Listar los tópicos disponibles
    list_topics()
    
    # Paso 7: Enviar un mensaje de prueba si se solicitó
    if CREATE_TEST_MESSAGE:
        send_test_message()
    
    print_section("VERIFICACIÓN COMPLETADA")
    print("✅ El tópico está disponible y listo para usar")
    return 0

if __name__ == "__main__":
    sys.exit(main())
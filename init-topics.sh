#!/bin/bash
set -e

echo "Esperando a que el broker esté listo..."
MAX_RETRIES=30
RETRY_COUNT=0

# Usar la URL de admin desde variables de entorno o un valor por defecto
BROKER_URL="${PULSAR_ADMIN_URL:-http://broker:8080}"
ADMIN_URL="--admin-url ${BROKER_URL}"

echo "Usando URL del broker: ${BROKER_URL}"


while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  RETRY_COUNT=$((RETRY_COUNT+1))
  
  if curl -s ${BROKER_URL}/admin/v2/clusters/cluster-a > /dev/null; then
    echo "Broker está en funcionamiento"
    break
  fi

  echo "Intento $RETRY_COUNT/$MAX_RETRIES: Broker aún no está listo"
  sleep 5
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "No se pudo conectar al broker después de $MAX_RETRIES intentos"
  exit 1
fi

echo "Creando namespace public/default si no existe..."
bin/pulsar-admin ${ADMIN_URL} namespaces create public/default || echo "Namespace ya existe"

echo "Configurando retención para namespace public/default..."
bin/pulsar-admin ${ADMIN_URL} namespaces set-retention public/default --size 10G --time 7d

echo "Creando tópico eventos-suscripcion..."
bin/pulsar-admin ${ADMIN_URL} topics create persistent://public/default/eventos-suscripcion || echo "El tópico ya existe"

echo "Verificando tópicos existentes:"
bin/pulsar-admin ${ADMIN_URL} topics list public/default

echo "Inicialización completa"
#!/bin/bash

echo "====== DIAGNÓSTICO DE PULSAR ======"
echo

echo "1. Estado de los servicios principales:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "broker|bookie|zookeeper|pulsar-init"
echo

echo "2. Verificando broker:"
docker exec broker curl -s http://localhost:8080/admin/v2/clusters/cluster-a > /dev/null
if [ $? -eq 0 ]; then
  echo "✅ Broker está respondiendo correctamente"
else
  echo "❌ No se puede conectar al broker"
fi
echo

echo "3. Verificando tópicos existentes:"
docker exec broker bin/pulsar-admin topics list public/default
echo

echo "4. Intentando crear tópico manualmente:"
docker exec broker bin/pulsar-admin topics create persistent://public/default/eventos-suscripcion || echo "El tópico ya existe"
echo

echo "5. Últimos logs de broker:"
docker logs --tail 20 broker | grep -v DEBUG
echo

echo "6. Verificando BookKeeper:"
docker exec bookie bin/bookkeeper shell simpletest > /dev/null
if [ $? -eq 0 ]; then
  echo "✅ BookKeeper está funcionando correctamente"
else
  echo "❌ BookKeeper tiene problemas"
  echo "Detalles del error de BookKeeper:"
  docker exec bookie bin/bookkeeper shell simpletest
fi
echo

echo "7. Verificando los bookies disponibles:"
docker exec broker bin/pulsar-admin bookies list-bookies
echo

echo "====== FIN DEL DIAGNÓSTICO ======"
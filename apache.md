docker-compose down -v
rm -rf data/zookeeper/* data/bookkeeper/*
docker compose up --build -d
docker compose up -d
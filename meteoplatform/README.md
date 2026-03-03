# Meteo Platform (2 microservizi) + RabbitMQ (event-driven)

## Stack
- meteo-core-service (Spring Boot 3, Java 17): ingest realtime/history, persiste su TimescaleDB, pubblica eventi su RabbitMQ
- analysis-service (FastAPI, Python): consuma eventi da RabbitMQ, calcola choropleth/interpolazione (IDW) e serve GeoJSON
- frontend (React): mappa marker + grafici base + overlay GeoJSON
- TimescaleDB: storage time-series
- RabbitMQ: broker eventi
- (opzionale) Grafana: dashboard base su TimescaleDB

## Avvio
```bash
docker compose up --build
```

## URL
- Frontend: http://localhost:3000
- Swagger core: http://localhost:8080/swagger-ui/index.html
- Core health: http://localhost:8080/actuator/health
- Analysis docs: http://localhost:8000/docs
- RabbitMQ UI: http://localhost:15672 (guest/guest)
- Grafana: http://localhost:3001 (admin/admin)

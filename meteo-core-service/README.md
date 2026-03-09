# Meteo Core Service

This Spring Boot application is responsible for the ingestion, storage, and publishing of real-time weather data.

## Features
- **Data Ingestion**: Polls weather APIs on a cron schedule.
- **Message Publishing**: Emits AMQP messages to RabbitMQ (`meteo.realtime` exchange).
- **Relational Storage**: Stores historical weather data in TimescaleDB/PostgreSQL.

## Configuration Updates & Rate Limiting

Due to strict rate limiting on external meteorological APIs (such as Open-Meteo's 10,000 requests/day limit), the backend has been heavily optimized:

1. **Polling Rate**: Configured to poll the APIs exactly **once per hour** (`meteo.polling.realtimeMs=3600000`).
2. **API Batching**: 100 municipalities are requested in a single batch to drastically reduce HTTP overhead and avoid temporary bot-bans.
3. **Mock Fallback Generation**: If the APIs go entirely offline or ban the Kubernetes worker node IP, the `TorinoMeteoClient` will automatically generate highly contextual mock data for the 100 municipalities to ensure the dashboard remains functional. The user interface will warn clients that mock data is active.
4. **Caching**: Data stays highly cached up to 90 minutes.

### SSL / DNS Considerations
Due to DNS resolution instability in certain clustered environments, the internal HTTP client optionally ignores SSL hostname verification and routes directly to the IP if needed (refer to `TorinoMeteoClient.java`'s `init()` method).

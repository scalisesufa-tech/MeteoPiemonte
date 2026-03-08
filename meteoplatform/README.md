# 🌤️ MeteoPlatform - Progetto di Esame
## Monitoraggio Meteorologico in Tempo Reale (Piemonte/Torino)

Questo repository contiene l'implementazione di una piattaforma distribuita per l'ingestion, l'analisi e la visualizzazione di dati meteorologici in tempo reale. Il sistema è stato migrato e ottimizzato per operare stabilmente all'interno di un cluster Kubernetes con risorse condivise.

---

## 🚀 Panoramica del Lavoro Svolto

Il progetto ha affrontato diverse sfide tecniche, dalla connettività di rete alla gestione dei limiti delle API esterne, arrivando a una soluzione robusta e scalabile.

### 1. Migrazione della Sorgente Dati (Open-Meteo API)
A causa di restrizioni di rete che bloccavano l'accesso a `torinometeo.org`, la sorgente dati è stata migrata verso **Open-Meteo**. 
- **Integrazione:** Sviluppato un nuovo client in Spring Boot (`TorinoMeteoClient.java`) capace di interrogare le coordinate geografiche di precisione (latitudine/longitudine).
- **Enrichment:** Oltre alla temperatura, il sistema ora acquisisce **Umidità Relativa** e **Pressione Atmosferica** in superficie.

### 2. Espansione della Copertura Territoriale
Partendo da una singola stazione, la piattaforma è stata estesa per coprire l'intero territorio:
- **Dataset Geografico:** Integrato un dataset JSON in `/resources` contenente le coordinate di tutti i **1.179 comuni del Piemonte**.
- **Ottimizzazione Strategica:** Per rispettare le rigide "usage policies" delle API gratuite (600 r/min, 10k r/giorno), il sistema è stato configurato per monitorare **100 comuni della provincia di Torino**. Questa scelta garantisce un'alta densità di dati sulla mappa senza rischio di blocchi durante la presentazione.

### 3. Ingestion & Rate-Limiting
Per gestire il volume di dati (100 punti ogni ciclo), sono state implementate tecniche di polling avanzate:
- **Batch Processing:** I comuni vengono interrogati a gruppi di 50 per massimizzare l'efficienza delle chiamate HTTP.
- **Micro-Delay:** Inserito un delay di **5 secondi** tra ogni batch per non saturare il limite di velocità al minuto.
- **Soglia Giornaliera:** Intervallo di polling impostato a **15 minuti**, garantendo circa **9.600 richieste/giorno** (sotto il limite di 10.000), rendendo il sistema attivo h24.

### 4. Architettura Kubernetes
L'intera suite (Frontend, Backend, DB, RabbitMQ/Grafana) è stata containerizzata e deployata in un namespace dedicato:
- **Resilienza Pod:** Configurate `Liveness` e `Readiness Probes` con periodi di tolleranza estesi per compensare i tempi di avvio in ambiente cluster.
- **Gestione Repliche:** Il servizio `meteo-core` è stato scalato a **1 replica** per accentrare la gestione del budget API ed evitare accessi concorrenti duplicati.
- **Routing & Networking:** Gestito il deploy sotto subpath (es. `/group-6`) tramite variabili d'ambiente (`PUBLIC_URL`) e configurazione di Ingress/HTTPRoute.

---

## 🛠️ Stack Tecnologico
- **Backend:** Java 17, Spring Boot 3.3.2, Spring Data JPA.
- **Database:** PostgreSQL.
- **Messaging:** RabbitMQ per gli eventi in tempo reale.
- **Analytic:** Grafana per il monitoraggio dei flussi dati.
- **Frontend:** React + Leaflet per la cartografia dinamica.
- **Infrastruttura:** Docker, Kubernetes, Open-Meteo API.

---

## 📦 Come Verificare lo Stato
È possibile monitorare l'attività del sistema tramite i log del backend o interrogando il database:

```bash
# Visualizza l'avvio e il polling dei batch (100 comuni)
kubectl logs -l app=meteo-core -n group-6 --tail=100

# Verifica il numero di osservazioni salvate
kubectl exec -it meteo-db-0 -n group-6 -- psql -U meteo -d meteo -c "SELECT count(*) FROM meteo_observation;"
```

---

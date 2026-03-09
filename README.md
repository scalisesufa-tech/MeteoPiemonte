-# 🌤️ MeteoPlatform - Progetto di Esame
-## Monitoraggio Meteorologico in Tempo Reale (Piemonte/Torino)
+# MeteoPlatform — Documentazione tecnica completa
 
-Questo repository contiene l'implementazione di una piattaforma distribuita per l'ingestion, l'analisi e la visualizzazione di dati meteorologici in tempo reale. Il sistema è stato migrato e ottimizzato per operare stabilmente all'interno di un cluster Kubernetes con risorse condivise.
+> Progetto di monitoraggio meteorologico distribuito, real-time e cloud-native, con pipeline event-driven su Kubernetes.
+
+## 1) Obiettivo del progetto
+
+MeteoPlatform nasce per dimostrare un'architettura moderna end-to-end per:
+- ingestione periodica di dati meteo;
+- persistenza su database time-series;
+- distribuzione eventi real-time via message broker;
+- analisi spaziale (interpolazione) e previsione breve;
+- visualizzazione geospaziale su mappa web.
+
+Il progetto è stato progettato per essere eseguibile sia in locale (Docker Compose) sia su cluster Kubernetes, con particolare attenzione ai vincoli reali (rate limit API esterne, startup lenti dei componenti di stato, deploy sotto path condiviso).  
 
 ---
 
-## 🚀 Panoramica del Lavoro Svolto
+## 2) Architettura logica
+
+### Componenti principali
+
+1. **meteo-core-service (Spring Boot, Java 17)**
+   - Effettua polling periodico dei dati da Open-Meteo.
+   - Normalizza i payload.
+   - Salva le osservazioni su TimescaleDB.
+   - Pubblica eventi meteo su RabbitMQ.
 
-Il progetto ha affrontato diverse sfide tecniche, dalla connettività di rete alla gestione dei limiti delle API esterne, arrivando a una soluzione robusta e scalabile.
+2. **analysis-service (FastAPI, Python)**
+   - Consuma eventi da RabbitMQ e mantiene cache in-memory degli ultimi punti.
+   - Espone endpoint analitici (latest, stats, choropleth) e forecast.
+   - Applica interpolazione IDW per generare mappe continue da punti discreti.
 
-### 1. Migrazione della Sorgente Dati (Open-Meteo API)
-A causa di restrizioni di rete che bloccavano l'accesso a `torinometeo.org`, la sorgente dati è stata migrata verso **Open-Meteo**. 
-- **Integrazione:** Sviluppato un nuovo client in Spring Boot (`TorinoMeteoClient.java`) capace di interrogare le coordinate geografiche di precisione (latitudine/longitudine).
-- **Enrichment:** Oltre alla temperatura, il sistema ora acquisisce **Umidità Relativa** e **Pressione Atmosferica** in superficie.
+3. **frontend (React + Leaflet + Recharts)**
+   - Mostra marker georeferenziati in mappa.
+   - Visualizza layer areale interpolato (e versione predittiva a T+n ore).
+   - Mostra serie storiche + forecast per stazione selezionata.
 
-### 2. Espansione della Copertura Territoriale
-Partendo da una singola stazione, la piattaforma è stata estesa per coprire l'intero territorio:
-- **Dataset Geografico:** Integrato un dataset JSON in `/resources` contenente le coordinate di tutti i **1.179 comuni del Piemonte**.
-- **Ottimizzazione Strategica:** Per rispettare le rigide "usage policies" delle API gratuite (600 r/min, 10k r/giorno), il sistema è stato configurato per monitorare **100 comuni della provincia di Torino**. Questa scelta garantisce un'alta densità di dati sulla mappa senza rischio di blocchi durante la presentazione.
+4. **meteo-db (TimescaleDB/PostgreSQL)**
+   - Salvataggio storico osservazioni con hypertable indicizzata per tempo.
 
-### 3. Ingestion & Rate-Limiting
-Per gestire il volume di dati (100 punti ogni ciclo), sono state implementate tecniche di polling avanzate:
-- **Batch Processing:** I comuni vengono interrogati a gruppi di 50 per massimizzare l'efficienza delle chiamate HTTP.
-- **Micro-Delay:** Inserito un delay di **5 secondi** tra ogni batch per non saturare il limite di velocità al minuto.
-- **Soglia Giornaliera:** Intervallo di polling impostato a **15 minuti**, garantendo circa **9.600 richieste/giorno** (sotto il limite di 10.000), rendendo il sistema attivo h24.
+5. **rabbitmq (RabbitMQ + management plugin)**
+   - Backbone event-driven tra ingestion e analytics.
 
-### 4. Architettura Kubernetes
-L'intera suite (Frontend, Backend, DB, RabbitMQ/Grafana) è stata containerizzata e deployata in un namespace dedicato:
-- **Resilienza Pod:** Configurate `Liveness` e `Readiness Probes` con periodi di tolleranza estesi per compensare i tempi di avvio in ambiente cluster.
-- **Gestione Repliche:** Il servizio `meteo-core` è stato scalato a **1 replica** per accentrare la gestione del budget API ed evitare accessi concorrenti duplicati.
-- **Routing & Networking:** Gestito il deploy sotto subpath (es. `/group-6`) tramite variabili d'ambiente (`PUBLIC_URL`) e configurazione di Ingress/HTTPRoute.
+6. **grafana (Grafana)**
+   - Accesso rapido ai dati meteo su TimescaleDB per dashboard/monitoraggio.
 
 ---
 
-## 🛠️ Stack Tecnologico
-- **Backend:** Java 17, Spring Boot 3.3.2, Spring Data JPA.
-- **Database:** PostgreSQL.
-- **Messaging:** RabbitMQ per gli eventi in tempo reale.
-- **Analytic:** Grafana per il monitoraggio dei flussi dati.
-- **Frontend:** React + Leaflet per la cartografia dinamica.
-- **Infrastruttura:** Docker, Kubernetes, Open-Meteo API.
+## 3) Flusso dati end-to-end
+
+1. Scheduler di `meteo-core-service` esegue polling (`meteo.polling.realtimeMs`).
+2. `TorinoMeteoClient` carica elenco comuni (Piemonte) e seleziona i primi 100 della provincia di Torino.
+3. Le chiamate a Open-Meteo avvengono in **batch da 50** coordinate con **delay di 5s** tra batch.
+4. Il payload viene trasformato in `MeteoObservation` e persistito su TimescaleDB.
+5. Per ogni osservazione viene emesso evento `RealtimeEvent` su coda RabbitMQ (`meteo.realtime`).
+6. `analysis-service` consuma eventi, aggiorna la cache e fornisce endpoint analitici al frontend.
+7. Il frontend combina API core + analysis per mappa, statistiche, aree interpolate e forecast.
 
 ---
 
-## 📦 Come Verificare lo Stato
-È possibile monitorare l'attività del sistema tramite i log del backend o interrogando il database:
+## 4) Scelte tecniche e motivazioni
+
+### 4.1 Sorgente dati Open-Meteo
+**Scelta:** uso Open-Meteo con query multi-punto (`latitude`/`longitude` CSV).  
+**Perché:** maggiore affidabilità raggiungibilità rete e possibilità di chiedere più punti in una singola richiesta, riducendo overhead HTTP.
+
+### 4.2 Campionamento su 100 comuni
+**Scelta:** subset di 100 comuni della provincia di Torino (filtrando `id` con prefisso `001`).  
+**Perché:** equilibrio tra copertura spaziale utile in demo e contenimento del budget richieste verso API esterna.
+
+### 4.3 Pipeline event-driven (DB + broker)
+**Scelta:** persistenza transazionale su DB + pubblicazione su broker.  
+**Perché:**
+- il DB garantisce storico e query robuste;
+- RabbitMQ disaccoppia ingestion e analytics;
+- il consumer analytics può scalare indipendentemente senza bloccare ingestion.
+
+### 4.4 IDW per mappa areale
+**Scelta:** interpolazione Inverse Distance Weighting nel servizio Python.  
+**Perché:** metodo semplice, interpretabile e veloce, adatto a dimostrazione in tempo reale senza dipendenze GIS pesanti.
+
+### 4.5 Forecast con griglia ridotta
+**Scelta:** per choropleth predittiva si interrogano 25 punti (griglia 5x5) e poi si interpola su griglia più fine.  
+**Perché:** riduce drasticamente chiamate verso API forecast mantenendo una superficie continua visualmente efficace.
+
+---
+
+## 5) Kubernetes: spiegazione tecnica dettagliata
+
+La cartella `04-kubernetes/` contiene i manifest modulari e un file aggregato `all-manifests.yaml`.
+
+### 5.1 Namespace dedicato
+**Manifest:** `namespace/namespace.yaml` (`group-6`).  
+**Motivazione:** isolamento logico e operativo (risorse, secret, servizi, route).
+
+### 5.2 Config e secret separation
+- **Secret** per credenziali DB, RabbitMQ, admin Grafana.
+- **ConfigMap** per SQL init TimescaleDB e provisioning Grafana.
+
+**Motivazione:** separare config runtime da immagine container, facilitare manutenzione e sostituzione credenziali.
+
+### 5.3 StatefulSet per componenti stateful
+- `meteo-db` e `rabbitmq` deployati con **StatefulSet** + PVC.
+- Storage class: `csi-cinder-fast`.
 
+**Motivazione:** identità stabile del pod, volumi persistenti e comportamento prevedibile in restart/ricreazione.
+
+### 5.4 Deployment per servizi stateless
+- `meteo-core`, `analysis-service`, `frontend`, `grafana` su **Deployment**.
+
+**Motivazione:** rolling update semplice e gestione repliche efficiente per componenti senza stato locale critico.
+
+### 5.5 Strategia repliche (scelta intenzionale)
+- `meteo-core`: **1 replica**.
+- `analysis-service`: **2 repliche**.
+- `frontend`: 1 replica.
+
+**Motivazione:**
+- `meteo-core` a singola replica evita polling duplicato (quindi doppio consumo API e duplicazione ingest);
+- `analysis-service` scala in lettura/elaborazione e tollera parallelismo consumer.
+
+### 5.6 Probes conservative (readiness/liveness)
+Sono configurati delay iniziali elevati su alcuni servizi (`meteo-core`, `rabbitmq`, `frontend`).  
+**Motivazione:** in cluster condivisi o cold-start lenti, probe troppo aggressive causano restart inutili e loop di instabilità.
+
+### 5.7 Servizi interni ClusterIP
+Ogni workload espone un Service (`meteo-core`, `analysis-service`, `frontend`, `meteo-db`, `rabbitmq`, `grafana`).  
+**Motivazione:** discovery DNS interno (`<service>.<namespace>.svc`) e disaccoppiamento tra pod IP e client.
+
+### 5.8 Expose esterno con Gateway API + HTTPRoute
+La route unifica il progetto sotto prefisso `/group-6`:
+- `/group-6/core` → `meteo-core`
+- `/group-6/analysis` → `analysis-service`
+- `/group-6` → `frontend`
+
+Per i path backend è usato `URLRewrite` (ReplacePrefixMatch → `/`).  
+**Motivazione:** deploy multi-team su gateway condiviso senza collisioni path e senza cambiare codice backend.
+
+### 5.9 Frontend path-aware
+Variabili ambiente frontend in Kubernetes:
+- `PUBLIC_URL=/group-6`
+- `REACT_APP_CORE_BASE=/group-6/core`
+- `REACT_APP_ANALYSIS_BASE=/group-6/analysis`
+
+**Motivazione:** asset statici e chiamate API restano coerenti quando l'app non è montata in root (`/`).
+
+### 5.10 Provisioning Grafana as-code
+Datasource e dashboard provider montati via ConfigMap.  
+**Motivazione:** ambiente riproducibile senza configurazioni manuali post-deploy.
+
+---
+
+## 6) Struttura repository (alto livello)
+
+```text
+meteoplatform/
+├── analysis-service/          # FastAPI + consumer RabbitMQ + interpolazione/forecast
+├── meteo-core-service/        # Spring Boot ingestion + persistenza + publish eventi
+├── frontend/                  # React map UI
+├── db/init.sql                # schema + hypertable TimescaleDB
+├── grafana/provisioning/      # datasource/dashboard provisioning
+├── docker-compose.yml         # run locale completo
+└── 04-kubernetes/             # manifest Kubernetes (modulari + aggregato)
+```
+
+---
+
+## 7) Avvio in locale (Docker Compose)
+
+### Prerequisiti
+- Docker + Docker Compose
+
+### Run
+```bash
+docker compose up --build
+```
+
+### Endpoint locali
+- Frontend: `http://localhost:3000`
+- Core API: `http://localhost:8080`
+- Analysis API: `http://localhost:8000`
+- Grafana: `http://localhost:3001` (admin/admin)
+- RabbitMQ UI: `http://localhost:15672` (guest/guest)
+
+---
+
+## 8) Deploy su Kubernetes
+
+### Opzione A — manifest aggregato
 ```bash
-# Visualizza l'avvio e il polling dei batch (100 comuni)
-kubectl logs -l app=meteo-core -n group-6 --tail=100
+kubectl apply -f 04-kubernetes/all-manifests.yaml
+```
+
+### Opzione B — manifest modulari
+```bash
+kubectl apply -f 04-kubernetes/manifests/
+```
+
+### Verifiche operative consigliate
+```bash
+# Stato workload
+kubectl get pods -n group-6
+
+# Servizi esposti internamente
+kubectl get svc -n group-6
+
+# Route verso gateway condiviso
+kubectl get httproute -n group-6
 
-# Verifica il numero di osservazioni salvate
-kubectl exec -it meteo-db-0 -n group-6 -- psql -U meteo -d meteo -c "SELECT count(*) FROM meteo_observation;"
+# Log ingestion (batch polling)
+kubectl logs -l app=meteo-core -n group-6 --tail=200
+
+# Conteggio righe salvate
+kubectl exec -it meteo-db-0 -n group-6 -- \
+  psql -U meteo -d meteo -c "SELECT count(*) FROM meteo_observation;"
 ```
 
 ---
+
+## 9) API principali (sintesi)
+
+### meteo-core-service
+- `POST /api/ingest/realtime` — trigger ingest manuale.
+- `GET /api/geo/latest?minutes=...&limit=...` — ultimi punti geolocalizzati.
+- `GET /api/series?stationId=...&from=...&to=...` — serie storica per stazione.
+
+### analysis-service
+- `GET /health`
+- `GET /latest?metric=temperature|pressure|relativeHumidity`
+- `GET /stats?metric=...`
+- `GET /choropleth?metric=...&minLat=...&maxLat=...&minLon=...&maxLon=...`
+- `POST /forecast` (lat/lon/metric/hoursAhead)
+- `GET /choropleth/forecast?metric=...&hoursAhead=...`
+
+---
+
+## 10) Limiti noti e trade-off
+
+1. **Consumer in-memory in analysis-service**
+   - Veloce da implementare e sufficiente per demo.
+   - In caso di restart, la cache si ricostruisce dai nuovi eventi (non da replay storico).
+
+2. **Single replica per meteo-core**
+   - Riduce duplicazione ingest/richieste API.
+   - Meno throughput teorico, ma coerente con vincolo rate-limit esterno.
+
+3. **Credenziali di default in ambiente demo**
+   - Adeguate per laboratorio/esame.
+   - In produzione: secret manager, rotazione password, policy RBAC più strette.
+
+---
+
+## 11) Possibili evoluzioni
+
+- HPA su `analysis-service` basato su CPU/RPS.
+- Leader election per rendere `meteo-core` scalabile senza doppio polling.
+- Persistenza eventi (es. stream/log) per replay analytics.
+- Dashboard Grafana estese con alerting soglie meteo.
+- CI/CD per build immagini + deploy manifest versionati.
+
+---
+
+## 12) Messaggio finale per relazione tecnica
+
+Le scelte architetturali sono state guidate da vincoli reali (rate limit API, ambiente cluster condiviso, necessità di resilienza) e non solo da criteri teorici. In particolare, la configurazione Kubernetes è stata progettata per privilegiare **stabilità operativa, riproducibilità e deploy sotto path condiviso**, mantenendo al tempo stesso una pipeline dati completa e chiaramente dimostrabile in sede d'esame.

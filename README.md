# 🌦️ MeteoPlatform
## Piattaforma distribuita per monitoraggio, analisi e visualizzazione meteo in tempo reale

> Documentazione tecnica per consegna accademica (architettura, scelte progettuali, Kubernetes, trade-off).

---

## 1. Contesto e obiettivi

MeteoPlatform è un progetto end-to-end che dimostra come costruire una pipeline **data-driven** e **cloud-native** per dati meteorologici:

- **acquisizione periodica** da sorgenti esterne;
- **persistenza storica** su database time-series;
- **disaccoppiamento tramite eventi** (message broker);
- **analisi spaziale** (interpolazione su mappa);
- **forecast di breve orizzonte**;
- **visualizzazione web interattiva**.

L’obiettivo non è solo “far funzionare” il sistema, ma motivare le scelte in funzione di vincoli reali:

1. limiti delle API esterne (rate-limit giornaliero/minuto),
2. affidabilità in ambiente condiviso,
3. riproducibilità del deploy,
4. separazione chiara tra componenti stateful/stateless.

---

## 2. Architettura del sistema

L’architettura è composta da sei componenti principali:

### 2.1 `meteo-core-service` (Java 17 + Spring Boot)
Responsabilità:
- polling dei dati da Open-Meteo;
- normalizzazione payload;
- persistenza su TimescaleDB;
- pubblicazione eventi realtime su RabbitMQ.

### 2.2 `analysis-service` (Python + FastAPI)
Responsabilità:
- consumo eventi RabbitMQ;
- calcolo endpoint analitici (`latest`, `stats`, `choropleth`);
- endpoint forecast (`/forecast`, `/choropleth/forecast`);
- interpolazione spaziale IDW.

### 2.3 `frontend` (React + Leaflet + Recharts)
Responsabilità:
- rendering punti stazione su mappa;
- heat/choropleth interpolata;
- confronto dati storici + previsione;
- selezione metrica (temperatura/pressione/umidità).

### 2.4 `meteo-db` (TimescaleDB/PostgreSQL)
Responsabilità:
- storage storico osservazioni;
- hypertable per query time-series efficienti.

### 2.5 `rabbitmq`
Responsabilità:
- backbone event-driven tra ingestione e analytics;
- disaccoppiamento dei tempi di elaborazione.

### 2.6 `grafana`
Responsabilità:
- visualizzazione operativa dati su datasource PostgreSQL/Timescale.

---

## 3. Flusso dati (end-to-end)

1. Lo scheduler invoca periodicamente `ingestRealtimeAndPublish()`.
2. Il client meteo legge i comuni Piemonte e seleziona i 100 della provincia di Torino.
3. Le richieste a Open-Meteo sono effettuate in batch (50 + 50) con micro-delay.
4. Le osservazioni vengono trasformate in entità e persistite nel DB.
5. Ogni osservazione utile genera un evento realtime su RabbitMQ.
6. L’analysis-service consuma eventi e aggiorna lo stato analitico.
7. Il frontend interroga le API e aggiorna mappa, statistiche e grafici.

---

## 4. Scelte progettuali e motivazioni

### 4.1 Open-Meteo come sorgente
**Scelta:** uso di Open-Meteo con query multi-punto (lat/lon CSV).  
**Motivo:** robustezza di accesso + riduzione overhead HTTP rispetto a chiamate singole.

### 4.2 Campionamento a 100 comuni (provincia di Torino)
**Scelta:** subset stabile e rappresentativo.  
**Motivo:** bilanciare copertura geografica e limiti di consumo API.

### 4.3 Batch + micro-delay + polling controllato
**Scelta:** batching da 50, pausa di 5 secondi tra i batch, polling periodico configurabile.  
**Motivo:** prevenire throttling e mantenere acquisizione continua H24.

### 4.4 Pipeline event-driven
**Scelta:** DB per storico + RabbitMQ per eventi.  
**Motivo:** disaccoppiamento tra ingest e analytics, maggiore estendibilità, semplificazione scalabilità orizzontale dei consumer.

### 4.5 Interpolazione IDW
**Scelta:** Inverse Distance Weighting per la superficie meteo.  
**Motivo:** algoritmo semplice, interpretabile, computazionalmente leggero e adatto alla visualizzazione real-time.

### 4.6 Forecast a griglia ridotta
**Scelta:** 25 punti forecast (5x5) + interpolazione a griglia più fine.  
**Motivo:** riduzione drastica delle chiamate esterne mantenendo qualità visiva della previsione areale.

---

## 5. Kubernetes (spiegazione tecnica dettagliata)

La cartella `04-kubernetes/` contiene manifest modulari e aggregati (`all-manifests.yaml`).

## 5.1 Isolamento con Namespace
- Namespace dedicato: `group-6`.
- Tutte le risorse applicative (secret, configmap, workload, service, route) sono isolate nel namespace.

**Perché:** riduce collisioni con altri gruppi/progetti su cluster condiviso.

## 5.2 Configurazione e segreti
- `Secret`: credenziali DB, RabbitMQ, Grafana.
- `ConfigMap`: script init DB e provisioning Grafana.

**Perché:** separazione tra immagine e runtime config, migliore mantenibilità e sicurezza base.

## 5.3 StatefulSet per componenti con stato
- `meteo-db` e `rabbitmq` in `StatefulSet` + volumi persistenti.
- PVC con storage class `csi-cinder-fast`.

**Perché:** identità stabile dei pod, persistenza dati e recovery coerente.

## 5.4 Deployment per componenti stateless
- `meteo-core`, `analysis-service`, `frontend`, `grafana` in `Deployment`.

**Perché:** rollout semplice, gestione repliche e aggiornamenti progressivi.

## 5.5 Strategia repliche
- `meteo-core`: **1 replica** (scelta intenzionale).
- `analysis-service`: **2 repliche**.
- `frontend`: 1 replica.

**Perché questa scelta è importante:**
- con più repliche del core si rischia polling duplicato → doppio traffico verso API esterna e duplicazione ingest;
- analysis-service può scalare in consumo/elaborazione senza impattare il budget API.

## 5.6 Health probes conservative
- Readiness/Liveness con initial delay più alto su servizi lenti all’avvio (`rabbitmq`, `meteo-core`, `frontend`).

**Perché:** evita restart-loop in ambienti con cold-start o risorse condivise.

## 5.7 Service discovery interno
- Ogni workload espone un `Service` ClusterIP.
- Comunicazione interna via DNS Kubernetes (`service-name:port`).

**Perché:** stabilità endpoint interni e disaccoppiamento dagli IP dei pod.

## 5.8 Esposizione esterna con Gateway API + HTTPRoute
Routing path-based sotto prefisso comune:
- `/group-6` → frontend
- `/group-6/core` → meteo-core
- `/group-6/analysis` → analysis-service

Con `URLRewrite` sui backend per rimuovere il prefisso.

**Perché:** compatibilità con gateway condiviso multi-team e URL unificata lato utente.

## 5.9 Frontend path-aware
Variabili ambiente principali:
- `PUBLIC_URL=/group-6`
- `REACT_APP_CORE_BASE=/group-6/core`
- `REACT_APP_ANALYSIS_BASE=/group-6/analysis`

**Perché:** corretto caricamento asset/static e chiamate API quando l’app non è deployata alla root `/`.

## 5.10 Grafana provisioning as-code
Datasource e dashboard provider vengono montati da ConfigMap.

**Perché:** ambiente monitorabile in modo riproducibile senza setup manuale post-deploy.

---

## 6. Struttura repository

```text
meteoplatform/
├── meteo-core-service/        # Ingestion + persistenza + publish eventi
├── analysis-service/          # Consumer RabbitMQ + endpoint analytics/forecast
├── frontend/                  # UI geospaziale React/Leaflet
├── db/init.sql                # Schema + hypertable Timescale
├── grafana/provisioning/      # Config datasource/dashboard
├── docker-compose.yml         # Esecuzione locale completa
└── 04-kubernetes/             # Manifest Kubernetes

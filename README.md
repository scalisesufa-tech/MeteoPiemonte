# 🌦️ Meteo Platform

### Piattaforma cloud-native per raccolta, analisi e visualizzazione di dati meteorologici

Questa piattaforma distribuita è progettata per la **raccolta, l'elaborazione e la visualizzazione di dati meteorologici in tempo reale**. Il progetto è stato sviluppato seguendo i principi delle **architetture a microservizi** e delle applicazioni **cloud-native**, dimostrando come costruire un sistema scalabile, resiliente e completamente containerizzato.

---

## 🎯 Obiettivi del Progetto

L’obiettivo è realizzare una **pipeline completa di data management**, strutturata in:

1.  **Acquisizione**: Recupero dati da API meteorologiche esterne (Open-Meteo).
2.  **Persistenza**: Storage ottimizzato per serie temporali.
3.  **Comunicazione**: Disaccoppiamento dei servizi tramite architettura event-driven.
4.  **Analisi**: Elaborazione e interpolazione dei dati raccolti.
5.  **Visualizzazione**: Dashboard interattive per l'utente finale.

Questa separazione dei livelli (raccolta, elaborazione, visualizzazione) garantisce **manutenibilità, scalabilità e modularità**.

---

## 🧩 Architettura del Sistema

Il sistema è composto da microservizi indipendenti che comunicano in modo asincrono.

| Servizio | Tecnologia | Ruolo |
| :--- | :--- | :--- |
| **meteo-core-service** | Java + Spring Boot | Core logic e acquisizione dati esterni |
| **analysis-service** | Python + FastAPI | Analisi statistica e interpolazione dati |
| **frontend** | React | Interfaccia utente interattiva |
| **meteo-db** | PostgreSQL + TimescaleDB | Database relazionale ottimizzato per time-series |
| **RabbitMQ** | Message Broker | Gestione della comunicazione asincrona |
| **Grafana** | Monitoring | Dashboard di monitoraggio operativo |

### 🏗 Diagramma Architetturale

```mermaid
flowchart LR
    subgraph Client
        U[Utente]
        FE[Frontend React]
    end

    subgraph Kubernetes_Cluster [Kubernetes Cluster]
        CORE[meteo-core-service Spring Boot]
        AN[analysis-service FastAPI]
        RMQ[RabbitMQ]
        DB[(PostgreSQL + TimescaleDB)]
        GRAF[Grafana]
    end

    EXT[API Meteo Esterne Open-Meteo]

    U --> FE
    FE -->|REST API| CORE
    FE -->|REST API| AN

    CORE -->|Raccolta dati| EXT
    CORE -->|Salvataggio dati| DB
    CORE -->|Pubblica evento| RMQ

    RMQ -->|Consumo eventi| AN
    AN -->|Salvataggio risultati| DB

    GRAF -->|Dashboard| DB


---

## 🐳 Containerizzazione con Docker

Tutti i servizi sono distribuiti come container **Docker**. Questo approccio permette di:
* **Garantire ambienti di esecuzione consistenti** tra sviluppo e produzione.
* **Isolare le dipendenze** dei servizi (es. Java per il core, Python per l'analisi).
* **Facilitare il deployment** e migliorare la portabilità tra sistemi diversi.
* **Gestire deploy e aggiornamenti indipendenti** per ogni microservizio.

---

## ☸️ Orchestrazione con Kubernetes

Il sistema è orchestrato tramite **Kubernetes**, che gestisce il ciclo di vita dei container attraverso diverse risorse:

| Risorsa | Descrizione |
| :--- | :--- |
| **Pod** | Unità minima di esecuzione dei container. |
| **Deployment** | Gestione delle repliche e degli aggiornamenti dei servizi. |
| **StatefulSet** | Gestione dei servizi con stato (come il Database). |
| **Service** | Endpoint di rete stabili per il networking tra pod. |
| **Namespace** | Isolamento logico delle risorse nel cluster. |

### ⚙️ Gestione della configurazione
La configurazione è separata dal codice per garantire sicurezza e flessibilità:
* **ConfigMap**: Utilizzate per parametri applicativi e variabili d'ambiente non sensibili.
* **Secrets**: Utilizzati per credenziali del database, token API e chiavi di accesso.

### 💾 Storage persistente
Utilizziamo **PersistentVolume (PV)** e **PersistentVolumeClaim (PVC)** per garantire che i dati meteorologici salvati in *PostgreSQL/TimescaleDB* siano persistenti e non vadano persi in caso di riavvio o ripianificazione dei pod.

---

## 🔄 Flusso dei Dati (Pipeline)

Il percorso del dato segue una pipeline strutturata:

1.  **Ingestion**: Il *Core Service* interroga periodicamente le API esterne.
2.  **Storage**: I dati vengono normalizzati e salvati nel database.
3.  **Messaging**: Il servizio pubblica un evento su **RabbitMQ**.
4.  **Processing**: L’*Analysis Service* consuma l’evento, esegue l'interpolazione e salva i risultati.
5.  **Delivery**: Il *Frontend* visualizza i dati tramite mappe (**Leaflet**) e grafici (**Recharts**).

---

## 🛡 Resilienza e Scalabilità

* **Resilienza**: Kubernetes garantisce il riavvio automatico dei container. L'uso di **RabbitMQ** disaccoppia i servizi: se l'Analysis Service è temporaneamente offline, i messaggi rimangono in coda senza perdita di dati.
* **Scalabilità Orizzontale**: I servizi *stateless* possono essere scalati aumentando il numero di repliche in base al carico (es. più istanze di Analysis Service per calcoli intensivi).
* **Scheduling Avanzato**: Utilizzo di **Node Affinity** per eseguire i database su nodi con storage veloce e i servizi di calcolo su nodi con maggiore potenza di calcolo (CPU).

---

## 🔍 Monitoraggio

Il sistema integra **Grafana** per:
* Il monitoraggio costante delle **metriche operative** (health check dei servizi).
* La **visualizzazione rapida** dei dati meteorologici archiviati.
* Fornire una visione completa e centralizzata della salute dell'intera piattaforma.

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

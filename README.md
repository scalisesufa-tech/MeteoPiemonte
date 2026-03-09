# 🌦️ Meteo Platform

## Piattaforma cloud-native per raccolta, analisi e visualizzazione di dati meteorologici

Questo progetto implementa una **piattaforma distribuita per la raccolta, elaborazione e visualizzazione di dati meteorologici in tempo reale**, sviluppata seguendo i principi delle **architetture a microservizi** e delle applicazioni **cloud-native**.

Il sistema dimostra come progettare una piattaforma **scalabile, resiliente e containerizzata**, utilizzando tecnologie moderne come:

- Docker
- Kubernetes
- Spring Boot
- FastAPI
- RabbitMQ
- PostgreSQL / TimescaleDB
- React
- Grafana

---

# 🎯 Obiettivi del progetto

L’obiettivo del progetto è realizzare una **pipeline completa di gestione dei dati meteorologici**, composta da:

1. **Acquisizione dei dati** da API meteorologiche esterne
2. **Persistenza dei dati storici**
3. **Comunicazione event-driven tra servizi**
4. **Analisi e interpolazione dei dati**
5. **Visualizzazione interattiva**

L’architettura separa chiaramente i livelli di:

- raccolta dati
- elaborazione
- visualizzazione

migliorando **manutenibilità, scalabilità e modularità del sistema**.

---

# 🧩 Architettura del sistema

La piattaforma è composta da diversi **microservizi indipendenti**, ciascuno responsabile di una specifica funzionalità.

| Servizio | Tecnologia | Ruolo |
|--------|--------|--------|
| meteo-core-service | Java + Spring Boot | acquisizione dati meteorologici |
| analysis-service | Python + FastAPI | analisi e interpolazione dei dati |
| frontend | React | interfaccia utente |
| meteo-db | PostgreSQL + TimescaleDB | storage dei dati meteorologici |
| RabbitMQ | message broker | comunicazione asincrona |
| Grafana | monitoring | dashboard e visualizzazione dati |

Tutti i servizi sono **containerizzati con Docker** e orchestrati tramite **Kubernetes**.

---

# 🏗 Diagramma Architetturale

```mermaid
flowchart LR

    subgraph Client
        U[Utente]
        FE[Frontend<br/>React]
    end

    subgraph Kubernetes Cluster
        CORE[meteo-core-service<br/>Spring Boot]
        AN[analysis-service<br/>FastAPI]
        RMQ[RabbitMQ]
        DB[(PostgreSQL + TimescaleDB)]
        GRAF[Grafana]
    end

    EXT[API Meteo Esterne<br/>Open-Meteo]

    U --> FE

    FE -->|REST API| CORE
    FE -->|REST API| AN

    CORE -->|Raccolta dati| EXT
    CORE -->|Salvataggio dati| DB
    CORE -->|Pubblica evento| RMQ

    RMQ -->|Consumo eventi| AN
    AN -->|Salvataggio risultati| DB

    GRAF -->|Dashboard e monitoraggio| DB

# 🌦️ Meteo Platform

### Piattaforma cloud-native per raccolta, analisi e visualizzazione di dati meteorologici

Questa piattaforma distribuita è progettata per la **raccolta, l'elaborazione e la visualizzazione di dati meteorologici in tempo reale**. Il progetto è stato sviluppato seguendo i principi delle **architetture a microservizi** e delle applicazioni **cloud-native**, dimostrando come costruire un sistema scalabile, resiliente e completamente containerizzato.

---

## 🎯 Obiettivi del Progetto

L’obiettivo è realizzare una **pipeline completa di data management**, strutturata in:

1.  **Acquisizione Resiliente**: Recupero dati da API meteorologiche (TorinoMeteo e Open-Meteo) con ottimizzazioni per limiti di rate-limiting e failover automatico su dati simulati (mock).
2.  **Persistenza**: Storage basato su PostgreSQL.
3.  **Comunicazione Asincrona**: Disaccoppiamento dei servizi tramite RabbitMQ.
4.  **Analisi**: Elaborazione e interpolazione geografica dei dati raccolti.
5.  **Visualizzazione**: Dashboard web interattive per l'utente finale e monitoraggi operativi.

---

## 🧩 Architettura del Sistema

Il sistema è composto da microservizi indipendenti distribuiti su un cluster Kubernetes.

| Servizio | Tecnologia | Ruolo |
| :--- | :--- | :--- |
| **meteo-core-service** | Java + Spring Boot | Acquisizione dati. Implementa circuit-breakers, cache locali e fallback provider per gestire instabilità di rete e ban IP. |
| **analysis-service** | Python + FastAPI | Analisi statistica e fornitura degli endpoint REST per il frontend. |
| **frontend** | React | Interfaccia utente interattiva mappa-centrica. |
| **meteo-db** | PostgreSQL | Database relazionale per le letture ambientali. |
| **RabbitMQ** | Message Broker | Coda di messaggi in tempo reale. |
| **Grafana** | Monitoring | Dashboard per stato del sistema. |

---

## 🌐 Networking e Ingress (Gateway API)

A differenza dei classici Ingress Controller, il traffico in ingresso al cluster è interamente gestito tramite **Cilium e Kubernetes Gateway API**.

Le richeste esterne arrivano al `Gateway` (esposto in LoadBalancer/NodePort) e vengono direzionate dalle risorse `HTTPRoute` agli appositi servizi:
* Le richieste a `/group-6/` e sottomenù caricano gli asset statici dell'applicazione **Frontend** in React (compilata con subpath relativo).
* Le chiamate API a `/group-6/api/v1/meteo/` vengono trasparentemente inoltrate (con path rewrite) al **meteo-core**.
* Le chiamate API a `/group-6/api/v1/analysis/` vengono instradate verso l'**analysis-service** (FastAPI).

Questo approccio offre routing avanzato di Layer 7 senza dipendere da annotazioni complesse come su Nginx-Ingress.

---

## 🛡 Resilienza e Strategie API (Important!)

Il sistema è altamente ottimizzato per operare in ambienti cluster condivisi, dove l'IP di uscita verso internet potrebbe essere limitato.

### Gestione Dati Esterni e Limitazioni (Rate Limiting)
A causa di firewall anti-bot o restrizioni gratuite (come le 10'000 daily read di Open-Meteo), l'applicativo non esegue continui ping:
1. **Polling a Bassa Frequenza**: `meteo-core` scarica i dati ambientali reali **esattamente una volta all'ora**.
2. **Batching**: I comuni (100+) vengono raggruppati in un'unica enorme richiesta API verso i provider.
3. **Mock Data Fallback**: Se le API primarie diventano inaccessibili causa restrizioni IP o firewall cloud, il sistema genera autonomamente dati meteorologici fittizi plausibili. La dashboard React non va mai offline, notificando l'utente quando i dati sono "simulati".
4. **Caching Prolungata**: Per coprire l'intero lasso di 60 minuti tra un aggiornamento e l'altro, il DB e le memorie locali servono come layer di cache. Se i servizi crollano momentaneamente, il frontend utilizza in modo trasparente l'ultima lettura storica utile.

---

## ☸️ Componenti Kubernetes

Il deploy copre tutti i principali *kind* di Kubernetes:

* **Deployment/StatefulSet**: Gestione delle repliche. Il DB usa `StatefulSet` per preservare il volume, gli altri sono stateless.
* **Service**: Esportano internamente i Pod collegandoli tra loro (es. `rabbitmq:5672`).
* **ConfigMap / Secrets**: Isola le credenziali (password Postgres, username Grafana).
* **PersistentVolumes / PVC**: Utilizzati in PostgreSQL e Grafana per non perdere mai lo stato al restart. Lo Strategy di deploy per i DB è impostato accuratamente su `Recreate` per bypassare i blocchi di "Multi-Attach" classici dei volumi RWO.

---

## 🔍 Monitoraggio

Il sistema integra **Grafana** pronto all'uso. I *dashboard provisioning file* vengono montati automaticamente all'avvio all'interno del container tramite `subPath` per visualizzare istantaneamente pannelli vitali senza click manuali.

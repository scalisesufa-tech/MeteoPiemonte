# Consegna Progetto CI/CD

**Nome e Cognome**: Alessandro Scalise e Xhoana Sufa
**Gruppo**: Gruppo 6
**Repository**: https://github.com/scalisesufa-tech/MeteoPiemonte.git
**Branch**: `iac`
**Branch per Argo CD**: `iac` (coincide)

## Note e Scelte di Design

*   **Umbrella Chart**: Abbiamo scelto di ristrutturare i microservizi (Meteo-DB, RabbitMQ, Grafana, Analysis-Service, ecc.) adottando un **Umbrella Chart** (`04-kubernetes/meteo-umbrella`). Questa scelta permette di centralizzare la gestione delle dipendenze e facilita notevolmente l'installazione e la manutenzione dell'intero stack come un'unica entità coesa.
*   **Gestione dei Values (`values.yaml`)**: L'uso dell'umbrella chart ci ha permesso di utilizzare il suo `values.yaml` come "single source of truth". Tramite questo file vengono iniettati in maniera parametrica e dinamica i valori necessari ai singoli subcharts. All'interno dei chart abbiamo implementato diverse pratiche di *Helm hardening* utilizzando la funzione `required` per rendere obbligatori i valori critici (ad es. password e host) ed evitare deployment silenti fallati.
*   **Semplificazione Argo CD**: In virtù dell'adozione dell'umbrella chart, abbiamo migrato la logica di deployment in Argo CD passando da un più complesso `ApplicationSet` (utile quando si hanno decine di chart indipendenti) ad una più solida ed elegante risorsa `Application` singola. Questa punta direttamente alla root dell'umbrella chart, offrendo così una vista aggregata di tutto lo stack applicativo all'interno della UI di ArgoCD e garantendo rollback e sync coesi.
*   **Template e Labeling**: I manifest YAML sono stati refattorizzati applicando consistentemente le label standard di Kubernetes (`app.kubernetes.io/*`) tramite file di helper, migliorando l'organizzazione e la pulizia del codice.

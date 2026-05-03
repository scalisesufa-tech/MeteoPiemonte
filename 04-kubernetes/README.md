# MeteoPiemonte - Kubernetes & Helm Deployment

Questo repository contiene la configurazione Infrastructure as Code (IaC) per il deploy della piattaforma MeteoPiemonte su Kubernetes. 
Il progetto è stato strutturato seguendo le best practice utilizzando un'architettura **Helm Umbrella Chart** e supporta il rilascio continuo tramite **ArgoCD**.

## Architettura Helm (Umbrella Chart)
Per massimizzare la riusabilità del codice (principio DRY) e mantenere l'ordine, i microservizi non vengono installati singolarmente ma sono tutti raggruppati sotto un'unica chart padre chiamata `meteo-umbrella`.
I microservizi inclusi come dipendenze sono:
- `meteo-core`: Backend Spring Boot principale
- `analysis-service`: Servizio in Python per l'analisi dati
- `frontend`: Interfaccia utente React
- `meteo-db`: PostgreSQL con estensione TimescaleDB
- `rabbitmq`: Message broker per la coda di elaborazione
- `redis`: Sistema di caching
- `grafana`: Dashboard di monitoraggio

## Installazione (Guida Pre/Post Deploy)

### Metodo 1: GitOps tramite ArgoCD (Raccomandato)
L'infrastruttura è predisposta per l'installazione dichiarativa via ArgoCD.
Assicurati di aver fatto il commit e push delle tue modifiche sul branch `iac`, dopodiché applica la configurazione di ArgoCD:

```bash
kubectl apply -f 04-kubernetes/meteo-application.yaml
```
ArgoCD prenderà in carico la chart `meteo-umbrella`, scaricherà le dipendenze e farà il deploy dell'intero stack nel namespace `group-6`.

### Metodo 2: Installazione manuale con Helm (Per sviluppo locale)
Se non utilizzi ArgoCD o vuoi testare la chart in locale, assicurati di aggiornare le dipendenze prima di installare:

```bash
cd 04-kubernetes/meteo-umbrella
helm dependency update
helm upgrade --install meteopiemonte-stack . -n group-6 --create-namespace
```

## Configurazione (Hardening & Values)
Tutte le configurazioni specifiche (variabili d'ambiente, limiti, credenziali) sono state astratte dai template e centralizzate nei file `values.yaml`.
Per sovrascrivere un parametro di un servizio specifico senza toccare il suo codice, puoi farlo dal `values.yaml` dell'Umbrella chart:

```yaml
# 04-kubernetes/meteo-umbrella/values.yaml
meteo-core:
  replicaCount: 3
```

## Highlights Architetturali
- **Gateway API**: Il routing non usa i vecchi Ingress, ma sfrutta il moderno Kubernetes Gateway API (tramite `HTTPRoute`). Le rotte sono configurate all'interno delle rispettive sub-chart.
- **Probe di Sicurezza**: Tutti i servizi sono dotati di `readinessProbe` e `livenessProbe` per garantire alta affidabilità ed evitare il routing del traffico verso pod non pronti.
- **Persistenza**: `meteo-db` e `grafana` usano `StatefulSet` e/o `PersistentVolumeClaim` con storage di classe `csi-cinder-fast` e una strategia che previene conflitti sul disco.

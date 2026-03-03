# Service Routing Patterns in Kubernetes

Questo documento descrive i diversi pattern di routing disponibili per l'API Gateway verso i microservizi in Kubernetes, con focus sul passaggio da Consul Discovery a DNS diretto.

## Indice

1. [Pattern Disponibili](#pattern-disponibili)
2. [Confronto Dettagliato](#confronto-dettagliato)
3. [Migrazione da Consul Discovery a DNS Diretto](#migrazione-da-consul-discovery-a-dns-diretto)
4. [Configurazione Attuale vs Nuova](#configurazione-attuale-vs-nuova)
5. [Testing e Verifica](#testing-e-verifica)

---

## Pattern Disponibili

### Pattern 1: Kubernetes Service DNS Diretto

**URI**: `http://service-name:port`

**Come funziona**:
- API Gateway fa richiesta HTTP diretta al Service di Kubernetes
- Kubernetes DNS risolve `catalog-service` → IP del Service ClusterIP
- Il Service K8s fa bilanciamento round-robin automatico tra i pod
- Nessuna discovery, nessuna API call, nessuna dependency aggiuntiva

**Configurazione**:
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: catalog-service
          uri: http://catalog-service:8081  # DNS diretto
          predicates:
            - Path=/api/v1/products/**
```

**Dependency**: Nessuna (solo Spring Cloud Gateway base)

**ServiceAccount**: ❌ Non necessario

---

### Pattern 2: Spring Cloud Kubernetes LoadBalancer

**URI**: `lb://service-name`

**Come funziona**:
- Spring Cloud LoadBalancer interroga l'API di Kubernetes
- Chiede a K8s API: "dimmi quali pod ci sono per catalog-service"
- Fa bilanciamento a livello applicativo con discovery da K8s API
- Richiede permessi RBAC (get pods, get endpoints)

**Configurazione**:
```yaml
spring:
  cloud:
    kubernetes:
      loadbalancer:
        enabled: true
    gateway:
      routes:
        - id: catalog-service
          uri: lb://catalog-service  # Con discovery da K8s API
          predicates:
            - Path=/api/v1/products/**
```

**Dependency**: `spring-cloud-starter-kubernetes-client-loadbalancer`

**ServiceAccount**: ✅ Necessario (per accedere all'API di Kubernetes)

---

### Pattern 3: Consul Discovery (Attuale)

**URI**: `lb://service-name`

**Come funziona**:
- Spring Cloud LoadBalancer interroga Consul
- Chiede a Consul: "dimmi quali istanze ci sono per catalog-service"
- Non tocca l'API di Kubernetes
- Fa bilanciamento a livello applicativo con discovery da Consul

**Configurazione**:
```yaml
spring:
  cloud:
    consul:
      discovery:
        enabled: true
        prefer-ip-address: true
    gateway:
      routes:
        - id: catalog-service
          uri: lb://catalog-service  # Con discovery da Consul
          predicates:
            - Path=/api/v1/products/**
```

**Dependency**: `spring-cloud-starter-consul-discovery`

**ServiceAccount**: ❌ Non necessario

---

## Confronto Dettagliato

| Caratteristica | Pattern 1: DNS Diretto | Pattern 2: K8s LoadBalancer | Pattern 3: Consul Discovery |
|----------------|------------------------|----------------------------|----------------------------|
| **URI** | `http://service-name:port` | `lb://service-name` | `lb://service-name` |
| **Dependency** | Nessuna | `spring-cloud-starter-kubernetes-client-loadbalancer` | `spring-cloud-starter-consul-discovery` |
| **ServiceAccount** | ❌ No | ✅ Sì (necessario) | ❌ No |
| **Bilanciamento** | Round-robin del Service K8s | Spring Cloud LoadBalancer | Spring Cloud LoadBalancer |
| **Discovery** | Nessuna (DNS) | K8s API | Consul |
| **Visibilità Pod** | ❌ Solo Service | ✅ Singoli pod | ✅ Singoli pod |
| **Health Check Pod** | ❌ No | ✅ Sì | ✅ Sì |
| **Controllo Bilanciamento** | ❌ Limitato | ✅ Avanzato | ✅ Avanzato |
| **Complessità** | ⭐ Bassa | ⭐⭐⭐ Media | ⭐⭐ Media |
| **Performance** | ⭐⭐⭐ Ottima | ⭐⭐ Buona | ⭐⭐ Buona |
| **Monitoring** | ⭐ Limitato | ⭐⭐⭐ Completo | ⭐⭐⭐ Completo |

---

## Bilanciamento del Carico: Dettagli Tecnici

### Pattern 1: Kubernetes Service (DNS Diretto)

**Algoritmo**: Round-robin stateless  
**Livello**: Layer 4 (TCP/UDP)  
**Meccanismo**: kube-proxy con iptables/IPVS  
**Basato su**: Pod Ready/Not Ready (readiness probe)  
**Considera carico**: ❌ **NO** - distribuisce equamente tra tutti i pod Ready  

**Come funziona**:
1. Kubernetes DNS risolve `catalog-service` → ClusterIP del Service
2. kube-proxy (su ogni nodo) gestisce le regole iptables/IPVS
3. Ogni connessione TCP viene distribuita in round-robin tra i pod Ready
4. Se un pod diventa Not Ready, viene rimosso automaticamente dal pool
5. **NON** considera:
   - Carico CPU/Memory del pod
   - Numero di connessioni attive
   - Tempo di risposta
   - Metriche applicative

**Vantaggi**:
- ✅ Molto veloce (kernel-level, iptables/IPVS)
- ✅ Trasparente (nessuna configurazione necessaria)
- ✅ Automatico (si aggiorna quando pod cambiano stato)

**Limitazioni**:
- ❌ Solo round-robin (non configurabile)
- ❌ Non considera il carico reale
- ❌ Stateless (ogni connessione può andare a pod diversi)

---

### Pattern 3: Spring Cloud LoadBalancer + Consul Discovery

**Algoritmo**: Round-robin (default, configurabile)  
**Livello**: Layer 7 (HTTP)  
**Meccanismo**: Spring Cloud LoadBalancer (client-side)  
**Basato su**: Istanze healthy in Consul  
**Considera carico**: ❌ **NO** di default (ma configurabile)  

**Come funziona**:
1. Spring Cloud LoadBalancer interroga Consul per ottenere le istanze
2. Filtra solo le istanze con health check "passing" in Consul
3. Applica algoritmo di bilanciamento (default: round-robin)
4. Seleziona un'istanza e fa la richiesta HTTP direttamente al pod IP
5. **NON** considera di default:
   - Carico CPU/Memory
   - Numero di richieste attive
   - Tempo di risposta
   - Metriche applicative

**Algoritmi disponibili** (configurabili):
- `RoundRobinLoadBalancer` (default)
- `RandomLoadBalancer`
- `WeightedResponseTimeLoadBalancer` (basato su tempo di risposta)
- Custom `ReactorLoadBalancer` implementations

**Vantaggi**:
- ✅ Configurabile (puoi cambiare algoritmo)
- ✅ Health-aware (solo istanze healthy)
- ✅ Client-side (più controllo)
- ✅ Possibilità di implementare algoritmi custom

**Limitazioni**:
- ❌ Default: non considera il carico reale
- ❌ Overhead di discovery (query a Consul)
- ❌ Client-side (ogni client deve fare discovery)

**Configurazione avanzata** (esempio):
```yaml
spring:
  cloud:
    loadbalancer:
      configurations: default
      # Puoi configurare algoritmi custom
      # WeightedResponseTimeLoadBalancer considera il tempo di risposta
```

---

### Confronto: Bilanciamento su Carico

| Aspetto | Kubernetes Service | Consul + Spring Cloud LoadBalancer |
|---------|-------------------|-----------------------------------|
| **Considera carico CPU/Memory** | ❌ No | ❌ No (ma configurabile) |
| **Considera connessioni attive** | ❌ No | ❌ No (ma configurabile) |
| **Considera tempo di risposta** | ❌ No | ⚠️ Sì (con `WeightedResponseTimeLoadBalancer`) |
| **Considera health check** | ✅ Sì (readiness probe) | ✅ Sì (Consul health check) |
| **Configurabile** | ❌ No | ✅ Sì (algoritmi custom) |

**Conclusione**: 
- **Nessuno dei due** considera il carico reale (CPU/Memory) di default
- **Kubernetes**: Sempre round-robin, non configurabile
- **Consul**: Round-robin di default, ma puoi configurare algoritmi più sofisticati (es. basati su tempo di risposta)
- Per bilanciamento basato su carico reale, servono soluzioni più avanzate (es. Istio, Linkerd, o metriche custom)

### Vantaggi Pattern 1 (DNS Diretto)

✅ **Semplicità**: Nessuna dependency aggiuntiva, nessun ServiceAccount  
✅ **Performance**: Routing diretto, nessuna overhead di discovery  
✅ **Affidabilità**: Usa l'infrastruttura nativa di Kubernetes  
✅ **Manutenzione**: Meno componenti da gestire  

### Svantaggi Pattern 1 (DNS Diretto)

❌ **Visibilità**: Non puoi vedere i singoli pod, solo il Service  
❌ **Controllo**: Meno controllo sul bilanciamento (solo round-robin)  
❌ **Health Check**: Non puoi fare health check per singolo pod  
❌ **Monitoring**: Meno dettagli per il monitoring  

---

## Migrazione da Consul Discovery a DNS Diretto

### Step 1: Rimuovere Dependency Consul Discovery

**File**: `03b-microservices-async/api-gateway/pom.xml`

```xml
<!-- RIMUOVERE questa dependency -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-consul-discovery</artifactId>
</dependency>
```

### Step 2: Aggiornare application.yml

**File**: `03b-microservices-async/api-gateway/src/main/resources/application.yml`

**PRIMA (Consul Discovery)**:
```yaml
spring:
  application:
    name: api-gateway

  cloud:
    consul:
      host: ${CONSUL_HOST:localhost}
      port: ${CONSUL_PORT:8500}
      discovery:
        service-name: ${spring.application.name}
        health-check-path: /actuator/health
        health-check-interval: 10s
        enabled: true
        prefer-ip-address: true

    gateway:
      routes:
        - id: catalog-service
          uri: lb://catalog-service  # Con Consul discovery
          predicates:
            - Path=/api/v1/products/**
          filters:
            - StripPrefix=0

        - id: inventory-service
          uri: lb://inventory-service  # Con Consul discovery
          predicates:
            - Path=/api/v1/inventory/**
          filters:
            - StripPrefix=0
```

**DOPO (DNS Diretto)**:
```yaml
spring:
  application:
    name: api-gateway

  cloud:
    # Consul discovery rimosso - non più necessario
    gateway:
      routes:
        - id: catalog-service
          uri: http://catalog-service:8081  # DNS diretto
          predicates:
            - Path=/api/v1/products/**
          filters:
            - StripPrefix=0

        - id: inventory-service
          uri: http://inventory-service:8082  # DNS diretto
          predicates:
            - Path=/api/v1/inventory/**
          filters:
            - StripPrefix=0

        # Swagger UI routes - Catalog Service
        - id: swagger-catalog
          uri: http://catalog-service:8081  # DNS diretto
          predicates:
            - Path=/swagger/catalog/**
          filters:
            - RewritePath=/swagger/catalog/(?<segment>.*), /$\{segment}
            - name: OpenApiResponseModify
              args:
                baseUrl: ${SWAGGER_BASE_URL:https://130.192.100.243/group-1}

        # Swagger UI routes - Inventory Service
        - id: swagger-inventory
          uri: http://inventory-service:8082  # DNS diretto
          predicates:
            - Path=/swagger/inventory/**
          filters:
            - RewritePath=/swagger/inventory/(?<segment>.*), /$\{segment}
            - name: OpenApiResponseModify
              args:
                baseUrl: ${SWAGGER_BASE_URL:https://130.192.100.243/group-1}
```

### Step 3: Rimuovere Variabili d'Ambiente Consul (Opzionale)

**File**: `04-kubernetes/manifests/deployments/api-gateway-deployment.yaml`

Se non usi più Consul per discovery, puoi rimuovere:
- `SPRING_CLOUD_CONSUL_DISCOVERY_INSTANCE_ID` (non più necessario)
- Variabili `CONSUL_HOST`, `CONSUL_PORT` dal ConfigMap (se non usate per altro)

**NOTA**: Se vuoi mantenere Consul solo per monitoring (senza usarlo per routing), puoi lasciare la registrazione Consul nei microservizi ma rimuoverla dall'API Gateway.

### Step 4: Verificare che i Service K8s Esistano

I Service di Kubernetes devono esistere e funzionare correttamente:

```bash
# Verificare i Service
kubectl get services -n group-1

# Verificare gli endpoints (devono avere pod associati)
kubectl get endpoints -n group-1

# Test DNS interno
kubectl run -it --rm debug --image=busybox --restart=Never -n group-1 -- \
  nslookup catalog-service
```

**File da verificare**:
- `04-kubernetes/manifests/services/catalog-service-service.yaml`
- `04-kubernetes/manifests/services/inventory-service-service.yaml`

### Step 5: Rebuild e Deploy

```bash
# Rebuild dell'immagine API Gateway
cd 03b-microservices-async/api-gateway
mvn clean package
docker build -t docker.io/bortol88/03b-microservices-async-api-gateway:latest .
docker push docker.io/bortol88/03b-microservices-async-api-gateway:latest

# Restart del deployment
kubectl rollout restart deployment api-gateway -n group-1
```

### Step 6: Verificare i Log

```bash
# Verificare che non ci siano errori di discovery
kubectl logs -f deployment/api-gateway -n group-1 | grep -i consul

# Dovresti vedere che le richieste vanno direttamente ai Service
kubectl logs -f deployment/api-gateway -n group-1 | grep -i "catalog-service\|inventory-service"
```

---

## Configurazione Attuale vs Nuova

### Configurazione Attuale (Pattern 3: Consul Discovery)

**API Gateway**:
- Dependency: `spring-cloud-starter-consul-discovery`
- URI: `lb://catalog-service` (risolto via Consul)
- ServiceAccount: Non necessario
- Discovery: Consul

**Microservizi**:
- Registrazione su Consul con `instance-id` unico
- Health check su Consul per ogni pod
- Visibilità completa in Consul UI

**Vantaggi Attuali**:
- ✅ Visibilità completa dei pod in Consul
- ✅ Health check per singolo pod
- ✅ Monitoring avanzato
- ✅ Nessun ServiceAccount necessario

### Configurazione Nuova (Pattern 1: DNS Diretto)

**API Gateway**:
- Dependency: Nessuna (solo Spring Cloud Gateway)
- URI: `http://catalog-service:8081` (DNS diretto)
- ServiceAccount: Non necessario
- Discovery: Nessuna (DNS nativo K8s)

**Microservizi**:
- Possono ancora registrarsi su Consul per monitoring (opzionale)
- Health check gestito da Kubernetes (readiness probe)
- Visibilità limitata (solo Service, non singoli pod)

**Vantaggi Nuovi**:
- ✅ Semplicità massima
- ✅ Performance migliori (nessun overhead discovery)
- ✅ Meno componenti da gestire
- ✅ Affidabilità (infrastruttura nativa K8s)

**Svantaggi**:
- ❌ Meno visibilità sui singoli pod
- ❌ Meno controllo sul bilanciamento
- ❌ Monitoring meno dettagliato

---

## Testing e Verifica

### Test 1: Verificare DNS Resolution

```bash
# Test DNS da dentro un pod
kubectl run -it --rm debug --image=busybox --restart=Never -n group-1 -- \
  nslookup catalog-service.group-1.svc.cluster.local

# Dovrebbe risolvere l'IP del Service ClusterIP
```

### Test 2: Verificare Routing API Gateway

```bash
# Test endpoint prodotti
curl -k https://130.192.100.243/group-1/api/v1/products?page=0&size=10

# Test endpoint inventory
curl -k https://130.192.100.243/group-1/api/v1/inventory/1

# Verificare che le richieste vadano ai Service
kubectl logs -f deployment/api-gateway -n group-1
```

### Test 3: Verificare Bilanciamento

```bash
# Fare più richieste e verificare che vadano a pod diversi
for i in {1..10}; do
  curl -k https://130.192.100.243/group-1/api/v1/products?page=0&size=1
  echo ""
done

# Verificare nei log dei microservizi che le richieste siano distribuite
kubectl logs -f deployment/catalog-service -n group-1
```

### Test 4: Verificare Health Check

```bash
# Verificare che i pod siano healthy
kubectl get pods -n group-1

# Verificare che i Service abbiano endpoints
kubectl get endpoints -n group-1

# Test health check diretto
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n group-1 -- \
  curl http://catalog-service:8081/actuator/health
```

### Test 5: Verificare Swagger UI

```bash
# Test Swagger Catalog
curl -k https://130.192.100.243/group-1/swagger/catalog/swagger-ui.html

# Test Swagger Inventory
curl -k https://130.192.100.243/group-1/swagger/inventory/swagger-ui.html
```

---

## Rollback

Se qualcosa non funziona, puoi fare rollback:

1. **Ripristinare dependency Consul**:
   ```xml
   <dependency>
       <groupId>org.springframework.cloud</groupId>
       <artifactId>spring-cloud-starter-consul-discovery</artifactId>
   </dependency>
   ```

2. **Ripristinare application.yml** con `lb://` e configurazione Consul

3. **Rebuild e redeploy**

---

## Note Finali

- **Consul può rimanere**: I microservizi possono continuare a registrarsi su Consul per monitoring, anche se l'API Gateway non lo usa più per routing
- **Service K8s obbligatori**: I Service di Kubernetes devono esistere e funzionare correttamente
- **DNS interno**: Il DNS funziona solo all'interno del cluster Kubernetes
- **Bilanciamento**: Il Service K8s fa round-robin automatico tra i pod healthy

---

## Checklist Migrazione

- [ ] Rimuovere `spring-cloud-starter-consul-discovery` da `pom.xml`
- [ ] Aggiornare `application.yml` con URI `http://service-name:port`
- [ ] Aggiornare tutte le route (catalog, inventory, swagger)
- [ ] Verificare che i Service K8s esistano e abbiano endpoints
- [ ] Rebuild immagine API Gateway
- [ ] Push immagine Docker
- [ ] Restart deployment API Gateway
- [ ] Verificare log per errori
- [ ] Test endpoint API
- [ ] Test Swagger UI
- [ ] Verificare bilanciamento
- [ ] Documentare cambiamenti

---

**Data creazione**: 2026-02-15  
**Ultima modifica**: 2026-02-15  
**Autore**: CoreP Team

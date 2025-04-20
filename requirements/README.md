# Deployment Guide: Kafka, Redis, and MongoDB

This guide provides step-by-step instructions to deploy Kafka using Strimzi, Redis from Bitnami, and MongoDB from Bitnami in a Kubernetes environment.

## 1. Deploy Kafka with Strimzi

### Step 1: Create a Namespace for Kafka
```bash
kubectl create namespace kafka
```

### Step 2: Install Strimzi Kafka Operator
```bash
kubectl apply -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka
```

### Step 3: Deploy Kafka Cluster
Apply the Kafka cluster configuration:
```bash
kubectl apply -f kafka-cluster.yaml -n kafka
```

### Step 4: Create Kafka Topics
Apply the Kafka topics configuration:
```bash
kubectl apply -f kafka-topics.yaml -n kafka
```

---

## 2. Deploy Redis from Bitnami

### Step 1: Add the Bitnami Helm Repository
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### Step 2: Install Redis
```bash

kubectl create namespace redis

helm install my-redis -f redis-values.yaml bitnami/redis -n redis
```

### Step 3: Access Redis

#### Redis can be accessed on the following DNS names within your cluster:
- `my-redis-master.redis.svc.cluster.local` for read/write operations (port 6379)
- `my-redis-replicas.redis.svc.cluster.local` for read-only operations (port 6379)

#### To retrieve your Redis password:
```bash
export REDIS_PASSWORD=$(kubectl get secret --namespace redis my-redis -o jsonpath="{.data.redis-password}" | base64 -d)
```

#### To connect to your Redis server:

1. **Run a Redis pod to use as a client:**
    ```bash
    kubectl run --namespace redis redis-client --restart='Never' --env REDIS_PASSWORD=$REDIS_PASSWORD --image docker.io/bitnami/redis:7.2.5-debian-12-r0 --command -- sleep infinity
    ```

    **Attach to the pod:**
    ```bash
    kubectl exec --tty -i redis-client --namespace redis -- bash
    ```

2. **Connect using the Redis CLI:**
    ```bash
    REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli -h my-redis-master
    REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli -h my-redis-replicas
    ```

#### To connect to your Redis database from outside the cluster:
```bash
kubectl port-forward --namespace redis svc/my-redis-master 6379:6379 &
REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli -h 127.0.0.1 -p 6379
```

---

## 3. Deploy MongoDB from Bitnami

### Step 1: Add the Bitnami Helm Repository (if not already added)
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### Step 2: Install MongoDB
```bash

kubectl create namespace mongodb

#helm search repo bitnami/mongodb  --versions
#helm show values bitnami/mongodbi --version 16.0.3 > mongodb-values.yaml


helm install my-mongodb -f mongodb-values.yaml bitnami/mongodb -n mongodb
```

### Step 3: Access MongoDB

#### MongoDB can be accessed on the following DNS names within your cluster:
- `my-mongodb.mongodb.svc.cluster.local` for the MongoDB primary (port 27017)
- `my-mongodb-secondary.mongodb.svc.cluster.local` for MongoDB secondaries (port 27017)

#### To retrieve your MongoDB password:
```bash
export MONGODB_ROOT_PASSWORD=$(kubectl get secret --namespace mongodb my-mongodb -o jsonpath="{.data.mongodb-root-password}" | base64 -d)
```

#### To connect to your MongoDB server:

1. **Run a MongoDB pod to use as a client:**
    ```bash
    kubectl run --namespace mongodb mongodb-client --restart='Never' --env MONGODB_ROOT_PASSWORD=$MONGODB_ROOT_PASSWORD --image docker.io/bitnami/mongodb:6.0.9-debian-12-r0 --command -- sleep infinity
    ```

    **Attach to the pod:**
    ```bash
    kubectl exec --tty -i mongodb-client --namespace mongodb -- bash
    ```

2. **Connect using the MongoDB CLI:**
    ```bash
    mongo --host my-mongodb.mongodb.svc.cluster.local -u root -p $MONGODB_ROOT_PASSWORD
    ```

#### To connect to your MongoDB database from outside the cluster:
```bash
kubectl port-forward --namespace mongodb svc/my-mongodb 27017:27017 &
mongo --host 127.0.0.1 --port 27017 -u root -p $MONGODB_ROOT_PASSWORD
```

--------------

deploy minio:

kubectl apply -k "github.com/minio/operator?ref=v6.0.3"

kubectl create namespace minio-tenant

kubectl create secret generic minio-creds-secret \
  --from-literal=accesskey=minio-access-key \
  --from-literal=secretkey=minio-secret-key \
  -n minio-tenant

kubectl apply -f minio-tenant.yaml

kubectl port-forward svc/myminio-console 9443:9443 -n minio-tenant

use minio ui to certe buckets and secret adn access key

helm upgrade --install tempo grafana/tempo-distributed --values tempo-values.yaml -n tracing




curl -L https://istio.io/downloadIstio | sh -

export PATH="$PATH:/Users/Majid/tracing-enabled-microservices-with-opentelemetry/requirements/istio-1.23.2/bin"

istioctl x precheck

cd istio-1.23.2

istioctl install -f IstioOperator.yaml --skip-confirmation

kubectl rollout restart deployment istiod -n istio-system

kubectl get configmap istio -n istio-system -o yaml


kubectl label namespace default istio-injection=enabled

kubectl apply -f rke2-ingress-nginx-config.yaml

kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null || \
{ kubectl kustomize "github.com/kubernetes-sigs/gateway-api/config/crd?ref=v1.1.0" | kubectl apply -f -; }

kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.23/samples/bookinfo/platform/kube/bookinfo.yaml


kubectl exec "$(kubectl get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" -c ratings -- curl -sS productpage:9080/productpage | grep -o "<title>.*</title>"


kubectl apply -f samples/bookinfo/gateway-api/bookinfo-gateway.yaml

kubectl annotate gateway bookinfo-gateway networking.istio.io/service-type=ClusterIP --namespace=default

kubectl get gateway

kubectl port-forward svc/bookinfo-gateway-istio 8080:80


kubectl apply -f samples/addons/kiali.yaml


istioctl dashboard kiali


rebuilt the dockerfiel for arm:
sudo docker buildx build --platform linux/amd64,linux/arm64 -t majidni/tracing-demo-app:0e3fa54f67fa2ba430d4bbcc343d01f56d7de0e9 --push .

helm install my-app ./charts/test-app

kubectl logs rancher-logging-root-fluentd-0 -n cattle-logging-system

kubectl apply -f - --namespace=default <<"EOF"
apiVersion: logging.banzaicloud.io/v1beta1
kind: Flow
metadata:
  name: api-gw-flow
  namespace: default
spec:
  filters:
    - tag_normaliser: {}
  globalOutputRefs: []
  localOutputRefs:
    - test-app-output
  match:
    - select:
        labels:
          app: test-app-api-gateway
EOF

kubectl apply -f - --namespace=default <<"EOF"
apiVersion: logging.banzaicloud.io/v1beta1
kind: Flow
metadata:
  name: data-processor-flow
  namespace: default
spec:
  filters:
    - tag_normaliser: {}
  globalOutputRefs: []
  localOutputRefs:
    - test-app-output
  match:
    - select:
        labels:
          app: test-app-data-processor
EOF

kubectl apply -f - --namespace=default <<"EOF"
apiVersion: logging.banzaicloud.io/v1beta1
kind: Output
metadata:
  name: test-app-output
  namespace: default
spec:
  loki:
    buffer:
      chunk_limit_size: 2MB
      flush_interval: 3s
      flush_mode: interval
      queue_limit_length: 1024
    configure_kubernetes_labels: true
    url: http://loki-gateway.loki.svc.cluster.local
EOF
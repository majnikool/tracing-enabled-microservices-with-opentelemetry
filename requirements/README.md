# Deployment Guide: Kafka, Redis, and MongoDB

This guide provides step-by-step instructions to deploy Kafka using Strimzi, Redis from Bitnami, and MongoDB from Bitnami in a Kubernetes environment.

## 1. Deploy Kafka with Strimzi

### Step 1: Create a Namespace for Kafka
```bash
kubectl create namespace kafka
```

### Step 2: Install Strimzi Kafka Operator
```bash
kubectl apply -f https://strimzi.io/install/latest?namespace=kafka -n kafka
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


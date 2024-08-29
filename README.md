# Microservices Architecture with API Gateway and Data Processor

This repository contains a microservices architecture consisting of an API Gateway and a Data Processor service, both communicating through Apache Kafka. The system is designed to handle CRUD operations for a car database, with distributed tracing and logging capabilities.

## Goal of the Application

The primary goal of this application is to test and demonstrate effective tracing and logging in a microservices architecture. It serves as a practical example of how to implement and utilize distributed tracing and centralized logging across multiple services.

## Architecture Overview

1. **API Gateway**: Serves as the entry point for client requests, handles HTTP endpoints, and communicates with the Data Processor through Kafka.
2. **Data Processor**: Processes requests from the API Gateway, interacts with the MongoDB database, and sends responses back through Kafka.
3. **Apache Kafka**: Acts as a message broker between the API Gateway and Data Processor.
4. **MongoDB**: Stores the car data.
5. **Redis**: Used for caching in the API Gateway to improve response times.
6. **OpenTelemetry**: Provides distributed tracing across the microservices.

## Prerequisites

- Kubernetes cluster
- Helm 3+
- Apache Kafka
- MongoDB
- Redis

You can refer to the requirements folder for example deployments of Kafka, Mongo, and Redis.


## Deployment

This application can be deployed using Helm. A Helm chart is available in the `charts` directory of this repository.

To deploy the application:

1. Ensure you have Helm installed and configured with your Kubernetes cluster.

2. From the root of the repository, run:
   ```
   helm install my-app ./charts/test-app
   ```

   Replace `my-app` with your preferred release name.

3. For custom configurations, you can create a `values.yaml` file and use it during installation:
   ```
   helm install my-app ./charts/test-app -f my-values.yaml
   ```

## Usage

The API Gateway exposes the following endpoints:

- `GET /myapi/{id}`: Retrieve a car by ID
- `PUT /myapi/{id}`: Create or update a car
- `PATCH /myapi/{id}`: Partially update a car
- `DELETE /myapi/{id}`: Delete a car

### Example Usage

1. Create or update a car:
   ```
   curl -k -XPUT -H "Content-type: application/json" -d \
   '{"name": "backuptest", "price": 67676, "year": "2022"}' \
   'https://app.domain.com/myapi/10'
   ```

2. Retrieve a car:
   ```
   curl -k -XGET -H "Content-type: application/json"  \
   'https://app.domain.com/myapi/10'
   ```

## Monitoring and Tracing

The application is instrumented with OpenTelemetry for distributed tracing. Tracing data is sent to the specified OTLP endpoint. Logs are centralized and can be accessed through your configured logging solution.

## Continuous Integration and Deployment

This project uses GitHub Actions for CI/CD. The workflow is defined in `.github/workflows/ci-cd.yml`. It automatically builds and packages the application when changes are pushed to the repository.

The workflow includes:
- Checking for changes in the `source_code/` directory
- Building the Python package
- Building and pushing a Docker image to Docker Hub

The Docker image is tagged with the git commit hash and labeled with the release version and branch name.


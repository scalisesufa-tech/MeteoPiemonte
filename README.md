🌦️ Meteo Platform
Cloud-native microservices architecture for real-time weather data collection, analysis and visualization

This project implements a cloud-native platform for collecting, processing and visualizing meteorological data in real time.

The system is designed using a microservices architecture, where each component performs a specific task and communicates with other services through REST APIs and asynchronous messaging.

The platform demonstrates how to design a scalable, resilient and containerized distributed system, leveraging modern technologies such as:

Docker

Kubernetes

Spring Boot

FastAPI

RabbitMQ

PostgreSQL / TimescaleDB

React

Grafana

🎯 Project Goals

The goal of the project is to implement a complete data pipeline for meteorological data that includes:

Data ingestion from external weather APIs

Persistent storage of historical weather data

Event-driven communication between services

Data analysis and spatial interpolation

Visualization through interactive dashboards

The architecture separates clearly the responsibilities of data ingestion, processing and visualization, improving maintainability and scalability.

🧩 System Architecture

The platform is composed of several independent microservices, each deployed as a container.

Main components:

Service	Technology	Responsibility
meteo-core-service	Java + Spring Boot	collects weather data from external APIs
analysis-service	Python + FastAPI	performs data analysis and interpolation
frontend	React	user interface and data visualization
meteo-db	PostgreSQL + TimescaleDB	persistent time-series data storage
RabbitMQ	message broker	asynchronous communication
Grafana	monitoring	dashboards and metrics visualization

Each component runs inside its own container and is orchestrated through Kubernetes.

🏗 Architecture Design
Microservices Architecture

The system follows a microservices approach, where the application is decomposed into independent services that communicate over the network.

Benefits of this architecture include:

independent development and deployment

better fault isolation

independent scaling of components

easier maintainability

Each service is responsible for a specific domain of the application, reducing coupling between components.

Event-Driven Communication

Services communicate using RabbitMQ, implementing an event-driven architecture.

Instead of tightly coupling services through synchronous calls, events are published to a message queue and consumed asynchronously.

Advantages:

loose coupling between services

buffering of workload spikes

improved resilience

better scalability

Example flow:

Weather API → Core Service → RabbitMQ → Analysis Service → Database
🐳 Containerization with Docker

All services are packaged as Docker containers.

Docker provides:

consistent runtime environments

isolation of dependencies

portability across systems

simplified deployment

Each microservice has its own Docker image, enabling independent deployment and updates.

☸️ Deployment with Kubernetes

The platform is orchestrated using Kubernetes, which manages container deployment, networking and scaling.

Key Kubernetes resources used in this project include:

Resource	Purpose
Pod	smallest deployable unit
Deployment	manages stateless service replicas
StatefulSet	manages stateful components
Service	provides stable networking endpoints
Namespace	logical isolation of resources

This architecture allows the platform to run in a clustered and scalable environment.

⚙️ Configuration Management

Application configuration is externalized using Kubernetes resources:

ConfigMap

Used for non-sensitive configuration values, such as:

application parameters

environment variables

service configuration

This allows the same container image to run in multiple environments.

Secrets

Sensitive information such as:

database credentials

API tokens

access keys

is stored using Kubernetes Secrets, avoiding exposure in source code or container images.

💾 Persistent Storage

The platform stores meteorological data using PostgreSQL with TimescaleDB, which is optimized for time-series workloads.

Kubernetes persistent storage is managed through:

PersistentVolume

PersistentVolumeClaim

This ensures that data remains available even if containers are restarted or rescheduled.

🔄 Data Flow

The main workflow of the platform is the following:

The Core Service periodically queries external weather APIs.

Retrieved data is normalized and stored in the database.

An event is published to RabbitMQ.

The Analysis Service consumes the event and performs calculations.

Results are exposed via REST APIs.

The Frontend visualizes the data through charts and maps.

📊 Data Visualization

The frontend application provides interactive visualization tools using:

Leaflet for geographic maps

Recharts for time-series charts

Features include:

weather station visualization

spatial interpolation maps

historical data comparison

interactive metric selection

🛡 Resilience

The system is designed to be resilient to failures by leveraging several architectural mechanisms.

Service Isolation

Each microservice runs independently, preventing failures from propagating across the entire system.

Message Queue Buffering

RabbitMQ decouples producers and consumers.

If one service becomes temporarily unavailable:

messages remain in the queue

consumers can process them later

This prevents data loss and improves system reliability.

Container Restart Policies

Kubernetes automatically restarts failed containers, ensuring continuous service availability.

📈 Scalability

The architecture is designed to scale horizontally.

Horizontal Scaling

Stateless services such as:

API services

analysis services

frontend

can be scaled by increasing the number of replicas using Kubernetes Deployments.

Independent Scaling

Because services are independent, each component can scale separately depending on workload.

Example:

heavy data ingestion → scale core service

heavy analytics → scale analysis service

This avoids scaling the entire system unnecessarily.

🧠 Kubernetes Scheduling

Kubernetes automatically decides where to run containers using the scheduler.

The scheduler selects nodes based on:

available resources (CPU, memory)

node labels

scheduling policies

Advanced scheduling strategies can include:

Node Affinity

Allows services to run on specific nodes.

Example:

database pods on nodes with SSD storage

compute workloads on high-CPU nodes

Taints and Tolerations

Nodes can be reserved for specific workloads.

Example:

GPU nodes reserved for ML tasks

infrastructure nodes dedicated to monitoring services

This mechanism ensures efficient resource allocation within the cluster.

🔍 Monitoring

The platform integrates Grafana dashboards for monitoring and data visualization.

Grafana provides:

real-time data visualization

operational metrics

system observability

This helps detect anomalies and analyze system behavior.

🚀 Future Improvements

Potential extensions of the platform include:

autoscaling using Kubernetes HPA

distributed tracing

caching of analytical results

streaming analytics with Kafka

machine learning forecasting models

🧑‍💻 Technologies Used

Backend

Spring Boot

FastAPI

Python

Java

Infrastructure

Docker

Kubernetes

RabbitMQ

Database

PostgreSQL

TimescaleDB

Frontend

React

Leaflet

Recharts

Monitoring

Grafana

📚 Educational Context

This project was developed as part of a Cloud Computing and Microservices course, with the objective of demonstrating practical usage of:

containerization

distributed systems

microservices architecture

event-driven communication

Kubernetes orchestration

📦 Repository Structure

Example structure:

meteo-platform
│
├── core-service
├── analysis-service
├── frontend
├── database
├── kubernetes
├── docker
└── monitoring

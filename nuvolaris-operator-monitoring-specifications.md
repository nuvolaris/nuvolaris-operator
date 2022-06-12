## SRS For Nuvolaris Monitoring System - version 0.1.0

This document contains the software requirements specification (from hereon 'SRS') for the system (included in [Nuvolaris](https://github.com/nuvolaris/nuvolaris)) that will monitor the Nuvolaris component currently known as [nuvolaris-operator](https://github.com/nuvolaris/nuvolaris-operator) (from hereon 'the Operator').

The monitoring system must be based on __[Prometheus](https://prometheus.io/)__ and must expose its metrics to __[Grafana](https://grafana.com/docs/grafana/latest/getting-started/getting-started-prometheus/)__ to generate interactive dashboards. __[Dynamic service discovery](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config)__ is natively supported for Kubernetes-based deployments.

>### Prometheus glossary:
>
>- an endpoint you can scrape is called an ___instance___, usually corresponding to a single process. 
>- A collection of instances with the same purpose, a process replicated for scalability or reliability for example, is called a ___job___
>- ___Federation___ allows a Prometheus server to scrape selected time series from another Prometheus server.
>- ___Hierarchical federation___ allows Prometheus to scale to environments with tens of data centers and millions of nodes. In this use case, the federation topology resembles a tree.
>- In ___cross-service federation___, a Prometheus server of one service is configured to scrape selected data from another service's Prometheus server to enable alerting and queries against both datasets within a single server.
>- The Prometheus ___[Node Exporter](https://github.com/prometheus/node_exporter)___ exposes a wide variety of hardware- and kernel-related metrics.

## Requirements

The monitoring system __must__:
#### 1. Provide an endpoint for the Operator to expose its state
To expose the state of the Operator we can push custom metrics to a Prometheus server via a [custom exporter](https://prometheus.io/docs/instrumenting/exporters/) (a candidate could be [JSONExporter](https://github.com/prometheus-community/json_exporter)), suitable for long-running jobs, or via the [PushGateway](https://prometheus.io/docs/instrumenting/pushing/), suitable for monitoring shorter lived tasks. A new Kopf operator monitoring the Operator can take care of pushing/exporting metrics to Prometheus.

#### 2.   Provide an endpoint to expose the state of the [nuvolaris-controller ](https://github.com/nuvolaris/nuvolaris-controller) (from hereon 'the Controller')
See __(1)__. A new Kopf operator monitoring the Controller can take care of pushing/exporting metrics to Prometheus.

#### 3.   Provide an endpoint to expose the state of couchbd
An [unofficial CouchDB exporter](https://github.com/gesellix/couchdb-prometheus-exporter) already exists. We could include it as a sub-module in the operator and modify it to suit our needs or choose a simpler solution based on a Kopf operator pushing/exporting metrics to Prometheus.

#### 4.   Detect issues with memory, cpu and disk
Monitoring Linux host metrics can be done through the [Node Exporter](https://prometheus.io/docs/guides/node-exporter/), which exposes a wide variety of hardware- and kernel-related metrics.
#### 5.   Include dashboards for Grafana
The [Node Exporter](https://prometheus.io/docs/guides/node-exporter/) instrument also [acts as an interface with Grafana](https://grafana.com/docs/grafana/latest/getting-started/getting-started-prometheus/).
#### 6.   Include a way to send notifications when something is wrong
Prometheus has a [batteries-included alerting system](https://prometheus.io/docs/alerting/latest/alertmanager/).
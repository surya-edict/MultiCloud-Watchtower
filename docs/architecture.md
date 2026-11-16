# Architecture Overview

## 4-layer Design

### Layer 1 — Data Sources
- AWS Cost Explorer
- GCP Billing export via BigQuery
- Azure Cost Management API

### Layer 2 — Python Collectors
- [aws.py](../src/collectors/aws.py) fetches AWS cost and usage data
- [gcp.py](../src/collectors/gcp.py) queries the GCP billing export
- [azure.py](../src/collectors/azure.py) pulls Azure spend from Cost Management
- [mock.py](../src/collectors/mock.py) generates fallback data for local demos

### Layer 3 — Storage and Processing
- [influx.py](../src/storage/influx.py) stores normalized cost and recommendation time-series data
- [redis_cache.py](../src/storage/redis_cache.py) suppresses duplicate alerts
- [rules.py](../src/alerts/rules.py) detects spending spikes
- [engine.py](../src/recommendations/engine.py) produces rightsizing suggestions

### Layer 4 — Visualization and Delivery
- Grafana dashboards read data from the InfluxDB bucket
- A Slack webhook consumes alert events
- GitHub Actions triggers the daily cost sync

## Data Flow
1. The scheduler or a manual CLI run starts from [main.py](../src/main.py).
2. [pipeline.py](../src/service/pipeline.py) executes the selected cloud collectors.
3. Normalized `CostRecord` objects are written to InfluxDB.
4. Alert rules and the recommendation engine run against the same records.
5. Recommendations are persisted in InfluxDB, and alert events are sent to Slack.
6. Grafana queries the bucket and renders the pre-provisioned dashboard.

## Design Decisions
- InfluxDB was chosen because cost trends are naturally time-series data.
- Redis is a lightweight, fast store for alert deduplication state.
- The mock fallback makes demos and local validation easy.
- A shared normalized schema makes it straightforward to add more clouds or forecast modules later.

## Operational Notes
- Docker Compose is recommended for local runs.
- A GitHub Actions workflow is available for hosted scheduled syncs.
- In live mode, secrets belong in `.env` or GitHub Secrets, not in the codebase.

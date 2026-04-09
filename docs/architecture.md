# Architecture Overview

## 4-layer Design

### Layer 1 — Data Sources
- AWS Cost Explorer
- GCP Billing export via BigQuery
- Azure Cost Management API

### Layer 2 — Python Scrapers
- [aws.py](file:///d:/INTERN/DEVOPS/src/collectors/aws.py) AWS cost fetch karta hai
- [gcp.py](file:///d:/INTERN/DEVOPS/src/collectors/gcp.py) GCP billing export query karta hai
- [azure.py](file:///d:/INTERN/DEVOPS/src/collectors/azure.py) Azure spend pull karta hai
- [mock.py](file:///d:/INTERN/DEVOPS/src/collectors/mock.py) recruiter demo ke liye fallback data generate karta hai

### Layer 3 — Storage and Processing
- [influx.py](file:///d:/INTERN/DEVOPS/src/storage/influx.py) normalized cost aur recommendation time-series data store karta hai
- [redis_cache.py](file:///d:/INTERN/DEVOPS/src/storage/redis_cache.py) duplicate alert suppression karta hai
- [rules.py](file:///d:/INTERN/DEVOPS/src/alerts/rules.py) spike detection karta hai
- [engine.py](file:///d:/INTERN/DEVOPS/src/recommendations/engine.py) rightsizing suggestions nikalta hai

### Layer 4 — Visualization and Delivery
- Grafana dashboards InfluxDB bucket se data read karte hain
- Slack webhook alert events consume karta hai
- GitHub Actions daily sync trigger karta hai

## Data Flow
1. Scheduler ya manual CLI run [main.py](file:///d:/INTERN/DEVOPS/src/main.py) se start hota hai.
2. [pipeline.py](file:///d:/INTERN/DEVOPS/src/service/pipeline.py) selected cloud collectors execute karta hai.
3. Normalized `CostRecord` objects InfluxDB me write hote hain.
4. Same records par alert rules aur recommendation engine run hota hai.
5. Recommendations InfluxDB me persist hoti hain aur alert events Slack par jaate hain.
6. Grafana ready-made dashboard bucket ko query karke charts render karta hai.

## Design Decisions
- InfluxDB choose kiya gaya kyunki cost trend naturally time-series hai.
- Redis dedupe state ke liye lightweight aur fast hai.
- Mock fallback recruiter demo aur local validation ko easy banata hai.
- Shared normalized schema future me additional clouds ya forecast modules add karna easy banati hai.

## Operational Notes
- Local run ke liye Docker Compose recommended hai.
- Hosted scheduled sync ke liye GitHub Actions workflow available hai.
- Live mode me secrets `.env` ya GitHub Secrets me rahenge, codebase me nahi.

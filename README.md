# Automated Cloud Security Infrastructure Monitoring & Alerting Pipeline

An automated cloud telemetry pipeline designed to monitor infrastructure and application health, detect security incidents (such as SSH brute force attacks and Distributed Denial of Service floods), and route high-severity alerts to Slack in real time. 

This project was built as an InfoSec security engineering pipeline and utilizes a modern containerized telemetry stack.

---

## Architecture Diagram

```mermaid
flowchart TD
    subgraph Host [Host System (AWS EC2 / Ubuntu)]
        Log[System Logs /var/log/auth.log] -->|Parses failed logins| Daemon[SSH Failed Login Monitor Daemon]
        Daemon -->|Writes metrics| PromDir[Local .prom files /var/lib/node_exporter]
    end

    subgraph Docker Containers [Docker Orchestrated Network]
        Flask[Mock Flask Web App :5000] -->|Exposes HTTP telemetry| Prom
        Node[Node Exporter :9100] -->|Scrapes CPU/RAM & PromDir| Prom
        Prom[Prometheus :9090] -->|Polls metrics & runs rules| Grafana[Grafana :3000]
        Grafana -->|Triggers Alert Rules| Slack[Slack Channel via Webhook]
    end

    User([Attacker / User]) -->|Simulates DoS / Auth Floods| Flask
    User -->|Attempts failed SSH logins| Log
```

---

## Tech Stack
* **Cloud Hosting**: AWS EC2 (or local mock environment)
* **Application**: Flask (Mock Web App with `prometheus_client` instrumentation)
* **Telemetry Collection**: Prometheus + `node_exporter`
* **Visualization & Alerting**: Grafana v10 (provisioned automated dashboards & alerting policies)
* **Alert Target**: Slack Webhook
* **Orchestration**: Docker & Docker Compose
* **Testing Tooling**: Multi-threaded Python threat simulator (DoS, brute force, CPU stressors)

---

## Phase 1: EC2 Security Group Configuration

For a secure deployment on AWS, apply the following **least privilege** Security Group ingress rules to your EC2 instance.

| Port / Range | Protocol | Source Range | Purpose / Rule Description |
| :--- | :--- | :--- | :--- |
| `22` | TCP | `YOUR_IP/32` | **Secure SSH Admin**: Restrict administrative login access strictly to your public IP. |
| `80` / `443` | TCP | `0.0.0.0/0` | **Public Web Traffic**: Allows users to reach the Flask application. |
| `3000` | TCP | `YOUR_IP/32` | **Grafana Console**: Limit monitoring panel access to security staff. |
| `9090` | TCP | `127.0.0.1/32` | **Prometheus Core**: Block public access; accessed internally or via SSH tunnel. |
| `9100` | TCP | `127.0.0.1/32` | **Node Exporter**: Block public access; metrics should only be queried by Prometheus. |

---

## Phase 2: Pipeline Components & Configurations

All configuration definitions have been modularized and automated for zero-config startup:
* **Prometheus Configuration**: [prometheus/prometheus.yml](file:///prometheus/prometheus.yml)
* **Prometheus Alert Rules**: [prometheus/alert_rules.yml](file:///prometheus/alert_rules.yml)
* **Grafana Datasource Provisioning**: [grafana/provisioning/datasources/datasource.yml](file:///grafana/provisioning/datasources/datasource.yml)
* **Grafana Dashboard Provisioning**: [grafana/provisioning/dashboards/dashboard.yml](file:///grafana/provisioning/dashboards/dashboard.yml)
* **Grafana Alert Rules & Slack Routing**: [grafana/provisioning/alerting/alerting.yml](file:///grafana/provisioning/alerting/alerting.yml)
* **Security Dashboard Layout**: [grafana/dashboards/security_dashboard.json](file:///grafana/dashboards/security_dashboard.json)

---

## Phase 3: Setup & Deployment Instructions

### 1. Prerequisite Checklist
* Docker & Docker Compose installed.
* Python 3.x installed (for simulation and monitoring scripts).
* A Slack Webhook URL (from Slack's "Incoming Webhooks" app settings).

### 2. Deploying the Containers
Clone the repository and run Docker Compose, injecting your Slack webhook:

```bash
# Export webhook to host environment
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR_WORKSPACE_ID/YOUR_CHANNEL_ID/YOUR_TOKEN"

# Build and start services in detached mode
docker compose up -d --build
```

### 3. Running the SSH Failed Login Monitor Daemon
The node exporter parses system logs using a local python daemon. 

#### On AWS EC2 (Linux Host):
Run the script as root/sudo so it can read the secure authentication logs:
```bash
sudo python3 scripts/ssh_monitor.py
```

#### Local Mock Mode (Windows/macOS/Non-Root):
If running locally for testing, the script will automatically fallback to `./mock_auth.log`, initialize it, and simulate a failed login attempt every 12 seconds:
```bash
python scripts/ssh_monitor.py
```

---

## Phase 4: Threat Simulation & Verification

To verify that the monitoring pipeline is working, run the multi-threaded python telemetry stressor script:

```bash
# Run the full attack simulation (DoS HTTP flood, CPU spike, and Auth Brute Force)
python scripts/simulate_dos.py --duration 120 --attack all
```

### Available Attack Profiles:
* `--attack dos`: Initiates high-concurrency HTTP GET floods targeting `/api/v1/resource`.
* `--attack brute`: Rapidly fires HTTP POST authentication payloads with randomized passwords to `/api/v1/auth` (recording 401s).
* `--attack cpu`: Cryptographic calculation flood designed to force system CPU utilization beyond the 80% threshold.

---

## Phase 5: Verification & Console URLs

* **Flask Mock Application**: [http://localhost:5000](http://localhost:5000)
* **Flask Telemetry Output**: [http://localhost:5000/metrics](http://localhost:5000/metrics)
* **Prometheus Web Console**: [http://localhost:9090](http://localhost:9090)
* **Grafana Telemetry Dashboard**: [http://localhost:3000](http://localhost:3000)
  * *Credentials*: Passwordless guest login auto-configured (or log in with `admin`/`admin`).
  * Navigate to **Dashboards** -> **Security Monitoring** -> **Cloud Security Operations Telemetry Dashboard**.

### Expected Slack Notification Payload:
When SSH failed attempts exceed 5/min, Grafana triggers a payload to Slack:
```text
🚨 Grafana Alert: SSH Brute Force Attack Detected
Status: FIRING
Details: High rate of failed SSH logins detected on host. Rate has exceeded 5 failed attempts per minute.
Severity: critical
Active Alerts:
  - Metric: instance=node-exporter:9100 (Value: 8.5)
```

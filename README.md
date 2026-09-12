# Telecom AIOps NOC Automation Agent

An autonomous AIOps agent for Telecom Network Operations Centers (NOC), integrating Nokia NetAct, IBM Netcool, BMC Remedy / Helix ITSM, and AI-driven Root Cause Analysis (RCA).

---

## 🏗️ Architecture

```
[Nokia NetAct / Netcool] (Alarms / Traps / Webhooks)
               │
               ▼
[POST /webhook/alarm] ───> [Alert Correlator & Topology Graph]
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
[BMC Remedy / Helix ITSM]                    [Automated Diagnostics Worker]
  • Auto-Ticket Creation                       • S1-U / OAM Ping Checks
  • WorkLog Enrichment                         • Cisco/Nokia/Huawei CLI Triage
  • Auto-Resolution                                       │
                                                          ▼
                                            [AI Root Cause Analysis Engine]
                                              • Domain Classification (RAN/Core/IP)
                                              • Confidence Scoring
                                              • Auto-Remediation Recommendation
                                                          │
                                                          ▼
                                            [Closed-Loop Auto-Remediation]
                                              • IPsec Tunnel Reset
                                              • Soft BGP Session Clear
                                              • Post-Fix Health Verification
```

---

## 🚀 Quickstart

### 1. Run Automated Simulation
Test the full end-to-end flow with simulated Nokia NetAct alarms, BMC Remedy tickets, and auto-remediation:
```bash
python simulate_alarm.py
```

### 2. Run Interactive CLI
Manually triage and trigger automated diagnostics for sites in the CMDB:
```bash
python cli.py
```

### 3. Start the Webhook Listener Server
Start the HTTP server to receive real alarms from NetAct, Netcool, or Prometheus:
```bash
python server.py
```

#### Example Webhook Ingestion:
```bash
curl -X POST http://localhost:8000/webhook/alarm \
  -H "Content-Type: application/json" \
  -d '{
    "alarm_id": "ALM-9901",
    "source_system": "NetAct",
    "site_id": "AP001",
    "alarm_name": "BTS OM Link Failure",
    "severity": "Critical"
  }'
```

---

## ⚙️ Configuration (`config.py`)

- **BMC Remedy Integration:** Set `MOCK_REMEDY = False`, `REMEDY_BASE_URL`, `REMEDY_USER`, and `REMEDY_PASSWORD`.
- **Live Device SSH:** Set `use_mock_cli = False` in `diagnostics.py` to enable live `Netmiko` SSH connections to base stations and aggregation routers.
- **LLM Root Cause Analysis:** Set `OPENAI_API_KEY` to enable GPT-4o deep reasoning; otherwise, the built-in telecom heuristic rule engine is used.

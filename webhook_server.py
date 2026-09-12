import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from models import AlarmEvent
from agent import AIOpsNOCAgent
from config import settings

app = FastAPI(
    title="Telecom AIOps NOC Automation Agent",
    description="Autonomous Event Ingestion, Topology Correlation, Remedy Integration, and Closed-Loop Remediation",
    version="1.0.0"
)

noc_agent = AIOpsNOCAgent(use_mock=True)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "AIOps NOC Agent", "version": "1.0.0"}

@app.post("/webhook/alarm")
def receive_alarm(alarm: AlarmEvent):
    """
    Ingests alarms from Nokia NetAct, IBM Netcool OMNIbus, BMC Helix, or Monitoring Probes.
    """
    try:
        result = noc_agent.handle_alarm(alarm)
        return {"status": "processed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/incidents")
def list_incidents():
    """
    Returns active incidents from Remedy ITSM cache.
    """
    return noc_agent.remedy_client.incidents_db

if __name__ == "__main__":
    uvicorn.run("webhook_server:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

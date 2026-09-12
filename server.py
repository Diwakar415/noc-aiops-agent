import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from models import AlarmEvent
from agent import AIOpsNOCAgent
from config import settings

agent = AIOpsNOCAgent(use_mock=True)

class NOCWebhookHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            html_path = os.path.join(os.path.dirname(__file__), "index.html")
            try:
                with open(html_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._send_json(500, {"error": f"Failed to load UI: {e}"})
        elif self.path == "/health":
            self._send_json(200, {"status": "healthy", "service": "Telecom AIOps NOC Agent"})
        elif self.path == "/incidents":
            incidents = {k: v.model_dump() for k, v in agent.remedy_client.incidents_db.items()}
            self._send_json(200, incidents)
        elif self.path == "/metrics":
            # Prometheus scraping endpoint
            total_incidents = len(agent.remedy_client.incidents_db)
            healed = sum(1 for v in agent.remedy_client.incidents_db.values() if v.status == "Resolved")
            metrics_text = (
                "# HELP noc_incidents_total Total number of Remedy incidents processed\n"
                "# TYPE noc_incidents_total counter\n"
                f"noc_incidents_total {total_incidents}\n\n"
                "# HELP noc_auto_healed_total Total number of auto-remediated incidents\n"
                "# TYPE noc_auto_healed_total counter\n"
                f"noc_auto_healed_total {healed}\n\n"
                "# HELP noc_agent_status Status of the AIOps agent (1=UP, 0=DOWN)\n"
                "# TYPE noc_agent_status gauge\n"
                "noc_agent_status 1\n"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(metrics_text.encode("utf-8"))
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        if self.path == "/webhook/alarm":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                alarm = AlarmEvent(
                    alarm_id=data.get("alarm_id", "ALM-WEBHOOK-01"),
                    source_system=data.get("source_system", "NetAct"),
                    site_id=data.get("site_id", "AP001"),
                    alarm_name=data.get("alarm_name", "BTS OM Link Failure"),
                    severity=data.get("severity", "Critical"),
                    specific_problem=data.get("specific_problem"),
                    additional_text=data.get("additional_text")
                )
                result = agent.handle_alarm(alarm)
                self._send_json(200, {"status": "processed", "result": result})
            except Exception as e:
                self._send_json(500, {"status": "error", "detail": str(e)})
        else:
            self._send_json(404, {"error": "Not Found"})

def run_server():
    server_address = (settings.HOST, settings.PORT)
    httpd = HTTPServer(server_address, NOCWebhookHandler)
    print(f"Starting AIOps NOC Agent Webhook Server on http://localhost:{settings.PORT}")
    print(f"Dashboard: http://localhost:{settings.PORT}/")
    print(f"Prometheus Metrics: http://localhost:{settings.PORT}/metrics")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()

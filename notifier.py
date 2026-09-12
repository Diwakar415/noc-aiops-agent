import json
import urllib.request
from typing import Optional
from models import IncidentRecord, RCAResult, RemediationResult

class IncidentNotifier:
    """
    Broadcasts rich incident alerts and auto-remediation notifications
    to MS Teams, Slack, or Webhook channels for Tier-2/Tier-3 NOC engineering teams.
    """
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    def notify_incident_created(self, incident: IncidentRecord, rca: Optional[RCAResult] = None):
        title = f"[NOC-INCIDENT-CREATED] [{incident.incident_number}] {incident.site_id}"
        message = (
            f"Site ID: {incident.site_id}\n"
            f"Alarm: {incident.alarm_name} ({incident.severity})\n"
            f"Assigned Group: {incident.assigned_group}\n"
            f"Status: {incident.status}\n"
        )
        if rca:
            message += (
                f"\nAI Root Cause Analysis:\n"
                f"- Domain: {rca.affected_domain} (Confidence: {int(rca.confidence_score * 100)}%)\n"
                f"- Root Cause: {rca.root_cause_summary}\n"
                f"- Recommendation: {rca.recommended_action}\n"
            )
        self._dispatch(title, message, color="#ef4444")

    def notify_auto_remediated(self, incident_number: str, site_id: str, remediation: RemediationResult):
        title = f"[NOC-AUTO-REMEDIATION-SUCCESS] [{incident_number}] {site_id}"
        message = (
            f"Remediation Action: {remediation.action_taken}\n"
            f"Status: {remediation.status}\n"
            f"Remediation Log:\n{remediation.output_log}\n"
            f"Remedy Incident: Auto-Closed / Resolved\n"
        )
        self._dispatch(title, message, color="#22c55e")

    def _dispatch(self, title: str, message: str, color: str = "#38bdf8"):
        print(f"\n[Notification Dispatch] {title}\n{message}")
        if not self.webhook_url:
            return

        payload = {
            "title": title,
            "text": message,
            "themeColor": color.replace("#", "")
        }
        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"[Notifier] Webhook sent successfully (HTTP {resp.status})")
        except Exception as e:
            print(f"[Notifier] Failed to send webhook: {e}")

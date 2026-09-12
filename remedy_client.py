import random
import json
from typing import Dict, Any, Optional
from config import settings
from models import IncidentRecord

class RemedyHelixClient:
    """
    Client for BMC Remedy / Helix ITSM REST API.
    Supports JWT Auth, Incident Ticket Creation, WorkLog appending, and Incident Resolution.
    Works with both requests and python urllib (zero external dependency).
    """
    def __init__(self):
        self.base_url = settings.REMEDY_BASE_URL
        self.username = settings.REMEDY_USER
        self.password = settings.REMEDY_PASSWORD
        self.mock = settings.MOCK_REMEDY
        self.jwt_token: Optional[str] = None
        self.incidents_db: Dict[str, IncidentRecord] = {}

    def authenticate(self) -> bool:
        if self.mock:
            self.jwt_token = "mock_jwt_token_1234567890"
            return True

        url = f"{self.base_url}/api/arsys/v1/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"username={self.username}&password={self.password}".encode("utf-8")

        try:
            import urllib.request
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    self.jwt_token = resp.read().decode("utf-8").strip()
                    return True
        except Exception as e:
            print(f"[Remedy] Authentication failed: {e}")
        return False

    def create_incident(self, site_id: str, alarm_name: str, severity: str, summary: str, assigned_group: str = "NOC-Tier1") -> str:
        """
        Creates a ticket in BMC Remedy / Helix. Returns the Incident Number (e.g., INC0000084729).
        """
        incident_id = f"INC00000{random.randint(10000, 99999)}"

        if self.mock:
            rec = IncidentRecord(
                incident_number=incident_id,
                site_id=site_id,
                alarm_name=alarm_name,
                severity=severity,
                status="Assigned",
                assigned_group=assigned_group,
                worklogs=[f"Automated Ticket generated for {alarm_name} at Site {site_id}"]
            )
            self.incidents_db[incident_id] = rec
            return incident_id

        if not self.jwt_token:
            self.authenticate()

        url = f"{self.base_url}/api/arsys/v1/entry/HPD:IncidentInterface_Create"
        headers = {
            "Authorization": f"AR-JWT {self.jwt_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "values": {
                "First_Name": "AIOps",
                "Last_Name": "Engine",
                "Description": summary,
                "Detailed_Decription": f"Alarm: {alarm_name} on Node: {site_id}",
                "Impact": "2-Significant/Large" if severity == "Critical" else "3-Moderate/Limited",
                "Urgency": "2-High" if severity == "Critical" else "3-Medium",
                "Status": "Assigned",
                "Assigned_Group": assigned_group,
                "Service_Type": "Infrastructure Event",
                "z1D_Action": "CREATE"
            }
        }
        try:
            import urllib.request
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in [200, 201]:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    return res_data.get("values", {}).get("Incident Number", incident_id)
        except Exception as e:
            print(f"[Remedy] Failed to create incident: {e}")

        return incident_id

    def add_worklog(self, incident_number: str, log_type: str, text: str):
        """
        Appends diagnostic results or RCA to the Remedy Incident worklog.
        """
        if self.mock:
            if incident_number in self.incidents_db:
                self.incidents_db[incident_number].worklogs.append(f"[{log_type}] {text}")
            return

        if not self.jwt_token:
            self.authenticate()

        url = f"{self.base_url}/api/arsys/v1/entry/HPD:WorkLog"
        headers = {
            "Authorization": f"AR-JWT {self.jwt_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "values": {
                "Incident Number": incident_number,
                "Work Log Type": log_type,
                "Detailed Description": text,
                "View Access": "Public"
            }
        }
        try:
            import urllib.request
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print(f"[Remedy] Failed to post worklog: {e}")

    def resolve_incident(self, incident_number: str, resolution_summary: str):
        """
        Closes/Resolves incident in Remedy when alarm clear arrives or auto-remediation succeeds.
        """
        if self.mock:
            if incident_number in self.incidents_db:
                self.incidents_db[incident_number].status = "Resolved"
                self.incidents_db[incident_number].worklogs.append(f"[Auto-Closure] {resolution_summary}")
            return

        if not self.jwt_token:
            self.authenticate()

        url = f"{self.base_url}/api/arsys/v1/entry/HPD:IncidentInterface/{incident_number}"
        headers = {
            "Authorization": f"AR-JWT {self.jwt_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "values": {
                "Status": "Resolved",
                "Status_Reason": "Automated Remediation / Clear Received",
                "Resolution": resolution_summary
            }
        }
        try:
            import urllib.request
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print(f"[Remedy] Failed to resolve incident: {e}")

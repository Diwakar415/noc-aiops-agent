from typing import Dict, Any
from models import AlarmEvent, DiagnosticRequest, IncidentRecord
from correlator import AlertCorrelator
from diagnostics import NetworkDiagnosticsWorker
from remedy_client import RemedyHelixClient
from ai_rca import AIRCAReasoningEngine
from remediation import AutoRemediationWorker
from notifier import IncidentNotifier

class AIOpsNOCAgent:
    """
    Master AIOps NOC Automation Agent.
    Orchestrates NetAct/Netcool Ingestion, Correlation, Remedy Ticketing, Triage, AI RCA, and Auto-Remediation.
    """
    def __init__(self, use_mock: bool = True):
        self.correlator = AlertCorrelator()
        self.diag_worker = NetworkDiagnosticsWorker(use_mock_cli=use_mock)
        self.remedy_client = RemedyHelixClient()
        self.ai_rca = AIRCAReasoningEngine()
        self.remediator = AutoRemediationWorker(self.diag_worker, self.remedy_client)
        self.notifier = IncidentNotifier()

    def handle_alarm(self, alarm: AlarmEvent) -> Dict[str, Any]:
        print(f"\n{'='*70}")
        print(f"[ALARM INGESTED] [{alarm.severity}] {alarm.alarm_name} on Site: {alarm.site_id} (Source: {alarm.source_system})")
        print(f"{'='*70}")

        # Step 1: Correlation & Deduplication
        should_process, enriched_event, reason = self.correlator.process_alarm(alarm)
        print(f"[CORRELATION] {reason}")

        if not should_process:
            return {"status": "suppressed", "reason": reason}

        # Step 2: Handle Clear Alarms
        if alarm.severity.lower() == "clear":
            print(f"[CLEAR] Site {alarm.site_id} received Clear alarm. Resolving active incidents...")
            self.correlator.clear_active_incident(alarm.site_id)
            return {"status": "cleared", "site_id": alarm.site_id}

        # Step 3: BMC Remedy Incident Management
        if enriched_event.is_correlated_root:
            incident_id = self.remedy_client.create_incident(
                site_id=alarm.site_id,
                alarm_name=alarm.alarm_name,
                severity=alarm.severity,
                summary=f"[{alarm.severity}] {alarm.alarm_name} on {enriched_event.site_info.get('site_name')}",
                assigned_group="NOC-IP-Core" if "BGP" in alarm.alarm_name else "NOC-RAN"
            )
            print(f"[REMEDY ITSM] Created Incident Ticket: {incident_id}")
            self.correlator.register_active_incident(
                enriched_event.site_info.get("parent_transport_node", alarm.site_id),
                incident_id
            )
        else:
            incident_id = enriched_event.parent_incident_id
            print(f"[REMEDY ITSM] Correlated with existing Master Ticket: {incident_id}")
            self.remedy_client.add_worklog(
                incident_number=incident_id,
                log_type="Child Event Correlated",
                text=f"Correlated child alarm {alarm.alarm_name} from Site {alarm.site_id} to this master incident."
            )

        # Step 4: Automated Diagnostics / Triage
        target_ip = enriched_event.site_info.get("s1_ip", "127.0.0.1")
        print(f"[DIAGNOSTICS] Running automated health checks on S1 IP ({target_ip})...")
        
        diag_req = DiagnosticRequest(
            site_id=alarm.site_id,
            target_ip=target_ip,
            alarm_name=alarm.alarm_name,
            router_type=enriched_event.site_info.get("router_model", "cisco_ios"),
            check_commands=["show ip interface brief", "show ip bgp summary", "show oam status"]
        )
        diag_result = self.diag_worker.run_diagnostics(diag_req)
        print(f"   -> Ping Reachability: {diag_result.is_reachable} (Latency: {diag_result.ping_latency_ms}ms)")
        print(f"   -> Anomalies Detected: {len(diag_result.detected_anomalies)}")

        # Step 5: AI Root Cause Analysis (RCA)
        print(f"[AI-RCA] Invoking AIOps Reasoning Engine...")
        rca = self.ai_rca.analyze_incident(enriched_event, diag_result)
        print(f"   -> Root Cause: {rca.root_cause_summary}")
        print(f"   -> Domain: {rca.affected_domain} | Confidence: {int(rca.confidence_score * 100)}%")
        print(f"   -> Recommendation: {rca.recommended_action}")

        # Post RCA to Remedy
        self.remedy_client.add_worklog(
            incident_number=incident_id,
            log_type="AI Root Cause Analysis",
            text=(
                f"Confidence: {int(rca.confidence_score * 100)}%\n"
                f"Domain: {rca.affected_domain}\n"
                f"Root Cause: {rca.root_cause_summary}\n"
                f"Recommendation: {rca.recommended_action}"
            )
        )

        # Dispatch Notification to Engineering Channel
        if incident_id in self.remedy_client.incidents_db:
            self.notifier.notify_incident_created(self.remedy_client.incidents_db[incident_id], rca)

        # Step 6: Automated Closed-Loop Remediation
        remediation_result = None
        if rca.can_auto_remediate and rca.auto_remediation_action:
            print(f"[AUTO-HEALING] Auto-Remediation Candidate: {rca.auto_remediation_action}")
            remediation_result = self.remediator.execute_remediation(
                site_id=alarm.site_id,
                target_ip=target_ip,
                action_type=rca.auto_remediation_action,
                incident_id=incident_id
            )
            print(f"   -> Status: {remediation_result.status}")
            if remediation_result.status == "SUCCESS":
                self.notifier.notify_auto_remediated(incident_id, alarm.site_id, remediation_result)

        print(f"{'='*70}\n")

        return {
            "incident_id": incident_id,
            "alarm": alarm.alarm_name,
            "site_id": alarm.site_id,
            "correlated_root": enriched_event.is_correlated_root,
            "rca": rca.model_dump(),
            "remediation": remediation_result.model_dump() if remediation_result else None
        }

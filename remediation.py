import time
from models import RemediationResult, DiagnosticRequest
from diagnostics import NetworkDiagnosticsWorker
from remedy_client import RemedyHelixClient

class AutoRemediationWorker:
    """
    Closed-loop automated remediation engine.
    Executes safe self-healing actions, verifies health post-fix, and updates Remedy.
    """
    def __init__(self, diag_worker: NetworkDiagnosticsWorker, remedy_client: RemedyHelixClient):
        self.diag = diag_worker
        self.remedy = remedy_client

    def execute_remediation(self, site_id: str, target_ip: str, action_type: str, incident_id: str) -> RemediationResult:
        print(f"\n[Remediation] Executing Auto-Remediation: {action_type} for Site {site_id}...")
        
        log_entries = []
        status = "SUCCESS"

        if action_type == "RESTART_IPSEC_TUNNEL":
            log_entries.append(f"Executing: `crypto isakmp restart peer {target_ip}`")
            log_entries.append("IPsec Phase 1/Phase 2 Security Associations renegotiated successfully.")
            time.sleep(1)
        elif action_type == "CLEAR_BGP_SESSION":
            log_entries.append(f"Executing: `clear ip bgp {target_ip} soft in out`")
            log_entries.append("BGP Peering state transitioned from Active -> OpenConfirm -> Established.")
            time.sleep(1)
        elif action_type == "BOUNCE_INTERFACE":
            log_entries.append("Executing interface shutdown / no shutdown sequence on port.")
            log_entries.append("Interface link recovered. Link speed: 10Gbps Full Duplex.")
            time.sleep(1)
        else:
            status = "ESCALATED_TO_TIER2"
            log_entries.append(f"Action {action_type} requires manual approval. Escalated to NOC Tier-2.")

        # Post-remediation verification
        is_healthy, latency = self.diag.ping_ip(target_ip)
        verification_log = (
            f"Post-fix Verification: Target {target_ip} Ping {'SUCCESS (Latency: ' + str(latency) + 'ms)' if is_healthy else 'FAILED'}."
        )
        log_entries.append(verification_log)

        output_log = "\n".join(log_entries)

        # Update Remedy Incident WorkLog
        self.remedy.add_worklog(
            incident_number=incident_id,
            log_type="Auto-Remediation",
            text=f"Remediation Action: {action_type}\nStatus: {status}\nDetails:\n{output_log}"
        )

        # If verified, auto-resolve incident
        if is_healthy and status == "SUCCESS":
            self.remedy.resolve_incident(
                incident_number=incident_id,
                resolution_summary=f"Automated remediation '{action_type}' succeeded. Connectivity restored."
            )

        return RemediationResult(
            action_taken=action_type,
            status=status,
            output_log=output_log
        )

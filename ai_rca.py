import json
from typing import Dict, Any
from models import EnrichedEvent, DiagnosticResult, RCAResult
from config import settings

class AIRCAReasoningEngine:
    """
    AI Root Cause Analysis Engine.
    Uses LLM / Cognitive Heuristics to analyze telemetry, CLI output, and topology.
    """
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.mock_llm = settings.MOCK_LLM or not bool(self.api_key)

    def analyze_incident(self, enriched_event: EnrichedEvent, diag_result: DiagnosticResult) -> RCAResult:
        """
        Runs AI RCA on the gathered telemetry and diagnostic data.
        """
        if self.mock_llm:
            return self._heuristic_ai_rca(enriched_event, diag_result)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            system_prompt = (
                "You are an expert Telecom NOC and AIOps Incident Specialist. "
                "Analyze the provided network alarm, topology, and diagnostic CLI logs. "
                "Output JSON with keys: root_cause_summary, confidence_score, affected_domain, "
                "recommended_action, can_auto_remediate, auto_remediation_action."
            )
            
            user_content = {
                "alarm": enriched_event.alarm.model_dump(mode="json"),
                "site_info": enriched_event.site_info,
                "diagnostic_reachable": diag_result.is_reachable,
                "diagnostic_anomalies": diag_result.detected_anomalies,
                "cli_outputs": diag_result.cli_outputs
            }

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_content, indent=2)}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )

            data = json.loads(response.choices[0].message.content)
            return RCAResult(
                root_cause_summary=data.get("root_cause_summary", "Unknown root cause"),
                confidence_score=float(data.get("confidence_score", 0.85)),
                affected_domain=data.get("affected_domain", "RAN"),
                recommended_action=data.get("recommended_action", "Investigate link"),
                can_auto_remediate=bool(data.get("can_auto_remediate", False)),
                auto_remediation_action=data.get("auto_remediation_action")
            )
        except Exception as e:
            print(f"[AI-RCA] LLM invocation failed ({e}), falling back to heuristic engine.")
            return self._heuristic_ai_rca(enriched_event, diag_result)

    def _heuristic_ai_rca(self, enriched_event: EnrichedEvent, diag: DiagnosticResult) -> RCAResult:
        alarm_name = enriched_event.alarm.alarm_name.upper()
        site_id = enriched_event.alarm.site_id
        
        if "BTS OM LINK FAILURE" in alarm_name or "OM LINK" in alarm_name:
            return RCAResult(
                root_cause_summary=(
                    f"BTS OM Link down on {site_id}. S1-C IPsec negotiation failed due to "
                    "Phase 2 SA timeout over transmission tunnel."
                ),
                confidence_score=0.92,
                affected_domain="RAN / Transmission",
                recommended_action="Execute automated IPsec tunnel renegotiation and check Abis/OAM interface.",
                can_auto_remediate=True,
                auto_remediation_action="RESTART_IPSEC_TUNNEL"
            )
        elif "NE3WS" in alarm_name or "BGP" in alarm_name or "TRANSPORT" in alarm_name:
            return RCAResult(
                root_cause_summary=(
                    f"BGP session down between Site {site_id} ({enriched_event.site_info.get('s1_ip')}) and "
                    f"Aggregator {enriched_event.site_info.get('parent_transport_node')}. High CRC error rate detected on optical port."
                ),
                confidence_score=0.88,
                affected_domain="IP Core Transport",
                recommended_action="Soft-clear BGP neighbor and verify optical physical layer (SFP).",
                can_auto_remediate=True,
                auto_remediation_action="CLEAR_BGP_SESSION"
            )
        else:
            return RCAResult(
                root_cause_summary=f"Radio Cell Service Outage on {site_id}. Alarms indicate degraded throughput / RF fault.",
                confidence_score=0.75,
                affected_domain="RAN",
                recommended_action="Dispatch Field Operations or escalate to Tier-2 RAN team.",
                can_auto_remediate=False,
                auto_remediation_action=None
            )

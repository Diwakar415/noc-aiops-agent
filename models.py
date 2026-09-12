from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class AlarmEvent:
    alarm_id: str
    site_id: str
    alarm_name: str  # e.g., "BTS OM Link Failure", "NE3WS", "BGP Flapping", "Cell Out of Service"
    source_system: str = "NetAct"  # NetAct, Netcool, Prometheus, Helix
    severity: str = "Critical"  # Critical, Major, Minor, Warning, Clear
    node_name: Optional[str] = None
    specific_problem: Optional[str] = None
    additional_text: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

@dataclass
class EnrichedEvent:
    alarm: AlarmEvent
    site_info: Dict[str, Any]
    is_correlated_root: bool = True
    parent_incident_id: Optional[str] = None
    correlated_alarms_count: int = 1

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DiagnosticRequest:
    site_id: str
    target_ip: str
    alarm_name: str
    router_type: str = "cisco_ios"
    check_commands: List[str] = field(default_factory=list)

@dataclass
class DiagnosticResult:
    site_id: str
    target_ip: str
    is_reachable: bool
    ping_latency_ms: Optional[float] = None
    cli_outputs: Dict[str, str] = field(default_factory=dict)
    detected_anomalies: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

@dataclass
class RCAResult:
    root_cause_summary: str
    confidence_score: float
    affected_domain: str  # RAN, IP Transport, Core, Power/Facilities
    recommended_action: str
    can_auto_remediate: bool
    incident_id: Optional[str] = None
    auto_remediation_action: Optional[str] = None

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class RemediationResult:
    action_taken: str
    status: str  # SUCCESS, FAILED, ESCALATED_TO_TIER2
    output_log: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

@dataclass
class IncidentRecord:
    incident_number: str
    site_id: str
    alarm_name: str
    severity: str
    status: str  # Assigned, In Progress, Pending Vendor, Resolved, Closed
    assigned_group: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    worklogs: List[str] = field(default_factory=list)
    rca: Optional[RCAResult] = None
    remediation: Optional[RemediationResult] = None

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

import time
from typing import Dict, Optional, Tuple, List
from models import AlarmEvent, EnrichedEvent
from config import CMDB_TOPOLOGY, settings

class AlertCorrelator:
    """
    Correlates and deduplicates NOC alarms across RAN, IP Core, and Transmission.
    Suppresses alarm storms and maps child alarms to root parent outages.
    """
    def __init__(self):
        # Active incident map: site_id -> parent incident info
        self.active_parent_incidents: Dict[str, Dict] = {}
        # Recent alarm cache for deduplication: alarm_hash -> timestamp
        self.recent_alarms: Dict[str, float] = {}

    def _generate_alarm_hash(self, alarm: AlarmEvent) -> str:
        return f"{alarm.site_id}:{alarm.alarm_name}:{alarm.severity}"

    def process_alarm(self, alarm: AlarmEvent) -> Tuple[bool, Optional[EnrichedEvent], str]:
        """
        Processes incoming alarm.
        Returns (should_process, enriched_event, reason)
        """
        # 1. Deduplication check
        alarm_hash = self._generate_alarm_hash(alarm)
        now = time.time()
        
        if alarm_hash in self.recent_alarms:
            time_diff = now - self.recent_alarms[alarm_hash]
            if time_diff < settings.CORRELATION_WINDOW_SECONDS and alarm.severity != "Clear":
                return False, None, f"Duplicate alarm suppressed (last seen {int(time_diff)}s ago)"
        
        self.recent_alarms[alarm_hash] = now
        
        # 2. Enrich with CMDB Topology
        site_info = CMDB_TOPOLOGY.get(alarm.site_id, {
            "site_name": f"Unknown_Site_{alarm.site_id}",
            "s1_ip": "127.0.0.1",
            "oam_ip": "127.0.0.1",
            "transport_router_ip": "127.0.0.1",
            "router_model": "generic_cisco",
            "parent_transport_node": "UNKNOWN_HUB",
            "sla_tier": "Standard"
        })

        # 3. Topology Correlation (Parent-Child detection)
        parent_node = site_info.get("parent_transport_node")
        is_root = True
        parent_incident_id = None
        
        # Check if there is already an active upstream transport outage
        if parent_node and parent_node in self.active_parent_incidents:
            is_root = False
            parent_incident_id = self.active_parent_incidents[parent_node]["incident_id"]
            self.active_parent_incidents[parent_node]["child_count"] += 1
            reason = f"Correlated with parent transport outage {parent_node} (Incident: {parent_incident_id})"
        elif "Transport" in alarm.alarm_name or "Link Failure" in alarm.alarm_name or "NE3WS" in alarm.alarm_name:
            # Mark this as a candidate parent incident
            is_root = True
            reason = "Root event identified: Transmission / Core Link Failure"
        else:
            reason = "Single site alarm processed"

        enriched = EnrichedEvent(
            alarm=alarm,
            site_info=site_info,
            is_correlated_root=is_root,
            parent_incident_id=parent_incident_id,
            correlated_alarms_count=1
        )

        return True, enriched, reason

    def register_active_incident(self, node_or_site: str, incident_id: str):
        self.active_parent_incidents[node_or_site] = {
            "incident_id": incident_id,
            "created_at": time.time(),
            "child_count": 0
        }

    def clear_active_incident(self, node_or_site: str):
        if node_or_site in self.active_parent_incidents:
            del self.active_parent_incidents[node_or_site]

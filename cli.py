import sys
from models import AlarmEvent
from agent import AIOpsNOCAgent
from config import CMDB_TOPOLOGY

def interactive_cli():
    agent = AIOpsNOCAgent(use_mock=True)
    
    print("\n" + "="*60)
    print("      TELECOM AIOPS NOC AUTOMATION AGENT - INTERACTIVE CLI")
    print("="*60)
    print("Available Sites in CMDB:", list(CMDB_TOPOLOGY.keys()))
    print("Example Alarms: BTS OM Link Failure, NE3WS, BGP Flapping, Cell Out of Service")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            site_id = input("Enter Site ID (e.g. AP001): ").strip().upper()
            if site_id.lower() == "exit":
                break
            if not site_id:
                continue

            alarm_name = input("Enter Alarm Name: ").strip()
            if alarm_name.lower() == "exit":
                break
            if not alarm_name:
                alarm_name = "BTS OM Link Failure"

            severity = input("Enter Severity [Critical/Major/Minor/Clear] (default Critical): ").strip().capitalize()
            if not severity:
                severity = "Critical"

            alarm = AlarmEvent(
                alarm_id="ALM-CLI-001",
                source_system="CLI-Manual-Triage",
                site_id=site_id,
                alarm_name=alarm_name,
                severity=severity
            )

            agent.handle_alarm(alarm)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting AIOps Agent CLI.")
            break

if __name__ == "__main__":
    interactive_cli()

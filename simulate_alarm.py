import time
from models import AlarmEvent
from agent import AIOpsNOCAgent

def run_simulation():
    agent = AIOpsNOCAgent(use_mock=True)

    print("\n" + "#"*70)
    print(">>> STARTING AIOPS NOC AGENT SIMULATION")
    print("#"*70)

    # --- Scenario 1: BTS OM Link Failure (Auto-remediated) ---
    print("\n>>> SCENARIO 1: Single Cell Site Outage (BTS OM Link Failure)")
    alarm1 = AlarmEvent(
        alarm_id="ALM-1001",
        source_system="NetAct-RAN",
        site_id="AP001",
        alarm_name="BTS OM Link Failure",
        severity="Critical",
        specific_problem="S1-C OAM Communication Lost",
        additional_text="IPsec Phase 2 timeout with Core Security Gateway"
    )
    agent.handle_alarm(alarm1)

    time.sleep(1)

    # --- Scenario 2: Alarm Storm & Topology Correlation ---
    print("\n>>> SCENARIO 2: Upstream Transport Aggregator Failure + Cascading Radio Drops")
    # Master Alarm: Transport Outage
    master_alarm = AlarmEvent(
        alarm_id="ALM-2001",
        source_system="Netcool-IP-Transport",
        site_id="AP001",
        alarm_name="Transport Link Failure (NE3WS)",
        severity="Critical",
        specific_problem="Aggregator Link Down to HYD_AGG_RTR_01"
    )
    agent.handle_alarm(master_alarm)

    time.sleep(1)

    # Cascading Child Alarms from affected cells (Should be correlated to master ticket)
    child_alarm = AlarmEvent(
        alarm_id="ALM-2002",
        source_system="NetAct-RAN",
        site_id="AP001",
        alarm_name="Cell Out of Service (L1800)",
        severity="Major",
        specific_problem="Downstream Carrier Drop"
    )
    agent.handle_alarm(child_alarm)

    time.sleep(1)

    # --- Scenario 3: BGP Peering Flap (Auto-remediated) ---
    print("\n>>> SCENARIO 3: Core BGP Session Drop on Site AP002")
    alarm3 = AlarmEvent(
        alarm_id="ALM-3001",
        source_system="Netcool-IP",
        site_id="AP002",
        alarm_name="BGP Flapping / Session Down",
        severity="Critical",
        specific_problem="Peer 10.20.40.1 HoldTimer Expired"
    )
    agent.handle_alarm(alarm3)

    print("\n" + "#"*70)
    print(">>> SIMULATION COMPLETE: All alarms triaged, correlated, tickets managed, and remediated.")
    print("#"*70)

if __name__ == "__main__":
    run_simulation()

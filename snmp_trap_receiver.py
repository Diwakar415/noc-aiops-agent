import socket
import json
import urllib.request
from models import AlarmEvent

# Standard Telecom Enterprise OID mapping for Nokia/Cisco
OID_ALARM_MAP = {
    "1.3.6.1.4.1.94.1.16.1": {"name": "BTS OM Link Failure", "severity": "Critical", "source": "Nokia-AirScale"},
    "1.3.6.1.4.1.9.9.43.1.1": {"name": "Transport Link Failure (NE3WS)", "severity": "Critical", "source": "Cisco-ASR"},
    "1.3.6.1.2.1.15.0.1": {"name": "BGP Flapping / Session Down", "severity": "Critical", "source": "BGP4-MIB"},
    "1.3.6.1.4.1.2011.2.23": {"name": "Cell Out of Service", "severity": "Major", "source": "Huawei-NodeB"}
}

def parse_simple_trap(data: bytes, addr: tuple) -> AlarmEvent:
    """
    Lightweight SNMP trap payload decoder.
    Extracts trap text/OIDs and maps to structured AlarmEvent.
    """
    raw_str = data.decode("utf-8", errors="ignore")
    sender_ip = addr[0]
    
    # Default match
    matched_alarm = "BTS OM Link Failure"
    matched_severity = "Critical"
    source_sys = "SNMP-Trap"

    for oid, info in OID_ALARM_MAP.items():
        if oid in raw_str:
            matched_alarm = info["name"]
            matched_severity = info["severity"]
            source_sys = info["source"]
            break

    # Site mapping heuristic based on sender IP
    site_id = "AP001"
    if "10.20.40" in raw_str or "AP002" in raw_str:
        site_id = "AP002"
    elif "10.20.50" in raw_str or "AP003" in raw_str:
        site_id = "AP003"

    return AlarmEvent(
        alarm_id=f"SNMP-{abs(hash(raw_str)) % 10000}",
        source_system=source_sys,
        site_id=site_id,
        alarm_name=matched_alarm,
        severity=matched_severity,
        specific_problem=f"Raw Trap from {sender_ip}: {raw_str[:60]}"
    )

def start_trap_listener(port: int = 1162):
    """
    Starts UDP listener for incoming telecom SNMP traps on specified port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    print(f"\n[SNMP Trap Receiver] Listening for UDP traps on port {port}...")

    while True:
        try:
            data, addr = sock.recvfrom(2048)
            print(f"\n[SNMP Trap Receiver] Received {len(data)} bytes from {addr[0]}:{addr[1]}")
            
            alarm = parse_simple_trap(data, addr)
            print(f" -> Decoded Alarm: {alarm.alarm_name} (Site: {alarm.site_id})")

            # Forward to AIOps Agent Webhook
            req_data = json.dumps(alarm.model_dump()).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:8080/webhook/alarm",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f" -> Forwarded to AIOps Engine (HTTP {resp.status})")

        except KeyboardInterrupt:
            print("\nStopping SNMP listener.")
            break
        except Exception as e:
            print(f"[SNMP Trap Receiver] Error: {e}")

def send_test_trap(target_ip: str = "127.0.0.1", port: int = 1162, oid: str = "1.3.6.1.4.1.94.1.16.1"):
    """
    Helper to send a test UDP trap payload.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = f"SNMPv2-Trap: OID={oid} Site=AP001 Msg=LossOfSignal".encode("utf-8")
    sock.sendto(payload, (target_ip, port))
    print(f"[SNMP Test] Sent test trap payload ({oid}) to {target_ip}:{port}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_test_trap()
    else:
        start_trap_listener()

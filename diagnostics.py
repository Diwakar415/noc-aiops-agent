import subprocess
import platform
import time
from typing import Dict, List
from models import DiagnosticRequest, DiagnosticResult

class NetworkDiagnosticsWorker:
    """
    Automates network triage, ping verification, and CLI diagnostic collection.
    """
    def __init__(self, use_mock_cli: bool = True):
        self.use_mock_cli = use_mock_cli

    def ping_ip(self, ip_address: str, count: int = 2) -> tuple[bool, float]:
        """
        Executes an OS ping check and returns (is_reachable, latency_ms).
        """
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, str(count), ip_address]
        
        try:
            start_time = time.time()
            res = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=4
            )
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            is_up = (res.returncode == 0)
            return is_up, (elapsed_ms if is_up else 0.0)
        except Exception:
            return False, 0.0

    def run_diagnostics(self, req: DiagnosticRequest) -> DiagnosticResult:
        """
        Gathers automated network diagnostics for an alarm.
        """
        is_reachable, latency = self.ping_ip(req.target_ip)
        cli_outputs = {}
        detected_anomalies = []

        if not is_reachable:
            detected_anomalies.append(f"Target IP {req.target_ip} is UNREACHABLE (Packet Loss 100%)")
        else:
            detected_anomalies.append(f"Target IP {req.target_ip} is Reachable (Latency: {latency}ms)")

        # Collect CLI outputs
        if self.use_mock_cli:
            cli_outputs = self._generate_simulated_cli_output(req.alarm_name, req.site_id, is_reachable)
        else:
            cli_outputs = self._execute_netmiko_commands(req)

        # Parse anomalies from CLI output
        for cmd, output in cli_outputs.items():
            if "down" in output.lower() or "error" in output.lower() or "reset" in output.lower():
                detected_anomalies.append(f"Command '{cmd}' indicated errors or down state.")

        return DiagnosticResult(
            site_id=req.site_id,
            target_ip=req.target_ip,
            is_reachable=is_reachable,
            ping_latency_ms=latency,
            cli_outputs=cli_outputs,
            detected_anomalies=detected_anomalies
        )

    def _generate_simulated_cli_output(self, alarm_name: str, site_id: str, is_reachable: bool) -> Dict[str, str]:
        """
        Simulates carrier-grade router & BTS CLI output for NOC scenarios.
        """
        outputs = {}
        if "OM Link" in alarm_name or "BTS" in alarm_name:
            outputs["show oam connectivity status"] = (
                f"Node: {site_id}_eNodeB\n"
                f"OAM-IP-Link: DOWN (Last Flap: 2m ago, LossOfSync detected)\n"
                f"S1-Control-Plane: DOWN\n"
                f"S1-User-Plane (GTP-U): STALLED\n"
                f"Abis/IPsec Tunnel: NEGOTIATION_FAILED (Phase 2 timeout)"
            )
            outputs["show ip interface brief"] = (
                "Interface              IP-Address      OK? Status                Protocol\n"
                "GigabitEthernet0/0/1   10.20.30.2      YES up                    up      \n"
                "Tunnel100 (IPsec-OAM)  10.254.1.20     NO  down                  down    "
            )
        elif "BGP" in alarm_name or "NE3WS" in alarm_name:
            outputs["show ip bgp summary"] = (
                f"BGP router identifier 172.16.1.1, local AS number 65000\n"
                f"Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd\n"
                f"10.20.30.1      4 65001       0       0        0    0    0 00:04:12 Active\n"
                f"State: Active (TCP SYN Sent, No ACK Received from Peer)"
            )
            outputs["show interfaces GigabitEthernet0/0/0"] = (
                "GigabitEthernet0/0/0 is up, line protocol is up\n"
                "  Hardware is Gigabit Ethernet, address is 0050.56a1.b2c3\n"
                "  5 minute input rate 0 bits/sec, 0 packets/sec\n"
                "  CRC errors: 14209, framing errors: 852 (High BER on Transmission link)"
            )
        else:
            outputs["show environment status"] = "Power Supply 1: OK, Temperature: 32C Normal"
            outputs["show alarms active"] = f"Active Alarm: {alarm_name} on Site {site_id}"

        return outputs

    def _execute_netmiko_commands(self, req: DiagnosticRequest) -> Dict[str, str]:
        """
        Live Netmiko execution on network hardware (Cisco, Nokia, Huawei).
        """
        try:
            from netmiko import ConnectHandler
            device = {
                "device_type": req.router_type,
                "host": req.target_ip,
                "username": "noc_bot",
                "use_keys": True,
                "timeout": 10
            }
            outputs = {}
            with ConnectHandler(**device) as net_connect:
                for cmd in req.check_commands:
                    outputs[cmd] = net_connect.send_command(cmd)
            return outputs
        except Exception as e:
            return {"error": f"Failed to connect to {req.target_ip}: {str(e)}"}

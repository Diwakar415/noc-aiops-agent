import os
from dataclasses import dataclass

@dataclass
class Settings:
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8080"))
    DEBUG: bool = True
    
    # BMC Remedy / Helix REST API Configuration
    REMEDY_BASE_URL: str = os.getenv("REMEDY_BASE_URL", "https://remedy.telecom.local")
    REMEDY_USER: str = os.getenv("REMEDY_USER", "aiops_automation")
    REMEDY_PASSWORD: str = os.getenv("REMEDY_PASSWORD", "noc_secret_pass")
    MOCK_REMEDY: bool = True  # Set to False when connecting to live Remedy server
    
    # NetAct / Netcool Settings
    NETCOOL_HOST: str = os.getenv("NETCOOL_HOST", "netcool.noc.local")
    
    # LLM Root Cause Analysis Config
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MOCK_LLM: bool = True  # Uses built-in intelligent rule/pattern heuristic if no OpenAI API Key provided
    
    # Correlation Windows
    CORRELATION_WINDOW_SECONDS: int = 60

settings = Settings()

# Sample RAN / IP Core Topology & CMDB Inventory
CMDB_TOPOLOGY = {
    "AP001": {
        "site_name": "Hyderabad_CyberTowers_Cell1",
        "s1_ip": "127.0.0.1",
        "oam_ip": "127.0.0.1",
        "transport_router_ip": "127.0.0.1",
        "router_model": "cisco_ios",
        "cells": ["AP001_L1800", "AP001_L2100", "AP001_NR3500"],
        "parent_transport_node": "HYD_AGG_RTR_01",
        "sla_tier": "Gold"
    },
    "AP002": {
        "site_name": "Bangalore_Whitefield_Cell2",
        "s1_ip": "127.0.0.1",
        "oam_ip": "127.0.0.1",
        "transport_router_ip": "127.0.0.1",
        "router_model": "nokia_sros",
        "cells": ["AP002_L1800", "AP002_L2300"],
        "parent_transport_node": "BLR_AGG_RTR_02",
        "sla_tier": "Platinum"
    },
    "AP003": {
        "site_name": "Chennai_OMR_Cell3",
        "s1_ip": "127.0.0.1",
        "oam_ip": "127.0.0.1",
        "transport_router_ip": "127.0.0.1",
        "router_model": "huawei",
        "cells": ["AP003_L1800", "AP003_L2600"],
        "parent_transport_node": "MAA_AGG_RTR_03",
        "sla_tier": "Silver"
    }
}

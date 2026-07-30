#!/usr/bin/env python3
"""
API Test Script for QUANTIQUAN AI Engine.

This script tests the health and risk calculation endpoints.
Requires `requests` library. Install with: pip install requests
"""

import json
import sys
import sqlite3

try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Install with: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000/api/v1"

# Hex UUIDs (32 hex characters, no hyphens) to match SQLAlchemy binding
TENANT_ID = "11111111111111111111111111111111"
ASSET_ID = "22222222222222222222222222222222"


def ensure_tenant_exists():
    """Ensure the test tenant exists in the database."""
    conn = sqlite3.connect("quantiquan.db")
    cursor = conn.cursor()

    # Delete any existing tenant with same ID (clean slate)
    cursor.execute("DELETE FROM tenants WHERE id = ?", (TENANT_ID,))
    cursor.execute("""
        INSERT INTO tenants (id, name, plan)
        VALUES (?, ?, ?)
    """, (TENANT_ID, "Test Tenant", "free"))
    conn.commit()
    conn.close()
    print(f"✅ Inserted test tenant: {TENANT_ID}")
    return True


def ensure_asset_exists():
    """Ensure the test asset exists with correct lowercase enum values."""
    ensure_tenant_exists()

    conn = sqlite3.connect("quantiquan.db")
    cursor = conn.cursor()

    # Delete existing asset to force fresh insert with correct case
    cursor.execute("DELETE FROM assets WHERE id = ?", (ASSET_ID,))

    cursor.execute("""
        INSERT INTO assets (
            id, tenant_id, name, asset_type, importance_tier, owner_id,
            data_classification, compliance_scopes, exposure, is_production,
            downstream_dependents, revenue_impact
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ASSET_ID,
        TENANT_ID,
        "Payment API",
        "api",
        90,
        None,
        "regulated",           # ✅ matches DataSensitivity.REGULATED
        '["pci"]',             # ✅ lowercase to match ComplianceScope.PCI
        "customer-facing",
        1,
        15,
        "high"
    ))
    conn.commit()
    conn.close()
    print(f"✅ Inserted/replaced test asset: {ASSET_ID}")
    return True


def test_health():
    print("\n--- Testing Health Endpoint ---")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        print(f"✅ Health check passed. Status: {data.get('status')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_readiness():
    print("\n--- Testing Readiness Endpoint ---")
    try:
        response = requests.get(f"{BASE_URL}/readiness")
        response.raise_for_status()
        data = response.json()
        print(f"✅ Readiness check passed. Status: {data.get('status')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Readiness check failed: {e}")
        return False


def test_risk_calculation():
    print("\n--- Testing Risk Calculation Endpoint ---")
    ensure_asset_exists()

    payload = {
        "tenant_id": TENANT_ID,
        "asset_id": ASSET_ID,
        "source": "internal_scanner",
        "source_finding_id": "scan-test-123",
        "title": "Critical vulnerability in payment API",
        "description": "Unpatched RCE vulnerability in payment gateway",
        "raw_severity": 8.5,
        "raw_severity_scale": "cvss_v3",
        "detected_at": 1690000000,
        "raw_payload": {"scanner": "test", "details": "Sample finding"},
        "cve_id": "CVE-2024-12345",
        "status": "open",
    }

    print(f"📤 Sending payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            f"{BASE_URL}/risk/calculate",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ Risk calculation successful!")
        print(f"   Finding ID: {data.get('finding_id')}")
        print(f"   BIS: {data.get('bis')}")
        print(f"   Tier: {data.get('tier')}")
        print(f"   Confidence: {data.get('confidence')}")
        if data.get('summary'):
            print(f"   Summary: {data.get('summary')[:150]}...")
        print(f"   Drivers: {json.dumps(data.get('drivers'), indent=2)}")
        return data.get('finding_id')
    except requests.exceptions.RequestException as e:
        print(f"❌ Risk calculation failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return None


def test_get_decision(finding_id):
    if not finding_id:
        print("\n⏭️ Skipping get_decision test (no finding ID).")
        return

    print("\n--- Testing Get Decision Endpoint ---")
    try:
        response = requests.get(
            f"{BASE_URL}/risk/{finding_id}",
            params={"tenant_id": TENANT_ID},
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ Get decision successful!")
        print(f"   BIS: {data.get('bis')}")
        print(f"   Tier: {data.get('tier')}")
        print(f"   Confidence: {data.get('confidence')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Get decision failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False


def main():
    print("🚀 Starting API Tests for QUANTIQUAN AI Engine")
    print(f"Base URL: {BASE_URL}")

    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running at localhost:8000.")
        sys.exit(1)

    health_ok = test_health()
    readiness_ok = test_readiness()
    finding_id = test_risk_calculation() if health_ok else None

    if finding_id:
        test_get_decision(finding_id)

    print("\n--- Test Summary ---")
    print(f"✅ Health: {'PASS' if health_ok else 'FAIL'}")
    print(f"✅ Readiness: {'PASS' if readiness_ok else 'FAIL'}")
    print(f"✅ Risk Calculation: {'PASS' if finding_id else 'FAIL'}")


if __name__ == "__main__":
    main()
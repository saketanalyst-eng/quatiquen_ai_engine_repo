#!/usr/bin/env python3
"""
Test script for QUANTIQUAN AI Engine – with unique source_finding_id.

This script:
- Ensures tenant and asset exist in the database (Supabase/PostgreSQL).
- Tests health, readiness, risk calculation, and get decision endpoints.
- Prints the AI summary and decision details from the new DecisionObject response.
"""

import json
import sys
import uuid
import os

try:
    import requests
except ImportError:
    print("❌ 'requests' library not found. Install with: pip install requests")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("❌ 'psycopg2' library not found. Install with: pip install psycopg2-binary")
    sys.exit(1)

BASE_URL = "http://localhost:8000/api/v1"

# Fixed hex UUIDs (32 chars, no hyphens)
TENANT_ID = "11111111111111111111111111111111"
ASSET_ID = "22222222222222222222222222222222"

# Supabase Direct Connection Details (hardcoded for reliability)
SUPABASE_HOST = "db.uqshfzellpfvkwynaslm.supabase.co"  # ✅ Correct DB host
SUPABASE_USER = "postgres"
SUPABASE_PASSWORD = "Anantntera@123"  # Replace with your actual password if different
SUPABASE_DB = "postgres"
SUPABASE_PORT = "5432"


def get_db_connection():
    """Get a synchronous PostgreSQL connection using hardcoded Supabase credentials."""
    try:
        conn = psycopg2.connect(
            host=SUPABASE_HOST,
            user=SUPABASE_USER,
            password=SUPABASE_PASSWORD,
            dbname=SUPABASE_DB,
            port=SUPABASE_PORT,
            sslmode='require',  # Required for Supabase
        )
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        print("   Make sure the credentials are correct and the host is reachable.")
        print(f"   Host: {SUPABASE_HOST}, Port: {SUPABASE_PORT}")
        sys.exit(1)


def ensure_tenant_exists():
    """Insert test tenant if not exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tenants WHERE id = %s", (TENANT_ID,))
    cursor.execute("""
        INSERT INTO tenants (id, name, plan)
        VALUES (%s, %s, %s)
    """, (TENANT_ID, "Test Tenant", "free"))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Tenant ready: {TENANT_ID}")


def ensure_asset_exists():
    """Insert test asset if not exists."""
    ensure_tenant_exists()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM assets WHERE id = %s", (ASSET_ID,))
    cursor.execute("""
        INSERT INTO assets (
            id, tenant_id, name, asset_type, importance_tier, owner_id,
            data_classification, compliance_scopes, exposure, is_production,
            downstream_dependents, revenue_impact
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        ASSET_ID,
        TENANT_ID,
        "Payment API",
        "api",
        90,
        None,
        "regulated",
        '["pci"]',
        "customer-facing",
        True,
        15,
        "high"
    ))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Asset ready: {ASSET_ID}")


def test_health():
    print("\n--- Health Check ---")
    try:
        r = requests.get(f"{BASE_URL}/health")
        r.raise_for_status()
        print("✅ Health: PASS")
        return True
    except Exception as e:
        print(f"❌ Health: {e}")
        return False


def test_readiness():
    print("\n--- Readiness Check ---")
    try:
        r = requests.get(f"{BASE_URL}/readiness")
        r.raise_for_status()
        print("✅ Readiness: PASS")
        return True
    except Exception as e:
        print(f"❌ Readiness: {e}")
        return False


def test_risk_calculation():
    print("\n--- Risk Calculation with AI Summary ---")
    ensure_asset_exists()

    # Generate a unique source_finding_id to avoid UNIQUE constraint violation
    unique_id = uuid.uuid4().hex[:8]
    source_finding_id = f"scan-{unique_id}"

    payload = {
        "tenant_id": TENANT_ID,
        "asset_id": ASSET_ID,
        "source": "internal_scanner",
        "source_finding_id": source_finding_id,
        "title": "Critical vulnerability in payment API",
        "description": "Unpatched RCE vulnerability in payment gateway",
        "raw_severity": 8.5,
        "raw_severity_scale": "cvss_v3",
        "detected_at": 1690000000,
        "raw_payload": {"scanner": "test", "details": "Sample finding"},
        "cve_id": "CVE-2024-12345",
        "status": "open",
    }

    print("📤 Payload:", json.dumps(payload, indent=2))

    try:
        r = requests.post(
            f"{BASE_URL}/risk/calculate",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()

        print("\n✅ Risk calculation successful!")
        print(f"   Decision ID : {data.get('decision_id')}")
        print(f"   Finding ID  : {data.get('finding_id')}")
        print(f"   Decision    : {data.get('decision')}")
        print(f"   Priority    : {data.get('priority')}")
        print(f"   Risk Score  : {data.get('risk_score')}")
        print(f"   Tier        : {data.get('tier')}")
        print(f"   Confidence  : {data.get('confidence')}%")

        # Confidence breakdown
        cb = data.get('confidence_breakdown')
        if cb:
            print("\n📊 Confidence Breakdown:")
            print(f"   Overall: {cb.get('overall_confidence')}%")
            categories = cb.get('categories', {})
            if categories:
                print("   Categories:")
                for cat, score in categories.items():
                    print(f"      {cat}: {score}%")

        # AI Summary
        summary = data.get('summary')
        if summary:
            print("\n🧠 AI Summary:")
            if isinstance(summary, dict):
                print(f"   Business Risk: {summary.get('business_risk', 'N/A')[:150]}...")
                print(f"   Technical Risk: {summary.get('technical_risk', 'N/A')[:150]}...")
                print(f"   Why Scored: {summary.get('why_scored', 'N/A')[:150]}...")
                print(f"   Immediate Recommendation: {summary.get('immediate_recommendation', 'N/A')[:150]}...")
                print(f"   Expected Business Impact: {summary.get('expected_business_impact', 'N/A')[:150]}...")
            else:
                print(f"   {summary}")
        else:
            print("\n⚠️ No AI summary returned. Check:")
            print("   - GROQ_API_KEY in .env")
            print("   - Network connectivity to Groq API")
            print("   - Server logs for LLM errors")

        # Drivers
        drivers = data.get('drivers', {})
        if drivers:
            print("\n📊 Drivers:")
            for driver_name, driver_data in drivers.items():
                if isinstance(driver_data, dict):
                    value = driver_data.get('value', 'N/A')
                    explanation = driver_data.get('explanation', '')
                    print(f"   {driver_name}: {value} – {explanation}")
                else:
                    print(f"   {driver_name}: {driver_data}")

        return data.get('finding_id')
    except Exception as e:
        print(f"❌ Risk calculation failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return None


def test_get_decision(finding_id):
    if not finding_id:
        return
    print("\n--- Get Decision ---")
    try:
        r = requests.get(
            f"{BASE_URL}/risk/{finding_id}",
            params={"tenant_id": TENANT_ID},
        )
        r.raise_for_status()
        data = r.json()
        print("✅ Decision retrieved:")
        print(f"   Decision ID : {data.get('decision_id')}")
        print(f"   Risk Score  : {data.get('risk_score')}")
        print(f"   Tier        : {data.get('tier')}")
        print(f"   Confidence  : {data.get('confidence')}%")
        summary = data.get('summary')
        if summary and isinstance(summary, dict):
            print(f"   Summary (business_risk): {summary.get('business_risk', 'N/A')[:150]}...")
        elif summary:
            print(f"   Summary: {summary[:150]}...")
    except Exception as e:
        print(f"❌ Get decision failed: {e}")


def main():
    print("🚀 Testing QUANTIQUAN AI Engine with AI Summary")
    print(f"Base URL: {BASE_URL}")

    # Quick connectivity check
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot reach server. Is it running on localhost:8000?")
        sys.exit(1)

    h_ok = test_health()
    r_ok = test_readiness()
    if not h_ok or not r_ok:
        print("\n⚠️ Health/readiness failed – continuing anyway.")

    finding_id = test_risk_calculation()
    if finding_id:
        test_get_decision(finding_id)

    print("\n--- Test Summary ---")
    print(f"Health: {'✅ PASS' if h_ok else '❌ FAIL'}")
    print(f"Readiness: {'✅ PASS' if r_ok else '❌ FAIL'}")
    print(f"Risk Calculation: {'✅ PASS' if finding_id else '❌ FAIL'}")


if __name__ == "__main__":
    main()
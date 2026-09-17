#!/usr/bin/env python3
"""
Test script for QUANTIQUAN AI Engine – Deployed on Render.

This script:
- Tests the AI Engine deployed at https://quatiquen-ai-engine-repo.onrender.com
- Ensures tenant and asset exist in Supabase (for the database the engine uses).
- Tests health, readiness, risk calculation, and get decision endpoints.
- Prints the AI summary and decision details from the DecisionObject response.

Note:
- Render Free Tier sleeps after 15 minutes of inactivity.
  The first request may take 30–60 seconds (cold start). Be patient.
"""

import json
import sys
import uuid
import time
import os

try:
    import requests
except ImportError:
    print("❌ 'requests' library not found. Install with: pip install requests")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("❌ 'psycopg2' library not found. Install with: pip install psycopg2-binary")
    sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================

# Deployed Render URL
BASE_URL = "https://quatiquen-ai-engine-repo.onrender.com/api/v1"

# Optional API Key (if your Render service requires it)
API_KEY = os.getenv("QUANTIQUEN_API_KEY", "")  # Set as env var or hardcode for testing
HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY

# Fixed test UUIDs (32 hex chars, no hyphens)
TENANT_ID = "11111111111111111111111111111111"
ASSET_ID = "22222222222222222222222222222222"

# Supabase connection (same DB the Render engine uses)
SUPABASE_HOST = "db.uqshfzellpfvkwynaslm.supabase.co"
SUPABASE_USER = "postgres"
SUPABASE_PASSWORD = "Anantntera@123"
SUPABASE_DB = "postgres"
SUPABASE_PORT = "5432"

# Render cold start can take 60s – increase timeouts
REQUEST_TIMEOUT = 90


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db_connection():
    """Connect to Supabase PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=SUPABASE_HOST,
            user=SUPABASE_USER,
            password=SUPABASE_PASSWORD,
            dbname=SUPABASE_DB,
            port=SUPABASE_PORT,
            sslmode="require",
        )
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        print(f"   Host: {SUPABASE_HOST}, Port: {SUPABASE_PORT}")
        sys.exit(1)


def ensure_tenant_exists():
    """Insert test tenant if not exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tenants WHERE id = %s", (TENANT_ID,))
    cursor.execute(
        """
        INSERT INTO tenants (id, name, plan)
        VALUES (%s, %s, %s)
        """,
        (TENANT_ID, "Test Tenant", "free"),
    )
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
    cursor.execute(
        """
        INSERT INTO assets (
            id, tenant_id, name, asset_type, importance_tier, owner_id,
            data_classification, compliance_scopes, exposure, is_production,
            downstream_dependents, revenue_impact
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
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
            "high",
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Asset ready: {ASSET_ID}")


# ============================================================
# WAKE-UP HELPER (Handles Render Free Tier Cold Start)
# ============================================================

def wake_up_service(max_attempts: int = 5, wait_seconds: int = 15) -> bool:
    """
    Ping the service until it responds (up to max_attempts).
    Handles Render free tier cold starts (~30-60 seconds).
    """
    print(f"\n⏰ Waking up Render service (may take up to {max_attempts * wait_seconds}s)...")
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code < 500:
                print(f"✅ Service is awake (attempt {attempt}, status {r.status_code})")
                return True
        except requests.exceptions.RequestException as e:
            print(f"   Attempt {attempt}/{max_attempts} failed: {type(e).__name__}")
        time.sleep(wait_seconds)
    print("❌ Service did not wake up in time.")
    return False


# ============================================================
# API TESTS
# ============================================================

def test_health():
    print("\n--- Health Check ---")
    try:
        r = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        print(f"   Status Code : {r.status_code}")
        if r.status_code == 200:
            print(f"   Response    : {r.json()}")
            print("✅ Health: PASS")
            return True
        else:
            print(f"   Response    : {r.text[:300]}")
            print(f"❌ Health: FAIL (status {r.status_code})")
            return False
    except Exception as e:
        print(f"❌ Health: {e}")
        return False


def test_readiness():
    print("\n--- Readiness Check ---")
    try:
        r = requests.get(f"{BASE_URL}/readiness", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        print(f"   Status Code : {r.status_code}")
        if r.status_code == 200:
            print(f"   Response    : {r.json()}")
            print("✅ Readiness: PASS")
            return True
        else:
            print(f"   Response    : {r.text[:300]}")
            print(f"❌ Readiness: FAIL (status {r.status_code})")
            return False
    except Exception as e:
        print(f"❌ Readiness: {e}")
        return False


def test_risk_calculation():
    print("\n--- Risk Calculation with AI Summary ---")
    try:
        ensure_asset_exists()
    except SystemExit:
        print("⚠️ Skipping DB setup – continuing with API test anyway.")

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
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        print(f"   Status Code : {r.status_code}")

        if r.status_code not in (200, 201):
            print(f"❌ Risk calculation FAILED")
            print(f"   Response: {r.text[:500]}")
            return None

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
        cb = data.get("confidence_breakdown")
        if cb:
            print("\n📊 Confidence Breakdown:")
            print(f"   Overall: {cb.get('overall_confidence')}%")
            categories = cb.get("categories", {})
            if categories:
                print("   Categories:")
                for cat, score in categories.items():
                    print(f"      {cat}: {score}%")

        # AI Summary
        summary = data.get("summary")
        if summary:
            print("\n🧠 AI Summary:")
            if isinstance(summary, dict):
                print(f"   Business Risk: {str(summary.get('business_risk', 'N/A'))[:150]}...")
                print(f"   Technical Risk: {str(summary.get('technical_risk', 'N/A'))[:150]}...")
                print(f"   Why Scored: {str(summary.get('why_scored', 'N/A'))[:150]}...")
                print(f"   Immediate Recommendation: {str(summary.get('immediate_recommendation', 'N/A'))[:150]}...")
                print(f"   Expected Business Impact: {str(summary.get('expected_business_impact', 'N/A'))[:150]}...")
            else:
                print(f"   {summary}")
        else:
            print("\n⚠️ No AI summary returned.")
            print("   • Check GROQ_API_KEY in Render environment variables")
            print("   • Verify GROQ_MODEL is valid (e.g., llama-3.3-70b-versatile)")
            print("   • Check Render logs for LLM errors")

        # Drivers
        drivers = data.get("drivers", {})
        if drivers:
            print("\n📊 Drivers:")
            for driver_name, driver_data in drivers.items():
                if isinstance(driver_data, dict):
                    value = driver_data.get("value", "N/A")
                    explanation = driver_data.get("explanation", "")
                    print(f"   {driver_name}: {value} – {explanation}")
                else:
                    print(f"   {driver_name}: {driver_data}")

        return data.get("finding_id")

    except Exception as e:
        print(f"❌ Risk calculation failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text[:500]}")
        return None


def test_get_decision(finding_id):
    if not finding_id:
        return False
    print("\n--- Get Decision ---")
    try:
        r = requests.get(
            f"{BASE_URL}/risk/{finding_id}",
            params={"tenant_id": TENANT_ID},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        print(f"   Status Code : {r.status_code}")
        if r.status_code != 200:
            print(f"❌ Get decision FAILED – {r.text[:300]}")
            return False

        data = r.json()
        print("✅ Decision retrieved:")
        print(f"   Decision ID : {data.get('decision_id')}")
        print(f"   Risk Score  : {data.get('risk_score')}")
        print(f"   Tier        : {data.get('tier')}")
        print(f"   Confidence  : {data.get('confidence')}%")

        summary = data.get("summary")
        if summary and isinstance(summary, dict):
            print(f"   Summary (business_risk): {str(summary.get('business_risk', 'N/A'))[:150]}...")
        elif summary:
            print(f"   Summary: {str(summary)[:150]}...")

        return True
    except Exception as e:
        print(f"❌ Get decision failed: {e}")
        return False


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("🚀 Testing QUANTIQUAN AI Engine (Render Deployment)")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"API Key : {'SET' if API_KEY else 'NOT SET (may cause 400/401)'}")

    # Step 1: Wake up service (cold start handling)
    if not wake_up_service():
        print("❌ Cannot reach service after multiple attempts. Exiting.")
        sys.exit(1)

    # Step 2: Run tests
    h_ok = test_health()
    r_ok = test_readiness()

    if not h_ok or not r_ok:
        print("\n⚠️ Health/readiness failed – continuing anyway.")

    finding_id = test_risk_calculation()
    g_ok = test_get_decision(finding_id) if finding_id else False

    # Step 3: Summary
    print("\n" + "=" * 60)
    print("--- Test Summary ---")
    print(f"Health           : {'✅ PASS' if h_ok else '❌ FAIL'}")
    print(f"Readiness        : {'✅ PASS' if r_ok else '❌ FAIL'}")
    print(f"Risk Calculation : {'✅ PASS' if finding_id else '❌ FAIL'}")
    print(f"Get Decision     : {'✅ PASS' if g_ok else '❌ FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
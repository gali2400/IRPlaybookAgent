"""
Download MITRE ATT&CK framework data for offline use.
Run this once before starting the application.

Usage:
    python scripts/download_frameworks.py
"""

import os
import json
import urllib.request
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FRAMEWORK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "frameworks")

DOWNLOADS = [
    {
        "name": "MITRE ATT&CK Enterprise",
        "url": "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json",
        "filename": "mitre_attack_enterprise.json",
    }
]

# NIST SP 800-61 key phases (embedded — no download needed)
NIST_800_61 = {
    "title": "NIST SP 800-61 Rev 2 — Computer Security Incident Handling Guide",
    "phases": [
        {
            "id": "1",
            "name": "Preparation",
            "description": "Establishing incident response capability before incidents occur."
        },
        {
            "id": "2",
            "name": "Detection and Analysis",
            "description": "Identifying and analyzing potential incidents through monitoring and alerting."
        },
        {
            "id": "3.1",
            "name": "Containment",
            "description": "Stopping the incident from spreading. Short-term and long-term containment strategies."
        },
        {
            "id": "3.2",
            "name": "Eradication",
            "description": "Eliminating the components of the incident (malware, attacker accounts, vulnerabilities)."
        },
        {
            "id": "3.3",
            "name": "Recovery",
            "description": "Restoring systems to normal operation and verifying integrity."
        },
        {
            "id": "4",
            "name": "Post-Incident Activity",
            "description": "Lessons learned, documentation, and improvement of incident response capabilities."
        }
    ]
}


def main():
    os.makedirs(FRAMEWORK_PATH, exist_ok=True)

    # Save NIST 800-61 (embedded)
    nist_path = os.path.join(FRAMEWORK_PATH, "nist_800_61.json")
    with open(nist_path, "w") as f:
        json.dump(NIST_800_61, f, indent=2)
    print(f"✅ NIST SP 800-61 saved to {nist_path}")

    # Download MITRE ATT&CK
    for item in DOWNLOADS:
        dest_path = os.path.join(FRAMEWORK_PATH, item["filename"])
        if os.path.exists(dest_path):
            size_mb = os.path.getsize(dest_path) / (1024 * 1024)
            print(f"✅ {item['name']} already exists ({size_mb:.1f} MB) — skipping download")
            continue

        print(f"⬇️  Downloading {item['name']}...")
        print(f"    URL: {item['url']}")
        print(f"    This may take 1-2 minutes (file is ~10MB)...")
        try:
            req = urllib.request.Request(item["url"], headers={"User-Agent": "IRPlaybookAgent/1.0"})
            with urllib.request.urlopen(req, timeout=120) as response:
                data = response.read()
            with open(dest_path, "wb") as f:
                f.write(data)
            size_mb = len(data) / (1024 * 1024)
            print(f"✅ {item['name']} downloaded ({size_mb:.1f} MB) → {dest_path}")
        except Exception as e:
            print(f"⚠️  Could not download {item['name']}: {e}")
            print("    The system will use LLM knowledge for MITRE technique mapping instead.")

    print("\n✅ Framework setup complete. You can now run the application.")
    print("   streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()

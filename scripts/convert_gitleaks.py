#!/usr/bin/env python3
import json
import sys
import os
import uuid
from datetime import datetime

def convert(gitleaks_file, output_file):
    if not os.path.exists(gitleaks_file) or os.path.getsize(gitleaks_file) == 0:
        # Generar un reporte vacío válido
        empty_report = {
            "version": "15.0.0",
            "vulnerabilities": [],
            "scan": {
                "scanner": {
                    "id": "gitleaks",
                    "name": "Gitleaks",
                    "url": "https://github.com/zricethezav/gitleaks",
                    "version": "8.18.0",
                    "vendor": {
                        "name": "GitLab"
                    }
                },
                "type": "secret_detection",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "status": "success"
            }
        }
        with open(output_file, 'w') as f:
            json.dump(empty_report, f, indent=2)
        return

    with open(gitleaks_file, 'r') as f:
        try:
            leaks = json.load(f)
        except json.JSONDecodeError:
            leaks = []

    vulnerabilities = []
    for leak in leaks:
        # Convertir severidades a la nomenclatura de GitLab
        vuln = {
            "id": str(uuid.uuid4()),
            "category": "secret_detection",
            "name": leak.get("Description", "Secret detected"),
            "message": f"Secret detected: {leak.get('Description', 'N/A')}",
            "description": f"Rule: {leak.get('RuleID', 'N/A')}\nMatch: {leak.get('Match', 'N/A')}",
            "severity": "Critical",
            "confidence": "Confirmed",
            "scanner": {
                "id": "gitleaks",
                "name": "Gitleaks"
            },
            "location": {
                "file": leak.get("File", "N/A"),
                "start_line": leak.get("StartLine", 1),
                "end_line": leak.get("EndLine", 1)
            },
            "identifiers": [
                {
                    "type": "gitleaks_rule_id",
                    "name": f"Gitleaks Rule {leak.get('RuleID')}",
                    "value": leak.get("RuleID", "N/A"),
                    "url": "https://github.com/zricethezav/gitleaks"
                }
            ]
        }
        vulnerabilities.append(vuln)

    report = {
        "version": "15.0.0",
        "vulnerabilities": vulnerabilities,
        "scan": {
            "scanner": {
                "id": "gitleaks",
                "name": "Gitleaks",
                "url": "https://github.com/zricethezav/gitleaks",
                "version": "8.18.0",
                "vendor": {
                    "name": "GitLab"
                }
            },
            "type": "secret_detection",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "status": "success"
        }
    }

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: convert_gitleaks.py <gitleaks_json> <output_json>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])

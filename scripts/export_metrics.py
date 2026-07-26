#!/usr/bin/env python3
# scripts/export_metrics.py
import os
import sys
import json
import urllib.request

def main():
    pushgateway_url = os.getenv("PUSHGATEWAY_URL", "http://pushgateway.monitoring.svc.cluster.local:9091")
    service_name = os.getenv("CI_PROJECT_NAME", "unknown-service")
    env_name = os.getenv("DORA_ENV", "production")
    commit_sha = os.getenv("CI_COMMIT_SHA", "none")
    
    # 1. Mapear Score de Letra a Porcentaje Numérico para Grafana
    score_map = {"A+": 100, "A": 95, "B": 85, "C": 70, "D": 50, "F": 20}
    
    # Intentar leer variables de reporte inyectadas o consolidadas
    score_grade = os.getenv("SCORE_GRADE", "A")
    score_penalty = float(os.getenv("SCORE_PENALTY", "0.0"))
    
    # Vulnerabilidades por severidad
    vuln_critical = int(os.getenv("VULN_CRITICAL", "0"))
    vuln_high = int(os.getenv("VULN_HIGH", "0"))
    vuln_medium = int(os.getenv("VULN_MEDIUM", "0"))
    vuln_low = int(os.getenv("VULN_LOW", "0"))
    
    score_numeric = score_map.get(score_grade, 95)
    
    # 2. Generar el payload Prometheus Text Format
    metrics = [
        f'# HELP gitlab_security_health_percent Porcentaje de salud de seguridad del microservicio',
        f'# TYPE gitlab_security_health_percent gauge',
        f'gitlab_security_health_percent{{service="{service_name}",env="{env_name}",commit="{commit_sha}"}} {score_numeric}',
        
        f'# HELP gitlab_security_penalty_points Puntos de penalización acumulados',
        f'# TYPE gitlab_security_penalty_points gauge',
        f'gitlab_security_penalty_points{{service="{service_name}",env="{env_name}"}} {score_penalty}',
        
        f'# HELP gitlab_security_vulnerabilities_total Total de vulnerabilidades activas por severidad',
        f'# TYPE gitlab_security_vulnerabilities_total gauge',
        f'gitlab_security_vulnerabilities_total{{service="{service_name}",severity="critical"}} {vuln_critical}',
        f'gitlab_security_vulnerabilities_total{{service="{service_name}",severity="high"}} {vuln_high}',
        f'gitlab_security_vulnerabilities_total{{service="{service_name}",severity="medium"}} {vuln_medium}',
        f'gitlab_security_vulnerabilities_total{{service="{service_name}",severity="low"}} {vuln_low}',
    ]
    
    payload = "\n".join(metrics) + "\n"
    
    # 3. Enviar vía HTTP POST/PUT a la Pushgateway
    dest_url = f"{pushgateway_url}/metrics/job/gitlab-ci/service/{service_name}"
    print(f"📤 Exportando telemetría a Pushgateway: {dest_url}")
    
    try:
        req = urllib.request.Request(
            dest_url,
            data=payload.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "text/plain; version=0.0.4"}
        )
        with urllib.request.urlopen(req) as res:
            print(f"✅ Telemetría registrada correctamente. Status: {res.status}")
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo conectar con la Pushgateway: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

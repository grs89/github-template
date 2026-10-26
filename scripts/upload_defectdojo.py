#!/usr/bin/env python3
import os
import sys
import glob
import json
import requests

def sanitize_report_timestamps(file_path):
    """Sanitiza timestamps ISO en reportes GitLab para compatibilidad con DefectDojo.
    DefectDojo parsea start_time/end_time usando estrictamente %Y-%m-%dT%H:%M:%S (19 caracteres).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        modified = False
        def clean_node(node):
            nonlocal modified
            if isinstance(node, dict):
                for k, v in node.items():
                    if isinstance(v, str) and len(v) > 19 and ("T" in v) and (k.endswith(("_time", "_at", "date")) or k in ["start_time", "end_time"]):
                        node[k] = v[:19]
                        modified = True
                    else:
                        clean_node(v)
            elif isinstance(node, list):
                for item in node:
                    clean_node(item)
                    
        clean_node(data)
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    except Exception:
        pass

def upload_scan(url, token, product, engagement, scan_type, file_path, product_type="Research and Development"):
    print(f"🚀 Cargando {os.path.basename(file_path)} a DefectDojo ({scan_type})...")
    api_url = f"{url.rstrip('/')}/api/v2/import-scan/"
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json"
    }
    
    data = {
        "active": "true",
        "verified": "true",
        "scan_type": scan_type,
        "product_type_name": product_type,
        "product_name": product,
        "engagement_name": engagement,
        "auto_create_context": "true",
        "close_old_findings": "true",
        "minimum_severity": "Info"
    }
    
    try:
        with open(file_path, 'rb') as f:
            files = {"file": (os.path.basename(file_path), f, "application/json")}
            response = requests.post(api_url, headers=headers, data=data, files=files, timeout=45)
            
        if response.status_code in [200, 201]:
            print(f"   ✅ Éxito: Reporte cargado. Status {response.status_code}")
            return True
        else:
            try:
                err_json = response.json()
                print(f"   ❌ Error {response.status_code}: {err_json}")
            except Exception:
                preview = [line.strip() for line in response.text.split("\n") if line.strip()][:5]
                print(f"   ❌ Error {response.status_code}: {' '.join(preview)[:300]}")
            return False
    except Exception as e:
        print(f"   ❌ Fallo crítico al conectar con DefectDojo: {e}")
        return False

def main():
    url = os.environ.get('DEFECTDOJO_URL') or os.environ.get('CI_DEFECTDOJO_URL')
    token = os.environ.get('DEFECTDOJO_TOKEN') or os.environ.get('CI_DEFECTDOJO_TOKEN')
    product = os.environ.get('DEFECTDOJO_PRODUCT') or os.environ.get('DEFECTDOJO_PRODUCT_NAME') or os.environ.get('GITHUB_REPOSITORY') or os.environ.get('CI_PROJECT_PATH', 'GRS-Project')
    engagement = os.environ.get('DEFECTDOJO_ENGAGEMENT', 'Pipeline Run')
    product_type = os.environ.get('DEFECTDOJO_PRODUCT_TYPE', 'Research and Development')
    
    if not url or not token:
        print("❌ Error: DEFECTDOJO_URL y DEFECTDOJO_TOKEN son requeridas.")
        sys.exit(1)
        
    # Normalizar hostname: Django (RFC 1034/1035) rechaza guiones bajos en el HTTP Host header
    if "defectdojo_nginx" in url:
        url = url.replace("defectdojo_nginx", "defectdojo-nginx")
        
    # Mapeo de archivos existentes a tipos oficiales de escáner en DefectDojo
    mappings = [
        ('gl-sast-report.json', 'GitLab SAST Report'),
        ('trivy-sast-report.json', 'Trivy Scan'),
        ('gl-secret-detection-report.json', 'GitLab Secret Detection Report'),
        ('gitleaks-report-*.json', 'Gitleaks Scan'),  # Mapeo nativo de Gitleaks
        ('gl-container-scanning-report*.json', 'GitLab Container Scan'),
        ('trivy-report.json', 'Trivy Scan'),
        ('trivy-iac-report.json', 'Trivy Scan'),
        ('checkov-report.json', 'Checkov Scan'),
        ('zap-report.json', 'ZAP Scan'),
        ('gl-api-security-report.json', 'GitLab DAST Report'),
        # GitHub Actions: los escáneres publican SARIF y reportes ZAP
        ('.sarif', 'SARIF'),
        ('api-security-report.json', 'ZAP Scan'),
        ('zap-baseline-report.json', 'ZAP Scan'),
        ('zap-full-report.json', 'ZAP Scan'),
        ('zap-api-report.json', 'ZAP Scan'),
    ]
    
    uploaded_count = 0
    failed_count = 0
    for file_name, scan_type in mappings:
        for matched_file in glob.glob(f"*{file_name}"):
            if os.path.exists(matched_file) and os.path.getsize(matched_file) > 0:
                sanitize_report_timestamps(matched_file)
                if upload_scan(url, token, product, engagement, scan_type, matched_file, product_type):
                    uploaded_count += 1
                else:
                    failed_count += 1
                    
    print(f"\n✨ Proceso de carga finalizado: {uploaded_count} sincronizados, {failed_count} fallidos.")
    
    if failed_count > 0:
        print(f"❌ Fallo: {failed_count} reporte(s) no pudieron sincronizarse con DefectDojo.")
        sys.exit(1)

if __name__ == "__main__":
    main()

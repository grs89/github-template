#!/usr/bin/env python3
import os
import sys
import glob
import requests

def upload_scan(url, token, product, engagement, scan_type, file_path):
    print(f"🚀 Cargando {os.path.basename(file_path)} a DefectDojo ({scan_type})...")
    api_url = f"{url.rstrip('/')}/api/v2/import-scan/"
    headers = {"Authorization": f"Token {token}"}
    
    data = {
        "active": "true",
        "verified": "true",
        "scan_type": scan_type,
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
            print(f"   ❌ Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Fallo crítico al conectar con DefectDojo: {e}")
        return False

def main():
    url = os.environ.get('DEFECTDOJO_URL')
    token = os.environ.get('DEFECTDOJO_TOKEN')
    product = os.environ.get('DEFECTDOJO_PRODUCT', 'GRS-Project')
    engagement = os.environ.get('DEFECTDOJO_ENGAGEMENT', 'Pipeline Run')
    
    if not url or not token:
        print("❌ Error: DEFECTDOJO_URL y DEFECTDOJO_TOKEN son requeridas.")
        sys.exit(1)
        
    # Mapeo de archivos existentes a tipos oficiales de escáner en DefectDojo
    mappings = [
        ('gl-sast-report.json', 'GitLab SAST Report'),
        ('trivy-sast-report.json', 'Trivy Scan'),
        ('gl-secret-detection-report.json', 'Gitleaks Scan'),
        ('gitleaks-report-*.json', 'Gitleaks Scan'),  # Mapeo nativo de Gitleaks
        ('trivy-report.json', 'Trivy Scan'),
        ('trivy-iac-report.json', 'Trivy Scan'),
        ('checkov-report.json', 'Checkov Scan'),
        ('zap-report.json', 'ZAP Scan'),
        ('gl-api-security-report.json', 'GitLab DAST Report')
    ]
    
    uploaded_count = 0
    for file_name, scan_type in mappings:
        for matched_file in glob.glob(f"*{file_name}"):
            if os.path.exists(matched_file) and os.path.getsize(matched_file) > 0:
                if upload_scan(url, token, product, engagement, scan_type, matched_file):
                    uploaded_count += 1
                    
    print(f"\n✨ Proceso de carga finalizado: {uploaded_count} reportes sincronizados con DefectDojo.")

if __name__ == "__main__":
    main()

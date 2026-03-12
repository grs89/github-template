#!/usr/bin/env python3
"""
Script para generar reportes HTML/PDF a partir de reportes JSON de seguridad.
Soporta múltiples formatos:
- SAST (gl-sast-report.json)
- Dependency Scanning (gl-dependency-scanning-report.json)
- Secret Detection (gl-secret-detection-report.json)
- Trivy Container Scanning (trivy-report.json)
"""

import json
import sys
import os
from jinja2 import Template
from weasyprint import HTML
from datetime import datetime
import glob

def normalize_gl_report(data, report_type):
    """Normaliza reportes de GitLab (SAST, Dependency Scanning, Secret Detection)"""
    vulnerabilities = data.get('vulnerabilities', [])
    findings = []
    
    for vuln in vulnerabilities:
        finding = {
            'name': vuln.get('name', 'N/A'),
            'severity': vuln.get('severity', 'UNKNOWN'),
            'description': vuln.get('description', ''),
            'file': vuln.get('location', {}).get('file', 'N/A'),
            'line': vuln.get('location', {}).get('start_line', 'N/A'),
            'cve': vuln.get('cve', 'N/A'),
            'identifier': vuln.get('identifiers', [{}])[0].get('value', 'N/A') if vuln.get('identifiers') else 'N/A',
            'report_type': report_type
        }
        findings.append(finding)
    
    return findings

def normalize_trivy_report(data):
    """Normaliza reportes de Trivy (Container Scanning e IaC)"""
    findings = []
    
    if 'Results' not in data:
        return findings
    
    for result in data.get('Results', []):
        target = result.get('Target', 'N/A')
        
        # Procesar Vulnerabilidades (Container Scanning)
        vulnerabilities = result.get('Vulnerabilities', [])
        for vuln in vulnerabilities:
            finding = {
                'name': vuln.get('VulnerabilityID', 'N/A'),
                'severity': vuln.get('Severity', 'UNKNOWN'),
                'description': vuln.get('Description', ''),
                'file': target,
                'line': 'N/A',
                'cve': vuln.get('VulnerabilityID', 'N/A'),
                'identifier': vuln.get('PkgName', 'N/A'),
                'report_type': 'Container Scanning (Trivy)',
                'package': vuln.get('PkgName', 'N/A'),
                'installed_version': vuln.get('InstalledVersion', 'N/A'),
                'fixed_version': vuln.get('FixedVersion', 'N/A')
            }
            findings.append(finding)
            
        # Procesar Misconfigurations (IaC)
        misconfigs = result.get('Misconfigurations', [])
        for mis in misconfigs:
            finding = {
                'name': mis.get('ID', 'N/A'),
                'severity': mis.get('Severity', 'UNKNOWN'),
                'description': mis.get('Description', ''),
                'file': target,
                'line': mis.get('CauseMetadata', {}).get('StartLine', 'N/A'),
                'cve': mis.get('ID', 'N/A'),
                'identifier': mis.get('Title', 'N/A'),
                'report_type': 'IaC Scanning (Trivy)'
            }
            findings.append(finding)
    
    return findings

def normalize_checkov_report(data):
    """Normaliza reportes de Checkov"""
    findings = []
    
    # Checkov puede venir como lista si hay varios checks (terraform, dockerfile, etc)
    if isinstance(data, list):
        reports = data
    else:
        reports = [data]
        
    for report in reports:
        results = report.get('results', {})
        failed_checks = results.get('failed_checks', [])
        
        for check in failed_checks:
            finding = {
                'name': check.get('check_id', 'N/A'),
                'severity': check.get('severity', 'UNKNOWN'),
                'description': check.get('check_name', ''),
                'file': check.get('file_path', 'N/A'),
                'line': check.get('file_line_range', [0, 0])[0],
                'cve': check.get('check_id', 'N/A'),
                'identifier': check.get('resource', 'N/A'),
                'report_type': f"IaC Scanning (Checkov - {report.get('check_type', 'N/A')})"
            }
            findings.append(finding)
            
    return findings

def normalize_license_report(data):
    """Normaliza reportes de License Compliance"""
    findings = []
    # Palabras clave para considerar una licencia como crítica/bloqueada
    blocked_keywords = ["GPL", "AGPL", "LGPL", "SSPL", "EUPL"]
    
    for entry in data:
        pkg_name = entry.get('package', 'N/A')
        license_name = entry.get('license', 'Unknown')
        
        is_blocked = any(kw in license_name.upper() for kw in blocked_keywords)
        
        finding = {
            'name': pkg_name,
            'severity': 'CRITICAL' if is_blocked else ('INFO' if license_name != 'Unknown' and license_name != 'Revisar manualmente' else 'MEDIUM'),
            'description': f"Licencia detectada para {pkg_name}: {license_name}",
            'file': entry.get('repository', 'N/A'),
            'line': 'N/A',
            'cve': 'LICENSE-CHECK',
            'identifier': license_name,
            'report_type': 'License Compliance'
        }
        findings.append(finding)
    
    return findings

def normalize_dependency_update_report(data):
    """Normaliza reportes de Dependency Update Check"""
    findings = []
    
    for entry in data:
        pkg_name = entry.get('package', 'N/A')
        current = entry.get('current', 'N/A')
        latest = entry.get('latest', 'N/A')
        pkg_type = entry.get('type', 'N/A')
        
        finding = {
            'name': f"Update available: {pkg_name}",
            'severity': 'INFO',
            'description': f"Nueva versión disponible para {pkg_name} ({pkg_type}): {current} -> {latest}",
            'file': pkg_type,
            'line': 'N/A',
            'cve': 'DEP-UPDATE',
            'identifier': pkg_name,
            'report_type': 'Dependency Update Check',
            'package': pkg_name,
            'installed_version': current,
            'fixed_version': latest
        }
        findings.append(finding)
    
    return findings

def normalize_cleanup_report(data):
    """Normaliza reportes de limpieza del Registry"""
    findings = []
    
    for entry in data:
        action = entry.get('action', 'UNKNOWN')
        tag = entry.get('tag', 'N/A')
        repo = entry.get('repository', 'N/A')
        reason = entry.get('reason', 'N/A')
        
        # Consideramos los eliminados como INFO y los conservados como UNKNOWN/DEBUG
        # para que aparezcan en el reporte
        finding = {
            'name': f"{action}: {tag}",
            'severity': 'INFO' if action == 'DELETED' else 'UNKNOWN',
            'description': f"Acción de cleanup en {repo}. Razón: {reason}",
            'file': repo,
            'line': 'N/A',
            'cve': 'REGISTRY-CLEANUP',
            'identifier': tag,
            'report_type': 'Registry Cleanup'
        }
        findings.append(finding)
        
    return findings

def normalize_signing_report(data):
    """Normaliza reporte de firma de imágenes"""
    findings = []
    
    image = data.get('image', 'N/A')
    status = data.get('signing_status', 'UNKNOWN')
    mode = data.get('signing_mode', 'UNKNOWN')
    verify = data.get('verification_status', 'NOT_VERIFIED')
    attest = data.get('attestation_status', 'NOT_ATTESTED')

    # Hallazgo de firma
    findings.append({
        'name': f"Firma: {status}",
        'severity': 'LOW' if status == 'SUCCESS' else 'CRITICAL',
        'description': f"Estado de firma de imagen ({mode}). Imagen: {image}",
        'file': 'Container Registry',
        'line': 'N/A',
        'cve': 'IMAGE-SIGNING',
        'identifier': image,
        'report_type': 'Image Integrity'
    })

    # Hallazgo de verificación
    findings.append({
        'name': f"Verificación: {verify}",
        'severity': 'LOW' if verify == 'SUCCESS' else 'MEDIUM',
        'description': f"Estado de verificación de firma para {image}",
        'file': 'Supply Chain',
        'line': 'N/A',
        'cve': 'SIGN-VERIFY',
        'identifier': image,
        'report_type': 'Image Integrity'
    })

    # Hallazgo de atestación
    findings.append({
        'name': f"Atestación: {attest}",
        'severity': 'LOW' if attest == 'SUCCESS' else 'MEDIUM',
        'description': f"Estado de atestaciones (SLSA/SBOM) para {image}",
        'file': 'Supply Chain',
        'line': 'N/A',
        'cve': 'ATTESTATION',
        'identifier': image,
        'report_type': 'Image Integrity'
    })

    return findings

def normalize_zap_report(data):
    """Normaliza reportes de OWASP ZAP (DAST)"""
    findings = []
    
    # ZAP JSON tiene una estructura con 'site' -> 'alerts'
    sites = data.get('site', [])
    for site in sites:
        target_site = site.get('@name', 'N/A')
        alerts = site.get('alerts', [])
        
        for alert in alerts:
            # Normalizar severidad (ZAP usa nombres con detalles, ej: "High (Medium)")
            risk_desc = alert.get('riskdesc', 'UNKNOWN').upper()
            severity = 'UNKNOWN'
            if 'HIGH' in risk_desc: severity = 'HIGH'
            elif 'MEDIUM' in risk_desc: severity = 'MEDIUM'
            elif 'LOW' in risk_desc: severity = 'LOW'
            elif 'INFORMATIONAL' in risk_desc: severity = 'INFO'

            # Obtener primera URL de las instancias si existe
            instances = alert.get('instances', [])
            location = target_site
            if instances:
                location = instances[0].get('uri', target_site)

            finding = {
                'name': alert.get('alert', 'N/A'),
                'severity': severity,
                'description': alert.get('desc', ''),
                'file': location,
                'line': 'N/A',
                'cve': alert.get('pluginid', 'ZAP'),
                'identifier': alert.get('alert', 'N/A'),
                'report_type': 'DAST (ZAP)'
            }
            findings.append(finding)
            
    return findings

def load_report(file_path):
    """Carga y normaliza un reporte según su tipo"""
    if not os.path.exists(file_path):
        # Ocultar advertencia si el archivo simplemente no ha sido generado en este pipeline
        return []
    
    # Ignorar archivos vacíos
    if os.path.getsize(file_path) == 0:
        print(f"ℹ️  Saltando {os.path.basename(file_path)}: tamaño 0")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ Error: No se pudo decodificar JSON en {file_path}")
            print(f"   Motivo: {e}")
            print(f"   Primeros 100 caracteres: {repr(content[:100])}")
            return []
    
    filename = os.path.basename(file_path).lower()
    
    # 1. Prioridad: nombres específicos exactos
    if filename == 'dependency-report.json':
        return normalize_dependency_update_report(data)
    elif filename == 'license-report.json':
        return normalize_license_report(data)
    elif filename == 'cleanup-report.json':
        return normalize_cleanup_report(data)
    elif filename == 'signing-report.json':
        return normalize_signing_report(data)
    elif 'zap' in filename:
        return normalize_zap_report(data)
    
    # 2. Búsqueda por palabras clave
    if 'trivy' in filename:
        return normalize_trivy_report(data)
    elif 'checkov' in filename:
        return normalize_checkov_report(data)
    elif 'sast' in filename:
        return normalize_gl_report(data, 'SAST')
    elif 'dependency' in filename:
        return normalize_gl_report(data, 'Dependency Scanning')
    elif 'secret' in filename:
        return normalize_gl_report(data, 'Secret Detection')
    else:
        # Intento por contenido
        if isinstance(data, dict):
            if 'check_type' in data or (isinstance(data, list) and len(data) > 0 and 'check_type' in data[0]):
                return normalize_checkov_report(data)
            if 'vulnerabilities' in data:
                return normalize_gl_report(data, 'Security Scan')
            if 'Results' in data:
                return normalize_trivy_report(data)
        
        print(f"⚠️  Advertencia: Formato desconocido o no procesable en {os.path.basename(file_path)}")
        return []

def generate_report(findings, report_title="Reporte de Seguridad", output_prefix="report"):
    """Genera reporte HTML y PDF a partir de findings normalizados"""
    
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4, 'UNKNOWN': 5}
    findings.sort(key=lambda x: (severity_order.get(x.get('severity', 'UNKNOWN'), 99), x.get('name', '')))
    
    # Conteo general por severidad
    severity_counts = {}
    for finding in findings:
        severity = finding.get('severity', 'UNKNOWN')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
    # Agrupación por categoría para el resumen ejecutivo
    categories = {}
    for finding in findings:
        cat = finding.get('report_type', 'Otros')
        if cat not in categories:
            categories[cat] = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0, 'UNKNOWN': 0, 'total': 0}
        
        sev = finding.get('severity', 'UNKNOWN')
        categories[cat][sev] = categories[cat].get(sev, 0) + 1
        categories[cat]['total'] += 1

    template_str = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <style>
    body { 
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
      margin: 20px; 
      background-color: #f5f5f5;
      color: #333;
    }
    .header {
      background: linear-gradient(135deg, #1a237e 0%, #43a047 100%);
      color: white;
      padding: 30px;
      border-radius: 10px;
      margin-bottom: 30px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header h1 { margin: 0; font-size: 2.2em; }
    .header .meta { margin-top: 10px; opacity: 0.9; font-weight: 300; }
    
    h2 { color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 10px; margin-top: 40px; }
    
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 15px;
      margin-bottom: 30px;
    }
    .summary-card {
      background: white;
      padding: 15px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      text-align: center;
      border-top: 4px solid #ccc;
    }
    .summary-card h3 { margin: 0; font-size: 0.8em; color: #666; text-transform: uppercase; }
    .summary-card .count { font-size: 1.8em; font-weight: bold; margin: 5px 0; }
    
    .card-total { border-top-color: #333; }
    .card-CRITICAL { border-top-color: #b71c1c; color: #b71c1c; }
    .card-HIGH { border-top-color: #e65100; color: #e65100; }
    .card-MEDIUM { border-top-color: #fbc02d; color: #fbc02d; }
    .card-LOW { border-top-color: #2e7d32; color: #2e7d32; }
    .card-INFO { border-top-color: #0277bd; color: #0277bd; }

    /* Executive Summary Table */
    .exec-table {
      width: 100%;
      border-collapse: collapse;
      background: white;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      margin-bottom: 30px;
    }
    .exec-table th { background: #f8f9fa; padding: 12px; text-align: left; color: #666; font-size: 0.9em; }
    .exec-table td { padding: 12px; border-top: 1px solid #eee; }
    .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
    .status-clean { background: #e8f5e9; color: #2e7d32; }
    .status-warning { background: #fff3e0; color: #e65100; }
    .status-danger { background: #ffebee; color: #b71c1c; }

    .vuln {
      background: white;
      margin-bottom: 25px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      overflow: hidden;
    }
    .vuln-header {
      padding: 15px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: white;
    }
    .header-CRITICAL { background-color: #b71c1c; }
    .header-HIGH { background-color: #e65100; }
    .header-MEDIUM { background-color: #fbc02d; color: #333; }
    .header-LOW { background-color: #2e7d32; }
    .header-INFO { background-color: #0277bd; }
    
    .vuln-body { padding: 20px; }
    .vuln-title { margin: 0; font-size: 1.2em; }
    
    .details-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
      margin-bottom: 15px;
    }
    .detail-box { background: #fcfcfc; padding: 10px; border-radius: 4px; border: 1px solid #f0f0f0; }
    .label { font-size: 0.75em; color: #888; text-transform: uppercase; font-weight: bold; }
    .value { font-size: 0.95em; color: #444; word-break: break-all; }
    
    .description { background: #f9f9f9; padding: 15px; border-radius: 4px; font-size: 0.9em; line-height: 1.5; }
    
    @media print {
      body { margin: 0; }
      .vuln { break-inside: avoid; }
      .header { border-radius: 0; }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>{{ title }}</h1>
    <div class="meta">Fecha de generación: {{ date }} | Pipeline #{{ os_env.get('CI_PIPELINE_ID', 'Local') }}</div>
  </div>

  <h2>📊 Resumen Ejecutivo</h2>
  <div class="summary-grid">
    <div class="summary-card card-total">
      <h3>Hallazgos</h3>
      <div class="count">{{ findings|length }}</div>
    </div>
    {% if severity_counts.CRITICAL %}
    <div class="summary-card card-CRITICAL">
      <h3>Críticos</h3>
      <div class="count">{{ severity_counts.CRITICAL }}</div>
    </div>
    {% endif %}
    {% if severity_counts.HIGH %}
    <div class="summary-card card-HIGH">
      <h3>Altos</h3>
      <div class="count">{{ severity_counts.HIGH }}</div>
    </div>
    {% endif %}
    {% if severity_counts.MEDIUM %}
    <div class="summary-card card-MEDIUM">
      <h3>Medios</h3>
      <div class="count">{{ severity_counts.MEDIUM }}</div>
    </div>
    {% endif %}
  </div>

  <table class="exec-table">
    <thead>
      <tr>
        <th>Categoría de Análisis</th>
        <th style="text-align: center;">Críticos</th>
        <th style="text-align: center;">Altos</th>
        <th style="text-align: center;">Otros</th>
        <th style="text-align: center;">Estado</th>
      </tr>
    </thead>
    <tbody>
      {% for cat_name, stats in categories.items() %}
      <tr>
        <td><strong>{{ cat_name }}</strong></td>
        <td style="text-align: center; color: {{ '#b71c1c' if stats.CRITICAL > 0 else '#ccc' }};">{{ stats.CRITICAL }}</td>
        <td style="text-align: center; color: {{ '#e65100' if stats.HIGH > 0 else '#ccc' }};">{{ stats.HIGH }}</td>
        <td style="text-align: center; color: #666;">{{ stats.MEDIUM + stats.LOW + stats.INFO }}</td>
        <td style="text-align: center;">
          {% if stats.CRITICAL > 0 %}
            <span class="status-badge status-danger">PELIGRO</span>
          {% elif stats.HIGH > 0 %}
            <span class="status-badge status-warning">REVISIÓN</span>
          {% else %}
            <span class="status-badge status-clean">LIMPIO</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <h2>🔍 Detalle de Hallazgos</h2>
  {% if findings %}
    {% for vuln in findings %}
    <div class="vuln">
      <div class="vuln-header header-{{ vuln.severity }}">
        <h3 class="vuln-title">{{ vuln.name }}</h3>
        <span class="status-badge" style="background: rgba(255,255,255,0.2);">{{ vuln.severity }}</span>
      </div>
      <div class="vuln-body">
        <div class="details-grid">
          <div class="detail-box">
            <div class="label">Origen</div>
            <div class="value">{{ vuln.report_type }}</div>
          </div>
          <div class="detail-box">
            <div class="label">Identificador</div>
            <div class="value">{{ vuln.cve }}</div>
          </div>
          <div class="detail-box">
            <div class="label">Localización</div>
            <div class="value">{{ vuln.file }}{% if vuln.line != 'N/A' %}:{{ vuln.line }}{% endif %}</div>
          </div>
          {% if vuln.package %}
          <div class="detail-box">
            <div class="label">Paquete / Componente</div>
            <div class="value">{{ vuln.package }} ({{ vuln.installed_version }} -> {{ vuln.fixed_version or 'N/A' }})</div>
          </div>
          {% endif %}
        </div>
        {% if vuln.description %}
        <div class="description">
          <div class="label" style="margin-bottom: 5px;">Descripción y Mitigación</div>
          {{ vuln.description }}
        </div>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  {% else %}
    <div class="no-findings">
      <h3>✅ No se detectaron vulnerabilidades</h3>
      <p>Todos los escaneos finalizaron sin encontrar problemas de seguridad críticos o pendientes.</p>
    </div>
  {% endif %}
</body>
</html>
"""
    
    html = Template(template_str).render(
        title=report_title,
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        findings=findings,
        severity_counts=severity_counts,
        categories=categories,
        os_env=dict(os.environ)
    )
    
    html_path = f"{output_prefix}.html"
    pdf_path = f"{output_prefix}.pdf"
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    try:
        HTML(string=html).write_pdf(pdf_path)
        print(f"✅ Reportes generados: {html_path} y {pdf_path}")
    except Exception as e:
        print(f"⚠️  Error al generar PDF: {e}")
        print(f"✅ Reporte HTML generado: {html_path}")

def main():
    """Función principal con descubrimiento dinámico de reportes"""
    # 1. Lista base de reportes estándar
    standard_files = [
        'gl-sast-report.json',
        'gl-dependency-scanning-report.json',
        'gl-secret-detection-report.json',
        'trivy-report.json',
        'trivy-iac-report.json',
        'trivy-sast-report.json',
        'checkov-report.json',
        'license-report.json',
        'dependency-report.json',
        'dependency_scanning.json',
        'cleanup-report.json',
        'signing-report.json',
        'zap-report.json'
    ]
    
    # 2. Descubrimiento dinámico de cualquier JSON que parezca un reporte
    # Buscamos archivos que terminen en report.json o scanning.json
    dynamic_files = glob.glob("*report.json") + glob.glob("*scanning.json") + glob.glob("*compliance.json")
    
    # Combinar y eliminar duplicados manteniendo el orden
    all_potential_files = list(dict.fromkeys(standard_files + dynamic_files))
    
    all_findings = []
    found_reports = []
    
    print("🔍 Iniciando descubrimiento de reportes...")
    for report_file in all_potential_files:
        if not os.path.exists(report_file):
            continue
            
        findings = load_report(report_file)
        if findings:
            all_findings.extend(findings)
            found_reports.append(report_file)
            print(f"✅ Cargado: {report_file} ({len(findings)} hallazgos)")
        elif os.path.exists(report_file):
            # Si el archivo existe pero load_report devolvió vacío, es que no tenía hallazgos
            # o se saltó por tamaño 0 (ya logueado en load_report)
            pass
    
    if not all_findings:
        print("ℹ️  No se encontraron hallazgos en ningún reporte.")
        print("📄 Generando reporte de seguridad limpio...")
        generate_report([], "Reporte Consolidado de Seguridad", "security-report")
        sys.exit(0)

    # Reporte consolidado
    print(f"\n📊 Generando reporte consolidado con {len(all_findings)} hallazgos...")
    generate_report(all_findings, "Reporte Consolidado de Seguridad", "security-report")
    
    # Reportes individuales
    if len(found_reports) > 1:
        print("\n📄 Generando reportes individuales...")
        for report_file in found_reports:
            findings = load_report(report_file)
            if findings:
                report_type = os.path.basename(report_file).replace('.json', '').replace('gl-', '').replace('-', ' ').title()
                output_name = report_file.replace('.json', '').replace('gl-', '')
                generate_report(findings, f"Reporte de {report_type}", output_name)

if __name__ == "__main__":
    main()

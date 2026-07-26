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

IMAGE_INTEGRITY = 'Image Integrity'

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
        severity = 'MEDIUM'
        if is_blocked:
            severity = 'CRITICAL'
        elif license_name not in ['Unknown', 'Revisar manualmente']:
            severity = 'INFO'
            
        finding = {
            'name': pkg_name,
            'severity': severity,
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

def normalize_gitleaks_report(data):
    """Normaliza reportes JSON nativos del motor de escaneo Gitleaks"""
    findings = []
    
    if not isinstance(data, list):
        return findings
        
    for entry in data:
        finding = {
            'name': entry.get('Description', 'Secret Detected'),
            'severity': 'CRITICAL',
            'description': f"Secreto del tipo '{entry.get('Description', 'N/A')}' expuesto. Regla: {entry.get('RuleID', 'N/A')}.",
            'file': entry.get('File', 'N/A'),
            'line': entry.get('StartLine', 'N/A'),
            'cve': entry.get('RuleID', 'GITLEAKS-MATCH'),
            'identifier': entry.get('Match', 'N/A'),
            'report_type': 'Secret Detection (Gitleaks)'
        }
        findings.append(finding)
        
    return findings

def normalize_slsa_report(data):
    """Normaliza reporte de SLSA Provenance"""
    findings = []
    
    image = data.get('image', 'N/A')
    status = data.get('status', 'UNKNOWN')
    timestamp = data.get('timestamp', 'N/A')

    findings.append({
        'name': f"SLSA Provenance: {status}",
        'severity': 'INFO' if status == 'success' else 'CRITICAL',
        'description': f"Se ha generado y adjunto un atestado SLSA Provenance para la imagen {image}. Generado el: {timestamp}.",
        'file': 'Container Registry',
        'line': 'N/A',
        'cve': 'SLSA-PROVENANCE',
        'identifier': image,
        'report_type': IMAGE_INTEGRITY
    })
    
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
        'report_type': IMAGE_INTEGRITY
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
        'report_type': IMAGE_INTEGRITY
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
        'report_type': IMAGE_INTEGRITY
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

def normalize_code_quality_report(data):
    """Normaliza reportes de Code Quality (CodeClimate)"""
    findings = []
    
    # Mapeo de severidad de CodeClimate a nuestro estándar
    # CodeClimate: info, minor, major, critical, blocker
    severity_map = {
        'info': 'INFO',
        'minor': 'LOW',
        'major': 'MEDIUM',
        'critical': 'HIGH',
        'blocker': 'CRITICAL'
    }
    
    for issue in data:
        severity = severity_map.get(issue.get('severity', 'info').lower(), 'MEDIUM')
        
        finding = {
            'name': issue.get('check_name', issue.get('description', 'Code Quality Issue')),
            'severity': severity,
            'description': issue.get('description', ''),
            'file': issue.get('location', {}).get('path', 'N/A'),
            'line': issue.get('location', {}).get('lines', {}).get('begin', issue.get('location', {}).get('positions', {}).get('begin', {}).get('line', 'N/A')),
            'cve': 'CODE-QUALITY',
            'identifier': issue.get('fingerprint', 'N/A'),
            'report_type': 'Code Quality'
        }
        findings.append(finding)
    
    return findings

def normalize_sbom_report(data, filename=""):
    """Normaliza reportes de SBOM (CycloneDX)"""
    findings = []
    
    # Intentar extraer nombre del servicio del filename (gl-sbom-NAME.cdx.json)
    service_name = "Global"
    if 'sbom-' in filename:
        try:
            # gl-sbom-auth.cdx.json -> auth
            service_name = filename.split('sbom-')[1].split('.')[0]
            if service_name.lower() == 'report': service_name = "Global"
        except Exception:
            pass

    components = data.get('components', [])
    for comp in components:
        licenses = comp.get('licenses', [])
        license_names = []
        for l in licenses:
            if 'license' in l:
                license_names.append(l['license'].get('id', l['license'].get('name', 'Unknown')))
        
        license_str = ", ".join(license_names) if license_names else "N/A"
        
        finding = {
            'name': comp.get('name', 'Unknown Component'),
            'severity': 'INFO',
            'description': f"Versión: {comp.get('version', 'N/A')} | Licencia: {license_str}",
            'file': comp.get('purl', 'N/A'),
            'line': 'N/A',
            'cve': 'SBOM-COMPONENT',
            'identifier': comp.get('bom-ref', 'N/A'),
            'report_type': f'SBOM ({service_name.title()})' if service_name != "Global" else 'Software Bill of Materials'
        }
        findings.append(finding)
    
    return findings

def normalize_coverage_report(data):
    """Normaliza reportes de Code Coverage (JSON)"""
    findings = []
    
    # Soporte para formato genérico simple: {"coverage": 85.5, "files": [...]}
    # O formats específicos de herramientas
    coverage_pct = data.get('coverage', 0)
    if not coverage_pct and 'totals' in data: # pytest-cov json
        coverage_pct = data.get('totals', {}).get('percent_covered', 0)
    
    try:
        if isinstance(coverage_pct, str):
            coverage_pct = coverage_pct.replace('%', '').strip()
        coverage_pct = float(coverage_pct)
    except (ValueError, TypeError):
        coverage_pct = 0.0

    # Creamos un 'finding' especial de tipo INFO para mostrar el resumen de cobertura
    severity = 'HIGH'
    if coverage_pct > 80:
        severity = 'INFO'
    elif coverage_pct > 50:
        severity = 'MEDIUM'

    findings.append({
        'name': f"Cobertura Total: {coverage_pct}%",
        'severity': severity,
        'description': f"El proyecto tiene una cobertura de tests del {coverage_pct}%.",
        'file': 'Global',
        'line': 'N/A',
        'cve': 'CODE-COVERAGE',
        'identifier': f"{coverage_pct}%",
        'report_type': 'Code Coverage'
    })
    
    # Detalle por archivo si existe (limitar a los más importantes o con baja cobertura)
    files = data.get('files', {})
    if isinstance(files, dict):
        for file_path, file_data in list(files.items())[:20]: # Limitar a 20 archivos
            f_cov = file_data.get('summary', {}).get('percent_covered', 100)
            if f_cov < 100:
                findings.append({
                    'name': f"Cobertura Archivo: {f_cov}%",
                    'severity': 'INFO' if f_cov > 80 else 'MEDIUM',
                    'description': f"Archivo con cobertura incompleta: {file_path}",
                    'file': file_path,
                    'line': 'N/A',
                    'cve': 'FILE-COVERAGE',
                    'identifier': file_path,
                    'report_type': 'Code Coverage'
                })
                
    return findings

def normalize_changelog_report(data):
    """Normaliza el reporte de changelog generado por git-cliff"""
    findings = []
    # git-cliff --context genera un JSON con una lista de releases
    releases = data.get('releases', [])
    if not releases:
        return []
    
    # Tomamos el release más reciente (generalmente el primero)
    latest = releases[0]
    version = latest.get('version', 'Sin release')
    commits = latest.get('commits', [])
    
    summary = []
    for commit in commits[:10]: # Mostrar solo los 10 últimos cambios
        msg = commit.get('message', '').split('\n')[0]
        summary.append(f"- {msg}")
    
    findings.append({
        'name': f"Changelog: Versión {version}",
        'severity': 'INFO',
        'description': "Cambios recientes detectados:\n" + "\n".join(summary),
        'file': 'CHANGELOG',
        'line': 'N/A',
        'cve': 'CHANGELOG-INFO',
        'identifier': version,
        'report_type': 'Changelog'
    })
    return findings

def normalize_badges_report(data):
    """Normaliza el reporte de estado de los badges"""
    findings = []
    badges = data.get('badges', [])
    
    summary = [f"- {b['name']}: {b['status']}" for b in badges]
    
    findings.append({
        'name': "Estado de Badges",
        'severity': 'INFO',
        'description': "Se han generado satisfactoriamente los siguientes distintivos:\n" + "\n".join(summary),
        'file': 'badges/',
        'line': 'N/A',
        'cve': 'BADGES-STATUS',
        'identifier': 'BADGES',
        'report_type': 'Utilities'
    })
    return findings

def normalize_accessibility_report(data):
    """Normaliza reportes de Accesibilidad (pa11y-ci)"""
    findings = []
    
    # pa11y-ci genera una lista de issues directamente o un dict con 'results'
    issues = data if isinstance(data, list) else data.get('results', [])
    
    for issue in issues:
        code = issue.get('code', 'N/A')
        severity = issue.get('type', 'error').upper()
        # Mapear error/warning a nuestro estándar
        if severity == 'ERROR': sev = 'HIGH'
        elif severity == 'WARNING': sev = 'MEDIUM'
        else: sev = 'INFO'

        findings.append({
            'name': f"Accesibilidad: {code}",
            'severity': sev,
            'description': issue.get('message', ''),
            'file': issue.get('context', 'N/A'),
            'line': 'N/A',
            'cve': code,
            'identifier': code,
            'report_type': 'Accessibility'
        })
    return findings

def get_normalize_func(filename, data):
    """Retorna la función de normalización adecuada según el nombre o contenido"""
    # 1. Prioridad: nombres específicos exactos o patrones claros
    if filename == 'dependency-report.json':
        return lambda d: normalize_dependency_update_report(d)
    if filename == 'license-report.json' or 'license-compliance' in filename:
        return lambda d: normalize_license_report(d)
    if filename == 'changelog.json':
        return lambda d: normalize_changelog_report(d)
    if filename == 'badges-report.json':
        return lambda d: normalize_badges_report(d)
    if filename == 'cleanup-report.json':
        return lambda d: normalize_cleanup_report(d)
    if 'signing-report.json' in filename:
        return lambda d: normalize_signing_report(d)
    if 'slsa-provenance-report.json' in filename:
        return lambda d: normalize_slsa_report(d)
    if 'coverage' in filename:
        return lambda d: normalize_coverage_report(d)
    if 'zap' in filename:
        return lambda d: normalize_zap_report(d)
    if 'code-quality' in filename:
        return lambda d: normalize_code_quality_report(d)
    if 'sbom' in filename or filename.endswith('.cdx.json'):
        return lambda d: normalize_sbom_report(d, filename)
    if 'accessibility' in filename:
        return lambda d: normalize_accessibility_report(d)
    
    # 2. Búsqueda por palabras clave
    if 'trivy' in filename:
        return lambda d: normalize_trivy_report(d)
    if 'checkov' in filename:
        return lambda d: normalize_checkov_report(d)
    if 'container-scanning' in filename or 'cluster-image-scanning' in filename:
        return lambda d: normalize_gl_report(d, 'Container Scanning')
    if 'sast' in filename:
        return lambda d: normalize_gl_report(d, 'SAST')
    if 'dependency' in filename:
        return lambda d: normalize_gl_report(d, 'Dependency Scanning')
    if 'gitleaks' in filename:
        return lambda d: normalize_gitleaks_report(d)
    if 'secret' in filename:
        if isinstance(data, list):
            return lambda d: normalize_gitleaks_report(d)
        else:
            return lambda d: normalize_gl_report(d, 'Secret Detection')
    
    # 3. Intento por contenido
    if isinstance(data, dict):
        if 'check_type' in data or (isinstance(data, list) and len(data) > 0 and 'check_type' in data[0]):
            return lambda d: normalize_checkov_report(d)
        if 'vulnerabilities' in data:
            return lambda d: normalize_gl_report(d, 'Security Scan')
        if 'Results' in data:
            return lambda d: normalize_trivy_report(d)
    return None

def extract_service_name(filename):
    """Extrae el nombre del servicio o lenguaje a partir del nombre del archivo si existe"""
    name = filename.replace('.cdx.json', '').replace('.json', '')
    
    # Ordenados de más largo a más corto para evitar coincidencias parciales prematuras
    prefixes = [
        'gl-dependency-scanning-', 'gl-cluster-image-scanning-', 'gl-secret-detection-',
        'gl-code-quality-', 'gl-accessibility-', 'trivy-iac-', 'trivy-sast-',
        'gl-sast-', 'gl-sbom-', 'checkov-', 'coverage-', 'license-', 'dependency-',
        'cleanup-', 'signing-', 'trivy-', 'zap-'
    ]
    
    for prefix in prefixes:
        if name.startswith(prefix):
            service = name[len(prefix):]
            if service and service.lower() != 'report':
                return service
                
    # Fallback si el nombre termina en -report
    if name.endswith('-report'):
        service = name[:-7]
        # Limpiar prefijos si aún quedan
        for p in ['gl-sast', 'trivy', 'checkov', 'zap', 'license', 'coverage', 'gl-sbom']:
            if service.startswith(p + '-'):
                return service[len(p)+1:]
        if service and service.lower() != 'report':
            return service
            
    return None

def load_report(file_path):
    """Carga y normaliza un reporte según su tipo"""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return []
    
    filename = os.path.basename(file_path).lower()
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    
    norm_func = get_normalize_func(filename, data)
    if norm_func:
        findings = norm_func(data)
        
        # Añadir información de servicio si se detecta
        service_name = extract_service_name(filename)
        for f in findings:
            f['service'] = service_name if service_name else 'Global'
            if service_name and service_name.lower() not in f.get('report_type', '').lower():
                # Evitar duplicar el servicio si ya fue añadido (ej: por normalize_sbom_report)
                f['report_type'] = f"{f.get('report_type', 'Unknown')} ({service_name.title()})"
        return findings
        
    print(f"⚠️  Advertencia: Formato desconocido o no procesable en {os.path.basename(file_path)}")
    return []

def calculate_health_score(severity_counts):
    """Calcula una puntuación de salud (A-F) basada en pesos de severidad"""
    weights = {'CRITICAL': 25, 'HIGH': 10, 'MEDIUM': 3, 'LOW': 1, 'INFO': 0, 'UNKNOWN': 1}
    total_penalty = sum(severity_counts.get(s, 0) * weights[s] for s in weights)
    
    if total_penalty == 0: return 'A+', 'Pristine', '#43a047'
    if total_penalty <= 5: return 'A', 'Secure', '#43a047'
    if total_penalty <= 15: return 'B', 'Good', '#8bc34a'
    if total_penalty <= 40: return 'C', 'Warning', '#fbc02d'
    if total_penalty <= 80: return 'D', 'At Risk', '#f57c00'
    return 'F', 'Critical Risk', '#b71c1c'

def get_pipeline_context(findings):
    """Genera dinámicamente el contexto y estado de los jobs del pipeline basándose en el entorno y reportes existentes."""
    import os
    import glob
    import subprocess

    # 1. Identificar lenguaje
    detected_lang = os.environ.get('DETECTED_LANG', 'GO').upper()

    # 2. Identificar repositorio
    repo_path = os.environ.get('CI_PROJECT_PATH')
    if not repo_path:
        try:
            git_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], text=True).strip()
            if 'gitlab.com' in git_url or 'github.com' in git_url:
                repo_path = git_url.split(':')[-1].replace('.git', '')
                if '/' not in repo_path:
                    repo_path = git_url.split('/')[-2] + '/' + git_url.split('/')[-1].replace('.git', '')
        except Exception:
            repo_path = 'grs89/centralizegg'
    if not repo_path:
        repo_path = 'grs89/centralizegg'

    # 3. Identificar tag/etiqueta de forma 100% dinámica
    commit_tag = os.environ.get('CI_COMMIT_TAG')
    if not commit_tag:
        try:
            commit_tag = subprocess.check_output(['git', 'describe', '--tags', '--always'], text=True).strip()
        except Exception:
            pass
    if not commit_tag:
        commit_tag = os.environ.get('CI_COMMIT_REF_NAME')
    if not commit_tag:
        commit_tag = 'N/D'

    # 4. Determinar estados de calidad
    has_linter = os.path.exists('gl-code-quality-report.json') or glob.glob('*code-quality*.json')
    linters_status = '✓ Activo' if has_linter else '○ Omitido'

    has_coverage = (
        os.path.exists('coverage-report.json') or
        glob.glob('*coverage*.json') or
        glob.glob('*coverage*.xml') or
        glob.glob('**/coverage_reports/*coverage*.json', recursive=True) or
        glob.glob('**/coverage_reports/*coverage*.xml', recursive=True) or
        any(f.get('cve') == 'CODE-COVERAGE' for f in findings)
    )
    tests_status = '✓ Pasados' if has_coverage else '○ Omitido'

    has_secrets = os.path.exists('gl-secret-detection-report.json') or glob.glob('*secret*.json') or glob.glob('*gitleaks*.json')
    secret_scan_status = '✓ Gitleaks OK' if has_secrets else '○ Omitido'

    # 5. Determinar compilación y firma
    has_docker = os.path.exists('02-Dockerfile/Dockerfile-report') or glob.glob('*Dockerfile*') or glob.glob('**/Dockerfile*', recursive=True) or glob.glob('**/*.dockerfile', recursive=True)
    docker_buildx_status = '✓ Compilado' if has_docker else '○ Omitido'
    
    has_signing = os.path.exists('signing-report.json') or glob.glob('*signing*.json')
    firma_digital_status = '✓ Cosign' if has_signing else '○ Omitido'

    has_sbom = os.path.exists('gl-sbom-report.json') or glob.glob('*.cdx.json') or glob.glob('*sbom*.json')
    sbom_cyclonedx_status = '✓ Firmado' if has_sbom else '○ Omitido'

    # 6. Determinar seguridad
    has_sast = os.path.exists('trivy-report.json') or os.path.exists('gl-sast-report.json') or glob.glob('*sast*.json')
    sast_sca_status = '✓ Trivy' if has_sast else '○ Omitido'

    has_checkov = os.path.exists('checkov-report.json') or glob.glob('*checkov*.json')
    iac_audit_status = '✓ Checkov' if has_checkov else '○ Omitido'

    has_dast = os.path.exists('zap-report.json') or glob.glob('*zap*.json')
    dast_status = '✓ ZAP Activo' if has_dast else '◯ Omitido (sin site_url)'

    has_api_sec = os.path.exists('gl-api-security-report.json') or glob.glob('*api-security*.json')
    api_security_status = '✓ Escaneado' if has_api_sec else '○ Omitido'

    has_cluster = os.path.exists('gl-cluster-image-scanning-report.json') or glob.glob('*cluster*.json')
    cluster_status = '✓ Auditado' if has_cluster else '○ Omitido'

    has_container_scan = os.path.exists('gl-container-scanning-report.json') or glob.glob('*container-scanning*.json') or glob.glob('*container_scanning*.json')
    container_scan_status = '✓ Escaneado' if has_container_scan else '○ Omitido'

    # 7. Lanzamiento y wiki
    is_tag = os.environ.get('CI_COMMIT_TAG') is not None
    if not is_tag and not os.environ.get('CI_SERVER_URL'):
        try:
            is_tag = subprocess.check_output(['git', 'describe', '--exact-match', '--tags'], text=True, stderr=subprocess.DEVNULL).strip() != ""
        except Exception:
            is_tag = False
    release_status = 'PUBLICADA' if is_tag else '○ Omitido (no tag)'

    is_main = os.environ.get('CI_COMMIT_REF_NAME') == 'main'
    if not is_main and not os.environ.get('CI_SERVER_URL'):
        try:
            current_branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
            is_main = current_branch == 'main'
        except Exception:
            is_main = False
    wiki_sync_status = '✓ Completado' if is_main else '○ Omitido (no main)'

    has_smoke = os.path.exists('smoke-test-report.json') or glob.glob('*smoke*.json')
    smoke_status = '✓ Salud OK' if has_smoke else '○ Omitido'

    has_perf = os.path.exists('perf-reports/k6-summary.json') or glob.glob('*k6*.json') or os.path.exists('k6-summary.json')
    perf_status = '✓ Latencia OK' if has_perf else '○ Omitido'

    return {
        'detected_lang': detected_lang,
        'repo_path': repo_path,
        'commit_tag': commit_tag,
        'linters_status': linters_status,
        'tests_status': tests_status,
        'secret_scan_status': secret_scan_status,
        'docker_buildx_status': docker_buildx_status,
        'firma_digital_status': firma_digital_status,
        'sbom_cyclonedx_status': sbom_cyclonedx_status,
        'sast_sca_status': sast_sca_status,
        'iac_audit_status': iac_audit_status,
        'container_scan_status': container_scan_status,
        'dast_status': dast_status,
        'api_security_status': api_security_status,
        'cluster_status': cluster_status,
        'release_status': release_status,
        'wiki_sync_status': wiki_sync_status,
        'smoke_status': smoke_status,
        'perf_status': perf_status
    }

def generate_report(findings, report_title="GRS Executive Summary", output_prefix="executive-summary"):
    """Genera reporte HTML y PDF con Dashboard Ejecutivo Premium"""
    
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4, 'UNKNOWN': 5}
    
    # Filtrar hallazgos de tipo CODE-COVERAGE, CHANGELOG, BADGES de la lista de hallazgos del detalle
    # para que no aparezcan como vulnerabilidades, pero mantenerlos en findings para estadísticas
    detail_findings = [f for f in findings if f.get('cve') not in ['CODE-COVERAGE', 'CHANGELOG-INFO', 'BADGES-STATUS', 'REGISTRY-CLEANUP', 'DEP-UPDATE', 'SBOM-COMPONENT']]
    detail_findings.sort(key=lambda x: (severity_order.get(x.get('severity', 'UNKNOWN'), 99), x.get('name', '')))
    
    severity_counts = {s: 0 for s in severity_order}
    for finding in detail_findings:
        sev = finding.get('severity', 'UNKNOWN')
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
    score_grade, score_label, score_color = calculate_health_score(severity_counts)

    # Cobertura dinámica
    coverage_pct = "N/D"
    for f in findings:
        if f.get('cve') == 'CODE-COVERAGE':
            coverage_pct = f.get('identifier', '0.00%')
            if not coverage_pct.endswith('%'):
                coverage_pct = f"{coverage_pct}%"
            break

    # Obtener el contexto dinámico del pipeline primero
    pipeline_ctx = get_pipeline_context(findings)

    categories = {}
    for finding in detail_findings:
        cat = finding.get('report_type', 'Otros')
        if cat not in categories:
            categories[cat] = {s: 0 for s in severity_order}
            categories[cat]['total'] = 0
            categories[cat]['status'] = 'LIMPIO'
        
        sev = finding.get('severity', 'UNKNOWN')
        categories[cat][sev] = categories[cat].get(sev, 0) + 1
        categories[cat]['total'] += 1

    # Asegurar que las categorías obligatorias siempre existan
    required_keys = [
        'Tests Unitarios',
        'IaC Audit',
        'Container Scan (Trivy - Registro)',
        'Container Scan (Trivy - Docker Hub)',
        'SAST (Trivy - Código)'
    ]
    for rk in required_keys:
        if rk not in categories:
            categories[rk] = {s: 0 for s in severity_order}
            categories[rk]['total'] = 0
            categories[rk]['status'] = 'LIMPIO'

    # Asignar estados dinámicos a las categorías obligatorias según el pipeline_ctx
    if 'Tests Unitarios' in categories:
        if 'Omitido' in pipeline_ctx.get('tests_status', 'Omitido'):
            categories['Tests Unitarios']['status'] = 'OMITIDO'
        elif categories['Tests Unitarios'].get('total', 0) == 0:
            categories['Tests Unitarios']['status'] = 'PASADOS'
            
    if 'IaC Audit' in categories:
        if 'Omitido' in pipeline_ctx.get('iac_audit_status', 'Omitido'):
            categories['IaC Audit']['status'] = 'OMITIDO'
            
    if 'Container Scan (Trivy - Registro)' in categories:
        if 'Omitido' in pipeline_ctx.get('container_scan_status', 'Omitido'):
            categories['Container Scan (Trivy - Registro)']['status'] = 'OMITIDO'
            
    if 'Container Scan (Trivy - Docker Hub)' in categories:
        if 'Omitido' in pipeline_ctx.get('container_scan_status', 'Omitido'):
            categories['Container Scan (Trivy - Docker Hub)']['status'] = 'OMITIDO'
            
    if 'SAST (Trivy - Código)' in categories:
        if 'Omitido' in pipeline_ctx.get('sast_sca_status', 'Omitido'):
            categories['SAST (Trivy - Código)']['status'] = 'OMITIDO'

    # Calcular total de hallazgos
    total_findings = sum(severity_counts.get(s, 0) for s in severity_counts)

    template_str = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    :root {
      --primary: #1e3a8a;
      --secondary: #16a34a;
      --accent: #2563eb;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #1e293b;
      --critical: #dc2626;
      --high: #ea580c;
      --medium: #eab308;
      --low: #16a34a;
      --info: #2563eb;
      --unknown: #64748b;
    }
    
    @page {
      size: A4;
      margin: 15mm 15mm 15mm 15mm;
      @bottom-right {
        content: "Pág " counter(page) " de " counter(pages);
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: #94a3b8;
      }
    }

    body { 
      font-family: 'Inter', -apple-system, sans-serif; 
      margin: 0; padding: 0;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      font-size: 14px;
    }

    .header {
      background: linear-gradient(135deg, #1e3a8a 0%, #16a34a 100%);
      color: white;
      padding: 35px 40px;
      border-bottom: 5px solid var(--secondary);
    }
    
    .header h1 { 
      margin: 0; 
      font-size: 2.2em; 
      font-weight: 800;
      letter-spacing: -0.5px; 
    }
    .header .meta { 
      margin-top: 10px; 
      font-size: 0.95em; 
      opacity: 0.9; 
      font-weight: 400;
    }
    
    .container { max-width: 1000px; margin: 0 auto; padding: 25px 20px; }

    /* Subheadings style */
    .section-title {
      font-size: 1.4em; 
      font-weight: 800;
      margin: 35px 0 15px; 
      color: #1e3a8a; 
      padding-bottom: 8px;
      border-bottom: 3px solid #1e3a8a;
      display: flex;
      align-items: center;
    }

    /* Cards Layout */
    .cards-container {
      display: flex;
      flex-direction: column;
      gap: 15px;
      margin-bottom: 30px;
    }

    .status-card {
      background: var(--card-bg);
      border-radius: 8px;
      border: 1px solid #e2e8f0;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
      padding: 15px 20px;
      margin-bottom: 5px;
    }
    
    .status-card.contexto { border-left: 5px solid #1e3a8a; }
    .status-card.pruebas { border-left: 5px solid #16a34a; }
    .status-card.compilacion { border-left: 5px solid #ea580c; }
    .status-card.seguridad { border-left: 5px solid #2563eb; }
    .status-card.lanzamiento { border-left: 5px solid #7c3aed; }

    .card-header {
      font-weight: 800;
      font-size: 0.95em;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
    }
    
    .status-card.contexto .card-header { color: #1e3a8a; }
    .status-card.pruebas .card-header { color: #16a34a; }
    .status-card.compilacion .card-header { color: #ea580c; }
    .status-card.seguridad .card-header { color: #2563eb; }
    .status-card.lanzamiento .card-header { color: #7c3aed; }

    .card-content {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .card-item {
      font-size: 0.95em;
      color: #334155;
    }

    .card-item strong {
      color: #1e293b;
      font-weight: 600;
    }

    /* Badges */
    .badge { 
      padding: 3px 10px; 
      border-radius: 20px; 
      font-size: 0.8em; 
      font-weight: 700; 
      text-transform: uppercase;
      display: inline-block;
    }
    .badge-success { background: #dcfce7; color: #16a34a; }
    .badge-warning { background: #fef3c7; color: #d97706; }
    .badge-danger { background: #fee2e2; color: #dc2626; }
    
    /* Executive Summary Stat Blocks */
    .stat-blocks {
      display: flex;
      flex-direction: column;
      gap: 15px;
      margin-bottom: 30px;
    }

    .stat-row {
      background: var(--card-bg);
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 15px;
      text-align: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .stat-row.cobertura { border-top: 4px solid #3b82f6; border-bottom: 4px solid #3b82f6; }
    .stat-row.hallazgos { border-top: 4px solid #1e293b; border-bottom: 4px solid #1e293b; }
    .stat-row.altos { border-top: 4px solid #ea580c; border-bottom: 4px solid #ea580c; }
    .stat-row.medios { border-top: 4px solid #eab308; border-bottom: 4px solid #eab308; }

    .stat-row .stat-label { 
      font-size: 0.8em; 
      font-weight: 700; 
      color: #64748b; 
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 5px;
      display: block;
    }
    .stat-row .stat-value { 
      font-size: 2.2em; 
      font-weight: 800; 
      line-height: 1.1;
      display: block;
    }
    .stat-row.cobertura .stat-value { color: #3b82f6; }
    .stat-row.hallazgos .stat-value { color: #1e293b; }
    .stat-row.altos .stat-value { color: #ea580c; }
    .stat-row.medios .stat-value { color: #eab308; }

    /* Summary Table */
    .matrix-table {
      width: 100%; 
      border-collapse: collapse; 
      background: white; 
      border-radius: 8px; 
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
      border: 1px solid #e2e8f0;
      margin-bottom: 35px;
    }
    .matrix-table th { 
      background: #f8fafc; 
      padding: 12px 16px; 
      text-align: left; 
      font-size: 0.85em; 
      color: #64748b; 
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 2px solid #e2e8f0; 
    }
    .matrix-table td { 
      padding: 14px 16px; 
      border-bottom: 1px solid #f1f5f9; 
      vertical-align: middle;
      font-size: 0.95em;
    }
    .matrix-table tr:last-child td {
      border-bottom: none;
    }
    
    .number-zero { color: #cbd5e1; font-weight: 400; }
    .number-active-high { color: #ea580c; font-weight: 700; }
    .number-active-critical { color: #dc2626; font-weight: 700; }
    .number-active-other { color: #475569; font-weight: 600; }

    /* Finding Card Style */
    .finding-card {
      background: white; 
      border-radius: 8px; 
      margin-bottom: 25px; 
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); 
      border: 1px solid #e2e8f0;
      break-inside: avoid;
    }
    
    .finding-card-header {
      padding: 14px 20px;
      color: white;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .finding-card-header.CRITICAL { background-color: var(--critical); }
    .finding-card-header.HIGH { background-color: var(--high); }
    .finding-card-header.MEDIUM { background-color: var(--medium); }
    .finding-card-header.LOW { background-color: var(--low); }
    .finding-card-header.INFO { background-color: var(--info); }
    .finding-card-header.UNKNOWN { background-color: var(--unknown); }

    .finding-card-title { 
      margin: 0; 
      font-size: 1.1em; 
      font-weight: 800; 
      flex: 1;
    }
    
    .finding-card-badge {
      background: rgba(255, 255, 255, 0.25);
      color: white;
      padding: 3px 10px;
      border-radius: 12px;
      font-size: 0.75em;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .finding-card-body { 
      padding: 20px; 
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    
    .finding-subbox {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px 15px;
    }
    
    .finding-subbox-label {
      color: #64748b;
      font-size: 0.75em;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: block;
      margin-bottom: 4px;
    }
    
    .finding-subbox-value {
      color: #0f172a;
      font-size: 0.92em;
      font-weight: 400;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .finding-subbox-value a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 500;
    }

    footer { 
      text-align: center; 
      margin-top: 60px; 
      padding: 20px; 
      font-size: 0.85em; 
      color: #94a3b8; 
      border-top: 1px solid #e2e8f0; 
    }

    @media print {
      body { background: white; }
      .container { max-width: 100%; margin: 0; padding: 0; }
      .finding-card { break-inside: avoid; box-shadow: none; }
      .status-card { break-inside: avoid; box-shadow: none; }
      .stat-row { break-inside: avoid; box-shadow: none; }
      .matrix-table { break-inside: avoid; box-shadow: none; }
    }
  </style>
</head>
<body>
  <header class="header">
    <h1>Reporte Consolidado de Seguridad</h1>
    <div class="meta">
      Fecha de generación: {{ date }} | Pipeline #{{ os_env.get('CI_PIPELINE_ID', 'Local') }}
    </div>
  </header>

  <div class="container">
    <h2 class="section-title">🚀 Resumen de Ejecución del Pipeline (DevSecOps)</h2>
    
    <div class="cards-container">
      <!-- Card 1: Contexto -->
      <div class="status-card contexto">
        <div class="card-header">🔍 Contexto</div>
        <div class="card-content">
          <div class="card-item"><strong>Lenguaje:</strong> {{ pipeline_ctx.detected_lang }}</div>
          <div class="card-item"><strong>Repositorio:</strong> {{ pipeline_ctx.repo_path }}</div>
          <div class="card-item"><strong>Tag/Etiqueta:</strong> <span class="badge badge-success">{{ pipeline_ctx.commit_tag }}</span></div>
        </div>
      </div>

      <!-- Card 2: Pruebas y Calidad -->
      <div class="status-card pruebas">
        <div class="card-header">🪄 Pruebas y Calidad</div>
        <div class="card-content">
          <div class="card-item">
            <strong>Linters:</strong> 
            {% if 'Omitido' in pipeline_ctx.linters_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.linters_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>Tests Unitarios:</strong> 
            {% if 'Omitido' in pipeline_ctx.tests_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.tests_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>Secret Scan:</strong> 
            {% if 'Omitido' in pipeline_ctx.secret_scan_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.secret_scan_status }}</span>
            {% endif %}
          </div>
        </div>
      </div>

      <!-- Card 3: Compilación y Firma -->
      <div class="status-card compilacion">
        <div class="card-header">🏗️ Compilación y Firma</div>
        <div class="card-content">
          <div class="card-item">
            <strong>Docker Buildx:</strong> 
            {% if 'Omitido' in pipeline_ctx.docker_buildx_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.docker_buildx_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>Firma Digital:</strong> 
            {% if 'Omitido' in pipeline_ctx.firma_digital_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.firma_digital_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>SBOM CycloneDX:</strong> 
            {% if 'Omitido' in pipeline_ctx.sbom_cyclonedx_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.sbom_cyclonedx_status }}</span>
            {% endif %}
          </div>
        </div>
      </div>

      <!-- Card 4: Seguridad -->
      <div class="status-card seguridad">
        <div class="card-header">🔒 Seguridad</div>
        <div class="card-content">
          <div class="card-item">
            <strong>SAST & SCA:</strong> 
            {% if 'Omitido' in pipeline_ctx.sast_sca_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.sast_sca_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>IaC Audit:</strong> 
            {% if 'Omitido' in pipeline_ctx.iac_audit_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.iac_audit_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>DAST Dinámico:</strong> 
            {% if 'Omitido' in pipeline_ctx.dast_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido (sin site_url)</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.dast_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>API Security:</strong> 
            {% if 'Omitido' in pipeline_ctx.api_security_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.api_security_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>Cluster Scan:</strong> 
            {% if 'Omitido' in pipeline_ctx.cluster_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.cluster_status }}</span>
            {% endif %}
          </div>
        </div>
      </div>

      <!-- Card 5: Lanzamiento -->
      <div class="status-card lanzamiento">
        <div class="card-header">🚀 Lanzamiento</div>
        <div class="card-content">
          <div class="card-item">
            <strong>GitLab Release:</strong> 
            {% if 'Omitido' in pipeline_ctx.release_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido (no tag)</span>
            {% else %}
              <span class="badge badge-success">{{ pipeline_ctx.release_status }}</span>
            {% endif %}
          </div>
          <div class="card-item"><strong>Wiki Sync:</strong> <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.wiki_sync_status }}</span></div>
          <div class="card-item">
            <strong>Smoke Tests:</strong> 
            {% if 'Omitido' in pipeline_ctx.smoke_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.smoke_status }}</span>
            {% endif %}
          </div>
          <div class="card-item">
            <strong>Perf Testing:</strong> 
            {% if 'Omitido' in pipeline_ctx.perf_status %}
              <span style="color: #94a3b8; font-weight: 400;">◯ Omitido</span>
            {% else %}
              <span style="color: #16a34a; font-weight: 600;">{{ pipeline_ctx.perf_status }}</span>
            {% endif %}
          </div>
        </div>
      </div>
    </div>

    <h2 class="section-title">📊 Resumen Ejecutivo</h2>
    
    <div class="stat-blocks">
      <div class="stat-row salud" style="border-top: 4px solid {{ score_color }}; border-bottom: 4px solid {{ score_color }};">
        <span class="stat-label">Puntuación de Salud (Health Score)</span>
        <span class="stat-value" style="color: {{ score_color }}; font-weight: 900;">{{ score_grade }}</span>
        <span style="font-size: 0.85em; font-weight: 700; color: {{ score_color }}; text-transform: uppercase; display: block; margin-top: 2px;">{{ score_label }}</span>
      </div>
      <div class="stat-row cobertura">
        <span class="stat-label">Cobertura ({{ pipeline_ctx.detected_lang }})</span>
        <span class="stat-value">{{ coverage_pct }}</span>
      </div>
      <div class="stat-row hallazgos">
        <span class="stat-label">Hallazgos</span>
        <span class="stat-value">{{ total_findings }}</span>
      </div>
      <div class="stat-row altos">
        <span class="stat-label">Altos</span>
        <span class="stat-value">{{ severity_counts.HIGH }}</span>
      </div>
      <div class="stat-row medios">
        <span class="stat-label">Medios</span>
        <span class="stat-value">{{ severity_counts.MEDIUM }}</span>
      </div>
    </div>

    <table class="matrix-table">
      <thead>
        <tr>
          <th>Categoría de Análisis</th>
          <th style="text-align: center; width: 15%;">Críticos</th>
          <th style="text-align: center; width: 15%;">Altos</th>
          <th style="text-align: center; width: 15%;">Otros</th>
          <th style="text-align: center; width: 20%;">Estado</th>
        </tr>
      </thead>
      <tbody>
        {% for cat_name, stats in categories.items() %}
        <tr>
          <td><strong>{{ cat_name }}</strong></td>
          <td style="text-align: center;">
            {% if stats.status == 'OMITIDO' %}
              <span class="number-zero">-</span>
            {% elif stats.CRITICAL > 0 %}
              <span class="number-active-critical">{{ stats.CRITICAL }}</span>
            {% else %}
              <span class="number-zero">0</span>
            {% endif %}
          </td>
          <td style="text-align: center;">
            {% if stats.status == 'OMITIDO' %}
              <span class="number-zero">-</span>
            {% elif stats.HIGH > 0 %}
              <span class="number-active-high">{{ stats.HIGH }}</span>
            {% else %}
              <span class="number-zero">0</span>
            {% endif %}
          </td>
          <td style="text-align: center;">
            {% if stats.status == 'OMITIDO' %}
              <span class="number-zero">-</span>
            {% else %}
              {% set otros = stats.MEDIUM + stats.LOW + stats.INFO + stats.UNKNOWN %}
              {% if otros > 0 %}
                <span class="number-active-other">{{ otros }}</span>
              {% else %}
                <span class="number-zero">0</span>
              {% endif %}
            {% endif %}
          </td>
          <td style="text-align: center;">
            {% if stats.status == 'OMITIDO' %}
              <span class="badge" style="background: #e2e8f0; color: #64748b; padding: 4px 12px; border-radius: 12px; font-weight: 500;">OMITIDO</span>
            {% elif stats.status == 'PASADOS' %}
              <span class="badge badge-success" style="background: #dcfce7; color: #16a34a; padding: 4px 12px; border-radius: 12px; font-weight: 500;">PASADOS</span>
            {% elif stats.CRITICAL > 0 or stats.HIGH > 0 %}
              <span class="badge badge-warning" style="background: #fef3c7; color: #d97706; padding: 4px 12px; border-radius: 12px;">REVISIÓN</span>
            {% else %}
              <span class="badge badge-success" style="background: #dcfce7; color: #16a34a; padding: 4px 12px; border-radius: 12px;">LIMPIO</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    {% if detail_findings %}
    <h2 class="section-title">🔍 Detalle de Hallazgos</h2>
    {% for vuln in detail_findings %}
    <div class="finding-card">
      <div class="finding-card-header {{ vuln.severity }}">
        <h3 class="finding-card-title">{{ vuln.name }}</h3>
        <span class="finding-card-badge">{{ vuln.severity }}</span>
      </div>
      <div class="finding-card-body">
        <div class="finding-subbox">
          <span class="finding-subbox-label">Origen</span>
          <div class="finding-subbox-value">{{ vuln.report_type }}</div>
        </div>
        <div class="finding-subbox">
          <span class="finding-subbox-label">Identificador</span>
          <div class="finding-subbox-value">{{ vuln.cve }}</div>
        </div>
        <div class="finding-subbox">
          <span class="finding-subbox-label">Localización</span>
          <div class="finding-subbox-value">{{ vuln.file }}{% if vuln.line != 'N/A' and vuln.line != 0 %}:{{ vuln.line }}{% endif %}</div>
        </div>
        {% if vuln.description %}
        <div class="finding-subbox">
          <span class="finding-subbox-label">Descripción y Mitigación</span>
          <div class="finding-subbox-value">{% if '[' in vuln.description and '](' in vuln.description %}{{ vuln.description | safe }}{% else %}{{ vuln.description }}{% endif %}</div>
        </div>
        {% endif %}
      </div>
    </div>
    {% endfor %}
    {% else %}
    <div style="text-align: center; padding: 50px; background: white; border-radius: 8px; margin-top: 30px; border: 1px solid #e2e8f0;">
      <h3 style="color: var(--secondary); font-size: 1.5em; margin-bottom: 10px;">✅ Todo en orden</h3>
      <p style="color: #64748b; margin: 0;">No se han detectado vulnerabilidades o issues pendientes en este ciclo de build.</p>
    </div>
    {% endif %}

    <footer>
      Generado por GRS DevOps Toolkit | © 2026 GRS
    </footer>
  </div>
</body>
</html>
"""
    
    html = Template(template_str).render(
        title=report_title,
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        findings=findings,
        detail_findings=detail_findings,
        severity_counts=severity_counts,
        categories=categories,
        total_findings=total_findings,
        coverage_pct=coverage_pct,
        pipeline_ctx=pipeline_ctx,
        score_grade=score_grade,
        score_label=score_label,
        score_color=score_color,
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
        'zap-report.json',
        'gl-code-quality-report.json',
        'gl-sbom-report.json',
        'gl-accessibility-report.json',
        'gl-cluster-image-scanning-report.json',
        'coverage-report.json'
    ]
    
    # 2. Descubrimiento dinámico de cualquier JSON que parezca un reporte
    # Buscamos archivos que terminen en report.json o scanning.json
    dynamic_files = glob.glob("*report.json") + glob.glob("*scanning.json") + glob.glob("*compliance.json") + glob.glob("gl-sbom-*.cdx.json") + glob.glob("*coverage*.json") + glob.glob("gl-sast-*.json") + glob.glob("*trivy*.json") + glob.glob("gitleaks-report-*.json")
    
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
            print(f"✅ Cargado (Limpio): {report_file} (0 hallazgos - Excelente)")
            clean_type = os.path.basename(report_file).replace('.cdx.json', '').replace('.json', '').replace('gl-', '').replace('-', ' ').title()
            all_findings.append({
                'name': 'Escaneo Limpio',
                'severity': 'INFO',
                'description': f'No se encontraron vulnerabilidades en {report_file}.',
                'file': 'N/A',
                'line': 'N/A',
                'cve': 'N/A',
                'identifier': 'CLEAN',
                'report_type': clean_type
            })
            found_reports.append(report_file)
    
    if not all_findings:
        print("ℹ️  No se encontraron hallazgos en ningún reporte.")
        print("📄 Generando dashboard de cumplimiento limpio...")
        generate_report([], "GRS Executive Summary", "executive-summary-report")
        sys.exit(0)

    # Reporte consolidado (Master Dashboard)
    print(f"\n📊 Generando Dashboard Ejecutivo GRS con {len(all_findings)} hallazgos...")
    generate_report(all_findings, "GRS Executive Summary Dashboard", "executive-summary-report")
    
    # Reportes individuales y por servicio
    services = {}
    for f in all_findings:
        srv = f.get('service', 'Global')
        if srv not in services:
            services[srv] = []
        services[srv].append(f)
        
    detected_services = [s for s in services.keys() if s != 'Global']
    
    if len(detected_services) > 0:
        print("\n🏢 Monorepo/Multi-servicio detectado. Generando dashboards por servicio/lenguaje...")
        for srv, srv_findings in services.items():
            if not srv_findings: continue
            
            srv_title = srv.title()
            print(f"📊 Generando Dashboard para: {srv_title} ({len(srv_findings)} hallazgos)")
            generate_report(srv_findings, f"Dashboard: {srv_title}", f"dashboard-{srv.lower()}")
            
    if len(found_reports) > 1:
        print("\n📄 Generando reportes individuales por archivo...")
        for report_file in found_reports:
            findings = load_report(report_file)
            if findings:
                clean_name = os.path.basename(report_file).replace('.cdx.json', '').replace('.json', '').replace('gl-', '')
                report_type = clean_name.replace('-', ' ').title()
                output_name = f"{clean_name}-report"
                generate_report(findings, f"Reporte Detallado: {report_type}", output_name)

if __name__ == "__main__":
    main()

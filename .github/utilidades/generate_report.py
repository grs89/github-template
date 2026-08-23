#!/usr/bin/env python3
"""
Script para generar reportes HTML/PDF a partir de reportes JSON de seguridad.
Soporta múltiples formatos:
- SAST (gl-sast-report.json)
- Dependency Scanning (gl-dependency-scanning-report.json)
- Secret Detection (gl-secret-detection-report.json)
- Trivy Container Scanning (trivy-report.json)
- Checkov IaC Scanning (checkov-report.json)
- SBOM CycloneDX (gl-sbom-*.cdx.json)
- SLSA Provenance (*-slsa-provenance-report.json)
- Cosign Image Signing (*-signing-report.json)
- Code Coverage (coverage-report.json)
- Code Quality (gl-code-quality-report.json)
- ZAP DAST (zap-report.json)
"""

import json
import sys
import os
import glob
from jinja2 import Template
from weasyprint import HTML
from datetime import datetime

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
    
    sites = data.get('site', [])
    for site in sites:
        target_site = site.get('@name', 'N/A')
        alerts = site.get('alerts', [])
        
        for alert in alerts:
            risk_desc = alert.get('riskdesc', 'UNKNOWN').upper()
            severity = 'UNKNOWN'
            if 'HIGH' in risk_desc: severity = 'HIGH'
            elif 'MEDIUM' in risk_desc: severity = 'MEDIUM'
            elif 'LOW' in risk_desc: severity = 'LOW'
            elif 'INFORMATIONAL' in risk_desc: severity = 'INFO'

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

def normalize_llm_report(data):
    """Normaliza reportes de PromptFoo (OWASP LLM Top 10 - red-team dinámico)"""
    findings = []

    # PromptFoo v1 output: {"results": [{"prompt": ..., "pass": bool, "score": float, "testCase": {...}}]}
    results = data.get('results', [])
    for result in results:
        # Solo reportar los tests que fallaron
        passed = result.get('pass', result.get('success', True))
        if passed:
            continue

        test_case = result.get('testCase', result.get('test', {}))
        test_vars = test_case.get('vars', {})
        owasp_cat = test_vars.get('owasp_llm', 'LLM Risk')
        description_text = test_case.get('description', '')
        score = result.get('score', None)

        # Calcular severidad según score
        if score is None:
            severity = 'HIGH'
        elif score < 0.3:
            severity = 'CRITICAL'
        elif score < 0.6:
            severity = 'HIGH'
        else:
            severity = 'MEDIUM'

        response_preview = ''
        raw_output = result.get('response', result.get('output', ''))
        if isinstance(raw_output, str):
            response_preview = raw_output[:300]
        elif isinstance(raw_output, dict):
            response_preview = str(raw_output.get('output', raw_output))[:300]

        score_str = f"{score:.2f}" if isinstance(score, float) else str(score)

        finding = {
            'name': description_text or f"{owasp_cat}: Test fallido",
            'severity': severity,
            'description': (
                f"[{owasp_cat}] Score de seguridad: {score_str}\n"
                f"Respuesta del modelo: {response_preview}..."
                if response_preview else f"[{owasp_cat}] Score: {score_str}"
            ),
            'file': 'LLM Endpoint',
            'line': 'N/A',
            'cve': owasp_cat.split(' - ')[0] if ' - ' in owasp_cat else owasp_cat,
            'identifier': owasp_cat,
            'report_type': 'LLM Security (PromptFoo)'
        }
        findings.append(finding)

    return findings


def normalize_llm_dependency_report(data):
    """Normaliza reportes de auditoría de dependencias LLM (pip-audit/npm audit filtrado)"""
    findings = []

    # Vulnerabilidades Python (pip-audit filtrado)
    for vuln in data.get('llm_vulnerabilities', []):
        finding = {
            'name': vuln.get('vuln_id', vuln.get('package', 'LLM Dependency Vuln')),
            'severity': 'HIGH',
            'description': (
                f"Paquete LLM: {vuln.get('package', 'N/A')} v{vuln.get('version', 'N/A')} | "
                f"{vuln.get('description', '')} | "
                f"Fix: {', '.join(vuln.get('fix_versions', [])) or 'Sin fix disponible'}"
            ),
            'file': 'requirements.txt / pyproject.toml',
            'line': 'N/A',
            'cve': vuln.get('vuln_id', 'N/A'),
            'identifier': vuln.get('package', 'N/A'),
            'report_type': 'LLM Security (Dependencias)'
        }
        findings.append(finding)

    # Vulnerabilidades Node.js (npm audit filtrado)
    for name, vuln in data.get('npm_llm_vulnerabilities', {}).items() if isinstance(data.get('npm_llm_vulnerabilities'), dict) else [(v.get('name', ''), v) for v in data.get('npm_llm_vulnerabilities', [])]:
        severity_map = {'critical': 'CRITICAL', 'high': 'HIGH', 'moderate': 'MEDIUM', 'low': 'LOW'}
        finding = {
            'name': vuln.get('name', name) or name,
            'severity': severity_map.get(vuln.get('severity', 'high'), 'HIGH'),
            'description': vuln.get('via', [{}])[0].get('title', str(vuln.get('via', '')))[:300] if vuln.get('via') else 'LLM npm dependency vulnerability',
            'file': 'package.json',
            'line': 'N/A',
            'cve': str(vuln.get('via', [{}])[0].get('url', 'N/A'))[:100] if vuln.get('via') else 'N/A',
            'identifier': vuln.get('name', name) or name,
            'report_type': 'LLM Security (Dependencias)'
        }
        findings.append(finding)

    # Si no hay vulnerabilidades, reportar estado limpio
    if not findings and data.get('total_llm_vulns', -1) == 0:
        findings.append({
            'name': 'Dependencias LLM sin vulnerabilidades conocidas',
            'severity': 'INFO',
            'description': data.get('message', 'Auditoría de dependencias LLM completada sin hallazgos.'),
            'file': 'N/A',
            'line': 'N/A',
            'cve': 'N/A',
            'identifier': 'CLEAN',
            'report_type': 'LLM Security (Dependencias)'
        })

    return findings


def normalize_code_quality_report(data):
    """Normaliza reportes de Code Quality (CodeClimate)"""
    findings = []
    
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
    
    service_name = "Global"
    if 'sbom-' in filename:
        try:
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
    
    coverage_pct = data.get('coverage', 0)
    if not coverage_pct and 'totals' in data:
        coverage_pct = data.get('totals', {}).get('percent_covered', 0)
    
    try:
        if isinstance(coverage_pct, str):
            coverage_pct = coverage_pct.replace('%', '').strip()
        coverage_pct = float(coverage_pct)
    except (ValueError, TypeError):
        coverage_pct = 0.0

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
    
    files = data.get('files', {})
    if isinstance(files, dict):
        for file_path, file_data in list(files.items())[:20]:
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
    releases = data.get('releases', [])
    if not releases:
        return []
    
    latest = releases[0]
    version = latest.get('version', 'Sin release')
    commits = latest.get('commits', [])
    
    summary = []
    for commit in commits[:10]:
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
    issues = data if isinstance(data, list) else data.get('results', [])
    
    for issue in issues:
        code = issue.get('code', 'N/A')
        severity = issue.get('type', 'error').upper()
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
    # LLM Security reports
    if 'llm-promptfoo' in filename:
        return lambda d: normalize_llm_report(d)
    if 'llm-dependency' in filename:
        return lambda d: normalize_llm_dependency_report(d)
    if 'gl-sast-llm' in filename:
        return lambda d: normalize_gl_report(d, 'LLM Security (SAST)')
    if 'code-quality' in filename:
        return lambda d: normalize_code_quality_report(d)
    if 'sbom' in filename or filename.endswith('.cdx.json'):
        return lambda d: normalize_sbom_report(d, filename)
    if 'accessibility' in filename:
        return lambda d: normalize_accessibility_report(d)
    
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
    
    if isinstance(data, dict):
        if 'check_type' in data or (isinstance(data, list) and len(data) > 0 and 'check_type' in data[0]):
            return lambda d: normalize_checkov_report(d)
        if 'vulnerabilities' in data:
            return lambda d: normalize_gl_report(d, 'Security Scan')
        if 'Results' in data:
            return lambda d: normalize_trivy_report(d)
    return None

def extract_service_name(filename):
    """Extrae el nombre del servicio o lenguaje a partir del nombre del archivo si existe (para monorepos)"""
    name = filename.replace('.cdx.json', '').replace('.json', '').lower()
    
    generic_reports = {
        'gl-sast-report', 'gl-dependency-scanning-report', 'gl-secret-detection-report',
        'gl-code-quality-report', 'trivy-report', 'trivy-iac-report', 'trivy-sast-report',
        'checkov-report', 'license-report', 'dependency-report', 'dependency_scanning',
        'cleanup-report', 'signing-report', 'zap-report', 'gl-sbom-report',
        'gl-accessibility-report', 'gl-cluster-image-scanning-report', 'coverage-report',
        'gitleaks-report-root', 'root-slsa-provenance-report', 'root-signing-report',
        'executive-summary-report', 'gl-api-security-report'
    }
    
    if name in generic_reports:
        return 'Global'
        
    patterns = [
        r'^gl-sbom-(.+)$',
        r'^gitleaks-report-(.+)$',
        r'^coverage-(.+)$',
        r'^(.+)-coverage-report$',
        r'^(.+)-slsa-provenance-report$',
        r'^(.+)-signing-report$',
        r'^gl-sast-(.+)$',
        r'^gl-dependency-scanning-(.+)$',
        r'^gl-secret-detection-(.+)$',
        r'^trivy-(.+)$'
    ]
    import re
    for pat in patterns:
        m = re.match(pat, name)
        if m:
            srv = m.group(1).strip()
            if srv and srv not in ('report', 'root', 'global', 'iac', 'sast', 'cdx'):
                return srv
                
    return 'Global'

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
        
        service_name = extract_service_name(filename)
        for f in findings:
            f['service'] = service_name if service_name else 'Global'
            if service_name and service_name != 'Global' and service_name.lower() not in f.get('report_type', '').lower():
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
    import subprocess

    service_lang = os.environ.get('SERVICE_LANG')
    if service_lang:
        detected_lang = service_lang.upper()
    else:
        detected_lang = os.environ.get('DETECTED_LANG', 'GO').upper()

    service_name = os.environ.get('SERVICE_NAME', '')
    service_path = os.environ.get('SERVICE_PATH', os.environ.get('BUILD_SERVICE_PATH', ''))

    repo_path = os.environ.get('GITHUB_REPOSITORY') or os.environ.get('CI_PROJECT_PATH')
    if not repo_path:
        try:
            git_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], text=True).strip()
            if 'gitlab.com' in git_url or 'github.com' in git_url:
                repo_path = git_url.split(':')[-1].replace('.git', '')
                if '/' not in repo_path:
                    repo_path = git_url.split('/')[-2] + '/' + git_url.split('/')[-1].replace('.git', '')
        except Exception:
            repo_path = 'company/project'
    if not repo_path:
        repo_path = 'company/project'

    commit_tag = os.environ.get('GITHUB_REF_NAME') or os.environ.get('CI_COMMIT_TAG') or os.environ.get('CI_COMMIT_REF_NAME')
    if not commit_tag:
        try:
            commit_tag = subprocess.check_output(['git', 'describe', '--tags', '--always'], text=True).strip()
        except Exception:
            pass
    if not commit_tag:
        commit_tag = 'N/D'

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

    has_docker = os.path.exists('02-Dockerfile/Dockerfile-report') or glob.glob('*Dockerfile*') or glob.glob('**/Dockerfile*', recursive=True) or glob.glob('**/*.dockerfile', recursive=True)
    docker_buildx_status = '✓ Compilado' if has_docker else '○ Omitido'
    
    has_signing = os.path.exists('signing-report.json') or glob.glob('*signing*.json')
    firma_digital_status = '✓ Cosign' if has_signing else '○ Omitido'

    has_sbom = os.path.exists('gl-sbom-report.json') or glob.glob('*.cdx.json') or glob.glob('*sbom*.json')
    sbom_cyclonedx_status = '✓ Firmado' if has_sbom else '○ Omitido'

    has_sast = os.path.exists('trivy-report.json') or os.path.exists('gl-sast-report.json') or glob.glob('*sast*.json')
    sast_sca_status = '✓ Trivy' if has_sast else '○ Omitido'

    has_checkov = os.path.exists('checkov-report.json') or glob.glob('*checkov*.json')
    iac_audit_status = '✓ Checkov' if has_checkov else '○ Omitido'

    has_dast = os.path.exists('zap-report.json') or glob.glob('*zap*.json')
    dast_status = '✓ ZAP Activo' if has_dast else '◯ Omitido (sin site_url)'

    has_api_sec = os.path.exists('gl-api-security-report.json') or glob.glob('*api-security*.json')
    api_security_status = '✓ Escaneado' if has_api_sec else '○ Omitido'

    # LLM Security detection
    has_llm_promptfoo = os.path.exists('llm-promptfoo-report.json') or glob.glob('llm-promptfoo*.json')
    has_llm_deps      = os.path.exists('llm-dependency-report.json') or glob.glob('llm-dependency*.json')
    has_llm_sast      = glob.glob('gl-sast-llm*.json')
    llm_promptfoo_status = '✓ PromptFoo OK' if has_llm_promptfoo else '◯ Omitido (sin LLM_ENDPOINT)'
    llm_deps_status      = '✓ Auditado'    if has_llm_deps      else '○ Omitido'
    llm_sast_status      = '✓ Semgrep OK'  if has_llm_sast      else '○ Omitido'

    # Compute LLM Top 10 coverage for the HTML section
    llm_coverage = [
        {'id': 'LLM01', 'name': 'Prompt Injection',              'tools': 'PromptFoo + Semgrep', 'active': has_llm_promptfoo or bool(has_llm_sast)},
        {'id': 'LLM02', 'name': 'Sensitive Info Disclosure',     'tools': 'Semgrep',             'active': bool(has_llm_sast)},
        {'id': 'LLM03', 'name': 'Supply Chain',                  'tools': 'pip-audit / npm audit','active': has_llm_deps},
        {'id': 'LLM04', 'name': 'Data & Model Poisoning',        'tools': '— (revisión manual)', 'active': False},
        {'id': 'LLM05', 'name': 'Improper Output Handling',      'tools': 'Semgrep',             'active': bool(has_llm_sast)},
        {'id': 'LLM06', 'name': 'Excessive Agency',              'tools': 'pip-audit (parcial)', 'active': has_llm_deps},
        {'id': 'LLM07', 'name': 'System Prompt Leakage',         'tools': 'PromptFoo + Semgrep', 'active': has_llm_promptfoo or bool(has_llm_sast)},
        {'id': 'LLM08', 'name': 'Vector & Embedding Weaknesses', 'tools': '— (fuera de scope)', 'active': False},
        {'id': 'LLM09', 'name': 'Misinformation',                'tools': 'PromptFoo',           'active': has_llm_promptfoo},
        {'id': 'LLM10', 'name': 'Unbounded Consumption',         'tools': 'Semgrep + k6',        'active': bool(has_llm_sast)},
    ]

    has_cluster = os.path.exists('gl-cluster-image-scanning-report.json') or glob.glob('*cluster*.json')
    cluster_status = '✓ Auditado' if has_cluster else '○ Omitido'

    has_container_scan = os.path.exists('gl-container-scanning-report.json') or glob.glob('*container-scanning*.json') or glob.glob('*container_scanning*.json')
    container_scan_status = '✓ Escaneado' if has_container_scan else '○ Omitido'

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
        'service_name': service_name,
        'service_path': service_path,
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
        'perf_status': perf_status,
        'llm_promptfoo_status': llm_promptfoo_status,
        'llm_deps_status': llm_deps_status,
        'llm_sast_status': llm_sast_status,
        'llm_coverage': llm_coverage
    }

def generate_report(findings, report_title="GRS Executive Summary Dashboard", output_prefix="executive-summary-report"):
    """Genera UN SOLO reporte consolidado HTML y PDF interactivo y práctico para leer"""
    
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4, 'UNKNOWN': 5}
    
    detail_findings = [f for f in findings if f.get('cve') not in ['CODE-COVERAGE', 'CHANGELOG-INFO', 'BADGES-STATUS', 'REGISTRY-CLEANUP', 'DEP-UPDATE', 'SBOM-COMPONENT']]
    detail_findings.sort(key=lambda x: (severity_order.get(x.get('severity', 'UNKNOWN'), 99), x.get('name', '')))
    
    severity_counts = {s: 0 for s in severity_order}
    for finding in detail_findings:
        sev = finding.get('severity', 'UNKNOWN')
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
    score_grade, score_label, score_color = calculate_health_score(severity_counts)

    coverage_pct = "N/D"
    for f in findings:
        if f.get('cve') == 'CODE-COVERAGE':
            coverage_pct = f.get('identifier', '0.00%')
            if not coverage_pct.endswith('%'):
                coverage_pct = f"{coverage_pct}%"
            break

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

    if 'Tests Unitarios' in categories:
        if 'Omitido' in pipeline_ctx.get('tests_status', 'Omitido'):
            categories['Tests Unitarios']['status'] = 'OMITIDO'
        elif categories['Tests Unitarios'].get('total', 0) == 0:
            categories['Tests Unitarios']['status'] = 'PASADOS'
            
    if 'IaC Audit' in categories and 'Omitido' in pipeline_ctx.get('iac_audit_status', 'Omitido'):
        categories['IaC Audit']['status'] = 'OMITIDO'
            
    if 'Container Scan (Trivy - Registro)' in categories and 'Omitido' in pipeline_ctx.get('container_scan_status', 'Omitido'):
        categories['Container Scan (Trivy - Registro)']['status'] = 'OMITIDO'
            
    if 'Container Scan (Trivy - Docker Hub)' in categories and 'Omitido' in pipeline_ctx.get('container_scan_status', 'Omitido'):
        categories['Container Scan (Trivy - Docker Hub)']['status'] = 'OMITIDO'
            
    if 'SAST (Trivy - Código)' in categories and 'Omitido' in pipeline_ctx.get('sast_sca_status', 'Omitido'):
        categories['SAST (Trivy - Código)']['status'] = 'OMITIDO'

    services_dict = {}
    for f in detail_findings:
        srv = f.get('service', 'Global')
        if srv not in services_dict:
            services_dict[srv] = {s: 0 for s in severity_order}
            services_dict[srv]['total'] = 0
        sev = f.get('severity', 'UNKNOWN')
        services_dict[srv][sev] = services_dict[srv].get(sev, 0) + 1
        services_dict[srv]['total'] += 1

    services_summary = []
    for srv, counts in services_dict.items():
        grade, label, color = calculate_health_score(counts)
        services_summary.append({
            'name': srv.title(),
            'slug': srv.lower(),
            'counts': counts,
            'total': counts['total'],
            'grade': grade,
            'label': label,
            'color': color
        })
    services_summary.sort(key=lambda x: x['name'])

    total_findings = sum(severity_counts.get(s, 0) for s in severity_counts)
    unique_services = sorted(list({f.get('service', 'Global') for f in detail_findings}))
    unique_categories = sorted(list({f.get('report_type', 'General') for f in detail_findings}))

    template_str = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    :root {
      --primary: #0f172a;
      --primary-accent: #2563eb;
      --secondary: #16a34a;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #1e293b;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --critical: #dc2626;
      --high: #ea580c;
      --medium: #eab308;
      --low: #16a34a;
      --info: #2563eb;
      --unknown: #64748b;
    }
    
    @page {
      size: A4;
      margin: 12mm;
      @bottom-right {
        content: "Pág " counter(page) " de " counter(pages);
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: #94a3b8;
      }
    }

    * { box-sizing: border-box; }

    body { 
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
      margin: 0; padding: 0;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      font-size: 14px;
    }

    .header {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #1e3a8a 100%);
      color: white;
      padding: 30px 40px;
      border-bottom: 4px solid var(--primary-accent);
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .header-content {
      max-width: 1100px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 15px;
    }

    .header h1 { 
      margin: 0; 
      font-size: 2em; 
      font-weight: 800;
      letter-spacing: -0.5px; 
    }
    
    .header .meta { 
      margin-top: 6px; 
      font-size: 0.9em; 
      color: #94a3b8; 
      font-weight: 400;
    }

    .header-badge {
      background: rgba(37, 99, 235, 0.2);
      border: 1px solid rgba(59, 130, 246, 0.4);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 0.85em;
      font-weight: 600;
      color: #93c5fd;
    }
    
    .container { max-width: 1100px; margin: 0 auto; padding: 25px 20px; }

    .section-title {
      font-size: 1.3em; 
      font-weight: 800;
      margin: 30px 0 15px; 
      color: #0f172a; 
      padding-bottom: 8px;
      border-bottom: 2px solid #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .pipeline-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
      margin-bottom: 25px;
    }

    .status-card {
      background: var(--card-bg);
      border-radius: 8px;
      border: 1px solid var(--border);
      padding: 14px 16px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .status-card.contexto { border-top: 3px solid #3b82f6; }
    .status-card.pruebas { border-top: 3px solid #10b981; }
    .status-card.compilacion { border-top: 3px solid #f97316; }
    .status-card.seguridad { border-top: 3px solid #6366f1; }
    .status-card.lanzamiento { border-top: 3px solid #8b5cf6; }

    .card-header {
      font-weight: 700;
      font-size: 0.85em;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 10px;
      color: var(--text-muted);
    }

    .card-item {
      font-size: 0.9em;
      margin-bottom: 6px;
      color: #334155;
    }
    .card-item:last-child { margin-bottom: 0; }
    .card-item strong { color: #0f172a; font-weight: 600; }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 15px;
      margin-bottom: 25px;
    }

    .kpi-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      text-align: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .kpi-card .kpi-label { 
      font-size: 0.75em; 
      font-weight: 700; 
      color: var(--text-muted); 
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
      display: block;
    }
    .kpi-card .kpi-value { 
      font-size: 2em; 
      font-weight: 800; 
      line-height: 1.1;
      display: block;
    }

    .data-table {
      width: 100%; 
      border-collapse: collapse; 
      background: white; 
      border-radius: 8px; 
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
      border: 1px solid var(--border);
      margin-bottom: 25px;
    }
    .data-table th { 
      background: #f8fafc; 
      padding: 10px 14px; 
      text-align: left; 
      font-size: 0.8em; 
      color: var(--text-muted); 
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 2px solid var(--border); 
    }
    .data-table td { 
      padding: 12px 14px; 
      border-bottom: 1px solid #f1f5f9; 
      vertical-align: middle;
      font-size: 0.92em;
    }
    .data-table tr:last-child td { border-bottom: none; }
    
    .number-zero { color: #cbd5e1; font-weight: 400; }
    .number-active-high { color: #ea580c; font-weight: 700; }
    .number-active-critical { color: #dc2626; font-weight: 700; }
    .number-active-other { color: #475569; font-weight: 600; }

    .interactive-toolbar {
      background: white;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 15px 18px;
      margin-bottom: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    .search-row {
      display: flex;
      gap: 10px;
      align-items: center;
    }

    .search-input {
      flex: 1;
      padding: 9px 14px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 0.9em;
      outline: none;
      font-family: inherit;
    }
    .search-input:focus { border-color: var(--primary-accent); box-shadow: 0 0 0 2px rgba(37,99,235,0.1); }

    .filter-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .filter-label {
      font-size: 0.8em;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      margin-right: 4px;
    }

    .filter-btn {
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      color: #475569;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.8em;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .filter-btn:hover { background: #e2e8f0; color: #0f172a; }
    .filter-btn.active {
      background: #0f172a;
      color: white;
      border-color: #0f172a;
    }

    .badge { 
      padding: 3px 8px; 
      border-radius: 12px; 
      font-size: 0.75em; 
      font-weight: 700; 
      text-transform: uppercase;
      display: inline-block;
    }
    .badge-success { background: #dcfce7; color: #16a34a; }
    .badge-warning { background: #fef3c7; color: #d97706; }
    .badge-danger { background: #fee2e2; color: #dc2626; }
    .badge-info { background: #dbeafe; color: #2563eb; }

    .finding-card {
      background: white; 
      border-radius: 8px; 
      margin-bottom: 15px; 
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02); 
      border: 1px solid var(--border);
      break-inside: avoid;
    }
    
    .finding-card-header {
      padding: 12px 18px;
      color: white;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    }
    
    .finding-card-header.CRITICAL { background-color: var(--critical); }
    .finding-card-header.HIGH { background-color: var(--high); }
    .finding-card-header.MEDIUM { background-color: var(--medium); }
    .finding-card-header.LOW { background-color: var(--low); }
    .finding-card-header.INFO { background-color: var(--info); }
    .finding-card-header.UNKNOWN { background-color: var(--unknown); }

    .finding-card-title { 
      margin: 0; 
      font-size: 1em; 
      font-weight: 700; 
      flex: 1;
    }
    
    .finding-card-body { 
      padding: 15px 18px; 
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    
    .finding-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
    }

    .finding-subbox {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 8px 12px;
    }
    
    .finding-subbox-label {
      color: var(--text-muted);
      font-size: 0.7em;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: block;
      margin-bottom: 2px;
    }
    
    .finding-subbox-value {
      color: #0f172a;
      font-size: 0.88em;
      word-break: break-word;
    }

    footer { 
      text-align: center; 
      margin-top: 40px; 
      padding: 20px; 
      font-size: 0.85em; 
      color: var(--text-muted); 
      border-top: 1px solid var(--border); 
    }

    @media print {
      body { background: white; font-size: 12px; }
      .header { padding: 15px 20px; background: #0f172a !important; color: white !important; }
      .container { max-width: 100%; margin: 0; padding: 10px 0; }
      .interactive-toolbar { display: none !important; }
      .finding-card { break-inside: avoid; box-shadow: none; margin-bottom: 10px; }
      .status-card { break-inside: avoid; box-shadow: none; }
      .kpi-card { break-inside: avoid; box-shadow: none; }
      .data-table { break-inside: avoid; box-shadow: none; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <div>
        <h1>Reporte Consolidado DevSecOps</h1>
        <div class="meta">
          Fecha: {{ date }} | Repositorio: <strong>{{ pipeline_ctx.repo_path }}</strong> | Tag: <strong>{{ pipeline_ctx.commit_tag }}</strong>
        </div>
      </div>
      <div class="header-badge">
        Pipeline #{{ os_env.get('CI_PIPELINE_ID', 'Local') }}
      </div>
    </div>
  </header>

  <div class="container">
    <!-- 1. Resumen de Ejecución -->
    <h2 class="section-title">🚀 Estado de Flujo DevSecOps</h2>
    <div class="pipeline-grid">
      <div class="status-card contexto">
        <div class="card-header">🔍 Contexto</div>
        {% if pipeline_ctx.service_name and pipeline_ctx.service_name not in ['.', 'root', 'Global', ''] %}
        <div class="card-item"><strong>Microservicio:</strong> {{ pipeline_ctx.service_name }}</div>
        {% endif %}
        <div class="card-item"><strong>Lenguaje:</strong> {{ pipeline_ctx.detected_lang }}</div>
        <div class="card-item"><strong>Rama/Tag:</strong> {{ pipeline_ctx.commit_tag }}</div>
      </div>

      <div class="status-card pruebas">
        <div class="card-header">🪄 Calidad & Tests</div>
        <div class="card-item"><strong>Linters:</strong> {{ pipeline_ctx.linters_status }}</div>
        <div class="card-item"><strong>Tests Unitarios:</strong> {{ pipeline_ctx.tests_status }}</div>
        <div class="card-item"><strong>Secret Scan:</strong> {{ pipeline_ctx.secret_scan_status }}</div>
      </div>

      <div class="status-card compilacion">
        <div class="card-header">🏗️ Build & Supply Chain</div>
        <div class="card-item"><strong>Docker:</strong> {{ pipeline_ctx.docker_buildx_status }}</div>
        <div class="card-item"><strong>Firma Cosign:</strong> {{ pipeline_ctx.firma_digital_status }}</div>
        <div class="card-item"><strong>SBOM CycloneDX:</strong> {{ pipeline_ctx.sbom_cyclonedx_status }}</div>
      </div>

      <div class="status-card seguridad">
        <div class="card-header">🔒 Seguridad</div>
        <div class="card-item"><strong>SAST / SCA:</strong> {{ pipeline_ctx.sast_sca_status }}</div>
        <div class="card-item"><strong>IaC Audit:</strong> {{ pipeline_ctx.iac_audit_status }}</div>
        <div class="card-item"><strong>DAST / API:</strong> {{ pipeline_ctx.dast_status }}</div>
      </div>

      <div class="status-card" style="border-left: 3px solid #7c3aed;">
        <div class="card-header" style="color: #7c3aed;">🤖 LLM Security</div>
        <div class="card-item"><strong>Red-Team (PromptFoo):</strong> {{ pipeline_ctx.llm_promptfoo_status }}</div>
        <div class="card-item"><strong>Deps LLM:</strong> {{ pipeline_ctx.llm_deps_status }}</div>
        <div class="card-item"><strong>SAST LLM:</strong> {{ pipeline_ctx.llm_sast_status }}</div>
      </div>

      <div class="status-card lanzamiento">
        <div class="card-header">🚀 Entrega</div>
        <div class="card-item"><strong>Release:</strong> {{ pipeline_ctx.release_status }}</div>
        <div class="card-item"><strong>Smoke Tests:</strong> {{ pipeline_ctx.smoke_status }}</div>
        <div class="card-item"><strong>Perf Tests:</strong> {{ pipeline_ctx.perf_status }}</div>
      </div>
    </div>

    <!-- 2. KPIs y Health Score -->
    <h2 class="section-title">📊 Resumen Ejecutivo</h2>
    <div class="kpi-grid">
      <div class="kpi-card" style="border-top: 3px solid {{ score_color }};">
        <span class="kpi-label">Health Score</span>
        <span class="kpi-value" style="color: {{ score_color }};">{{ score_grade }}</span>
        <span style="font-size: 0.75em; font-weight: 700; color: {{ score_color }}; text-transform: uppercase;">{{ score_label }}</span>
      </div>
      <div class="kpi-card" style="border-top: 3px solid #3b82f6;">
        <span class="kpi-label">Cobertura</span>
        <span class="kpi-value" style="color: #3b82f6;">{{ coverage_pct }}</span>
      </div>
      <div class="kpi-card" style="border-top: 3px solid #0f172a;">
        <span class="kpi-label">Total Hallazgos</span>
        <span class="kpi-value">{{ total_findings }}</span>
      </div>
      <div class="kpi-card" style="border-top: 3px solid var(--critical);">
        <span class="kpi-label">Críticos</span>
        <span class="kpi-value" style="color: var(--critical);">{{ severity_counts.CRITICAL }}</span>
      </div>
      <div class="kpi-card" style="border-top: 3px solid var(--high);">
        <span class="kpi-label">Altos</span>
        <span class="kpi-value" style="color: var(--high);">{{ severity_counts.HIGH }}</span>
      </div>
      <div class="kpi-card" style="border-top: 3px solid var(--medium);">
        <span class="kpi-label">Medios</span>
        <span class="kpi-value" style="color: var(--medium);">{{ severity_counts.MEDIUM }}</span>
      </div>
    </div>

    {% if services_summary|length > 1 %}
    <!-- 3. Desglose por Servicio (Monorepo) -->
    <h2 class="section-title">🏢 Desglose por Servicio / Componente</h2>
    <table class="data-table">
      <thead>
        <tr>
          <th>Servicio / Módulo</th>
          <th style="text-align: center; width: 12%;">Salud</th>
          <th style="text-align: center; width: 12%;">Críticos</th>
          <th style="text-align: center; width: 12%;">Altos</th>
          <th style="text-align: center; width: 12%;">Medios</th>
          <th style="text-align: center; width: 12%;">Total</th>
        </tr>
      </thead>
      <tbody>
        {% for srv in services_summary %}
        <tr>
          <td><strong>{{ srv.name }}</strong></td>
          <td style="text-align: center;">
            <span class="badge" style="background: {{ srv.color }}20; color: {{ srv.color }};">{{ srv.grade }} ({{ srv.label }})</span>
          </td>
          <td style="text-align: center;">
            {% if srv.counts.CRITICAL > 0 %}<span class="number-active-critical">{{ srv.counts.CRITICAL }}</span>{% else %}<span class="number-zero">0</span>{% endif %}
          </td>
          <td style="text-align: center;">
            {% if srv.counts.HIGH > 0 %}<span class="number-active-high">{{ srv.counts.HIGH }}</span>{% else %}<span class="number-zero">0</span>{% endif %}
          </td>
          <td style="text-align: center;">
            {% if srv.counts.MEDIUM > 0 %}<span class="number-active-other">{{ srv.counts.MEDIUM }}</span>{% else %}<span class="number-zero">0</span>{% endif %}
          </td>
          <td style="text-align: center;"><strong>{{ srv.total }}</strong></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% endif %}

    <!-- 4. Matriz por Categoría -->
    <h2 class="section-title">🛡️ Estado por Categoría de Seguridad</h2>
    <table class="data-table">
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
              <span class="badge" style="background: #e2e8f0; color: #64748b;">OMITIDO</span>
            {% elif stats.status == 'PASADOS' %}
              <span class="badge badge-success">PASADOS</span>
            {% elif stats.CRITICAL > 0 or stats.HIGH > 0 %}
              <span class="badge badge-warning">REVISIÓN</span>
            {% else %}
              <span class="badge badge-success">LIMPIO</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <!-- 5. OWASP LLM Top 10 Coverage -->
    <h2 class="section-title">🤖 Cobertura OWASP LLM Top 10</h2>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 8%;">ID</th>
          <th>Riesgo</th>
          <th style="width: 30%;">Herramienta(s)</th>
          <th style="text-align: center; width: 15%;">Estado</th>
        </tr>
      </thead>
      <tbody>
        {% for item in pipeline_ctx.llm_coverage %}
        <tr>
          <td><span class="badge" style="background: #7c3aed20; color: #7c3aed; font-weight: 700;">{{ item.id }}</span></td>
          <td><strong>{{ item.name }}</strong></td>
          <td style="color: var(--text-muted); font-size: 0.85em;">{{ item.tools }}</td>
          <td style="text-align: center;">
            {% if item.active %}
              <span class="badge badge-success">✓ ACTIVO</span>
            {% elif '—' in item.tools %}
              <span class="badge" style="background: #e2e8f0; color: #64748b;">MANUAL</span>
            {% else %}
              <span class="badge" style="background: #fef3c720; color: #d97706;">⚠ INACTIVO</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <p style="font-size: 0.8em; color: var(--text-muted); margin-top: 4px;">
      ⚠ <strong>INACTIVO</strong> indica que la herramienta existe en el pipeline pero requiere configuración
      (p.ej. <code>LLM_ENDPOINT</code>). <strong>MANUAL</strong> indica que la categoría está fuera del alcance
      de herramientas automatizadas y requiere revisión de arquitectura.
    </p>

    <!-- 6. Detalle de Hallazgos -->
    <h2 class="section-title">
      <span>🔍 Hallazgos Detallados</span>
      <span id="findings-count" style="font-size: 0.7em; font-weight: 500; color: var(--text-muted);">{{ detail_findings|length }} hallazgos</span>
    </h2>

    {% if detail_findings %}
    <!-- Barra de Filtros Interactiva -->
    <div class="interactive-toolbar">
      <div class="search-row">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Buscar por CVE, archivo, paquete, descripción..." onkeyup="filterFindings()">
      </div>
      <div class="filter-group">
        <span class="filter-label">Severidad:</span>
        <button class="filter-btn active" data-filter="sev" data-val="ALL" onclick="setFilter(this)">Todos</button>
        <button class="filter-btn" data-filter="sev" data-val="CRITICAL" onclick="setFilter(this)">Crítico ({{ severity_counts.CRITICAL }})</button>
        <button class="filter-btn" data-filter="sev" data-val="HIGH" onclick="setFilter(this)">Alto ({{ severity_counts.HIGH }})</button>
        <button class="filter-btn" data-filter="sev" data-val="MEDIUM" onclick="setFilter(this)">Medio ({{ severity_counts.MEDIUM }})</button>
        <button class="filter-btn" data-filter="sev" data-val="LOW" onclick="setFilter(this)">Bajo ({{ severity_counts.LOW }})</button>
      </div>
      {% if unique_services|length > 1 %}
      <div class="filter-group">
        <span class="filter-label">Servicio:</span>
        <button class="filter-btn active" data-filter="srv" data-val="ALL" onclick="setFilter(this)">Todos los Servicios</button>
        {% for srv in unique_services %}
        <button class="filter-btn" data-filter="srv" data-val="{{ srv }}" onclick="setFilter(this)">{{ srv.title() }}</button>
        {% endfor %}
      </div>
      {% endif %}
    </div>

    <!-- Lista de Tarjetas de Hallazgos -->
    <div id="findings-container">
      {% for vuln in detail_findings %}
      <div class="finding-card" 
           data-severity="{{ vuln.severity }}" 
           data-service="{{ vuln.service }}"
           data-search="{{ vuln.name|lower }} {{ vuln.cve|lower }} {{ vuln.file|lower }} {{ vuln.description|lower }} {{ vuln.report_type|lower }}">
        <div class="finding-card-header {{ vuln.severity }}">
          <h3 class="finding-card-title">{{ vuln.name }}</h3>
          <span class="badge" style="background: rgba(255,255,255,0.25); color: white;">{{ vuln.severity }}</span>
        </div>
        <div class="finding-card-body">
          <div class="finding-grid">
            <div class="finding-subbox">
              <span class="finding-subbox-label">Herramienta / Categoría</span>
              <div class="finding-subbox-value">{{ vuln.report_type }}</div>
            </div>
            <div class="finding-subbox">
              <span class="finding-subbox-label">Servicio</span>
              <div class="finding-subbox-value"><strong>{{ vuln.service.title() }}</strong></div>
            </div>
            <div class="finding-subbox">
              <span class="finding-subbox-label">Identificador / CVE</span>
              <div class="finding-subbox-value">{{ vuln.cve }}</div>
            </div>
            <div class="finding-subbox">
              <span class="finding-subbox-label">Ubicación</span>
              <div class="finding-subbox-value">{{ vuln.file }}{% if vuln.line != 'N/A' and vuln.line != 0 %}:{{ vuln.line }}{% endif %}</div>
            </div>
          </div>
          {% if vuln.description %}
          <div class="finding-subbox">
            <span class="finding-subbox-label">Descripción & Mitigación</span>
            <div class="finding-subbox-value">{% if '[' in vuln.description and '](' in vuln.description %}{{ vuln.description | safe }}{% else %}{{ vuln.description }}{% endif %}</div>
          </div>
          {% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <div style="text-align: center; padding: 40px 20px; background: white; border-radius: 8px; border: 1px solid var(--border);">
      <h3 style="color: var(--secondary); font-size: 1.3em; margin-bottom: 6px;">✅ Todo en orden</h3>
      <p style="color: var(--text-muted); margin: 0;">No se han detectado vulnerabilidades o incidentes de seguridad pendientes en este ciclo.</p>
    </div>
    {% endif %}

    <footer>
      Generado por GRS DevOps Toolkit | © 2026 GRS DevSecOps
    </footer>
  </div>

  <script>
    let currentSev = 'ALL';
    let currentSrv = 'ALL';

    function setFilter(btn) {
      const type = btn.getAttribute('data-filter');
      const val = btn.getAttribute('data-val');
      
      const parentGroup = btn.parentElement;
      parentGroup.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      if (type === 'sev') currentSev = val;
      if (type === 'srv') currentSrv = val;

      filterFindings();
    }

    function filterFindings() {
      const searchVal = document.getElementById('searchInput') ? document.getElementById('searchInput').value.toLowerCase().trim() : '';
      const cards = document.querySelectorAll('.finding-card');
      let visibleCount = 0;

      cards.forEach(card => {
        const cardSev = card.getAttribute('data-severity');
        const cardSrv = card.getAttribute('data-service');
        const cardText = card.getAttribute('data-search') || '';

        const matchSev = (currentSev === 'ALL' || cardSev === currentSev);
        const matchSrv = (currentSrv === 'ALL' || cardSrv === currentSrv);
        const matchSearch = (searchVal === '' || cardText.includes(searchVal));

        if (matchSev && matchSrv && matchSearch) {
          card.style.display = 'block';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      const countEl = document.getElementById('findings-count');
      if (countEl) {
        countEl.innerText = visibleCount + ' de ' + cards.length + ' hallazgos visibles';
      }
    }
  </script>
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
        services_summary=services_summary,
        unique_services=unique_services,
        unique_categories=unique_categories,
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
        print(f"✅ Reporte unificado generado exitosamente: {html_path} y {pdf_path}")
    except Exception as e:
        print(f"⚠️  Error al generar PDF: {e}")
        print(f"✅ Reporte HTML unificado generado: {html_path}")


def main():
    """Descubre todos los escaneos de seguridad y genera UN ÚNICO reporte consolidado."""
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
    
    dynamic_files = (
        glob.glob("*report.json") +
        glob.glob("*scanning.json") +
        glob.glob("*compliance.json") +
        glob.glob("*.cdx.json") +
        glob.glob("*coverage*.json") +
        glob.glob("gl-sast-*.json") +
        glob.glob("*trivy*.json") +
        glob.glob("gitleaks-report-*.json") +
        # LLM Security reports
        glob.glob("llm-*.json") +
        glob.glob("gl-sast-llm-*.json")
    )
    
    all_potential_files = list(dict.fromkeys(standard_files + dynamic_files))
    
    all_findings = []
    found_reports = []
    
    print("🔍 Iniciando descubrimiento de reportes DevSecOps...")
    for report_file in all_potential_files:
        if not os.path.exists(report_file):
            continue
            
        findings = load_report(report_file)
        if findings:
            all_findings.extend(findings)
            found_reports.append(report_file)
            print(f"✅ Procesado: {report_file} ({len(findings)} hallazgos)")
        elif os.path.exists(report_file):
            print(f"✅ Procesado (Limpio): {report_file} (0 hallazgos)")
            clean_type = os.path.basename(report_file).replace('.cdx.json', '').replace('.json', '').replace('gl-', '').replace('-', ' ').title()
            all_findings.append({
                'name': 'Escaneo Limpio',
                'severity': 'INFO',
                'description': f'No se encontraron vulnerabilidades en {report_file}.',
                'file': 'N/A',
                'line': 'N/A',
                'cve': 'N/A',
                'identifier': 'CLEAN',
                'report_type': clean_type,
                'service': extract_service_name(report_file)
            })
            found_reports.append(report_file)
    
    service_name = os.environ.get('SERVICE_NAME', '')
    service_path = os.environ.get('SERVICE_PATH', os.environ.get('BUILD_SERVICE_PATH', ''))
    
    if service_name and service_name not in ('.', 'root', 'Global', ''):
        clean_path = service_path.lstrip('./').rstrip('/')
        filtered_findings = []
        for f in all_findings:
            f_file = f.get('file', '')
            f_service = f.get('service', '')
            
            # 1. Si el hallazgo viene marcado para un servicio específico
            if f_service and f_service != 'Global':
                if f_service.lower() == service_name.lower():
                    filtered_findings.append(f)
                continue
            
            # 2. Si el hallazgo tiene ruta de archivo (SAST, IaC, Secret, Code Quality)
            if f_file and f_file != 'N/A':
                clean_file = f_file.lstrip('./')
                if clean_path and (clean_file.startswith(clean_path + '/') or clean_file == clean_path):
                    filtered_findings.append(f)
                elif not clean_path:
                    filtered_findings.append(f)
                continue
            
            # 3. Hallazgos globales (cluster, DAST, etc.)
            filtered_findings.append(f)
            
        all_findings = filtered_findings
        report_title = f"Reporte de Seguridad — Microservicio {service_name.title()}"
        output_prefix = f"security-report-{service_name}"
    else:
        report_title = "GRS Executive Summary Dashboard"
        output_prefix = "executive-summary-report"

    print(f"\n📊 Generando Reporte ({len(all_findings)} hallazgos para {output_prefix})...")
    generate_report(all_findings, report_title, output_prefix)

    # Copiar también a executive-summary-report para compatibilidad
    if output_prefix != "executive-summary-report":
        import shutil
        if os.path.exists(f"{output_prefix}.html"):
            shutil.copyfile(f"{output_prefix}.html", "executive-summary-report.html")
        if os.path.exists(f"{output_prefix}.pdf"):
            shutil.copyfile(f"{output_prefix}.pdf", "executive-summary-report.pdf")

if __name__ == "__main__":
    main()

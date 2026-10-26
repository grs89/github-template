"""Tests del conversor Gitleaks -> formato Secret Detection de GitLab.

Este parser decide si un secreto llega o no al reporte de seguridad, y el job
que lo usa es bloqueante. Un fallo silencioso aqui deja pasar credenciales.
"""
import json

import convert_gitleaks


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def test_reporte_vacio_valido_si_no_existe_la_entrada(tmp_path):
    salida = tmp_path / "out.json"
    convert_gitleaks.convert(str(tmp_path / "no-existe.json"), str(salida))

    report = _read(salida)
    assert report["vulnerabilities"] == []
    assert report["scan"]["type"] == "secret_detection"
    assert report["scan"]["status"] == "success"


def test_reporte_vacio_valido_si_la_entrada_esta_vacia(tmp_path):
    entrada = tmp_path / "gitleaks.json"
    entrada.write_text("", encoding="utf-8")
    salida = tmp_path / "out.json"

    convert_gitleaks.convert(str(entrada), str(salida))
    assert _read(salida)["vulnerabilities"] == []


def test_json_corrupto_no_revienta_y_da_reporte_vacio(tmp_path):
    entrada = tmp_path / "gitleaks.json"
    entrada.write_text("{esto no es json", encoding="utf-8")
    salida = tmp_path / "out.json"

    convert_gitleaks.convert(str(entrada), str(salida))
    assert _read(salida)["vulnerabilities"] == []


def test_convierte_un_hallazgo_con_todos_los_campos(tmp_path):
    entrada = tmp_path / "gitleaks.json"
    entrada.write_text(json.dumps([{
        "Description": "AWS Access Key",
        "RuleID": "aws-access-token",
        "Match": "AKIA...",
        "File": "config/settings.py",
        "StartLine": 42,
        "EndLine": 42,
    }]), encoding="utf-8")
    salida = tmp_path / "out.json"

    convert_gitleaks.convert(str(entrada), str(salida))
    vulns = _read(salida)["vulnerabilities"]

    assert len(vulns) == 1
    vuln = vulns[0]
    assert vuln["category"] == "secret_detection"
    assert vuln["severity"] == "Critical"
    assert vuln["name"] == "AWS Access Key"
    assert vuln["location"] == {
        "file": "config/settings.py",
        "start_line": 42,
        "end_line": 42,
    }
    assert vuln["identifiers"][0]["value"] == "aws-access-token"


def test_hallazgo_con_campos_ausentes_no_pierde_la_vulnerabilidad(tmp_path):
    """Un hallazgo incompleto debe seguir apareciendo: no puede desaparecer."""
    entrada = tmp_path / "gitleaks.json"
    entrada.write_text(json.dumps([{"RuleID": "generic-api-key"}]), encoding="utf-8")
    salida = tmp_path / "out.json"

    convert_gitleaks.convert(str(entrada), str(salida))
    vulns = _read(salida)["vulnerabilities"]

    assert len(vulns) == 1
    assert vulns[0]["location"]["file"] == "N/A"
    assert vulns[0]["severity"] == "Critical"


def test_varios_hallazgos_reciben_ids_unicos(tmp_path):
    entrada = tmp_path / "gitleaks.json"
    entrada.write_text(json.dumps([
        {"RuleID": "a", "File": "x.py", "StartLine": 1, "EndLine": 1},
        {"RuleID": "b", "File": "y.py", "StartLine": 2, "EndLine": 2},
        {"RuleID": "c", "File": "z.py", "StartLine": 3, "EndLine": 3},
    ]), encoding="utf-8")
    salida = tmp_path / "out.json"

    convert_gitleaks.convert(str(entrada), str(salida))
    vulns = _read(salida)["vulnerabilities"]

    assert len(vulns) == 3
    assert len({v["id"] for v in vulns}) == 3

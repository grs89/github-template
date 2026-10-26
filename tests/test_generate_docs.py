"""generate_docs: markdown -> HTML de la wiki. Las URLs de enlaces e imagenes no pueden ejecutar codigo."""
import pytest

import generate_docs as gd


@pytest.fixture(autouse=True)
def _mapeo_limpio():
    gd.LINK_MAPPING.clear()
    yield
    gd.LINK_MAPPING.clear()


def test_escape_html():
    assert gd.escape_html("<a href=\"x\">&") == "&lt;a href=\"x\"&gt;&amp;"


@pytest.mark.parametrize("url", ["https://a.com/x", "http://a.com", "#seccion", "mailto:a@b.c"])
def test_resolve_deja_intactas_las_urls_absolutas_y_anclas(url):
    assert gd.resolve_link_to_anchor(url) == url


def test_resolve_usa_el_mapeo_con_y_sin_extension_y_con_subancla():
    gd.LINK_MAPPING.update({"Usage-Guide.md": "usage-guide", "usage-guide": "usage-guide"})
    assert gd.resolve_link_to_anchor("Usage-Guide.md") == "#usage-guide"
    assert gd.resolve_link_to_anchor("../Usage-Guide.md#paso-2") == "#usage-guide#paso-2"
    assert gd.resolve_link_to_anchor("usage-guide") == "#usage-guide"


def test_resolve_convierte_md_desconocido_en_html_y_conserva_otros():
    assert gd.resolve_link_to_anchor("otro.md") == "otro.html"
    assert gd.resolve_link_to_anchor("imagen.png") == "imagen.png"


def test_inline_negrita_cursiva_y_codigo_escapado():
    html = gd.parse_inline("**fuerte** y *suave* y `<b>`")
    assert "<strong" in html and ">fuerte</strong>" in html and "<em" in html
    assert "&lt;b&gt;" in html and "<b>" not in html


def test_inline_enlace_e_imagen():
    assert 'href="https://x.com"' in gd.parse_inline("[web](https://x.com)")
    img = gd.parse_inline("![logo](https://x.com/l.png)")
    assert 'src="https://x.com/l.png"' in img and 'alt="logo"' in img


@pytest.mark.parametrize("md", ["[x](javascript:alert(1))", "[x](JaVaScRiPt:alert(1))", "[x](  javascript:alert(1))",
                                "![x](javascript:alert(1))", "[x](data:text/html;base64,AAAA)", "[x](vbscript:msgbox(1))"])
def test_esquemas_ejecutables_se_neutralizan(md):
    html = gd.parse_inline(md)
    assert "javascript:" not in html.lower() and "vbscript:" not in html.lower() and "data:text" not in html.lower()


def test_comillas_en_la_url_no_rompen_el_atributo():
    html = gd.parse_inline('[x](https://a.com/" onmouseover="alert(1))')
    assert 'onmouseover="' not in html
    assert 'alt="a&quot;b"' in gd.parse_inline('![a"b](https://x.com/i.png)')


def test_markdown_bloques_basicos():
    html = gd.parse_markdown("# Titulo\n\n## Sub\n\ntexto con **negrita**\n\n- uno\n- dos\n")
    assert "<h1" in html and ">Titulo</h1>" in html and "<h2" in html
    assert html.count("<li>") == 2 and "<ul" in html and "</ul>" in html
    assert "<strong" in html


def test_markdown_bloque_de_codigo_se_escapa_y_mermaid_se_mantiene():
    html = gd.parse_markdown("```python\nx = '<script>'\n```\n\n```mermaid\ngraph TD; A-->B\n```\n")
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert 'class="mermaid' in html and "graph TD" in html


def test_markdown_tabla():
    html = gd.parse_markdown("| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert "<table" in html and ">A</th>" in html and ">1</td>" in html and "</table>" in html


def test_markdown_tabla_bien_formada():
    html = gd.parse_markdown("| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\ntexto\n")
    assert html.count("<thead") == html.count("</thead>") == 1
    assert html.count("<tbody>") == html.count("</tbody>") == 1
    cabecera, cuerpo = html.split("</thead>")
    assert ">A</th>" in cabecera and ">B</th>" in cabecera and "<td" not in cabecera
    assert ">1</td>" in cuerpo and ">4</td>" in cuerpo and "<th" not in cuerpo


def test_dos_tablas_seguidas_quedan_separadas():
    html = gd.parse_markdown("| A |\n|---|\n| 1 |\n\ntexto\n\n| B |\n|---|\n| 2 |\n")
    assert html.count("<table") == html.count("</table>") == 2
    assert html.count("<tbody>") == html.count("</tbody>") == 2


def test_main_compila_readme_wiki_y_changelog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CI_PROJECT_NAME", "mi-app")
    (tmp_path / "README.md").write_text("# Hola\n\nVer [guia](Usage-Guide.md)\n")
    (tmp_path / "CHANGELOG.md").write_text("# Cambios\n\n- algo\n")
    (tmp_path / "01-wiki").mkdir()
    (tmp_path / "01-wiki" / "Usage-Guide.md").write_text("# Guia\n\n- paso\n")
    gd.main()
    html = (tmp_path / "public" / "index.html").read_text(encoding="utf-8")
    assert 'id="home"' in html and 'id="changelog"' in html and 'id="usage-guide"' in html
    assert 'href="#usage-guide"' in html          # el enlace relativo del README apunta a su seccion
    assert "Mi-App" in html or "Mi App" in html


def test_main_sin_markdown_genera_pagina_de_bienvenida_y_termina(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as salida:
        gd.main()
    assert salida.value.code == 0 and (tmp_path / "public" / "index.html").exists()

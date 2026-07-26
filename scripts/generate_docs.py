#!/usr/bin/env python3
import os
import re
import sys
import glob

LINK_MAPPING = {}

def resolve_link_to_anchor(url):
    # Si la URL es absoluta o comienza con #, dejarla intacta
    if url.startswith('http://') or url.startswith('https://') or url.startswith('#') or url.startswith('mailto:'):
        return url
        
    cleaned_url = url.split('#')[0] # quitar cualquier ancla interna
    cleaned_url = re.sub(r'^\.+/', '', cleaned_url) # quitar ./ o ../ al inicio
    
    # Intentar buscar directamente en el mapeo
    for key in [cleaned_url, os.path.basename(cleaned_url), os.path.basename(cleaned_url).lower()]:
        if key in LINK_MAPPING:
            anchor = LINK_MAPPING[key]
            sub_anchor = ""
            if '#' in url:
                sub_anchor = "#" + url.split('#')[1]
            return f"#{anchor}{sub_anchor}"
            
    # Intentar sin extensión .md o .html
    suffix_free = cleaned_url
    if suffix_free.endswith('.md'):
        suffix_free = suffix_free[:-3]
    elif suffix_free.endswith('.html'):
        suffix_free = suffix_free[:-5]
        
    for key in [suffix_free, os.path.basename(suffix_free), os.path.basename(suffix_free).lower()]:
        if key in LINK_MAPPING:
            anchor = LINK_MAPPING[key]
            sub_anchor = ""
            if '#' in url:
                sub_anchor = "#" + url.split('#')[1]
            return f"#{anchor}{sub_anchor}"
            
    # Si no se encuentra, como fallback, si termina en .md la convertimos a .html
    if url.endswith('.md'):
        return url[:-3] + '.html'
    return url

def escape_html(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def parse_markdown(md_content):
    html = []
    lines = md_content.split('\n')
    in_code_block = False
    code_lang = ""
    code_lines = []
    in_list = False
    
    for line in lines:
        # Code Blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # Close code block
                code_content = '\n'.join(code_lines)
                if code_lang == 'mermaid':
                    html.append(f'<div class="mermaid flex justify-center bg-themeCodeBg/40 border border-themeBorder rounded-2xl p-6 my-6 shadow-inner">\n{code_content}\n</div>')
                else:
                    html.append(f'<div class="relative group my-6"><div class="absolute right-3 top-3 text-xs text-slate-500 font-mono select-none uppercase">{code_lang}</div><pre class="bg-themeCodeBg border border-themeBorder rounded-xl p-5 overflow-x-auto text-sm text-themeSecText font-mono"><code>{code_content}</code></pre></div>')
                in_code_block = False
                code_lines = []
            else:
                # Open code block
                in_code_block = True
                code_lang = line.strip().replace('```', '').strip()
                if not code_lang:
                    code_lang = "code"
            continue
            
        if in_code_block:
            if code_lang == 'mermaid':
                code_lines.append(line) # No escapar HTML en diagramas Mermaid (como -->)
            else:
                code_lines.append(escape_html(line))
            continue
            
        # Paragraph & List cleanups
        stripped = line.strip()
        
        # Omitir comentarios HTML
        if stripped.startswith('<!--') or stripped.endswith('-->') or stripped.startswith('-->'):
            continue
            
        # Unordered Lists
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html.append('<ul class="list-disc pl-6 my-4 space-y-2 text-themeSecText">')
                in_list = True
            item_text = stripped[2:]
            # Process inline formatting
            item_text = parse_inline(item_text)
            html.append(f'<li>{item_text}</li>')
            continue
        else:
            if in_list:
                html.append('</ul>')
                in_list = False
                
        # Empty lines
        if not stripped:
            html.append('<div class="h-3"></div>')
            continue
            
        # Headings
        if stripped.startswith('# '):
            html.append(f'<h1 class="text-3xl font-extrabold text-themeText mt-8 mb-4 border-b border-themeBorder pb-2 tracking-tight">{parse_inline(stripped[2:])}</h1>')
        elif stripped.startswith('## '):
            html.append(f'<h2 class="text-2xl font-bold text-themeText mt-8 mb-4 border-b border-themeBorderSubtle pb-1 tracking-tight">{parse_inline(stripped[3:])}</h2>')
        elif stripped.startswith('### '):
            html.append(f'<h3 class="text-xl font-semibold text-themeText mt-6 mb-3 tracking-tight">{parse_inline(stripped[4:])}</h3>')
        elif stripped.startswith('#### '):
            html.append(f'<h4 class="text-lg font-semibold text-themeSecText mt-5 mb-2 tracking-tight">{parse_inline(stripped[5:])}</h4>')
            
        # GitHub style Alerts / Blockquotes
        elif stripped.startswith('> '):
            alert_text = stripped[2:]
            alert_class = "border-l-4 border-slate-500 bg-slate-500/10 dark:bg-slate-900/30 text-slate-600 dark:text-slate-400 p-4 rounded-r-xl my-5"
            alert_title = ""
            
            if alert_text.startswith('[!NOTE]'):
                alert_class = "border-l-4 border-sky-500 bg-sky-500/10 dark:bg-sky-950/20 text-sky-800 dark:text-sky-200 p-4 rounded-r-xl my-5"
                alert_title = '<div class="font-bold text-sky-600 dark:text-sky-400 mb-1 flex items-center gap-2"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>NOTA</div>'
                alert_text = alert_text.replace('[!NOTE]', '').strip()
            elif alert_text.startswith('[!TIP]'):
                alert_class = "border-l-4 border-emerald-500 bg-emerald-500/10 dark:bg-emerald-950/20 text-emerald-800 dark:text-emerald-200 p-4 rounded-r-xl my-5"
                alert_title = '<div class="font-bold text-emerald-600 dark:text-emerald-400 mb-1 flex items-center gap-2"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>SUGERENCIA</div>'
                alert_text = alert_text.replace('[!TIP]', '').strip()
            elif alert_text.startswith('[!IMPORTANT]'):
                alert_class = "border-l-4 border-indigo-500 bg-indigo-500/10 dark:bg-indigo-950/20 text-indigo-800 dark:text-indigo-200 p-4 rounded-r-xl my-5"
                alert_title = '<div class="font-bold text-indigo-600 dark:text-indigo-400 mb-1 flex items-center gap-2"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>IMPORTANTE</div>'
                alert_text = alert_text.replace('[!IMPORTANT]', '').strip()
            elif alert_text.startswith('[!WARNING]'):
                alert_class = "border-l-4 border-amber-500 bg-amber-500/10 dark:bg-amber-950/20 text-amber-800 dark:text-amber-200 p-4 rounded-r-xl my-5"
                alert_title = '<div class="font-bold text-amber-600 dark:text-amber-400 mb-1 flex items-center gap-2"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>ADVERTENCIA</div>'
                alert_text = alert_text.replace('[!WARNING]', '').strip()
            elif alert_text.startswith('[!CAUTION]'):
                alert_class = "border-l-4 border-rose-500 bg-rose-500/10 dark:bg-rose-950/20 text-rose-800 dark:text-rose-200 p-4 rounded-r-xl my-5"
                alert_title = '<div class="font-bold text-rose-600 dark:text-rose-400 mb-1 flex items-center gap-2"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>CUIDADO</div>'
                alert_text = alert_text.replace('[!CAUTION]', '').strip()
                
            html.append(f'<div class="{alert_class}">{alert_title}{parse_inline(alert_text)}</div>')
            
        # Tables (simplified parsing)
        elif stripped.startswith('|') and '|' in line[1:]:
            # Check if separator
            if '---' in line:
                continue
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            cell_tags = "".join([f'<td class="px-4 py-3 border-b border-themeBorder text-sm text-themeSecText">{parse_inline(c)}</td>' for c in cells])
            html.append(f'<tr class="hover:bg-themeCard/50 transition-colors">{cell_tags}</tr>')
            
        # Standard paragraphs
        else:
            # Evitar envolver código HTML crudo/etiquetas en etiquetas <p>
            if stripped.startswith('<'):
                html.append(parse_inline(line))
            else:
                # Wrap standard lines in paragraphs
                html.append(f'<p class="text-themeSecText leading-relaxed my-4">{parse_inline(stripped)}</p>')
            
    if in_list:
        html.append('</ul>')
        
    # Re-structure table structures
    final_html = []
    in_table = False
    for line in html:
        if line.startswith('<tr'):
            if not in_table:
                final_html.append('<div class="overflow-x-auto my-6 border border-themeBorder rounded-xl"><table class="w-full text-left border-collapse"><thead class="bg-themeCodeBg text-xs font-semibold text-themeMuted uppercase tracking-wider">')
                in_table = True
            elif in_table and '</thead>' not in "".join(final_html[-2:]):
                # Simple table header separation: first row is treated as header
                # We do a dirty header finish after the first row
                # (in a real markdown table, separator follows. We just wrap it cleanly)
                pass
        else:
            if in_table:
                final_html.append('</tbody></table></div>')
                in_table = False
        final_html.append(line)
        
    if in_table:
        final_html.append('</tbody></table></div>')
        
    return '\n'.join(final_html)

def parse_inline(text):
    # 1. Code tags first (escaped to prevent HTML rendering of code contents)
    text = re.sub(r'`(.*?)`', lambda m: f'<code class="px-1.5 py-0.5 rounded bg-themeCodeBg border border-themeBorder text-themeAccent font-mono text-xs">{escape_html(m.group(1))}</code>', text)
    
    # 2. Markdown Images: ![alt](url) -> <img src="\2" alt="\1" class="inline-block my-1 rounded hover:scale-105 transition-transform max-w-full">
    text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1" class="inline-block my-1 rounded hover:scale-105 transition-transform max-w-full">', text)
    
    # 3. Links: [text](url) -> convert relative links to anchors or keep absolute
    def link_repl(match):
        label, url = match.groups()
        target_url = resolve_link_to_anchor(url)
        return f'<a href="{target_url}" class="text-themeAccent hover:text-themeAccentHover hover:underline transition-colors font-medium">{label}</a>'
        
    text = re.sub(r'\[(.*?)\]\((.*?)\)', link_repl, text)
    
    # 4. Bold: **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong class="font-bold text-themeText">\1</strong>', text)
    
    # 5. Italic: *text*
    text = re.sub(r'\*(.*?)\*', r'<em class="italic text-themeText/90">\1</em>', text)
    
    return text

def main():
    print("🚀 Iniciando compilación de documentación (Apple Showcase Single-Page)...")
    os.makedirs('public', exist_ok=True)
    
    global LINK_MAPPING
    LINK_MAPPING.clear()
    
    # 🔍 Buscar archivos markdown
    md_files = []
    seen_ids = set()
    
    # 1. Agregar README.md raíz si existe
    if os.path.isfile('README.md'):
        section_id = 'home'
        seen_ids.add(section_id)
        md_files.append(('README.md', section_id, '🏠 Home (README)'))
        # Mapear aliases para README
        LINK_MAPPING['README.md'] = section_id
        LINK_MAPPING['readme.md'] = section_id
        LINK_MAPPING['readme'] = section_id
        LINK_MAPPING['README'] = section_id
        
    # 2. Agregar CHANGELOG.md raíz si existe
    if os.path.isfile('CHANGELOG.md'):
        section_id = 'changelog'
        seen_ids.add(section_id)
        md_files.append(('CHANGELOG.md', section_id, '📜 Changelog'))
        # Mapear aliases para CHANGELOG
        LINK_MAPPING['CHANGELOG.md'] = section_id
        LINK_MAPPING['changelog.md'] = section_id
        LINK_MAPPING['changelog'] = section_id
        LINK_MAPPING['CHANGELOG'] = section_id
        
    # 3. Buscar en 01-wiki/
    if os.path.isdir('01-wiki'):
        wiki_files = glob.glob('01-wiki/**/*.md', recursive=True)
        for f in sorted(wiki_files):
            basename = os.path.basename(f)
            raw_id = basename[:-3].lower().replace('_', '-').replace(' ', '-')
            section_id = raw_id
            
            # Evitar duplicados prependiando 'wiki-'
            if section_id in seen_ids:
                section_id = f"wiki-{section_id}"
                
            # Resolver colisiones adicionales
            counter = 1
            original_section_id = section_id
            while section_id in seen_ids:
                section_id = f"{original_section_id}-{counter}"
                counter += 1
                
            seen_ids.add(section_id)
            
            # Crear un título legible desde el nombre de archivo
            title = basename[:-3].replace('-', ' ').replace('_', ' ').title()
            try:
                with open(f, 'r', encoding='utf-8') as file_obj:
                    first_line = file_obj.readline().strip()
                    if first_line.startswith('# '):
                        title = first_line[2:].strip()
            except Exception:
                pass
            md_files.append((f, section_id, title))
            
            # Registrar todos los alias para este archivo en el mapeo global
            LINK_MAPPING[f] = section_id
            LINK_MAPPING[basename] = section_id
            LINK_MAPPING[basename.lower()] = section_id
            LINK_MAPPING[basename[:-3]] = section_id
            LINK_MAPPING[basename[:-3].lower()] = section_id
            
    if not md_files:
        print("⚠️ No se encontraron archivos markdown para compilar. Generando página de bienvenida por defecto...")
        project_title = os.environ.get('CI_PROJECT_NAME', os.path.basename(os.getcwd())).title()
        project_url = os.environ.get('CI_PROJECT_URL', '#')
        
        fallback_html = f'''<!DOCTYPE html>
<html lang="es" class="h-full bg-[#07080d] dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portal de Documentación | {project_title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #07080d;
        }}
        h1, h2, .outfit {{
            font-family: 'Outfit', sans-serif;
        }}
    </style>
</head>
<body class="h-full text-slate-300 flex items-center justify-center p-6 antialiased">
    <div class="max-w-md w-full bg-[#0b0d16] border border-white/10 rounded-3xl p-8 text-center shadow-2xl relative overflow-hidden group">
        <!-- Glow Effect -->
        <div class="absolute -inset-0.5 bg-gradient-to-r from-sky-500 to-indigo-600 rounded-3xl blur opacity-20 group-hover:opacity-35 transition duration-1000"></div>
        
        <div class="relative bg-[#0b0d16] rounded-2xl p-2">
            <!-- Icon -->
            <div class="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gradient-to-tr from-sky-400 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
                </svg>
            </div>
            
            <!-- Title -->
            <h1 class="text-2xl font-extrabold text-white mb-3 outfit tracking-tight">Portal de Documentación</h1>
            <p class="text-sm text-sky-400 font-mono font-medium mb-6 uppercase tracking-wider outfit">{project_title}</p>
            
            <!-- Content -->
            <div class="text-slate-400 text-sm space-y-4 mb-8 leading-relaxed">
                <p>¡Hola! Este portal web inmersivo está listo para mostrar la documentación de tu proyecto.</p>
                <p class="bg-white/5 border border-white/5 rounded-xl p-4 text-xs text-left">
                    💡 <strong>¿Cómo empezar?</strong><br>
                    Crea un archivo <code class="text-sky-300 font-mono">README.md</code> en la raíz de tu repositorio o añade guías en formato Markdown dentro de la carpeta <code class="text-sky-300 font-mono">01-wiki/</code>. El pipeline compilará todo automáticamente.
                </p>
            </div>
            
            <!-- Button -->
            <a href="{project_url}" target="_blank" class="inline-flex items-center justify-center w-full py-3 px-5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 transition-all duration-300 shadow-lg shadow-indigo-500/20 outfit">
                Ir al Repositorio en GitLab
            </a>
        </div>
    </div>
</body>
</html>'''
        with open('public/index.html', 'w', encoding='utf-8') as f:
            f.write(fallback_html)
        print("✅ Generada página de bienvenida por defecto en 'public/index.html'.")
        sys.exit(0)
        
    print(f"📦 Se compilarán {len(md_files)} secciones en una única página inmersiva.")
    
    # Procesar y compilar cada sección
    compiled_sections = []
    sidebar_links = []
    dot_links = []
    
    for source_path, section_id, title in md_files:
        print(f"📖 Procesando sección: {source_path} -> ID: #{section_id}")
        
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
        except Exception as e:
            print(f"⚠️ Error al leer {source_path}: {e}")
            continue
            
        parsed_body = parse_markdown(md_content)
        compiled_sections.append((section_id, title, parsed_body))
        
        # Generar enlaces laterales
        is_readme = (section_id == 'home')
        is_changelog = (section_id == 'changelog')
        
        icon_svg = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>'
        if is_readme:
            icon_svg = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>'
        elif is_changelog:
            icon_svg = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
            
        sidebar_links.append(f'''
        <a href="#{section_id}" data-section="{section_id}" class="nav-item flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-xl text-themeMuted hover:text-themeText hover:bg-themeCard transition-all duration-200">
            {icon_svg}
            <span class="truncate">{title}</span>
        </a>''')
        
        # Generar puntos del Dot-Nav flotante derecho
        dot_links.append(f'''
        <a href="#{section_id}" data-dot="{section_id}" class="dot-item w-3 h-3 rounded-full bg-themeMuted hover:bg-themeAccent transition-all duration-300 relative group" title="{title}">
            <span class="absolute right-6 top-1/2 transform -translate-y-1/2 bg-themeSidebar border border-themeBorder text-xs font-semibold text-themeText px-2 py-1 rounded-md opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-300 shadow-md outfit whitespace-nowrap">{title}</span>
        </a>''')
        
    sidebar_html = "\n".join(sidebar_links)
    dot_html = "\n".join(dot_links)
    project_title = os.environ.get('CI_PROJECT_NAME', os.path.basename(os.getcwd())).title()
    project_url = os.environ.get('CI_PROJECT_URL', '#')
    
    # Concatenar todas las secciones en el cuerpo principal
    body_html_parts = []
    for section_id, title, parsed_body in compiled_sections:
        body_html_parts.append(f'''
        <section id="{section_id}" class="apple-reveal py-16 lg:py-24 border-b border-themeBorderSubtle last:border-b-0 min-h-[85vh] flex flex-col justify-center opacity-0 translate-y-8 transition-all duration-1000 ease-out scroll-mt-24">
            <article class="prose max-w-none text-themeSecText">
                {parsed_body}
            </article>
        </section>''')
        
    all_sections_html = "\n".join(body_html_parts)
    
    # Escribir la única página index.html
    html_page = f'''<!DOCTYPE html>
<html lang="es" class="h-full bg-themeBg scroll-smooth dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portal de Documentación | {project_title}</title>
    <!-- Google Fonts: Inter, Outfit, Sora, JetBrains Mono, Merriweather -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&family=Sora:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Merriweather:ital,wght@0,300;0,400;0,700;1,300&display=swap" rel="stylesheet">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        themeBg: 'var(--bg-main)',
                        themeSidebar: 'var(--bg-sidebar)',
                        themeCard: 'var(--bg-card)',
                        themeText: 'var(--text-primary)',
                        themeSecText: 'var(--text-secondary)',
                        themeMuted: 'var(--text-muted)',
                        themeBorder: 'var(--border-color)',
                        themeBorderSubtle: 'var(--border-subtle)',
                        themeAccent: 'var(--accent)',
                        themeAccentHover: 'var(--accent-hover)',
                        themeAccentBg: 'var(--accent-bg)',
                        themeCodeBg: 'var(--code-bg)',
                    }}
                }}
            }}
        }}
    </script>
    <style>
        :root {{
            /* Modo Claro */
            --bg-main: #f8fafc;
            --bg-sidebar: #ffffff;
            --bg-card: #f1f5f9;
            --text-primary: #0f172a;
            --text-secondary: #334155;
            --text-muted: #94a3b8;
            --border-color: rgba(0, 0, 0, 0.08);
            --border-subtle: rgba(0, 0, 0, 0.03);
            --accent: #0284c7;
            --accent-hover: #0369a1;
            --accent-bg: rgba(2, 132, 199, 0.08);
            --code-bg: #f1f5f9;
            --shadow-premium: 0 4px 30px rgba(0, 0, 0, 0.03);
        }}

        :root.dark {{
            /* Modo Oscuro */
            --bg-main: #07080d;
            --bg-sidebar: #0b0d16;
            --bg-card: #0f121d;
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --text-muted: #64748b;
            --border-color: rgba(255, 255, 255, 0.08);
            --border-subtle: rgba(255, 255, 255, 0.04);
            --accent: #38bdf8;
            --accent-hover: #7dd3fc;
            --accent-bg: rgba(56, 189, 248, 0.1);
            --code-bg: #030408;
            --shadow-premium: 0 4px 30px rgba(0, 0, 0, 0.4);
        }}

        body, aside, header, main, div, pre, code, a, input, button, select {{
            transition: background-color 0.25s ease, border-color 0.25s ease, color 0.2s ease, box-shadow 0.2s ease;
        }}

        /* Clases de Fuentes Selectables */
        .font-inter {{ font-family: 'Inter', sans-serif; }}
        .font-outfit {{ font-family: 'Outfit', sans-serif; }}
        .font-sora {{ font-family: 'Sora', sans-serif; }}
        .font-mono-tech {{ font-family: 'JetBrains Mono', monospace; }}
        .font-merriweather {{ font-family: 'Merriweather', serif; }}

        h1, h2, h3, h4, h5, h6, .outfit {{
            font-family: 'Outfit', sans-serif;
        }}
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: var(--bg-main);
        }}
        ::-webkit-scrollbar-thumb {{
            background: var(--border-color);
            border-radius: 10px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--accent);
        }}
        /* Estilos e inyecciones de animaciones Apple */
        .apple-reveal.revealed {{
            opacity: 1 !important;
            transform: translateY(0) !important;
        }}
        /* Estilos optimizados de Mermaid */
        .mermaid svg {{
            max-width: 100% !important;
            height: auto !important;
            background: transparent !important;
        }}
    </style>
    <!-- Mermaid.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body class="h-full text-themeSecText bg-themeBg flex flex-col antialiased font-inter">

    <!-- Header / Top Navbar (Apple style blur) -->
    <header class="bg-themeBg/80 backdrop-blur-md border-b border-themeBorder px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-400 via-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-base outfit shadow-lg shadow-indigo-500/20">
                {project_title[0]}
            </div>
            <div class="flex items-baseline gap-2">
                <span class="font-extrabold text-themeText outfit text-lg tracking-wide">{project_title}</span>
                <span id="active-indicator" class="text-xs text-themeAccent font-mono hidden md:inline-block border border-themeAccent/30 px-2 py-0.5 rounded-full bg-themeAccentBg outfit capitalize font-medium">Home</span>
            </div>
        </div>
        
        <div class="flex items-center gap-3">
            <!-- Selector de Fuentes -->
            <div class="relative flex items-center gap-1.5 bg-themeCodeBg border border-themeBorder rounded-lg px-2 py-1">
                <svg class="w-3.5 h-3.5 text-themeMuted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                <select id="font-selector" class="bg-transparent text-themeSecText hover:text-themeText text-xs font-semibold focus:outline-none cursor-pointer outfit">
                    <option value="font-inter">Inter (Sans)</option>
                    <option value="font-outfit">Outfit (Modern)</option>
                    <option value="font-sora">Sora (Tech)</option>
                    <option value="font-mono-tech">JetBrains Mono</option>
                    <option value="font-merriweather">Merriweather (Serif)</option>
                </select>
            </div>

            <!-- Botón de Modo Día/Noche -->
            <button id="theme-toggle-btn" class="p-2 rounded-lg text-themeSecText hover:text-themeText hover:bg-themeCard border border-themeBorder transition-colors flex items-center justify-center" title="Cambiar Tema (Día/Noche)">
                <!-- Icono Sol (se muestra en modo oscuro para ir a claro) -->
                <svg id="theme-icon-light" class="w-4 h-4 hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z"></path>
                </svg>
                <!-- Icono Luna (se muestra en modo claro para ir a oscuro) -->
                <svg id="theme-icon-dark" class="w-4 h-4 hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>
                </svg>
            </button>

            <a href="{project_url}" target="_blank" class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold text-themeSecText hover:text-themeText bg-themeCodeBg border border-themeBorder transition-all outfit">
                GitLab Repo
            </a>
            <button id="menu-btn" class="lg:hidden p-2 rounded-lg text-themeSecText hover:text-themeText hover:bg-themeCard transition-colors">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
            </button>
        </div>
    </header>
 
    <div class="flex flex-1 overflow-hidden relative">

        <!-- Sidebar / Navigation Menu -->
        <aside id="sidebar" class="fixed inset-y-0 left-0 z-40 w-72 bg-themeSidebar border-r border-themeBorder flex flex-col transform -translate-x-full lg:translate-x-0 lg:static transition-transform duration-300 ease-in-out">
            <!-- Sidebar Header (Desktop) -->
            <div class="hidden lg:flex items-center gap-3 px-6 py-5 border-b border-themeBorderSubtle">
                <div class="flex flex-col">
                    <span class="text-xs text-themeAccent font-extrabold tracking-widest uppercase outfit font-mono">Tabla de Contenidos</span>
                    <span class="text-[10px] text-themeMuted font-mono mt-0.5">Navegación Interactiva Scroll</span>
                </div>
            </div>
            
            <!-- Buscador en Sidebar -->
            <div class="px-5 py-4 border-b border-themeBorderSubtle">
                <div class="relative">
                    <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-themeMuted">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                    </span>
                    <input type="text" id="search-input" placeholder="Filtrar menú..." class="w-full pl-9 pr-4 py-2 text-sm bg-themeCodeBg border border-themeBorder rounded-xl focus:outline-none focus:border-themeAccent text-themeText placeholder-slate-500 transition-colors">
                </div>
            </div>

            <!-- Menú de Documentos -->
            <nav class="flex-1 overflow-y-auto px-4 py-4 space-y-1.5" id="nav-container">
                {sidebar_html}
            </nav>

            <!-- Sidebar Footer -->
            <div class="p-4 border-t border-themeBorder bg-themeSidebar">
                <a href="{project_url}" target="_blank" class="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-themeText bg-themeCodeBg border border-themeBorder hover:bg-themeCard transition-all outfit">
                    <svg class="w-4 h-4 text-orange-500" fill="currentColor" viewBox="0 0 24 24"><path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/></svg>
                    Ver Repositorio GitLab
                </a>
            </div>
        </aside>

        <!-- Overlay Móvil -->
        <div id="overlay" class="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-30 hidden lg:hidden"></div>

        <!-- Dot-Nav Flotante Derecho (Apple style) -->
        <div class="fixed right-6 top-1/2 transform -translate-y-1/2 z-40 hidden md:flex flex-col gap-3 bg-themeSidebar/60 backdrop-blur-md px-3 py-5 border border-themeBorder rounded-full shadow-lg">
            {dot_html}
        </div>

        <!-- Main Content Area -->
        <main class="flex-1 overflow-y-auto px-6 py-8 md:px-12 lg:px-16 bg-themeBg relative scroll-py-24" id="main-content">
            <div class="max-w-4xl mx-auto">
                <div class="space-y-12">
                    {all_sections_html}
                </div>
                
                <!-- Footer -->
                <footer class="mt-20 pt-8 border-t border-themeBorder text-xs text-themeMuted flex flex-col md:flex-row items-center justify-between gap-4">
                    <span>Generado automáticamente por el pipeline de GitLab Templates &bull; Enterprise CI/CD</span>
                    <span class="font-mono">Apple Showcase Portal &bull; {project_title}</span>
                </footer>
            </div>
        </main>
    </div>

    <script>
        // Hamburguer Menu Móvil
        const menuBtn = document.getElementById('menu-btn');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('overlay');

        function toggleMenu() {{
            sidebar.classList.toggle('-translate-x-full');
            overlay.classList.toggle('hidden');
        }}

        menuBtn.addEventListener('click', toggleMenu);
        overlay.addEventListener('click', toggleMenu);

        // Cerrar menú móvil al hacer clic en un link
        document.querySelectorAll('.nav-item').forEach(item => {{
            item.addEventListener('click', () => {{
                if (!sidebar.classList.contains('-translate-x-full')) {{
                    toggleMenu();
                }}
            }});
        }});

        // Búsqueda interactiva en Sidebar
        const searchInput = document.getElementById('search-input');
        const navContainer = document.getElementById('nav-container');
        const navItems = navContainer.querySelectorAll('.nav-item');

        searchInput.addEventListener('input', (e) => {{
            const term = e.target.value.toLowerCase().trim();
            navItems.forEach(item => {{
                const titleText = item.querySelector('span').textContent.toLowerCase();
                if (titleText.includes(term)) {{
                    item.style.display = 'flex';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }});

        // 🌟 SISTEMA INMERSIVO APPLE: IntersectionObserver (ScrollSpy y Animaciones de Revelado)
        const sections = document.querySelectorAll('section.apple-reveal');
        const sidebarItems = document.querySelectorAll('.nav-item');
        const dotItems = document.querySelectorAll('.dot-item');
        const activeIndicator = document.getElementById('active-indicator');

        const scrollContainer = document.getElementById('main-content');

        // Revelar la primera sección inmediatamente para evitar pantalla en blanco en la carga
        if (sections.length > 0) {{
            sections[0].classList.add('revealed');
        }}

        // Revelar sección del hash inicial
        const initialHash = window.location.hash;
        if (initialHash) {{
            const targetSec = document.querySelector(initialHash);
            if (targetSec) {{
                targetSec.classList.add('revealed');
            }}
        }}

        // Forzar revelado al hacer clic en enlaces de navegación
        function forceReveal(targetId) {{
            const targetSec = document.getElementById(targetId);
            if (targetSec) {{
                targetSec.classList.add('revealed');
            }}
        }}

        document.querySelectorAll('.nav-item, .dot-item').forEach(item => {{
            item.addEventListener('click', () => {{
                const href = item.getAttribute('href');
                if (href && href.startsWith('#')) {{
                    forceReveal(href.substring(1));
                }}
            }});
        }});

        // 1. Revelar elementos al hacer Scroll (Apple style Entrance Animations)
        const revealObserver = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.classList.add('revealed');
                }}
            }});
        }}, {{
            root: scrollContainer,
            threshold: 0.1,
            rootMargin: "0px 0px -50px 0px"
        }});

        sections.forEach(sec => revealObserver.observe(sec));

        // 2. ScrollSpy: Seguimiento del menú activo basado en scroll
        const scrollSpyObserver = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    const id = entry.target.getAttribute('id');
                    
                    // Actualizar Indicador del Header
                    const titleText = entry.target.querySelector('h1, h2')?.textContent || id;
                    if (activeIndicator) {{
                        activeIndicator.textContent = titleText;
                        activeIndicator.style.display = 'inline-block';
                    }}

                    // Actualizar Sidebar
                    sidebarItems.forEach(item => {{
                        if (item.getAttribute('data-section') === id) {{
                            item.classList.remove('text-themeMuted', 'hover:bg-themeCard');
                            item.classList.add('text-themeText', 'bg-gradient-to-r', 'from-themeAccent/10', 'to-themeAccent/5', 'border-l-2', 'border-themeAccent', 'bg-themeCard');
                        }} else {{
                            item.classList.add('text-themeMuted', 'hover:bg-themeCard');
                            item.classList.remove('text-themeText', 'bg-gradient-to-r', 'from-themeAccent/10', 'to-themeAccent/5', 'border-l-2', 'border-themeAccent', 'bg-themeCard');
                        }}
                    }});

                    // Actualizar Dot-Nav Derecho
                    dotItems.forEach(dot => {{
                        if (dot.getAttribute('data-dot') === id) {{
                            dot.classList.remove('bg-themeMuted', 'w-3', 'h-3');
                            dot.classList.add('bg-themeAccent', 'w-4', 'h-4', 'ring-4', 'ring-themeAccent/20');
                        }} else {{
                            dot.classList.add('bg-themeMuted', 'w-3', 'h-3');
                            dot.classList.remove('bg-themeAccent', 'w-4', 'h-4', 'ring-4', 'ring-themeAccent/20');
                        }}
                    }});
                }}
            }});
        }}, {{
            root: scrollContainer,
            threshold: 0.25,
            rootMargin: "-15% 0px -55% 0px"
        }});

        sections.forEach(sec => scrollSpyObserver.observe(sec));

        // --- SISTEMA DE TEMA (DÍA/NOCHE) ---
        const themeBtn = document.getElementById('theme-toggle-btn');
        const iconDark = document.getElementById('theme-icon-dark');
        const iconLight = document.getElementById('theme-icon-light');

        // Determinar tema inicial (por defecto oscuro como el diseño original)
        let currentTheme = localStorage.getItem('theme') || 'dark';

        function applyTheme(theme) {{
            if (theme === 'dark') {{
                document.documentElement.classList.add('dark');
                iconLight.classList.remove('hidden');
                iconDark.classList.add('hidden');
            }} else {{
                document.documentElement.classList.remove('dark');
                iconDark.classList.remove('hidden');
                iconLight.classList.add('hidden');
            }}
            localStorage.setItem('theme', theme);
            currentTheme = theme;
        }}

        themeBtn.addEventListener('click', () => {{
            applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
        }});

        // Aplicar tema inicial
        applyTheme(currentTheme);

        // --- SISTEMA DE TIPOGRAFÍA SELECCIONABLE ---
        const fontSelector = document.getElementById('font-selector');
        let currentFont = localStorage.getItem('selected-font') || 'font-inter';

        function applyFont(fontClass) {{
            // Quitar clases anteriores
            document.body.classList.remove('font-inter', 'font-outfit', 'font-sora', 'font-mono-tech', 'font-merriweather');
            document.body.classList.add(fontClass);
            fontSelector.value = fontClass;
            localStorage.setItem('selected-font', fontClass);
            currentFont = fontClass;
        }}

        fontSelector.addEventListener('change', (e) => {{
            applyFont(e.target.value);
        }});

        // Aplicar fuente inicial
        applyFont(currentFont);

        // 📊 Inicializar Mermaid con tema adaptativo
        if (typeof mermaid !== 'undefined') {{
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'dark',
                themeVariables: {{
                    background: '#07080d',
                    primaryColor: '#1e293b',
                    primaryTextColor: '#cbd5e1',
                    primaryBorderColor: '#334155',
                    lineColor: '#64748b',
                    secondaryColor: '#0f172a',
                    tertiaryColor: '#1e1b4b'
                }}
            }});
        }}
    </script>
</body>
</html>
'''
    
    # Escribir la única página index.html
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.write(html_page)
        
    print("✅ Compilación inmersiva estática finalizada. Todo el contenido está consolidado en 'public/index.html'.")

if __name__ == '__main__':
    main()

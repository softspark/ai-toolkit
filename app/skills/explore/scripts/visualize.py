#!/usr/bin/env python3
"""Generate an interactive collapsible tree visualization of a codebase.

Usage: python visualize.py [directory]
Output: codebase-map.html (opened in browser)
"""

import json
import sys
import webbrowser
from pathlib import Path
from collections import Counter

IGNORE = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next', '.nuxt', '.cache', 'vendor', '.dart_tool'}

def scan(path: Path, stats: dict) -> dict:
    result = {"name": path.name, "children": [], "size": 0}
    try:
        for item in sorted(path.iterdir()):
            if item.name in IGNORE or item.name.startswith('.'):
                continue
            if item.is_file():
                size = item.stat().st_size
                ext = item.suffix.lower() or '(no ext)'
                result["children"].append({"name": item.name, "size": size, "ext": ext})
                result["size"] += size
                stats["files"] += 1
                stats["extensions"][ext] += 1
                stats["ext_sizes"][ext] += size
            elif item.is_dir():
                stats["dirs"] += 1
                child = scan(item, stats)
                if child["children"]:
                    result["children"].append(child)
                    result["size"] += child["size"]
    except PermissionError:
        pass
    return result

def fmt(b):
    if b < 1024: return f"{b} B"
    if b < 1048576: return f"{b/1024:.1f} KB"
    return f"{b/1048576:.1f} MB"

def generate_html(data: dict, stats: dict, output: Path) -> None:
    ext_sizes = stats["ext_sizes"]
    total_size = sum(ext_sizes.values()) or 1
    sorted_exts = sorted(ext_sizes.items(), key=lambda x: -x[1])[:8]
    colors = {
        '.js': '#f7df1e', '.ts': '#3178c6', '.py': '#3776ab', '.go': '#00add8',
        '.rs': '#dea584', '.rb': '#cc342d', '.css': '#264de4', '.html': '#e34c26',
        '.json': '#6b7280', '.md': '#083fa1', '.yaml': '#cb171e', '.yml': '#cb171e',
        '.tsx': '#3178c6', '.jsx': '#61dafb', '.sh': '#4eaa25', '.dart': '#0175c2',
        '.php': '#777bb4', '.vue': '#42b883', '.svelte': '#ff3e00',
    }
    lang_bars = "".join(
        f'<div class="bar-row"><span class="bar-label">{ext}</span>'
        f'<div class="bar" style="width:{(size/total_size)*100}%;background:{colors.get(ext,"#6b7280")}"></div>'
        f'<span class="bar-pct">{(size/total_size)*100:.1f}%</span></div>'
        for ext, size in sorted_exts
    )
    html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Codebase Explorer</title>
<style>
body {{ font: 14px/1.5 system-ui, sans-serif; margin: 0; background: #1a1a2e; color: #eee; }}
.container {{ display: flex; height: 100vh; }}
.sidebar {{ width: 280px; background: #252542; padding: 20px; border-right: 1px solid #3d3d5c; overflow-y: auto; flex-shrink: 0; }}
.main {{ flex: 1; padding: 20px; overflow-y: auto; }}
h1 {{ margin: 0 0 10px; font-size: 18px; }} h2 {{ margin: 20px 0 10px; font-size: 14px; color: #888; text-transform: uppercase; }}
.stat {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #3d3d5c; }}
.stat-value {{ font-weight: bold; }}
.bar-row {{ display: flex; align-items: center; margin: 6px 0; }}
.bar-label {{ width: 55px; font-size: 12px; color: #aaa; }}
.bar {{ height: 18px; border-radius: 3px; }} .bar-pct {{ margin-left: 8px; font-size: 12px; color: #666; }}
.tree {{ list-style: none; padding-left: 20px; }}
details {{ cursor: pointer; }} summary {{ padding: 4px 8px; border-radius: 4px; }}
summary:hover {{ background: #2d2d44; }} .folder {{ color: #ffd700; }}
.file {{ display: flex; align-items: center; padding: 4px 8px; border-radius: 4px; }}
.file:hover {{ background: #2d2d44; }} .size {{ color: #888; margin-left: auto; font-size: 12px; }}
.dot {{ width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; display: inline-block; }}
</style></head><body>
<div class="container">
<div class="sidebar">
<h1>Summary</h1>
<div class="stat"><span>Files</span><span class="stat-value">{stats["files"]:,}</span></div>
<div class="stat"><span>Directories</span><span class="stat-value">{stats["dirs"]:,}</span></div>
<div class="stat"><span>Total size</span><span class="stat-value">{fmt(data["size"])}</span></div>
<div class="stat"><span>File types</span><span class="stat-value">{len(stats["extensions"])}</span></div>
<h2>By file type</h2>{lang_bars}
</div>
<div class="main"><h1>{data["name"]}</h1><ul class="tree" id="root"></ul></div>
</div>
<script>
const data={json.dumps(data)};const colors={json.dumps(colors)};
function fmt(b){{if(b<1024)return b+' B';if(b<1048576)return(b/1024).toFixed(1)+' KB';return(b/1048576).toFixed(1)+' MB';}}
function render(n,p){{if(n.children){{const d=document.createElement('details');d.open=p===document.getElementById('root');
d.innerHTML=`<summary><span class="folder">${{n.name}}</span><span class="size">${{fmt(n.size)}}</span></summary>`;
const u=document.createElement('ul');u.className='tree';n.children.sort((a,b)=>(b.children?1:0)-(a.children?1:0)||a.name.localeCompare(b.name));
n.children.forEach(c=>render(c,u));d.appendChild(u);const l=document.createElement('li');l.appendChild(d);p.appendChild(l);
}}else{{const l=document.createElement('li');l.className='file';
l.innerHTML=`<span class="dot" style="background:${{colors[n.ext]||'#6b7280'}}"></span>${{n.name}}<span class="size">${{fmt(n.size)}}</span>`;
p.appendChild(l);}}}}
data.children.forEach(c=>render(c,document.getElementById('root')));
</script></body></html>'''
    output.write_text(html)

if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    stats = {"files": 0, "dirs": 0, "extensions": Counter(), "ext_sizes": Counter()}
    data = scan(target, stats)
    out = Path('codebase-map.html')
    generate_html(data, stats, out)
    print(f'Generated {out.absolute()}')
    try:
        webbrowser.open(f'file://{out.absolute()}')
    except Exception:
        pass

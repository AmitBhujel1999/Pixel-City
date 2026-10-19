#!/usr/bin/env python3
"""Build the PC version of Pixel's City: one .html file that opens by double-click.

Browsers block reading models.bin from a page opened as a file (file://), so the PC
copy carries models.bin inside itself as base64 text, and three.min.js inline.
Phones keep using www/index.html + www/models.bin (much less memory).

    python3 tools/pc_build.py [out.html]      (default: Pixel's City.html in the repo root)
"""
import base64, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WWW = os.path.join(ROOT, 'www')
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "Pixel's City.html")

html = open(os.path.join(WWW, 'index.html'), encoding='utf8').read()
three = open(os.path.join(WWW, 'three.min.js'), encoding='utf8').read()
models = base64.b64encode(open(os.path.join(WWW, 'models.bin'), 'rb').read()).decode('ascii')

tag = '<script src="three.min.js"></script>'
assert html.count(tag) == 1, 'three.min.js script tag not found'
html = html.replace(tag, '<script>' + three.replace('</script', '<\\/script') + '</script>')

fetch = "fetch('models.bin')"
assert html.count(fetch) == 1, 'models.bin loader not found'
# decode the inline copy instead of fetching; the base64 text is dropped once decoded
inline = ("(window.PC_BIN_B64?new Promise(function(ok){var s=atob(window.PC_BIN_B64),n=s.length,u=new Uint8Array(n);"
          "for(var i=0;i<n;i++)u[i]=s.charCodeAt(i);window.PC_BIN_B64=null;ok({ok:true,arrayBuffer:function(){return u.buffer}})}):"
          + fetch + ")")
html = html.replace(fetch, inline)

loader = '<script>/* the 3D models are in models.bin'
assert html.count(loader) == 1, 'loader script not found'
html = html.replace(loader, '<script>window.PC_BIN_B64="' + models + '"</script>\n' + loader)

with open(out, 'w', encoding='utf8', newline='\n') as f:
    f.write(html)
print('wrote', out, round(len(html) / 1e6, 1), 'MB')

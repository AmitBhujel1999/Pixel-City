#!/usr/bin/env python3
"""The game's 3D models (.glb files) live in www/models.bin, one binary file, next to www/index.html.

In index.html the line between /*PC_MODELS_START*/ and /*PC_MODELS_END*/ that starts with `const PC_MODELS=`
says where each model sits in models.bin: {name:[offset,length],...}. The page loads models.bin before the game
starts (window.PC_BIN), and glbParts() reads a model from it the first time it is needed.

Before, every model was written into index.html as base64 text (about 40 MB). Phones kept that text in memory
twice (the page's script and the strings), about 120 MB, which helped crash the app on big cities.

    python3 tools/models.py list                     names and sizes
    python3 tools/models.py add NAME file.glb        add a model, or replace the one with that name
    python3 tools/models.py remove NAME              take a model out
    python3 tools/models.py get NAME out.glb         write one model to a .glb file
    python3 tools/models.py pack                     one time only: move base64 models out of index.html

`add` also accepts a base64 string file (ending .b64 or .txt) in place of a .glb.
"""
import base64, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'www', 'index.html')
BIN = os.path.join(ROOT, 'www', 'models.bin')
# the index object only: base64 text and [offset,length] pairs never contain '}', and other constants may follow on
# the same line (PC_WHEELS does)
LINE = re.compile(r'^const PC_MODELS=(\{[^}]*\});', re.M)


def read_page():
    with open(PAGE, encoding='utf-8') as f:
        return f.read()


def write_page(s):
    with open(PAGE, 'w', encoding='utf-8') as f:
        f.write(s)


def index_line(s):
    m = LINE.search(s)
    if not m:
        sys.exit('No "const PC_MODELS={...};" line found in www/index.html')
    return m


def load():
    """the models as {name: bytes}, in file order"""
    s = read_page()
    body = index_line(s).group(1)
    if '"' in body[:200] and not re.match(r'^\{\s*"?[\w$]+"?\s*:\s*\[', body):
        sys.exit('index.html still has base64 models; run: python3 tools/models.py pack')
    idx = json.loads(re.sub(r'([{,])([\w$]+):', r'\1"\2":', body))
    data = open(BIN, 'rb').read() if os.path.exists(BIN) else b''
    return {k: data[o:o + n] for k, (o, n) in idx.items()}


def save(models):
    """write models.bin (each model 4-byte aligned) and the index line"""
    out, idx = bytearray(), {}
    for k, b in models.items():
        out += b'\0' * (-len(out) % 4)
        idx[k] = [len(out), len(b)]
        out += b
    with open(BIN, 'wb') as f:
        f.write(out)
    s = read_page()
    m = index_line(s)
    line = 'const PC_MODELS={' + ','.join(f'{k}:[{o},{n}]' for k, (o, n) in idx.items()) + '};'
    write_page(s[:m.start()] + line + s[m.end():])
    print(f'models.bin: {len(models)} models, {len(out) / 1048576:.1f} MB')


def pack():
    s = read_page()
    m = index_line(s)
    pairs = re.findall(r'([\w$]+):"([A-Za-z0-9+/=]*)"', m.group(1))
    if not pairs:
        sys.exit('PC_MODELS has no base64 models in it; already packed?')
    models = {k: base64.b64decode(v) for k, v in pairs}
    # glbParts: read the model from models.bin instead of decoding base64 text
    old = 'const bin=Uint8Array.from(atob(PC_MODELS[name]),c=>c.charCodeAt(0)),dv=new DataView(bin.buffer);'
    new = 'const e_=PC_MODELS[name],bin=new Uint8Array(PC_BIN.slice(e_[0],e_[0]+e_[1])),dv=new DataView(bin.buffer);'
    if s.count(old) != 1:
        sys.exit('glbParts decode line not found')
    s = s.replace(old, new)
    # the game script waits for models.bin: it is kept as text and started by a small loader once the file is in
    main_open = '<script src="three.min.js"></script>\n<script>'
    if s.count(main_open) != 1:
        sys.exit('main game <script> not found')
    s = s.replace(main_open, '<script src="three.min.js"></script>\n<script type="text/x-pc-game" id="pcGame">')
    close = s.index('</script>', s.index('id="pcGame"'))
    loader = r'''</script>
<script>/* the 3D models are in models.bin next to this page (tools/models.py); the game starts once it has loaded */
(function(){function fail(e){var l=document.getElementById('loadScr');if(l)l.remove();var d=document.createElement('div');d.style.cssText='position:fixed;left:16px;right:16px;top:40%;padding:16px;background:#141b24;color:#ffb4ab;font:14px/1.5 system-ui,sans-serif;border-radius:12px;z-index:99';
  d.textContent='The game could not load its 3D models ('+(e&&e.message||e)+'). Close the app and open it again.';document.body.appendChild(d)}
function run(b){window.PC_BIN=b;var g=document.getElementById('pcGame'),s=document.createElement('script');s.text=g.text;g.parentNode.removeChild(g);document.body.appendChild(s)}
function xhr(){return new Promise(function(ok,no){var x=new XMLHttpRequest();x.open('GET','models.bin');x.responseType='arraybuffer';x.onload=function(){x.response&&x.response.byteLength?ok(x.response):no(new Error('models.bin is empty'))};x.onerror=function(){no(new Error('models.bin did not load'))};x.send()})}
fetch('models.bin').then(function(r){if(!r.ok)throw new Error('models.bin: '+r.status);return r.arrayBuffer()}).catch(xhr).then(run).catch(fail)})();
'''
    s = s[:close] + loader + s[close:]
    m = index_line(s)
    s = s[:m.start()] + 'const PC_MODELS={};\n' + s[m.end():]
    write_page(s)
    save(models)


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help', 'help'):
        print(__doc__)
        return
    cmd = a[0]
    if cmd == 'pack':
        pack()
    elif cmd == 'list':
        for k, b in load().items():
            print(f'{len(b) / 1024:9.1f} KB  {k}')
    elif cmd == 'add' and len(a) == 3:
        name, path = a[1], a[2]
        if not re.match(r'^[A-Za-z_$][\w$]*$', name):
            sys.exit('model names are letters, digits and _ (not starting with a digit)')
        raw = open(path, 'rb').read()
        if path.endswith(('.b64', '.txt')):
            raw = base64.b64decode(raw.strip())
        if raw[:4] != b'glTF':
            sys.exit(f'{path} is not a binary glTF (.glb) file')
        models = load()
        print(('replaced ' if name in models else 'added ') + name)
        models[name] = raw
        save(models)
    elif cmd == 'remove' and len(a) == 2:
        models = load()
        if models.pop(a[1], None) is None:
            sys.exit(f'no model called {a[1]}')
        save(models)
    elif cmd == 'get' and len(a) == 3:
        models = load()
        if a[1] not in models:
            sys.exit(f'no model called {a[1]}')
        open(a[2], 'wb').write(models[a[1]])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()

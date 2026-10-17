# Put the Firebase web config into the game and the owner page.
# usage: python cloud/set_config.py <apiKey> <projectId>
# Updates www/index.html, ~/Downloads/Pixel's City.html, cloud/owner/index.html and cloud/.firebaserc.
import re, sys, pathlib

key, pid = sys.argv[1], sys.argv[2]
assert re.fullmatch(r'[A-Za-z0-9_-]{20,60}', key), 'apiKey looks wrong'
assert re.fullmatch(r'[a-z0-9-]{4,40}', pid), 'projectId looks wrong'
here = pathlib.Path(__file__).resolve().parent
game_line = re.compile(r"const PC_CLOUD=\{apiKey:'[^']*',projectId:'[^']*'\};")
new_game = f"const PC_CLOUD={{apiKey:'{key}',projectId:'{pid}'}};"
for f in [here.parent / 'www' / 'index.html', pathlib.Path.home() / 'Downloads' / "Pixel's City.html"]:
    b = f.read_bytes().decode('utf-8')
    assert len(game_line.findall(b)) == 1, f
    f.write_bytes(game_line.sub(new_game, b).encode('utf-8'))
    print('game', f)
owner = here / 'owner' / 'index.html'
s = owner.read_text(encoding='utf-8')
owner_line = re.compile(r"const FIREBASE_CONFIG = \{[^}]*\};")
assert len(owner_line.findall(s)) == 1
s = owner_line.sub(f"const FIREBASE_CONFIG = {{apiKey:'{key}',authDomain:'{pid}.firebaseapp.com',projectId:'{pid}'}};", s)
owner.write_text(s, encoding='utf-8', newline='\n')
(here / '.firebaserc').write_text('{ "projects": { "default": "%s" } }\n' % pid)
print('owner page + .firebaserc ->', pid)

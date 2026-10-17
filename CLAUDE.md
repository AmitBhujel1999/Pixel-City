# Pixel's City

The whole game is `www/index.html` (three.js r128 in `www/three.min.js`). Capacitor wraps `www/` as the Android app
(`.github/workflows/main.yml`) and the iPhone app (`.github/workflows/ios.yml`).

## 3D models are in `www/models.bin`, not in index.html

The .glb models used to be base64 text inside index.html (about 40 MB). Phones kept that text in memory twice, which
helped crash the app. They now live in one binary file, `www/models.bin`:

- The line `const PC_MODELS={name:[offset,length],...};` (between `/*PC_MODELS_START*/` and `/*PC_MODELS_END*/`)
  says where each model is. Code checks `PC_MODELS[name]` to see if a model exists; `glbParts(name)` reads it.
- The main game `<script>` has `type="text/x-pc-game"`. A small loader after it fetches `models.bin` into
  `window.PC_BIN`, then starts the game script.
- Never paste base64 models into index.html again. Use the tool:

```
python3 tools/models.py add NAME file.glb     # add or replace (also takes a .b64/.txt base64 file)
python3 tools/models.py remove NAME
python3 tools/models.py list
python3 tools/models.py get NAME out.glb
```

## Phones: memory rules

The app crashes (Android) or the picture goes white under the menus (iPhone) when the web view runs out of memory.

- Merged building meshes (`meshesFrom`) store normals and colours as bytes and drop their arrays once uploaded to the
  graphics chip (`meshFreeArr`). Each tile keeps its baked data (`tile.bk`) to rebuild a chunk from.
- Do not size buffers for the whole map (720 × 720 = 518,400 tiles) when only a few are used: grow them on demand
  (see `setHL`).
- If the graphics are lost (`webglcontextlost`), the game saves and reopens the city one graphics step lower.
- `frame()` is wrapped so an error in one frame never stops the next one.

Measure with the game running in headless Chromium (Playwright, phone viewport, `performance.memory`) before and
after a change that adds geometry or textures.

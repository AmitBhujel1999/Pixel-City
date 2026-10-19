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

## PC version (one file)

Browsers block `models.bin` when the page is opened as a file (double-click), so PC players get one .html with the
models and three.js inside: `python3 tools/pc_build.py "out.html"`. Build it from `www/` after every change; never
edit the PC file by hand.

## Smooth on slow devices

- Building LOD: each 8 × 8 chunk (`chunkLod`) is flat parts (roads, ground; always drawn), tall parts (shadow casters)
  and a simplified copy of the tall parts (`chunkLo`, `userData.lo`): vertices snapped to a `LODC` grid (0.16 phone,
  0.1 PC), collapsed triangles dropped, one draw call with `lodMat` (window grid + night lights). `chunkCull` shows the
  copy when the chunk is farther than `BLOD * drawK` (30 phone / 70 PC). Looks the same as full detail from there.
  Plain boxes were tried first and rejected by the user: far buildings must keep their shapes, colours and windows.
- `drawK` (0.5-1): when frames stay slow after the pixel ratio is already 1, `frame()` lowers it by 0.1 (fog and
  chunk culling come closer, LOD distance shrinks); it creeps back up by 0.05 after 10 s of smooth frames.

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

## Roads and river sit in the land

- Roads stand 0.06 (sidewalks 0.075) above the ground; every logic height (cars, `surfY`) assumes that, so the road is
  not lowered. Instead a grass verge (`VERGE` colour) slopes from the road's outer edge down to the ground: in
  `netRoadStrip` for network roads and in the `T.ROAD` case of `buildTile` for tile roads (open sides only).
- The river water is at `WLV` (-0.18, about 2.7 m down) with a channel mesh (grass edge, earth bank, mud, bed). The flat
  ground plane is cut away over the channel in `groundMat`'s shader (riverZ table in a float texture), and the outer
  landscape mesh, which lies just under the whole map, is pushed down to -0.6 there. Boats float at `WLV`; bridge piers
  reach -0.3.

## Road types (Cities: Skylines style)

- Each road segment keeps its base type `t` (0 street, 1 dirt, 2 one-way, 3 avenue, 4 boulevard, 5 highway); tiles
  under it keep `l = t`, so all older rules (zoning, speed table, upkeep, grid code) still see the base type.
- Variants add a look `sg.w` and options `sg.o` (saved inside `G.net`, old saves have neither): looks 10 highway ramp,
  11 alley, 12 pedestrian street, 13 one-way avenue, 14 one-way boulevard, 15 one-way highway, 16 avenue 2+1; options
  `tr` trees, `gr` grass, `bus` bus lanes, `bike` bike lanes, `nb` sound barriers. `NETW` / `NETLN` have entries for
  the look ids; drawing code gets `v = netLk(sg)` (look, or type). One-way looks are in `NETOWL`, highway looks in
  `NETHWL`; `netOW(sg)` decides one-way links (`NET.OW`).
- `NET.lk` maps tile to its segment for segments with a look or options; `NETBUS` / `NETPED` hold bus-lane and
  pedestrian-street tiles. Bus lanes: residents' routes avoid the kerb slot (`rLaneCost`), buses and cars on a bus-lane
  tile do not queue behind each other. Pedestrian streets cost 3 in the car route search (6 for agents), speed x0.35.
- Menu cards come from `ROADP` (road_types block before boot); `setRoadPreset(id)` sets `tool.rt` (base) and
  `tool.rp`; `netPresetLook(tl,base)` stamps `w`/`o` on new segments (only if the base matches, so code that builds
  ramps with `tl.rt=2` does not inherit a picked look); the variant's extra cost is added in the `netPlan` wrapper.
- Segment splits must copy the look: use `netLookOf(sg)` wherever a segment is cut in two.
- Upgrade / Reverse on network roads work per segment in the `apply` wrapper of road_types.
- Traffic noise: highways 80 (25 with barriers), boulevards 55, avenues 45, trees -20, grass -10; keep road noise
  below 90, which caps homes at level 2.

## Smooth on slow devices

- Building LOD: each 8 × 8 chunk (`chunkLod`) is flat parts (roads, ground; always drawn), tall parts (shadow casters)
  and a simplified copy of the tall parts (`chunkLo`, `userData.lo`): vertices snapped to a `LODC` grid (0.16 phone,
  0.06 PC), collapsed triangles dropped, one draw call with `lodMat` (window grid + night lights). `chunkCull` shows the
  copy when the chunk is farther than `blod()` (phones 30 × `drawK`; PC by graphics setting: Low 70, Normal 140,
  Ultra never; user saw the swap as buildings "loading from box to shape" while zooming), with a ±10% band so a chunk does not
  flip back and forth (`chunkFar(ci,cur)`). The copy must match the full model's brightness, or every swap shows as a
  flicker while zooming (user report 2026-10-20): the window grid only darkens window cells a little, and glass is
  lifted slightly because the snapping drops the light frames between panes. Looks the same as full detail from there.
  Plain boxes were tried first and rejected by the user: far buildings must keep their shapes, colours and windows.
- `drawK` (0.5-1): when frames stay slow after the pixel ratio is already 1, `frame()` lowers it by 0.1 (fog and
  chunk culling come closer, LOD distance shrinks on phones only); it creeps back up by 0.05 after 10 s of smooth frames.

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
- Boats float on the water grid level (`watLevelAt`), hidden where the river is blocked; bridge piers reach -0.3.

## Water: one simulated grid for river, sea, lakes and dug channels

- Per tile corner (`TN` x `TN`, in `WAT`): `B` dug bed height (absolute, `WNONE` = natural ground; only ever below
  `TC`), `G = min(B, TC)`, `D` water depth. Buildings, roads and bridges keep using `TC`, so nothing on them moves;
  only the ground mesh (`terrGround` lowers its vertices by `G - TC`) and the water use the bed. The drawn river and
  sea (`watBase`, from `riverZ` / `seaW`) are the starting bed; edits are saved as `G.wb`, tiles that turned water/land
  as `G.wt` (read by `inRiverBand`, which is the drawn band XOR `G.wt`; `inRiverBand0` is the drawn band only).
- `watStep` is a virtual-pipes shallow-water model (dt = 1): river comes in at the west edge (`FX` 2, inflow `WAT.Q`),
  leaves at the east edge (`FX` 1, fixed level `wLev(x)`, which falls `WDROP` across the map); the sea's deep water
  and edge are fixed level; other edges drain (`FX` 3). Water on land (`G > -0.005`) flows without momentum (no
  damping term, slower) and soaks away (`WSOAK`), so a dammed river spills over the land as a growing flood instead of
  a thin sheet over the whole valley. Only moving corners are in the active list `AL`; `watPrune` drops still ones and
  the sim sleeps when nothing changes (zero cost). The river's steady flow is solved directly at load (`watSteady`).
- Measure sim speed in node, not through the test harness: the harness's `eval` hook makes the game code ~9x slower
  (about 12 ns per active corner per step in real Chrome).
- Water is drawn per 40 x 40 chunk (`watChunk`) with `WMAT` (depth `aD`, current `aF`, land flood flag `aM`): flow-
  mapped ripples, depth colour, Fresnel sky, sun glitter, shore / fast-water / surf foam, muddy flood water over land.
  The outside river ribbons use the same material. Ground shader (`groundWater`): sand where the land dips toward
  the water, darker wet bed, caustics under water.
- Land tool water modes `dig` / `fill` / `beach` (`watBrush`; also in flat cities, where hills modes stay hidden):
  only empty land, trees and water; filling under water pushes the water out over the rim (a small wave). `watSync`
  (1 s) turns land under water into `T.RIVER` and drained edited water back into land; buildings standing in water
  give a "Water is spilling onto the land" notice. Tiles with a dug dip that is dry take no buildings (`watDug`).

## Branch rivers and waterfalls

- New river cities save `G.trib = 1`; the page decides at load like `RIVW` (`TRIB`, `trOf(id)`; `openCity` /
  `foundCity` reload when it differs), so old saves keep their map. `TRDEF` holds the courses (three side rivers and a
  creek joining one of them); `tribBuild` resamples them into `TRP` and stamps `TRE` (distance to the nearest side
  river edge, map + 128-tile margin) and `TRI`. `trE` feeds `inRiverBand0`, the water bed (`trBed` in `watBase`), the
  hill blending (`rivEdge`) and the scenery outside (`trLand`: valley floor, then a cliff at the source).
- Water enters at every map-edge corner that has water except the east end of the main river (`FX` 2).
- Mountain bay (`TRSC`) has its own `TRDEF`: two rivers from the northern mountains and a creek, ending out in the sea
  (`end`), widening into estuaries. With rivers, every non-river sea corner is fixed level (`FX` 1) and only the rivers
  are simulated. River corners in a sea map carry `aM = -1` so the water shader leaves out swell and surf there.
- Outside the map: stream ribbons (WMAT), a waterfall mesh per source (`fallMat`) and spray points (`tribTick`).

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

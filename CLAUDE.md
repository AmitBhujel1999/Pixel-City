# Cityloom: A City Builder (was Pixel's City)

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

## Map size: 480 for new cities, 720 for old ones

- `AREA` is picked at page load (`areaBoot`): new cities 160-tile areas (3 x 3 = 480 tiles, 7.2 km); cities saved on
  240-tile areas (v7 save with `N` 720 or 1200) keep them (`saveArea(o)`, `cityArea(id)`). `openCity` / `foundCity`
  reload the page when the size differs, like hills. `load` refuses a v7 save of the other area size.
- River, highway and start area are anchored to the start area (`XS`), so they scale with `AREA`; check any new
  scenery placed at absolute world positions on both sizes.

## Northern sound scenario (`sound`)

- `SC.sea==='sound'`: `soundW(x,z)` (x from the start area's centre; map x -80..400) puts a noisy oval island inside the
  map so sea fills the corners and edges (no square edge). `SND`: `ways` (wide fjord from the south splitting into three
  channels north, plus short inlets; polylines with half widths, `sndWay`), `bays`, `lakes`, `isles`. The middle of the
  start area and the highway line stay dry. No branch rivers (not in `TRSC`); all water is sea level.
- Mild green climate, `forest:1`, `ferry:1` (no highway, like the island: a harbour bay is cut right outside the west
  edge at the dock). Listed in `SCLIST`. Hills (ticked by default) use `sndHills` (ridged noise, strongest east of the
  fjord) instead of `farRaw`, a steeper slope cap in `farSmooth` (0.42 instead of `FARSL`) and no border hill band.

## Map view

- `#mapBtn` (top left, under the cinematic button): `mapView(on)` saves the camera, shows the whole map from about
  1.1 x N away at a tilt (`MAPVIEW` raises the zoom limit like `AREAMODE`), hides the locked-area shade, cancels the
  intro glide. Tap again or Esc to return.

## Riverbend scenery is open on two sides

- `openSide(x,z)` (classic and rich only): past the east and south map edges `terrainH` drops the mountains and
  keeps low rolling farmland to the horizon; mountains stay north and west. Scenery only, buildable land unchanged.

## Roads and river sit in the land

- Roads stand 0.06 (sidewalks 0.075) above the ground; every logic height (cars, `surfY`) assumes that, so the road is
  not lowered. Instead a grass verge (`VERGE` colour) slopes from the road's outer edge down to the ground: in
  `netRoadStrip` for network roads and in the `T.ROAD` case of `buildTile` for tile roads (open sides only).
  Network verges (0.2 wide) use `groundMat` with world-mapped uv (`netGroundUV`), not the flat `VERGE` colour: the
  dark flat strip read as a wall under a floating road (user report 2026-10-27).
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

- Water over land (patch_waterflow): land water keeps its current (`WLDAMP`), only thin sheets (< 0.02) soak away
  fast, so streams and lakes stay. Muddy colour only on thin sheets (`mud` in WMAT). Fast water on free land wears its
  bed down (`watErode` in `watPrune`, rate `WERO`, at most `WERMAX` below the land, never on the drawn river), so its
  path becomes a river channel that is saved in `G.wb`.
- Water sources: Land tool mode `spring` (`watSpring`; brush size picks the flow `WSQ`, max `WSMAX` 12, tap again to
  remove for half the price). `WSRC` [{k corner, q flow per step}], `WSF` flags, stone ring markers in `WSG`; saved as
  `G.ws` "corner:flow*1e5;..." with `G.wsN`. Water is not saved, so `wsLoad` runs the sim ~300 ms at load.
- Freezing: corners whose depth changed < 2e-7 for 48 steps freeze (`FZ`, skip the step, keep their pipes); a change
  > 5e-6 wakes the four neighbours, `wAct` wakes the corner. After load every river corner starts frozen.

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

## Bridges

- `netLift` raises road decks by crossing length (0.1 up to 0.42, `g.wl` wet length, `g.lift`), ramps up to 4 tiles but
  never past the segment ends (junctions stay on the ground). Rail keeps 0.16.
- Superstructures (`brInfo` per geo: water span s0..s1 at full lift, style `sg.o.br` or auto by length: beam < 3.5,
  arch < 7, cable-stayed < 14, suspension; curved spans fall back to beam) are one merged vertex-coloured mesh `BRG`,
  rebuilt in a `netRebuild` wrapper (`brBuild`, `beam(a,c,w,h,colour)` boxes). Arch >= 5 tiles per arch is a tied arch
  over the road, shorter ones sit under the deck. `netBridge` leaves out its plain piers inside non-beam spans.
- Road tool Bridge row (`BRSTY`, `NB.br`), stamped on new segments as `sg.o.br` (copied on splits with the look).

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
- Highway (`v === 5`, ground level, outside junction areas) is a split highway: grass median ±0.13 with gravel edges,
  carriageways 0.13-0.71, gravel shoulders to 0.8; lanes `NETLN[5]` = 0.29 / 0.55 and `laneOf` returns those on network
  tiles (`netOn`), old tile highways keep 0.13 / 0.33. `netHwyDecor`: tall lamps (prop_streetlight x1.55) alternating
  shoulders every 2, light pools, names painted every 7 from one text atlas (`HWYNAME`, `ST_N` + ' Highway').
  Elevated / bridge highways keep the older look.
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

## Realism pass (2026-10-28, user: "something is not feeling realistic")

- Ground shader (second `groundMat.onBeforeCompile` wrapper, cache key `groundWater2`): world-noise meadow / dry /
  lush patches at three scales, saturation 0.74; outer landscape vertex colours get the same treatment.
- Zone growth infill (`zSpawn`): 75% of new buildings go beside a standing one. Floors capped by population
  (3 floors under 600 people ... no cap from 25,000).
- Lot yards `zYards()` (rebuilt in `zInstBuild`): paved / gravel plots to the back of the zone for shops, offices,
  industry (with fence); homes keep the lawn with low hedge strips. Hedges are horizontal strips: vertical
  double-sided quads went black.
- Outer landscape smooth-shaded (was flat low-poly facets). Non-forest maps: woods from noise with ragged edges,
  hedgerows on warped field borders (`landTree`), no more periodic round clumps.
- Clouds: `renderOrder` 20 so they draw after the (transparent) water; with -1 the water painted over them and only
  land looked clouded. Opacity fades as the camera rises into the layer (y 60-140) and is 0.35 in Map view.
- Light: sun 0.8, sky fill 0.36-0.46 (more shadow contrast). River beaches uneven (low-freq noise in the sand edge).

## Free starter roads

- `hwFree()` (cached on `netVer` + `G.hw.b`): tiles of the starter highway pieces (`hwLay`), its ramps and starter
  street (`hwRamps`: segments among the ramp nodes, junction and `G.hw.gn`) and the entry stub. `stats` skips their
  upkeep; before this a new Riverbend city paid $552 a month for a highway the player never built (user report).

## Dual starting highway (new cities, `G.hw.d`)

- New cities get two one-way highways (look 15) `HWD` 1.4 either side of the route line instead of one two-way
  highway: eastbound on the +z (river) side, westbound on the city side (traffic keeps right). `hwOff(p,s)` gives the
  carriageway point; the westbound side swings out by up to `HWB` near the interchange (`hwBump`, `hwW`). Old cities
  (no `d`) keep the old two-way highway and ramps.
- Piece 0 (west entry to the split node `x0+HWSPL`) stays two-way. Piece 1 forks at about 55 degrees: at a smaller
  angle the opposite one-ways share tiles after the fork and the tile path (`bfs`) is cut.
- The carriageways must not share tiles anywhere (netPlan "runs along another road too closely"), hence the 1.2 tile
  median.
- Interchange (`hwRampsD`, ramp nodes at `xi +- HWRO`): frontage street JW-M-JE, starter street from M (glowing end).
  Westbound ramps leave and join on the right. Eastbound ramps drop into the wide median on the ground (stubs to XW /
  XE), then fly over the westbound side as elevated ramps (elevated ramps need ~2 tiles of road-free ground to rise).
  `NB.hwk` skips the wide-road side rule while these are built. Merge nodes get `setSig(j,{m:'none'})` (road
  junctions default to timed lights). `G.hw.rn` lists the starter nodes for `hwFree`.
- East end: two nodes, in (`HWY.eastN` / `eastJ`, westbound start) and out (`HWY.eastON` / `eastO`, eastbound end).
  The drawn highway past your land is two look-15 strips; `hwThru` lanes are offset by `HWD`.
- Junction drawing: where two highway arms run straight through a node (merge, split), the junction is highway asphalt
  and keeps the through lane lines, with a dashed edge on the side where the other road joins.

## Roads department and road wear

- `G.rwear` {tile: wear 0..1} grows each month in `rdMonth` (monthEnd wrapper): base + traffic (`jam`), dirt x1.6, highway
  x0.7, pedestrian x0.4. (`G.rw` is the river half width, a number: never reuse it; loading moves an old wear object out of `G.rw`.) Wear > 0.4 slows cars (`lkSpd` wrapper), city average > 0.35 costs happiness.
- Roads department = Gov size 7 (`gov:'roads'`, transport model in yellow). Each month every department sends
  1 + 2 x roads budget crews (`rdSend`: flatbed, yellow, role `roads`) to the worst roads within `RD_R` 60 tiles;
  `arrive` wrapper calls `rdFix` (tile and road tiles within 2, -0.85 wear, $5 a tile); no path = fixed directly ($15).
- `rdScan` caches department list and stats for 2 s (OWNIDX scan). Decals: two InstancedMeshes `RDI` (cracks > 0.35,
  potholes > 0.7) laid along the road (`rdDecor`, after `buildAll` and each month). Info view `roads` (Road condition).
- Test placement: single buildings go through free placement (`FP`); call `apply` with `FP.inner=1`.

## Shops with a purpose

- `SHOPS` (24 brands: dentist, soda bar, ice cream, clothes, grocery, bakery, pharmacy, food places...) picked per shop
  lot by a hash of `tl.seed` (`shopOf`; COM with level, not offices `s >= 10`). `bname` shows "Brand (kind)".
- `shopSigns` (adjTile wrapper installed AFTER `lotParking`, so it measures the building after `lotMakeRoom` moved it
  back; before, signs were left standing in the car park; local frame: +z faces the road) measures the big shadow-casting parts
  (height >= 0.12, footprint >= 0.03: no cars, trees, tables; glass facade front when there is one); modern-district shops get no rooftop billboard, then adds a shop-front
  sign, a rooftop billboard on buildings lower than 0.9 and, for food (`SHOPS[k][5]`), a pole sign at the lot corner.
- One atlas `SHOPAT` (2048², 4 x 16 panels of 512 x 128: panel 2k billboard, 2k+1 shop front, emoji icons) and one
  material `SHOPM` (emissive map; `applyTime` wrapper raises emissiveIntensity at night). Add brands at the end of
  `SHOPS` only (index decides the panel; max 32 brands).

## Parking on lots

- `lotParking` (adjTile wrapper, after `shopSigns`): `lotFree` collects bounding boxes of parts taller than 0.075,
  `lotStrip` finds the biggest free strip along a lot edge. Low shops (level <= 2), small industry and mid flats
  (`s 0`, level 2) whose building fills the lot get room first (`lotMakeRoom`: the non-flat parts shrink to 70% against
  the back edge). Shops/flats: paved strip with bays and low-poly cars (`lotCar`, <= 4, phones 2); houses: driveway,
  garage when there is side room, a car; industry: yard with a truck (`lotTruck`) and staff bays.
- Inside these helpers use `LY0` (0.03, lot ground); `Y0` only exists inside `buildTile0`.

## City billboards

- Road menu tab Signs: hidden tool `bboard` ($500, kind one) on empty land next to a road; `G.bb` [{i, ry, v}],
  slogan/colour in `G.brand` (prompt on picking the tool). Drawn as a separate group `BBG` (`bbDraw`, after
  `buildAll`, on place / doze / when the tile is built on), one canvas texture `BBT` (3 designs + back), `BBM` glows at
  night. Each adds +0.4 happiness ("City pride", max +2).
  Zone buildings (`ZN`) leave their tiles EMPTY, so `bbOk` also refuses `ZN.cov`, free-placed footprints, curved
  road cover and transit corridors; zone growth skips a building that would stand on a billboard (`bbHits`).

## Telecom (T.TEL = 32, `SV[32]`)

- Sizes: 0 mobile tower, 1 5G tower, 2 internet exchange, 3 radio and TV mast, 4 warning siren, 5 data centre. The tool
  definitions (`T.TEL`, `SV[32]`, `TOOLS` entry, `ICON.tel`) sit just before the toolbar is built (`TOOLS.forEach`);
  the rest is the telecom block before boot. Drawn from boxes/cylinders in `telDraw` (`case T.TEL` in `buildTile0`);
  blinking beacons and the turning siren horn are `funLive` groups (`telLive`), placed from `G.fp` when free-placed.
- `telScan` (recompute wrapper) fills `cellC` / `netC` / `radC` / `sirC` / `telV` and the home shares `TEL.cell/net/rad`.
  Effects: happiness parts, land value (+6 fibre, +3 signal), office demand, data centre jobs (needs `netC`).
- Disasters: `disStart` wrapper wails the sirens (`telWail`, generated sound `telSound`) and posts a warning when the hit
  point is in siren or radio reach; `disHit` wrapper: warned zone buildings drop one level instead of to 0, 40% of
  warned services hold. Info view `telecom`.

## People walking

- `updatePeds`: drawn position `p.wx/wz` follows the path target with exponential smoothing (round corners), facing
  `p.yawS` turns smoothly, speed eases in after stops (`p.v`). Side changes only at junction tiles (30%) or rarely
  mid-block, after a kerb wait with head turns (`p.look`); `p.sideF` slides across the road. Side-step oncoming walkers
  on the same tile and side (`PDG`). 22% of walkers bring a companion (`c.lead`, drawn beside the leader, not an agent,
  removed with it via `p.dead`). `p.phone` raises the right arm.

## Mayor's game (goals, advisors, elections, neighbours, festivals, achievements, hard mode)

- Star button in `#topBar` opens `#mayPanel` (tabs Goals / Effects / Election / Neighbours / Achievements);
  questions and campaign promises show in `#decCard` above the toolbar.
- State in G: `G.mo` month counter (monthEnd wrapper), `G.ms.i` mission index (`MISS`), `G.fx` timed effects
  (`fxAdd(nm,{h,m,d2,d3,d4,dO,mo})`, read by happyParts / computeDemand / monthly money), `G.dec` advisor questions
  (`DECS`, every 2-4 months from 300 people), `G.elec` (every 48 months after 500 people; promise 6 months before,
  vote from last year's happiness + promise + budget), `G.nb` three neighbour towns (trade money while
  `hwConnected()`), `G.fest` festivals with fireworks (`fwTick`), `G.hard` (new-city checkbox `#newHard`, passed
  through localStorage `pc-hard-next`: half money, upkeep x1.25, demand -0.05, extra disasters, rewards x1.5).
- Achievements are per player in localStorage `pc-ach` (`ACH`, `achCheck` every 3 s).

## Prices and touch placement

- Zoning (homes, shops, industry, offices) is free (`costFor` returns 0; zone cells along network roads never cost).
  Every `SV` size cost is doubled once, just before boot (after all modules added their sizes), then `refreshToolCosts`.
- Touch placement of free-placed buildings (net_ui scope, after `window.UCfp`): picking the tool puts the building at
  the screen centre (`UC.centre`), panning moves the map under it, a tap (< 10 px) moves it to the tapped spot, Build
  confirms and the next one returns to the centre; ✕ drops the tool. Mouse keeps following the pointer.
  `UC`, `ucGo`, `ucCancel` live inside the net_ui scope, so code that uses them must sit there.

## Tornado and fireworks

- Tornado (`torMake` / `torUpdate`, block before landmarks): two funnel shells (`torShell`, 30 rings x 24 sides,
  vertices rebuilt each frame: flaring radius, ripples, sway, top lags behind travel `d.lx/lz`, rope-out at the end),
  skewed streak texture scrolled for spin; dust skirt, wall cloud = instanced camera-facing quads (`torBill`, lit
  Lambert so they darken in storms / at night); debris = instanced boxes; storm weather and a brown-noise roar start
  with it. Path wanders (`d.hd`). 26 s life. `TORH` 45 (~675 m tall), wall cloud 130 puffs low enough to hide the funnel's top rim.
- THREE.Points and Sprites do not draw in this game: use instanced camera-facing quads (fireworks `FW.g` too).
  Call `setColorAt` before setting `count = 0`, or the colour buffer is created empty and everything renders black.

## Highway outside the map

- `terrainH` wrapper (before `HORIZ`): west of the map, land within 9 units of `hwZ(x)` blends to `hwBed(x)` (natural
  height averaged along the road, >= 0, easing to the map-edge height over the last 14 units), flat core 1.2. The road
  strip samples `terrainH`, so it now sits on a graded bed instead of disappearing under the coarse landscape mesh.

## Modern building style (`md`, Blender models `x_md_*`)

- Models come from `Downloads/PixelCity-Blender/scripts`: `modern.py` (28 zone models, slots rl1..tw plus `b`
  variants), `modern_civic.py` (`x_md_sv_<school|college|hosp|fire|police|garb><0-2>`, industry `x_md_inl1a..l3b`),
  `modern_city.py` (`x_md_gov0-6`, `pow0-2`, `wat0-2`, `sew0-1`, `dth0-1`, `metro`). Run in the Blender GUI to watch
  them build, or `-b` to export; then `tools/models.py add`.
- `archStyle(i)` returns `'md'` for 1 in 4 Mixed districts (`(h>>>9)&3`), or for every tile with `G.arch==='md'`
  (Buildings button cycles mix / eu / us / as / md / classic). Zone models use `ARCHMD` (own slot lists, incl. industry
  `4:0`; specialised res / com / office subtypes fall back to the base lists). Free-zoning `zPick` adds `b` variants.
- Services, government, power, water, sewage, death care and metro: each `buildTile0` case starts with
  `if(archStyle(i)==='md'...)model(g,'x_md_...',MDSVC,...);break`. `MDSVC` holds the colours of the extra materials
  (red, blue, yellow, teal, track, steel...). Chimney smoke: `CEM.x_md_inl3a` and `em.push` in the power / garbage cases.
- Glass on `x_md_*` uses `mdGlass` (tiles) / `zGlassMat(true)` (free zoning): lighter `#a3bccf` with sky reflection;
  the normal dark `archGlass` made the all-glass towers read as black.
- `modern_chain.py`: supply-chain plants `x_md_ch_<kind>` (processing kinds only; fields, pasture, plantation, sand pit,
  rig keep their models; `case T.CHAIN` swaps `nm` when the model exists) and specialised industry `x_md_z<forest|oil|ore><1-3>`
  (zoneModel returns them for `t.t===4`, `s` 1/3/4 in modern districts; farming keeps `farmModel`).
- `modern_parks.py`: parks `x_md_park0..8` (trees from `models/md_park_trees.json`, merged into `PARKTREES`; colours
  `PKMDCOL` = PARKCOL + corten / sail) and the stadium `x_md_stad_b` (no modern 3x3: the small stadium is not buildable, only old saves have it) (bowl, crowd and pitch reused from
  stadium.py / stadium_big.py, new `skin` material = `stSkin(team colour)`, white by day, glows at night via `winMats`).
  Famous stadiums keep their models.
- `modern_transport.py`: `x_md_rail_plat(_mid)` (trains.py platform tile with old canopy parts dropped, same track and
  platform heights) and `x_md_airport_domestic` / `x_md_airport_dom_land` (airport_domestic.py with the terminal and
  tower parts dropped, `TERM_DROP`; airfield, stands and roads unchanged so jets and cars still line up). Cargo stations
  only get modern colours (RCOL override in `railTile`).
- Fun attractions in modern districts: `buildTile` sets `MATMAP = FUNMD` while drawing a `T.FUN` tile and `mat()` swaps
  the old bright paint for the modern set (layout and animation unchanged). `MATMAP` is a `var` (mat runs early).
- Street furniture: `prop_streetlight` / `prop_signal` are the modern ones from `modern_street.py` (graphite `pole`
  material, `MODEL_COL.pole`); old ones kept as `models/prop_*.old.glb`. Road palette: asphalt `#5f6369` / `#5c6066`,
  lines `#fbfbf8`, pavement `#d0cec8`, kerb `#c2c4c6` (was `#74787d`, `#f1f1ec`, `#b9bdc3`, `#9da1a7`).
- Neon parts on `x_md_*` models use `mdNeonMat` (cyan) instead of the pink `neonMat`.
- Bus stops: `clStopMesh` draws `x_md_busstop` (modern_street.py; `sign` = line colour) 0.57 from the stop tile centre
  toward the first non-road side; meshes flagged `userData.sh` so `clDraw` does not dispose shared materials. `clDraw` also
  draws shelters for the city's own lines (stop tiles are buildings: the shelter goes on the road tile beside them).
- Benches `x_md_bench` (backless, long along local Z): tile roads opposite the street tree when `(x*7+z*3+k)%4===0`;
  network streets in `netDecor` every third tree gap, alternate sides.
- Trees `tree_round` / `tree_tall` / `tree_pine` (+ `_lo`) and `bush` come from `trees_real.py` (old ones kept as
  `models/tree_*.old.glb`). Parts: `leaf` (tinted per tree; on the full-detail broadleaf, columnar and bush models these are hundreds of
  separate double-sided leaf quads, `leaves()`), `leaf2` (inner shade mass, `MODEL_COL.leaf2`), `trunk`. Far tree
  LOD (`TI.loGeo`) only uses `leaf`, so `leaf2` simply hides at distance. `shrub()` draws the `bush` model.
- `grassTex` is 1024 px with tufts on PC (pointer fine), 512 px on phones.
- Sun path (`applyTime`): `sunDir` / `skyU.sunV` = (cos ang, el*0.72, 0.5), so the sun peaks at about 50 degrees to the
  south (was nearly overhead). `dayLight=(el+0.12)/0.3`; hemisphere light gets +0.2 around el 0.12 (low sun) so
  sunrise and late afternoon are not dark.
- 2026-11-09: the realistic tree update was rolled back at the user's request (lag when zooming / moving the camera on a
  laptop): `tree_*` are the old models again (from `models/tree_*.old.glb`), the `bush` model is removed so `shrub()`
  draws its old ball. `trees_real.py` is kept but not used.

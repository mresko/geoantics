# GeoAntics: notes for Claude Code

GeoAntics is a browser puzzle game by Siim. Ant colonies eat a pixel map of a country or continent, one terrain colour at a time, from the edges inward. It was built in a claude.ai chat. This file holds what the code alone does not tell you: Siim's decisions, how levels are generated and verified, and the pitfalls already found.

## Repo and workflow

- Repo: https://github.com/mresko/geoantics (branch `main`). The game is a single self-contained file, `index.html` (about 200 KB). GitHub Pages serves it.
- **Only commit and push a new `index.html` when Siim asks for it.** Otherwise make changes locally and show them.
- `tools/` holds the level-generation pipeline (Python), which is not part of the shipped game. The large source data is downloaded by `tools/fetch_data.sh` and must not be committed. Add to `.gitignore`: `tools/*.geojson`, `tools/topo.nc`, `tools/topo.npz`.

## Writing style for UI text and replies

Concise, direct prose. No em dashes, few colons, no marketing language. Bold only what would be stressed in speech.

## Game rules (current)

- 15 levels: Europe (Estonia, Finland, Italy, Iceland, boss Europe), Africa (Egypt, Kenya, Nigeria, Madagascar, boss Africa), Asia (Japan, Sri Lanka, Mongolia, India, boss Asia). Every 5th level is a continent boss.
- Columns of colony trays (3 on level 1, then 4). Only the top tray of a column can be tapped. Tapping moves it into one of **5 slots**. Its ants eat that many blocks of their colour, but only blocks that are exposed (touching the sea or an eaten cell).
- You lose when no tray can be placed and nothing in the slots can progress.
- **Fog**: purple cells hide their colour until exposed. It comes as large shapes (wavy bands, blobs, or whole regions), so players guess colours from geography. Siim likes the purple.
- **Keys and padlocks**: a golden key sits on one cell. Eating it unlocks a padlocked tray.
- **Tied colonies**: two trays with the same chain badge move together. Both must be on top and 2 slots must be free. Rules Siim set: partners are always in **neighbouring columns**, never more than **5 rows** apart, and the UI must show where the partner is (dotted line between visible partners, a chip under the column with the row number when the partner is deeper).
- A timer starts on the first tap. Best times per level are saved.
- The menu has a "Reveal all maps" toggle that opens every level and shows all thumbnails in colour, without touching real progress.
- Progress is stored in `localStorage` under `mapants-progress-v2`. Keep that key, or existing players lose their progress.

## Siim's design decisions (do not undo without asking)

- **Difficulty**: he likes tough puzzles. Later levels should be hard. A naive bot winning about 15% or less is the right range.
- **Landscape layout must never be easier than portrait**: both show exactly **3 rows** of trays.
- **The naive bot must win sometimes** (at least 3 of 60 games). A level that only the strong solver can win is not acceptable.
- **Padlock fairness** (v0.6): no padlock in the 3 rows visible at the start, padlocks at least 4 colonies apart (solution order and within a column), no tied colonies in the two places under a padlock, and the balancer never adds padlocks beyond the level's base number. Constants `LOCK_GAP`, `LOCK_MIN_ROW`, `BOT_MIN` in `tools/build.py`.
- Colony size cap: 32 on early countries, rising slowly to 44 on the Asia boss. No huge trays (82 was rejected).
- **No roads. No administrative borders inside countries.** Countries are divided by natural features (rivers, mountains). Continent bosses keep country borders as brown lines, which he liked.
- **Terrain is driven by real elevation.** Lowlands are farmland, hills are forest, grey mountains appear only above a per-country height, and **white means glaciers or anything at or above 2500 m**. Do not overemphasise mountain ranges.
- **Colours** (one antique atlas palette, he asked for cohesion): Borders `#6e4b2e`, Forest `#5f7f45`, Farmland `#d3a94e`, Water `#5b8ea0`, Cities `#2f2620` (black), Mountains `#9b9182` (grey), Desert `#c4774a`, Glaciers `#f4eee0` (white), Fog `#6d4f8e`. Tie colours: rose madder, verdigris, saffron, lapis. Walnut desk background, parchment sea, verdigris primary buttons, lapis secondary, vermilion for losing, gold for keys, padlocks and bosses.
- **Fonts**: IM Fell English SC for titles and map names, Alegreya Sans for everything else (both from Google Fonts).
- **Sea**: medieval chart parchment with rhumb lines, a compass rose, and a "here be dragons" sea serpent. The dragon must stay **subtle**: faint hollow sepia outlines almost the same colour as the parchment. Both are placed automatically in the emptiest stretch of sea.
- Layout is responsive: portrait (400x800 logical) on phones, landscape (1280x760, map left, colonies right) when the window is wider than 1.15:1.

## The deterministic eating model (most important technical point)

The game and the solver **must use identical eating rules**, otherwise a level that the solver marks solvable can be impossible in the game. This bug happened once: ants picked the nearest block on screen while the solver used a different order, and Europe became unwinnable.

The shared rules, implemented in `index.html` (`lg`, `lq`, `LK`, `hpush`, `hpop`, `active`, `lEat`, `runLogic`) and in `tools/build.py` (`Sim`, `playout`):

1. Each colour keeps a **priority queue (min-heap) of exposed cells**. A cell becomes exposed when it touches the sea or an eaten cell; when a cell is eaten, its neighbours (right, left, down, up, `NB`) that are non-empty and not yet queued join their colour's queue.
2. A tray eats the queued cell **nearest the bottom centre of the map** (Siim's choice, v0.6). The key is `((2i+1-GW)^2 + (2GH-2j-1)^2) * cellCount + id`: squared distance from cell centre to the point (GW/2, GH), ties broken by lower cell index. Integer maths, so both sides agree exactly. Before v0.6 this was a FIFO queue seeded in cell-index order.
3. Active trays are processed **in placement order** (not slot index), repeatedly, until no tray can progress.
4. A tied pair is placed tapped tray first, partner second.
5. A slot counts as free for logic as soon as its tray's remaining count reaches 0.

The game resolves the logic **instantly on tap**. Ants only animate the result (a visual queue per slot). A slot is visually busy until its ants have left, which only delays the next tap and never changes the outcome.

**If you change any game rule, change it in both places, rebuild the levels, and run the replay test.**

## Level pipeline (`tools/`)

- `fetch_data.sh` downloads Natural Earth GeoJSON (10m and 50m: countries, admin-1, rivers, lakes, urban areas, glaciers, geography regions, populated places) from github.com/nvkelso/natural-earth-vector, plus a 10 arc-minute global elevation grid from github.com/fatiando-data/earth-topography-10arcmin, which it converts to `topo.npz`. Needs `shapely numpy netCDF4`.
- `build.py` rasterises a country or continent to a grid, assigns terrain, generates trays, and verifies solvability. `levels.py` defines the 15 levels (terrain function, elevation thresholds `mtn_m`, facts, intro texts), the difficulty curve and the balancing targets. Run from inside `tools/`: `python3 levels.py`. It writes `levels.json` and `solutions.json` and takes several minutes.
- Keep the downloaded data and a Python venv outside Google Drive (Drive would sync about 150 MB). Run the builder with the data folder as the working directory, e.g. `cd <data dir> && <venv>/bin/python3 <repo>/tools/levels.py`. It writes `levels.json` and `solutions.json` into that folder; copy them to `tools/`.
- Any script that plays the game (replay test, bots) must set `AUTOPLAY=true` first. Otherwise its wins are saved as the player's cleared levels and best times.
- The replay test needs Playwright. Without it, the same JS can be run in the Claude browser pane against `index.html`.
- Then splice into the game with `python3 tools/splice_levels.py index.html tools/levels.json` and verify with `python3 tools/replay_test.py index.html tools/solutions.json`. Every level must end in `win`.

How generation works:

- **Grid size** targets a land-cell count per level (Estonia about 1300, rising to India about 2500, bosses 2600 to 3200), capped at 92 cells on the long side.
- **Terrain**: glaciers or max elevation in the cell of 2500 m or more give white. Elevation above the level's `mtn_m` gives grey. Natural Earth desert polygons give desert. Otherwise a per-level function uses elevation, latitude and smooth noise for forest and farmland. Then 10m lakes and rivers (water), urban area polygons (black, when they cover enough of a cell), coast and border cells (brown), and the largest cities as a fallback. The elevation grid averages about 18 km per cell, which flattens narrow Alpine peaks, so the Alps get their white mostly from glacier polygons.
- **Trays**: a solution order is generated by repeatedly picking a colour with exposed cells and eating a chunk from its FIFO queue. Padlocks are placed 2 to 8 trays after their key's chunk. Ties link trays 1 to 3 apart in the solution order. The order is then shuffled within a window `w` and dealt into columns, respecting the tie column and row rules.
- **Fog** is added after layout as bands, blobs and regions until it reaches the level's target share. It does not affect solvability.
- **Verification and balancing**: each candidate layout is played 30 times by a naive bot (taps a tray whose colour can eat 80% of the time, otherwise random). A stronger solver (200 playouts, 93% greedy) must find a win, and that winning tap sequence is saved to `solutions.json`. The generator picks the candidate whose bot win rate is closest to the level's target (from 0.75 on Estonia down to 0.06 on Asia). If it is too easy, it raises `w` and adds padlocks or ties (only on levels where those mechanics are already introduced). If it is too hard, it eases off. Current reality: Estonia and Finland stay easy (no padlocks or ties to add), several late levels have a bot rate near 0 but a proven solution.

## What drives difficulty (tested 2026-11-22, v0.6)

Tested with `tools/probe.py` (60 layouts per variant, counts how many land in the target bot-rate band):

- **The map barely matters.** Smaller forest/farmland patches (`patch`), forest belts through farmland (`hedge`, `hedge2`), riverside forest (`riparian`, more rivers via `river_rank`), towns cutting rivers (`river_towns`), more cities, lower `mtn_m`, desert oases (`oasis`) and more or less forest (`forest_bias`) all change the look but not the bot rate. These options stay in `build.py`, off by default, usable for looks.
- **The eating rule barely matters**: the old FIFO rule and nearest-bottom-centre give the same spread on the same maps.
- **4 slots instead of 5 and colonies 8 bigger barely matter** either.
- **Bot results are bimodal per layout**: most layouts the bot wins nearly always, a few it nearly never wins. Losses are almost all structural: every top colony is padlocked, or a tied colony's partner is buried deeper in its column. "Slots full of colonies that cannot eat" (the only map-driven loss) is 0 to 5% of games. Levels without padlocks or ties (Estonia, Finland) are won by the bot practically always.
- **3 slots is the one strong lever found** (probe, 8 off-target levels). Average bot rate: Africa 0.91 to 0.56, Europe 0.94 to 0.71, Finland 0.99 to 0.82, Kenya 0.93 to 0.82. Layouts the bot always wins drop sharply (Europe 40 of 60 to 0), so the balancer gets layouts in between to choose from. Little effect on Egypt, Sri Lanka, Iceland or Estonia.
- **An extra colour alone is weak** (a 9th colour carved as patches from the biggest colour, 20 to 35%: averages drop 0 to 0.1). **Combined with 3 slots it is the strongest**: Europe 0.48 with 15 of 60 layouts in its band, Africa 0.44. A real extra colour would need a new terrain type in the palette and legend.
- Probe options for these: `slots` and `extra` in `tools/probe.py`; `SLOTS` and `NCOL` constants in `build.py` (5 and 8, matching the game).
- **Tied pairs do not give middling difficulty either.** More ties (+2, +4), partners forced 2 to 5 or 3 to 5 rows deeper (`tie_rows`), or partners further apart in solution order (`tie_span`) lower the average only by adding layouts the bot never wins (mostly unwinnable, rejected by the solver and `BOT_MIN`). Layouts in the target band stay at 0 to 1 of 60. Forcing deeper partners also makes many layouts impossible to deal. Options stay in `build.py`, off by default.
- **What makes a layout hard (Europe 47% vs Asia 10%, same rules):** losses happen at one fixed tap in every game (Asia tap 51, Europe tap 105 of 113). The deciding factor is a padlock whose **key sits on a scarce colour far from the bottom centre**, e.g. Europe's key on one of only 6 glacier cells, in the far north. Ants eat the nearest cells first, so sending that colour's colonies early spends them on the near cells (the Alps). The only one left is then behind the padlock. Winners hold a colony of the key colour back until the key is next in line. Asia is harder because it has two such keys (glaciers, desert) and two tied pairs whose partners are buried at the same depth, so all four columns jam mid-game with nothing else to dig. Europe's trap only closes at the end. Which cell gets the key is random today (any non-border cell of a chunk 2 to 8 colonies before the padlock), so difficulty differs by build luck, not by continent.
- **Key on a rare colour** (`key_mode='rare'`, `key_back=12`: key on the last-eaten cell of the rarest colour's chunk before the padlock) lowers the naive bot's average on Asia (0.79 to 0.46), Africa (0.91 to 0.64), Kenya (0.93 to 0.73), Sri Lanka (0.92 to 0.80), Egypt (0.90 to 0.81), and does nothing on Europe or Iceland. Like extra ties, it works mostly by adding layouts the bot never wins; layouts in the target band stay at 0 to 4 of 60. `key_mode='far'` (last cell of a random chunk) does little.
- **Adding a rare 9th colour (4%, small patches)** alone does little. With the key on it, Sri Lanka 0.62, Africa 0.56, Kenya 0.78, Asia 0.62; same always/never pattern.
- **Fog on the rarest colour cannot be measured with these bots.** The naive bot ignores the map, so fog changes nothing for it. A first planning bot (`smart_play` in `probe.py`: holds back a key-colour colony that cannot reach the key, counting only visible cells) plays worse than the naive one, so its fog results mean nothing. Measuring fog needs a properly strong planning bot first.
- So with 5 slots, the bot either breezes through a layout or is stuck structurally.
- **What worked to hit targets (v0.6 rebuild):** per-level `tune` in `levels.py` (`TUNE`): a longer search (`rounds=12, cands=40`) plus `rare_keys=True`, which switches padlock keys to a rare colour once the level comes out too easy. Measuring each candidate with more games (`bot_games=150`) and a tighter stop (`tol=0.05`) avoids picking layouts that only looked hard by luck (Iceland and Kenya first came out at 43% and 38% over 600 games). Results over 600 games: Iceland 30% (target 32), Europe 21% (25), Egypt 38% (30), Kenya 24% (25), Sri Lanka 8% (12). All padlock rules hold. Rebuild a subset with `python3 levels.py Iceland Kenya` (merges into the existing levels.json). Always confirm a rebuilt level's rate over 600 games.
- Estonia and Finland cannot reach their targets without padlocks, ties, fewer slots or a new colour. Only fewer slots (3) creates layouts of middling difficulty. v0.5 met its targets largely by accepting near-zero layouts, which the `BOT_MIN` rule now rejects.

## Performance (fixed after lag on iPhone 15 Pro)

Keep these properties when changing rendering:

- Device pixel ratio capped at 2.
- The map lives in an offscreen layer. A full redraw happens only on level start or resize. Eaten cells are repainted individually (`patchBoard`, using a cached parchment background canvas).
- Fog "?" labels are recomputed at most about twice a second and drawn on the main canvas.
- All ant poses (8 colours x carrying x 2 leg frames x 16 headings) are pre-rendered into one atlas canvas per level. Each ant is one `drawImage`.
- At most 140 ants on screen. Extra ants wait in their slot.
- Font switches go through `setFont` (cached), and the anthill gradient is cached.

Measured at iPhone resolution in headless Chromium on the Asia boss: average draw time went from about 40 ms to about 5 ms per frame.

## Ideas not done yet

- Finland is still easy because its only lever is shuffling.
- Possible future features discussed: more countries, a hint button (the saved solution sequences could power it).

## Versioning
- Version format `MAJOR.MINOR.PATCH` (current line is pre-1.0, e.g. `0.5`, `0.5.1`, `0.6`).
  - MINOR bump (`0.5` → `0.6`): new feature, new maps, gameplay change.
  - PATCH bump (`0.5` → `0.5.1`): bug fix or small tweak.
  - `1.0` when the user calls the game finished.
- The version lives in three places in `index.html`, keep them in sync:
  1. `<meta name="version" content="X.Y">`
  2. `const VERSION='X.Y';` at the top of the main script
  3. (drawn automatically on the menu as `vX.Y`)
- Every version gets an entry in `CHANGELOG.md`. Work in progress goes under `[Unreleased]`.

## Releasing a version (only when the user says to commit)
1. Bump the version in `index.html` and move `[Unreleased]` notes into a new `CHANGELOG.md` section with the date.
2. Commit `index.html` + `CHANGELOG.md` with message `vX.Y: <short summary>`.
3. Tag it: `git tag vX.Y` and push with `git push origin main --tags`.
4. Old versions are recovered from tags (`git show v0.5:index.html`), not kept as extra files.

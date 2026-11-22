# Changelog

All notable changes to GeoAntics. Versions follow `MAJOR.MINOR.PATCH`
(see [CLAUDE.md](CLAUDE.md) for the rules). Each released version has a git tag `vX.Y[.Z]`.

## [Unreleased]

## [0.6] - 2026-11-22
- Added the level pipeline in `tools/` (builder, data download, level splicer, stored solutions, replay test) and `.gitignore` for the source data. Added `tools/probe.py` for quick difficulty tests and per-level tuning in `levels.py`.
- CLAUDE.md now holds the full project notes from the claude.ai chat plus the versioning rules.
- New eating rule: ants eat the exposed block of their colour nearest the bottom centre of the map, so maps are eaten from the bottom up. Same rule in the game and the level builder.
- All 15 levels rebuilt and rebalanced for the new rule. Maps are unchanged; colonies and their order are new.
- Fairer padlocks: none in the first 3 rows, never two close together, no tied colonies right under a padlock, and no extra padlocks added by the balancer.
- Fixed: test and bot wins were saved as the player's cleared levels and best times. Scripted play now sets `AUTOPLAY` and never touches saved progress.
- Iceland, Europe, Egypt, Kenya and Sri Lanka rebuilt to reach their difficulty targets, with padlock keys on rare colours and a longer search.
- Every level must be won by the naive bot at least 3 times in 60 games, so no level depends on one narrow solution.

## [0.5] - 2026-11-22
- Baseline version moved from Cowork into this repo (`index.html`).
- 15 maps in three worlds (Europe, Africa, Asia), each ending in a boss map.
- Added version number: `VERSION` constant, `<meta name="version">` and a "v0.5" label on the menu.

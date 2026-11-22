# GeoAntics (MapAntics)

Single-file canvas game. The whole game lives in `index.html`; no build step.
Repo: https://github.com/mresko/geoantics (branch `main`).

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

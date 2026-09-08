# Quest Forge loading plates

27 cinematic 16:9 stills, one per dimension. Style lock is the main-menu
background: path-traced cubes, not the knight-hall splash.

```
_loading-plates/
  README.md
  _refs/                         shared style + user references
  selected/                      current pick per plate (only winners)
    01-nether.png
  work/
    01-nether/                   numbered passes, oldest first
      current.png                copy of the live pick
      01-seeds/
      02-crags-ghast/
      …
    02-end/                      STATUS.txt until work starts
    …
    27-chaos/
```

## How a plate is worked

1. New pass = new numbered folder under `work/NN-name/`.
   `01-seeds`, `02-…`, never dump into the plate root.
2. Four seeds per pass, keep the generator filenames.
3. Mark the chosen seed with a `_picked` file (filename only).
4. When a direction dies, suffix the folder `_SCRAPPED`. Keep the files.
5. Promote a pick by copying it to both:
   - `work/NN-name/current.png`
   - `selected/NN-name.png`
6. Finish pass (crop, safe zones, 4K, cohesion grade) is last, after all 27
   have a `selected/` still. Do not 4K mid-set.

## Naming

`qf_dim<id>_<slug>_<pass>_a.png` … `_d.png`

Example: `qf_dim-1_nether_d2a_hathat_b.png`

## Status

| # | Plate | DIM | Shot | Status |
|---|---|---|---|---|
| 01 | The Nether | −1 | corridor | **picked** — `selected/01-nether.png` (integrate B) |
| 02 | The End | 1 | vista | **picked** — `selected/02-end.png` (xleg2 D) |
| 03 | Twilight Forest | 7 | ascent | **picked** — `selected/03-twilight-forest.png` (seed B) |
| 04 | Dream World | −37 | threshold | **picked** — `selected/04-dream-world.png` (steve C) |
| 05 | Torment | −38 | corridor | **picked** — `selected/05-torment.png` (seed C) |
| 06 | Mirror World | −39 | vista, reflected | **picked** — `selected/06-mirror-world.png` (red lantern A) |
| 07 | The Lost World | −42 | vista | **picked** — `selected/07-lost-world.png` (seed D) |
| 08 | Compact Machines | 4 | threshold | **picked** — `selected/08-compact-machines.png` (gloss A) |
| 09 | Outer Space | 30 | vista | **picked** — `selected/09-outer-space.png` (seed C) |
| 10 | Mars | 31 | vista | **picked** — `selected/10-mars.png` (sand B) |
| 11 | Ilum | 32 | corridor | **picked** — `selected/11-ilum.png` (seed A) |
| 12 | Hurikane | 33 | ascent | **picked** — `selected/12-hurikane.png` (chase A) |
| 13 | Tython | 34 | vista | **picked** — `selected/13-tython.png` (seed D) |
| 14 | Korriban | 35 | vista | **picked** — `selected/14-korriban.png` (seed A) |
| 15 | Tatooine | 36 | vista | **picked** — `selected/15-tatooine.png` (seed D) |
| 16 | Speed Force | 50 | corridor | **picked** — `selected/16-speed-force.png` (seed A) |
| 17 | Wakanda | 51 | vista | **picked** — `selected/17-wakanda.png` (reframe D) |
| 18 | Kingpin Takedown | 53 | threshold | **picked** — `selected/18-kingpin.png` (seed C) |
| 19 | Quantum Realm | 55 | ascent | **picked** — `selected/19-quantum-realm.png` (seed D) |
| 20 | Imortus | 58 | vista | **picked** — `selected/20-imortus.png` (ice B) |
| 21 | The Underworld | 66 | corridor | **picked** — `selected/21-underworld.png` (far A) |
| 22 | Utopia | 80 | ascent | **picked** — `selected/22-utopia.png` (3head D) |
| 23 | Extreme / Mining | 81 | corridor | 01-seeds — pick pending |
| 24 | Village Mania | 82 | vista | not started |
| 25 | Islands / Danger | 83 | vista | not started |
| 26 | Crystal | 84 | corridor | not started |
| 27 | Chaos | 85 | vista | not started |

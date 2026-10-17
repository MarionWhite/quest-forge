# Nebula dome (shelved 2026-10-13)

The jukebox's dome face as black glass with a small nebula behind it and
twinkling stars over it. Replaced by plain black glass; kept here so it can
come back.

- `jukebox_shoulder.png` -- the sheet as shipped (faint stars only; the bright
  ones are geometry). Regenerate with `ornate.nebula(1024)`.
- The twinkling stars are `JukeboxModel.stars(t)`, still in the model. They
  were drawn in the WHITE pass in `RenderJukebox`, just before the waveform.

To restore: in `make_jukebox_textures.py` point `"jukebox_shoulder"` back at
`lambda: ornate.nebula(1024)`, and put the `JukeboxModel.stars(t)` call back.

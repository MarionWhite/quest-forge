# r012 publish checkpoint (2026-10-28): DONE, live

- C:/qfb/shaderdev/r012/spec_scenes.py (backup spec_scenes.py.pre-publish): merges textures_scenes.json (4) and packs_scenes.json (16)
  after the 3 shader scenes, attaches critic.json notes; intro is two sentences; pk-hud keeps only the offline mock M (in-game
  shots dropped: chat over hearts, food draining; text says widgets.png in QuestForge.zip sits on top); pk-mob-4 and pk-mob-7 text
  says plainly the slime, magma cube and squid are missing.
- finish_round.py only prints OVER BUDGET (sunset-full/A p12 3.65 ms > 3.0), it does not stop; the number is in the rays/sunset text.
- Dry run: 23 scenes, 0 missing frames, 0 missing notes. --publish committed 4ebc2cc and pushed itself.
- r012.json returned 200 about 2 min after the push (404 before Pages deployed). Edge screenshot (needs --virtual-time-budget=15000,
  else it shows "Loading"): C:/qfb/shaderdev/r012/look/r012-page.png.

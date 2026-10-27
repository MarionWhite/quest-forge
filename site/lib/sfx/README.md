# Site sound bank

`manifest.json` maps event names to files. `mob/`, `step/`, `random/` ... are the 1.7.10 game sounds and OreSpawn's, rebuilt by `tools/site/build_sfx.py` (the game's sounds are not redistributable: `--own-only` drops them).
`qf/` holds our own sounds. Synthesised ones come from `tools/music/site_cues.py` and `scare_sounds.py`.
The screams and the mood set are layered **recordings**: `tools/music/scream_pack.py` (fetch, then build).

## Recordings in the scream pack (all CC0 1.0, OpenGameArt)

Machine-readable copy: `sources.json`. Licence text: https://creativecommons.org/publicdomain/zero/1.0/

| Source | Author | Licence | Used for |
|---|---|---|---|
| [grunts-male-death-and-pain](https://opengameart.org/content/grunts-male-death-and-pain) | thebardofblasphemy | CC0 1.0 | main male death/pain screams |
| [15-vocal-male-strainhurtpainjump-sounds](https://opengameart.org/content/15-vocal-male-strainhurtpainjump-sounds) | qubodup | CC0 1.0 | male strain/pain bursts |
| [male-dead-voice](https://opengameart.org/content/male-dead-voice) | mieki256 | CC0 1.0 | short male death cries |
| [man-hurt-sounds](https://opengameart.org/content/man-hurt-sounds) | Aharabada | CC0 1.0 | deep male roar of pain |
| [hurt-death-sound-effect-for-character](https://opengameart.org/content/hurt-death-sound-effect-for-character) | Badre-Eddine | CC0 1.0 | hurt/death cries |
| [pain-sounds-by-emopreben](https://opengameart.org/content/pain-sounds-by-emopreben) | EmoPreben | CC0 1.0 | grunts of pain |
| [evil-screech-1](https://opengameart.org/content/evil-screech-1) | Nocturnal_Vanguard | CC0 1.0 | screeches (jumpscreech, shriek) |
| [horror-scream1](https://opengameart.org/content/horror-scream1) | Vinrax | CC0 1.0 | high horror scream (jumpscreech) |
| [female-high-pitched-scream-sfx](https://opengameart.org/content/female-high-pitched-scream-sfx) | WuxiaScrub | CC0 1.0 | high screams (scream, jumpscreech) |
| [high-pitch-scream-sounds2](https://opengameart.org/content/high-pitch-scream-sounds2) | pauliuw | CC0 1.0 | high scream (jumpscreech) |
| [80-cc0-creature-sfx](https://opengameart.org/content/80-cc0-creature-sfx) | rubberduck | CC0 1.0 | creature screams/roars (jumpscreech, shriek) |
| [insect-or-alien-scream](https://opengameart.org/content/insect-or-alien-scream) | qubodup | CC0 1.0 | alien scream (shriek) |
| [sick-noises](https://opengameart.org/content/sick-noises) | frosty ham | CC0 1.0 | retching / gagging (gurgle) |
| [old-man-cough](https://opengameart.org/content/old-man-cough) | AntumDeluge | CC0 1.0 | wet cough (gurgle) |
| [ripping-into-meat](https://opengameart.org/content/ripping-into-meat) | Eldritch Grim | CC0 1.0 | gore foley: flesh tears |
| [slimy-monster-or-murder-sounds9](https://opengameart.org/content/slimy-monster-or-murder-sounds9) | pauliuw | CC0 1.0 | gore foley: wet impacts |
| [8-wet-squish-slurp-impacts](https://opengameart.org/content/8-wet-squish-slurp-impacts) | qubodup | CC0 1.0 | gore foley: squish |
| [2-wooden-squish-splatter-sequences](https://opengameart.org/content/2-wooden-squish-splatter-sequences) | qubodup | CC0 1.0 | gore foley: splatter, cracks |
| [40-wet-towel-clubpoundhitattack-sounds](https://opengameart.org/content/40-wet-towel-clubpoundhitattack-sounds) | qubodup | CC0 1.0 | gore foley: meaty hits |
| [5-hit-sounds-dying](https://opengameart.org/content/5-hit-sounds-dying) | TinyWorlds | CC0 1.0 | short male impact grunts |
| [bubble-sound-effects](https://opengameart.org/content/bubble-sound-effects) | BMacZero | CC0 1.0 | bubbles (underwater, gurgle) |
| [horror-breathing](https://opengameart.org/content/horror-breathing) | primbal | CC0 1.0 | breath_near |
| [breathing-tired](https://opengameart.org/content/breathing-tired) | mikeask | CC0 1.0 | breath_near |
| [ghost-breath](https://opengameart.org/content/ghost-breath) | qubodup | CC0 1.0 | breath_near |
| [scrapes](https://opengameart.org/content/scrapes) | AntumDeluge | CC0 1.0 | mood.scrape, scamper |

## Events from the pack

- `qf.scare.death_scream`: bubbles, deathpain, hurtdeath, maledead, manhurt, meat, sick, slimy
- `qf.scare.jumpscreech`: creature, deathpain, femscream, hipitch, horror1, hurtdeath, meat, screech
- `qf.scare.underwater`: bubbles, deathpain, manhurt, sick, slimy
- `qf.scare.static`: synthesised (noise and mains hum)
- `qf.scare.scream`: deathpain, femscream, hurtdeath, maledead, slimy
- `qf.scare.scream_far`: deathpain, femscream, hurtdeath, maledead, slimy
- `qf.scare.shriek`: creature, hipitch, insect, screech
- `qf.mood.scamper`: scrape
- `qf.mood.scrape`: scrape
- `qf.mood.breath_near`: horrorbreath, slimy, tiredbreath

## Mojang-derived (flagged `"mojang": true`; `build_sfx.py --own-only` drops them)

- `qf.mood.far_groan`: the bank's zombie / skeleton / enderman / ghast / spider / cat sounds, pitched down, low-passed, in a cave echo
- `qf.mood.far_rattle`: the bank's zombie / skeleton / enderman / ghast / spider / cat sounds, pitched down, low-passed, in a cave echo
- `qf.mood.far_vwoop`: the bank's zombie / skeleton / enderman / ghast / spider / cat sounds, pitched down, low-passed, in a cave echo
- `qf.mood.far_cry`: the bank's zombie / skeleton / enderman / ghast / spider / cat sounds, pitched down, low-passed, in a cave echo
- `qf.mood.far_hiss`: the bank's zombie / skeleton / enderman / ghast / spider / cat sounds, pitched down, low-passed, in a cave echo

## Freesound recordings (round 7 screams; all CC0 1.0, one real voice per file)

| Sound | Author | Licence | Events |
|---|---|---|---|
| [Startled, Tortured, and Terrified (Man)](https://freesound.org/people/ericnorcross81/sounds/575674/) | ericnorcross81 | CC0 1.0 | death_scream |
| [Man Screams His Death Into The Void](https://freesound.org/people/BlockFrog/sounds/752055/) | BlockFrog | CC0 1.0 | death_scream, underwater |
| [Male increasing scream - horror yelling in pain.wav](https://freesound.org/people/gtrempe/sounds/542128/) | gtrempe | CC0 1.0 | death_scream |
| [Pain man scream](https://freesound.org/people/Piement_infernal/sounds/724173/) | Piement_infernal | CC0 1.0 | death_scream, jumpscreech |
| [male scream pain torture.wav](https://freesound.org/people/martian/sounds/530471/) | martian | CC0 1.0 | death_scream |
| [Man screaming.wav](https://freesound.org/people/Archeos/sounds/325548/) | Archeos | CC0 1.0 | death_scream |
| [Guttural Screams.wav](https://freesound.org/people/fattirewhitey/sounds/381784/) | fattirewhitey | CC0 1.0 | death_scream |
| [Male Screams [1]](https://freesound.org/people/marc3122/sounds/556976/) | marc3122 | CC0 1.0 | scream |
| [Man Screams.WAV](https://freesound.org/people/Capt_Bligh1/sounds/690702/) | Capt_Bligh1 | CC0 1.0 | scream, scream_far |
| [screamimg pain](https://freesound.org/people/ronse/sounds/760720/) | ronse | CC0 1.0 | scream, scream_far |
| [Wounded man scream](https://freesound.org/people/joseppujol/sounds/221544/) | joseppujol | CC0 1.0 | jumpscreech |
| [manscreamingintowarmwaterfilledpot.WAV](https://freesound.org/people/Bemine2506/sounds/661477/) | Bemine2506 | CC0 1.0 | underwater |
| [young man screaming, pillow on face](https://freesound.org/people/WickedWeed/sounds/767590/) | WickedWeed | CC0 1.0 | underwater |

Built by `tools/music/scream_pack2.py` (trim, high-pass, presence, a pitch shift within one semitone, a short room, 48 kHz 160 kbps AAC).

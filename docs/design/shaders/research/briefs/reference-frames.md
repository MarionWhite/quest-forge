# Reference photos, one set per Shader Lab view

Written 2026-10-25 for the render-loop agent, so that every round can put a real-world frame
beside our render without a fresh search. One primary and one alternate per view where Commons
had a match; the file list is `tools/shaders/review/reference-frames.json` (the source of truth:
file page, download URL, author, licence, credit line, why it was chosen, an estimated sun
elevation, pixel size) and the images themselves are in `C:\qfb\shaderdev\refs\<view>-<n>.<ext>`
(not in the repo: `publish_round.py` resizes a reference to 1600 px and copies it into the round
when a round uses it). Every photo was checked on its own Commons file page on 2026-10-25: the
licence recorded here is the one the file page's licence template prints, not the category's.

## How to use them in a round

In the round spec, attach a reference to the option it should sit beside:

```
"ref": {"img": "C:/qfb/shaderdev/refs/ocean_sunset-1.jpg",
        "credit": "<credit from the JSON>",
        "source": "<source from the JSON>",
        "title": "<title from the JSON>"}
```

`publish_round.py` refuses a reference without `credit` and `source`. Copy both from the JSON
verbatim; the credit line is in the house style the round-6 publisher already writes
(`<Artist>, <licence>, via Wikimedia Commons`). The `why` field says what the photo is for; the
critic and the owner should read it as the question the photo answers, not as a target to copy.
The `sun_elevation_deg_estimate` is read off the photo (horizon, shadow length, the disc's
height) and is only there so a photo is not put beside a view whose sun is at a different
height; the view file's own numbers (`views-world-master.txt`, header) are the authority for
our side.

Which brief and scene each set supports:

- **Water** (`water.md`): `ocean_sunset`, `lake_glitter`, `lake_glow`, `shore_sunset`,
  `shore_noon`, `river_noon`, `beach_noon`, `biome_ocean`, `biome_swamp`, `ocean_swamp`,
  `river_swamp`, `underwater`. The sun-glitter pair (ocean_sunset) is the one to show beside
  any change to the glitter or path terms; the confluence pair (ocean_swamp, river_swamp) shows
  what a real colour boundary in water looks like, which is a soft mixing front, never a line
  across the surface.
- **Clouds** (`clouds.md`): `sky_noon`, `plains_noon`, `golden_lit`, `dawn_wide`, `night_full`,
  `night_moon`.
- **Sky** (`sky.md`): `dawn_wide`, `shore_dusk` (the twilight gradient toward the sun and the
  Earth-shadow side away from it), `biome_hills`, `biome_hillsplus` (aerial perspective),
  `night_sky`, `night_new`, `night_full`, `night_moon`.
- **Light shafts** (`light-shafts.md`): `forest_golden`, `forest_lit`, `leafview`,
  `biome_roofed`, `underwater`.
- **Tone mapping**, **bloom**, **AO**: no photo stands in for a display transform or for
  restraint; `golden_lit` (amber faces against blue shade), `plains_noon` (grass that must not
  go lime) and the night sets are the frames to judge those on. `texture_wall` and `glass_close`
  have no reference by design.
- **Biome fog** (the owner's per-biome asks): `biome_desert`, `biome_savanna`, `biome_taiga`,
  `biome_roofed`, `biome_swamp`, `biome_hills`, `biome_hillsplus`.

## The licence rule, restated

Only files whose own Commons file page states CC0, public domain, CC BY or CC BY-SA are in this
set; the rule in `README.md` applies to every future addition too. CC BY and CC BY-SA references
need the credit line next to the image wherever it is shown (the Lab page, the round JSON, this
doc) and a link to the file page; CC BY-SA ones may be resized for the page but not otherwise
edited (no crops, no colour work, no compositing with our render): if a crop is wanted, show the
whole frame and point at the region in the question text. CC0 and public-domain files carry no
obligation, but we credit them the same way so the page reads consistently and the owner can
find the original. Nothing from this set goes into the pack itself: these are references for
judging renders, not textures or sky images to ship.

## Views and picks

Thumbnail links open a 330 px rendition on Commons; the file page is the `source` link.

### `plains_noon` (yaw 135, pitch 8, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [20170703700DR Oberbobritzsch WEITES LAND.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f9/20170703700DR_Oberbobritzsch_WEITES_LAND.jpg/330px-20170703700DR_Oberbobritzsch_WEITES_LAND.jpg) ([file page](https://commons.wikimedia.org/wiki/File:20170703700DR_Oberbobritzsch_WEITES_LAND.jpg), 1920x1094 local) | Jörg Blobelt, CC BY-SA 4.0, via Wikimedia Commons | A flat field under a low horizon and a cumulus sky in early-afternoon sun: the plains_noon proportions of land to sky. Sun ~55 deg. |
| 2 | [2013-06-07 15-54-46-cumulus.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/0/00/2013-06-07_15-54-46-cumulus.jpg/330px-2013-06-07_15-54-46-cumulus.jpg) ([file page](https://commons.wikimedia.org/wiki/File:2013-06-07_15-54-46-cumulus.jpg), 1920x1280 local) | Thomas Bresson, CC BY 3.0, via Wikimedia Commons | Green meadow with a few trees under cumulus in afternoon light: the grass tone that must not go lime. Sun ~45 deg. |

### `forest_golden` (yaw 60, pitch 2, worldTime 12150)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Kiwihug 2017-05-24 (Unsplash).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e0/Kiwihug_2017-05-24_%28Unsplash%29.jpg/330px-Kiwihug_2017-05-24_%28Unsplash%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Kiwihug_2017-05-24_(Unsplash).jpg), 1920x1280 local) | Kiwihug, CC0, via Wikimedia Commons | Low sun seen through trunks with sharp beams, long shadows on mossy ground and a small figure for scale: the forest_golden beam scene. Sun ~8 deg. |
| 2 | [Sunrays in an autumn forest (Unsplash).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/c/ce/Sunrays_in_an_autumn_forest_%28Unsplash%29.jpg/330px-Sunrays_in_an_autumn_forest_%28Unsplash%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Sunrays_in_an_autumn_forest_(Unsplash).jpg), 1920x1371 local) | Ricardo Gomez Angel, CC0, via Wikimedia Commons | Warm autumn beams entering from the side with the sun out of frame; shows beams that stay readable without a visible source. Sun ~10 deg. |

### `golden_lit` (yaw 270, pitch 14, worldTime 12250)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Abandoned pickup at Kelvin A. Lewis farm in Creeds 3.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/4/4c/Abandoned_pickup_at_Kelvin_A._Lewis_farm_in_Creeds_3.jpg/330px-Abandoned_pickup_at_Kelvin_A._Lewis_farm_in_Creeds_3.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Abandoned_pickup_at_Kelvin_A._Lewis_farm_in_Creeds_3.jpg), 1920x1237 local) | PumpkinSky, CC BY-SA 3.0, via Wikimedia Commons | Sun a few degrees up behind the camera: every face toward it is amber, the tree line is lit from the front, and the sky stays blue; the golden_lit view with the sun at the camera's back. Sun ~5 deg. |
| 2 | [Cape Burhan, Shaman Rock, Olkhon Island, Lake Baikal, Russia.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f6/Cape_Burhan%2C_Shaman_Rock%2C_Olkhon_Island%2C_Lake_Baikal%2C_Russia.jpg/330px-Cape_Burhan%2C_Shaman_Rock%2C_Olkhon_Island%2C_Lake_Baikal%2C_Russia.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Cape_Burhan,_Shaman_Rock,_Olkhon_Island,_Lake_Baikal,_Russia.jpg), 1920x1276 local) | Vyacheslav Argenberg, CC BY 4.0, via Wikimedia Commons | Low evening sun from behind-right gilding cliffs and larches while the lake and sky hold their blue: amber faces against blue shade, with water. Sun ~8 deg. |

### `forest_lit` (yaw 250, pitch 4, worldTime 12150)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Camper's morning (Unsplash).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/7/75/Camper%27s_morning_%28Unsplash%29.jpg/330px-Camper%27s_morning_%28Unsplash%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Camper%27s_morning_(Unsplash).jpg), 1920x1280 local) | Michael Mroczek, CC0, via Wikimedia Commons | Low morning sun behind-left of the camera lighting trunks and canopy from the side with soft haze between them: the forest_lit framing. Sun ~10 deg. |
| 2 | [Crepuscular rays in the wood (21450795294).jpg](https://upload.wikimedia.org/wikipedia/commons/1/14/Crepuscular_rays_in_the_wood_%2821450795294%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Crepuscular_rays_in_the_wood_(21450795294).jpg), 1680x1120 local) | Rob Kemme, CC BY-SA 2.0, via Wikimedia Commons | Avenue of trees with the sun off to the side, lit trunks and shafts crossing the path; the lit-side view of a beam scene. Sun ~15 deg. |

### `shore_noon` (yaw 135, pitch 14, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Caustics Shallow Water Pic1.png](https://thumb.wikimedia.org/wikipedia/commons/thumb/1/1d/Caustics_Shallow_Water_Pic1.png/330px-Caustics_Shallow_Water_Pic1.png) ([file page](https://commons.wikimedia.org/wiki/File:Caustics_Shallow_Water_Pic1.png), 1920x1440 local) | Peacelovedeathmetal2, CC BY-SA 4.0, via Wikimedia Commons | Sunlit caustics on a sand bottom under a few centimetres of water at a beach: the caustic net's scale, contrast and sharpness at noon. Sun ~60 deg. |
| 2 | [Constructive interference.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0a/Constructive_interference.jpg/330px-Constructive_interference.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Constructive_interference.jpg), 1920x1440 local) | Scott Robinson, CC BY 2.0, via Wikimedia Commons | Ripple rings on a lake with their caustics on a sandy bed: a fresh-water version of the shallows with ripples and refraction together. Sun ~60 deg. |

### `shore_sunset` (yaw 100, pitch 6, worldTime 12650)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Kühlungsborn, Blick von der Seebrücke, Sonnenuntergang -- 2024 -- 5014-8.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/3/35/K%C3%BChlungsborn%2C_Blick_von_der_Seebr%C3%BCcke%2C_Sonnenuntergang_--_2024_--_5014-8.jpg/330px-K%C3%BChlungsborn%2C_Blick_von_der_Seebr%C3%BCcke%2C_Sonnenuntergang_--_2024_--_5014-8.jpg) ([file page](https://commons.wikimedia.org/wiki/File:K%C3%BChlungsborn,_Blick_von_der_Seebr%C3%BCcke,_Sonnenuntergang_--_2024_--_5014-8.jpg), 1920x1277 local) | Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons | Sun on the horizon, deep red, with a short path over calm water and groynes in silhouette; the 2-degree shore_sunset moment with the horizon band and cloud undersides lit. Sun ~1 deg. |
| 2 | [Sunset (40367604633).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5d/Sunset_%2840367604633%29.jpg/330px-Sunset_%2840367604633%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Sunset_(40367604633).jpg), 1920x1281 local) | Taymaz Valley, CC BY 2.0, via Wikimedia Commons | Sun about 2 degrees up in an orange haze over the sea with rocks in the foreground: the gradient from the sun's glow to the zenith, and the path over rippled water. Sun ~2 deg. |

### `shore_dusk` (yaw 100, pitch 6, worldTime 13000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Sunset Dscn1385.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c7/Sunset_Dscn1385.jpg/330px-Sunset_Dscn1385.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Sunset_Dscn1385.jpg), 1920x1440 local) | Titus Tscharntke, public domain, via Wikimedia Commons | Looking toward the sunset point half an hour after sunset: the orange-to-blue twilight gradient over a dark ridge, which is what shore_dusk's camera (yaw 100, sun 3 degrees down) sees. Sun ~-5 deg. |
| 2 | [Drei.Kraniche.im.Erdschattenbogen.Gaenselake.Stangenhagen.P1106005.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a8/Drei.Kraniche.im.Erdschattenbogen.Gaenselake.Stangenhagen.P1106005.jpg/330px-Drei.Kraniche.im.Erdschattenbogen.Gaenselake.Stangenhagen.P1106005.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Drei.Kraniche.im.Erdschattenbogen.Gaenselake.Stangenhagen.P1106005.jpg), 1920x1440 local) | Bautsch, CC0, via Wikimedia Commons | The other half of the same sky: Earth's shadow and the Belt of Venus over a reedy lake, for the anti-solar side of the dusk gradient. Sun ~-4 deg. |

### `night_full` (yaw 135, pitch 8, worldTime 18000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Moonlit Reflections.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6e/Moonlit_Reflections.jpg/330px-Moonlit_Reflections.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Moonlit_Reflections.jpg), 1920x1440 local) | Derk29, CC BY-SA 4.0, via Wikimedia Commons | High full moon over a lake with its glitter path, a glow halo and a navy sky with a few stars, land in silhouette: the night_full view across the lake. |
| 2 | [By the Light of the Moon (46694367714).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/5/57/By_the_Light_of_the_Moon_%2846694367714%29.jpg/330px-By_the_Light_of_the_Moon_%2846694367714%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:By_the_Light_of_the_Moon_(46694367714).jpg), 1920x1282 local) | Jason Jacobs, CC BY 2.0, via Wikimedia Commons | Moonlit coast where the land and water colours stay readable under the moon, with stars still visible: the brightness balance for a playable full-moon night. |

### `night_new` (yaw 135, pitch 8, worldTime 114000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Milky Way - First attempt (50259168433).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/5/54/Milky_Way_-_First_attempt_%2850259168433%29.jpg/330px-Milky_Way_-_First_attempt_%2850259168433%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Milky_Way_-_First_attempt_(50259168433).jpg), 1920x1440 local) | Josef Laimer, CC BY 2.0, via Wikimedia Commons | Moonless night over a lake with mountains: the land stays just readable while the sky carries the detail, which is the new-moon balance the owner asked for. |
| 2 | [Milky Way Glacier Point (Unsplash).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/1/1d/Milky_Way_Glacier_Point_%28Unsplash%29.jpg/330px-Milky_Way_Glacier_Point_%28Unsplash%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Milky_Way_Glacier_Point_(Unsplash).jpg), 1920x1280 local) | Jakub Gorajek, CC0, via Wikimedia Commons | Moonless sky over a tree line: a near-black silhouette ground with a rich, deep sky and no lamp glow. |

### `underwater` (yaw 135, pitch -4, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Soleil à travers un paysage sous-marin de Bretagne (Ifremer 00378-48922 - 902).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0b/Soleil_%C3%A0_travers_un_paysage_sous-marin_de_Bretagne_%28Ifremer_00378-48922_-_902%29.jpg/330px-Soleil_%C3%A0_travers_un_paysage_sous-marin_de_Bretagne_%28Ifremer_00378-48922_-_902%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Soleil_%C3%A0_travers_un_paysage_sous-marin_de_Bretagne_(Ifremer_00378-48922_-_902).jpg), 1920x1281 local) | Olivier Dugornay, CC BY 4.0, via Wikimedia Commons | The sun seen from below the surface with shafts fanning down through green water: the underwater light-shaft and fog-volume reference for a lake. Sun ~50 deg. |
| 2 | [Full Shot of a Caribbean Reef Shark at Tiger Beach Bahamas.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3c/Full_Shot_of_a_Caribbean_Reef_Shark_at_Tiger_Beach_Bahamas.jpg/330px-Full_Shot_of_a_Caribbean_Reef_Shark_at_Tiger_Beach_Bahamas.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Full_Shot_of_a_Caribbean_Reef_Shark_at_Tiger_Beach_Bahamas.jpg), 1920x1440 local) | Dennis Hipp (Zepto), CC0, via Wikimedia Commons | Sand ripples with caustics on the bed, the rippled surface seen from below and the blue water column between: the whole underwater composition in one frame. Sun ~60 deg. |
| 3 | [Reflet du soleil sur la mer Méditerranée (Ifremer 00729-84104 - 37514).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b9/Reflet_du_soleil_sur_la_mer_M%C3%A9diterran%C3%A9e_%28Ifremer_00729-84104_-_37514%29.jpg/330px-Reflet_du_soleil_sur_la_mer_M%C3%A9diterran%C3%A9e_%28Ifremer_00729-84104_-_37514%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Reflet_du_soleil_sur_la_mer_M%C3%A9diterran%C3%A9e_(Ifremer_00729-84104_-_37514).jpg), 1920x1281 local) | Olivier Dugornay, CC BY 4.0, via Wikimedia Commons | Clear blue water with the sun's disc and glare through the surface and the darkening with depth: the clear-water version beside the green one. Sun ~55 deg. |

### `night_moon` (yaw 90, pitch -72, worldTime 18000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Al-Jahra Full moon.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/9/96/Al-Jahra_Full_moon.jpg/330px-Al-Jahra_Full_moon.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Al-Jahra_Full_moon.jpg), 1920x2560 local) | Miskat2006, CC BY-SA 4.0, via Wikimedia Commons | Full moon high in the sky with broken cloud around it, cloud edges lit and a soft corona: the night_moon look-up with cloud rims. |
| 2 | [Full Moon In The Clouds, August 19, 2024, 4-01 a.m. - Flickr - the bridge.jpg](https://upload.wikimedia.org/wikipedia/commons/c/c2/Full_Moon_In_The_Clouds%2C_August_19%2C_2024%2C_4-01_a.m._-_Flickr_-_the_bridge.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Full_Moon_In_The_Clouds,_August_19,_2024,_4-01_a.m._-_Flickr_-_the_bridge.jpg), 1920x1080 local) | David Saddler, CC BY 2.0, via Wikimedia Commons | Moon through thin cloud with the glow spreading into the cloud sheet: the halo scale against a dark sky. |

### `dawn_wide` (yaw 135, pitch 4, worldTime 23400)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Münster, Aasee -- 2020 -- 9282-6.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/1/18/M%C3%BCnster%2C_Aasee_--_2020_--_9282-6.jpg/330px-M%C3%BCnster%2C_Aasee_--_2020_--_9282-6.jpg) ([file page](https://commons.wikimedia.org/wiki/File:M%C3%BCnster,_Aasee_--_2020_--_9282-6.jpg), 1920x1280 local) | Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons | A lake at sunrise with the sun a degree or two up behind trees, a still mirror and cumulus lit from below: dawn_wide over water. Sun ~2 deg. |
| 2 | [Dülmen, Börnste, Sonnenaufgang -- 2020 -- 6075-9.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/5/59/D%C3%BClmen%2C_B%C3%B6rnste%2C_Sonnenaufgang_--_2020_--_6075-9.jpg/330px-D%C3%BClmen%2C_B%C3%B6rnste%2C_Sonnenaufgang_--_2020_--_6075-9.jpg) ([file page](https://commons.wikimedia.org/wiki/File:D%C3%BClmen,_B%C3%B6rnste,_Sonnenaufgang_--_2020_--_6075-9.jpg), 1920x1280 local) | Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons | Clear-sky sunrise over a meadow with the sun on the horizon between two trees: the clean dawn sky gradient without clouds. Sun ~1 deg. |

### `leafview` (yaw 180, pitch 0, worldTime 10000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Leaves-Canopy-6859.jpg](https://upload.wikimedia.org/wikipedia/commons/e/e3/Leaves-Canopy-6859.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Leaves-Canopy-6859.jpg), 1872x2816 local) | Loadmaster (David R. Tribble), CC BY-SA 3.0, via Wikimedia Commons | Backlit leaves from inside a canopy with the sun above: the translucent green of lit leaves against the darker underside of the rest, which is what the leaves test is about. Sun ~35 deg. |
| 2 | [Autumn Sunlight Penetrating the Canopy Alpine Meadow - geograph.org.uk - 2626877.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b2/Autumn_Sunlight_Penetrating_the_Canopy_Alpine_Meadow_-_geograph.org.uk_-_2626877.jpg/330px-Autumn_Sunlight_Penetrating_the_Canopy_Alpine_Meadow_-_geograph.org.uk_-_2626877.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Autumn_Sunlight_Penetrating_the_Canopy_Alpine_Meadow_-_geograph.org.uk_-_2626877.jpg), 1920x1289 local) | Martin (geograph.org.uk), CC BY-SA 2.0, via Wikimedia Commons | A level view inside a wood with low sun through the leaves, lit crowns and soft shafts: the leafview camera's horizontal framing. Sun ~20 deg. |

### `lake_glow` (yaw 97, pitch 3, worldTime 12400)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Dülmen, Kirchspiel, Oedlerteich -- 2016 -- 1952-8.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b4/D%C3%BClmen%2C_Kirchspiel%2C_Oedlerteich_--_2016_--_1952-8.jpg/330px-D%C3%BClmen%2C_Kirchspiel%2C_Oedlerteich_--_2016_--_1952-8.jpg) ([file page](https://commons.wikimedia.org/wiki/File:D%C3%BClmen,_Kirchspiel,_Oedlerteich_--_2016_--_1952-8.jpg), 1920x1280 local) | Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons | Sun about 6 degrees up over a sheltered pond: a soft path on nearly still water, reeds in silhouette and a warm sky with cirrus; the lake_glow view. Sun ~6 deg. |
| 2 | [Dülmen, Kirchspiel, Oedlerteich -- 2016 -- 1966.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c5/D%C3%BClmen%2C_Kirchspiel%2C_Oedlerteich_--_2016_--_1966.jpg/330px-D%C3%BClmen%2C_Kirchspiel%2C_Oedlerteich_--_2016_--_1966.jpg) ([file page](https://commons.wikimedia.org/wiki/File:D%C3%BClmen,_Kirchspiel,_Oedlerteich_--_2016_--_1966.jpg), 1920x1280 local) | Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons | The same pond with the sun behind the trees: the mirror where little direct light reaches the surface, which is where our water went splotchy in round 6. Sun ~4 deg. |

### `night_sky` (yaw 200, pitch -45, worldTime 114000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Milky Way and tree from Inferno Cone (36882988746).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ee/Milky_Way_and_tree_from_Inferno_Cone_%2836882988746%29.jpg/330px-Milky_Way_and_tree_from_Inferno_Cone_%2836882988746%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Milky_Way_and_tree_from_Inferno_Cone_(36882988746).jpg), 1920x1280 local) | Craters of the Moon National Monument & Preserve (US National Park Service), public domain, via Wikimedia Commons | The Milky Way core at about 45 degrees over a lone tree with a dark horizon: the night_sky framing with a photographic galaxy, the look the owner rated in round 6. |
| 2 | [Meteors and the Milky Way (Meterorite-Jfuentes-CC).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d5/Meteors_and_the_Milky_Way_%28Meterorite-Jfuentes-CC%29.jpg/330px-Meteors_and_the_Milky_Way_%28Meterorite-Jfuentes-CC%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Meteors_and_the_Milky_Way_(Meterorite-Jfuentes-CC).jpg), 1920x1280 local) | NOIRLab/AURA/NSF/J. Fuentes, CC BY 4.0, via Wikimedia Commons | Milky Way with meteor streaks and green airglow near the horizon: the reference for the meteor-shower night the owner asked for after round 6. |

### `biome_swamp` (yaw 135, pitch 4, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [2025-06-04 13 37 39 View east through the Trap Pond Bald Cypress Swamp within Trap Pond State Park in Sussex County, Delaware.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/3/34/2025-06-04_13_37_39_View_east_through_the_Trap_Pond_Bald_Cypress_Swamp_within_Trap_Pond_State_Park_in_Sussex_County%2C_Delaware.jpg/330px-2025-06-04_13_37_39_View_east_through_the_Trap_Pond_Bald_Cypress_Swamp_within_Trap_Pond_State_Park_in_Sussex_County%2C_Delaware.jpg) ([file page](https://commons.wikimedia.org/wiki/File:2025-06-04_13_37_39_View_east_through_the_Trap_Pond_Bald_Cypress_Swamp_within_Trap_Pond_State_Park_in_Sussex_County,_Delaware.jpg), 1920x1440 local) | Famartin, CC BY-SA 4.0, via Wikimedia Commons | Dark tea-coloured water between cypress trunks at midday, reflections and almost no view of the bed: the murky teal-brown swamp water and its dim light. Sun ~65 deg. |
| 2 | [2025-06-04 12 08 52 Bald Cypress trees along the south shore of Trap Pond within Trap Pond State Park in Sussex County, Delaware.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a2/2025-06-04_12_08_52_Bald_Cypress_trees_along_the_south_shore_of_Trap_Pond_within_Trap_Pond_State_Park_in_Sussex_County%2C_Delaware.jpg/330px-2025-06-04_12_08_52_Bald_Cypress_trees_along_the_south_shore_of_Trap_Pond_within_Trap_Pond_State_Park_in_Sussex_County%2C_Delaware.jpg) ([file page](https://commons.wikimedia.org/wiki/File:2025-06-04_12_08_52_Bald_Cypress_trees_along_the_south_shore_of_Trap_Pond_within_Trap_Pond_State_Park_in_Sussex_County,_Delaware.jpg), 1920x1440 local) | Famartin, CC BY-SA 4.0, via Wikimedia Commons | Open swamp water with cypress standing in it under a blue noon sky: the swamp's water colour where sky light reaches it, beside the dense version. Sun ~70 deg. |

### `biome_hills` (yaw 180, pitch 4, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Blue Mountains National Park (AU), Three Sisters -- 2019 -- 2009.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b4/Blue_Mountains_National_Park_%28AU%29%2C_Three_Sisters_--_2019_--_2009.jpg/330px-Blue_Mountains_National_Park_%28AU%29%2C_Three_Sisters_--_2019_--_2009.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Blue_Mountains_National_Park_(AU),_Three_Sisters_--_2019_--_2009.jpg), 1920x1280 local) | Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons | Rock and scrub crisp at the camera's elevation while the valley floor and far cliffs go blue with distance: the height-aware haze the owner asked for in round 4. Sun ~45 deg. |
| 2 | [Blue ridge Mountains layered.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/5/50/Blue_ridge_Mountains_layered.jpg/330px-Blue_ridge_Mountains_layered.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Blue_ridge_Mountains_layered.jpg), 1920x1440 local) | Pdekyvere, CC BY-SA 4.0, via Wikimedia Commons | Ridges receding in six tones toward a low sun: the aerial-perspective ramp from near to far. Sun ~10 deg. |

### `biome_hillsplus` (yaw 180, pitch 2, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [MonNatForest.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/4/4e/MonNatForest.jpg/330px-MonNatForest.jpg) ([file page](https://commons.wikimedia.org/wiki/File:MonNatForest.jpg), 1920x1440 local) | Valerius Tygart, CC BY-SA 3.0, via Wikimedia Commons | Forested ridges in daylight with each layer bluer and lighter than the last and the near trees fully saturated: Extreme Hills+ with trees. Sun ~50 deg. |
| 2 | [Knob lick view-26aug06.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/ba/Knob_lick_view-26aug06.jpg/330px-Knob_lick_view-26aug06.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Knob_lick_view-26aug06.jpg), 1920x1245 local) | Kbh3rd, CC BY-SA 3.0, via Wikimedia Commons | Fields and trees at eye level crisp, distant hills hazy: haze that depends on distance and height below the camera. Sun ~45 deg. |

### `biome_roofed` (yaw 135, pitch 4, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Beech forest in Kokkozka Valley, Mystery, Crimea.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a8/Beech_forest_in_Kokkozka_Valley%2C_Mystery%2C_Crimea.jpg/330px-Beech_forest_in_Kokkozka_Valley%2C_Mystery%2C_Crimea.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Beech_forest_in_Kokkozka_Valley,_Mystery,_Crimea.jpg), 1920x1280 local) | Vyacheslav Argenberg, CC BY 4.0, via Wikimedia Commons | Closed beech canopy with a dim, slightly misty interior and only scattered light reaching the floor: the Roofed Forest's darkness at midday. Sun ~40 deg. |
| 2 | [Beech and ferns in Gullmarsskogen.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/bb/Beech_and_ferns_in_Gullmarsskogen.jpg/330px-Beech_and_ferns_in_Gullmarsskogen.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Beech_and_ferns_in_Gullmarsskogen.jpg), 1920x1280 local) | W.carter, CC0, via Wikimedia Commons | Forest floor under a dark canopy with ferns picked out by filtered light: how much the floor reads under a closed canopy. Sun ~55 deg. |

### `biome_savanna` (yaw 135, pitch 4, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Maasai-Mara-Typical-Scenery.JPG](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/bd/Maasai-Mara-Typical-Scenery.JPG/330px-Maasai-Mara-Typical-Scenery.JPG) ([file page](https://commons.wikimedia.org/wiki/File:Maasai-Mara-Typical-Scenery.JPG), 1920x1205 local) | Bjørn Christian Tørrissen, CC BY-SA 3.0, via Wikimedia Commons | Gold grass to the horizon with low hills going hazy under cumulus at 13:45: the savanna biome's land, sky and distance haze at midday. Sun ~70 deg. |
| 2 | [Acacia (Vachellia tortilis), parque nacional Serengueti, Tanzania, 2024-05-26, DD 26.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d8/Acacia_%28Vachellia_tortilis%29%2C_parque_nacional_Serengueti%2C_Tanzania%2C_2024-05-26%2C_DD_26.jpg/330px-Acacia_%28Vachellia_tortilis%29%2C_parque_nacional_Serengueti%2C_Tanzania%2C_2024-05-26%2C_DD_26.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Acacia_(Vachellia_tortilis),_parque_nacional_Serengueti,_Tanzania,_2024-05-26,_DD_26.jpg), 1920x1280 local) | Diego Delso, CC BY-SA 4.0, via Wikimedia Commons | Two flat-topped acacias on green-gold grass under a hazy bright sky: the acacia form the biome's trees stand in for. Sun ~45 deg. |

### `biome_desert` (yaw 90, pitch 4, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Erg Chebbi 01.JPG](https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0d/Erg_Chebbi_01.JPG/330px-Erg_Chebbi_01.JPG) ([file page](https://commons.wikimedia.org/wiki/File:Erg_Chebbi_01.JPG), 1920x1277 local) | Andreine, CC BY-SA 3.0, via Wikimedia Commons | Pale dunes under a bright, hazy desert sky near midday, soft shadows and a figure for scale: the desert biome's light and its washed sky. Sun ~45 deg. |
| 2 | [Erg Chebbi (4804565176).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/9/98/Erg_Chebbi_%284804565176%29.jpg/330px-Erg_Chebbi_%284804565176%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Erg_Chebbi_(4804565176).jpg), 1920x1280 local) | Mike Prince, CC BY 2.0, via Wikimedia Commons | Orange dunes with sparse scrub under a paler sky with the sun lower: dune shading and the sand colour against a clear sky. Sun ~20 deg. |

### `biome_taiga` (yaw 135, pitch 4, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Ergaki, Taiga in Siberia, Coniferous forest, Sayan Mountains, Siberia, Russia.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/6/69/Ergaki%2C_Taiga_in_Siberia%2C_Coniferous_forest%2C_Sayan_Mountains%2C_Siberia%2C_Russia.jpg/330px-Ergaki%2C_Taiga_in_Siberia%2C_Coniferous_forest%2C_Sayan_Mountains%2C_Siberia%2C_Russia.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Ergaki,_Taiga_in_Siberia,_Coniferous_forest,_Sayan_Mountains,_Siberia,_Russia.jpg), 1920x1280 local) | Vyacheslav Argenberg, CC BY 4.0, via Wikimedia Commons | Siberian taiga at midday: dark conifers, a lake and lighter meadow, with the far ridge going blue; the taiga biome's palette and haze. Sun ~50 deg. |
| 2 | [Lake shore, Wild taiga forest, Krasnoyarsk Reservoir, Russia.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/7/76/Lake_shore%2C_Wild_taiga_forest%2C_Krasnoyarsk_Reservoir%2C_Russia.jpg/330px-Lake_shore%2C_Wild_taiga_forest%2C_Krasnoyarsk_Reservoir%2C_Russia.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Lake_shore,_Wild_taiga_forest,_Krasnoyarsk_Reservoir,_Russia.jpg), 1920x1280 local) | Vyacheslav Argenberg, CC BY 4.0, via Wikimedia Commons | Dense spruce and pine on a lake shore under an overcast sky: the taiga's near-black greens beside water. Sun ~40 deg. |

### `biome_ocean` (yaw 90, pitch 4, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Wave open sea.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/d/de/Wave_open_sea.jpg/330px-Wave_open_sea.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Wave_open_sea.jpg), 1920x1440 local) | Unknown author, public domain, via Wikimedia Commons | Open sea at midday from just above the surface, saturated deep blue with a breaking crest and the horizon mid-frame: the deep-blue ocean the owner asked for. Sun ~55 deg. |
| 2 | [The Horizon Where Sea Meets Sky.png](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b9/The_Horizon_Where_Sea_Meets_Sky.png/330px-The_Horizon_Where_Sea_Meets_Sky.png) ([file page](https://commons.wikimedia.org/wiki/File:The_Horizon_Where_Sea_Meets_Sky.png), 1920x2560 local) | AustinXia, CC BY-SA 4.0, via Wikimedia Commons | Clear tropical sea from the surface: the bed showing through near the camera, deep blue toward the horizon, cumulus above; the clarity-to-depth gradient at sea. Sun ~60 deg. |

### `river_noon` (yaw 344, pitch 8, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [View of the Clear Water of the Conasauga River (5812266280).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/e/eb/View_of_the_Clear_Water_of_the_Conasauga_River_%285812266280%29.jpg/330px-View_of_the_Clear_Water_of_the_Conasauga_River_%285812266280%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:View_of_the_Clear_Water_of_the_Conasauga_River_(5812266280).jpg), 1920x1280 local) | U.S. Fish and Wildlife Service Southeast Region, public domain, via Wikimedia Commons | Looking along a clear river from just above the surface: mirror reflection far away, the bed showing through near the camera, trees both sides; the river_noon framing. Sun ~55 deg. |
| 2 | [Crystal clear river water.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/5/59/Crystal_clear_river_water.jpg/330px-Crystal_clear_river_water.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Crystal_clear_river_water.jpg), 1920x1080 local) | Satyanadipally3541, CC BY-SA 4.0, via Wikimedia Commons | A half-clear river with a faint green tint over a sandy bed: the slightly green, half-transparent river the round-4 and round-6 critic notes asked for. Sun ~70 deg. |

### `beach_noon` (yaw 293, pitch 10, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Bathala (Maldives) 6.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/5/57/Bathala_%28Maldives%29_6.jpg/330px-Bathala_%28Maldives%29_6.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Bathala_(Maldives)_6.jpg), 1920x1211 local) | Gzzz, CC BY-SA 4.0, via Wikimedia Commons | The Maldives gradient from white sand through turquoise to deep blue at the horizon under a noon sky: the coast colour the owner named. Sun ~55 deg. |
| 2 | [Clear Water at Kuredu Island, Maldives (4550565234).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d8/Clear_Water_at_Kuredu_Island%2C_Maldives_%284550565234%29.jpg/330px-Clear_Water_at_Kuredu_Island%2C_Maldives_%284550565234%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Clear_Water_at_Kuredu_Island,_Maldives_(4550565234).jpg), 1920x1440 local) | wardyboy400, CC BY 2.0, via Wikimedia Commons | Shallow lagoon with the bed showing through pale turquoise ripples and clouds reflected: the near-water clarity on a coast without land in frame. Sun ~50 deg. |

### `lake_glitter` (yaw 97, pitch 3, worldTime 12150)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Haltern am See, Seebucht Hohe Niemen -- 2014 -- 1157.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3a/Haltern_am_See%2C_Seebucht_Hohe_Niemen_--_2014_--_1157.jpg/330px-Haltern_am_See%2C_Seebucht_Hohe_Niemen_--_2014_--_1157.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Haltern_am_See,_Seebucht_Hohe_Niemen_--_2014_--_1157.jpg), 1920x1236 local) | Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons | Sun about 10 degrees up in frame over a calm lake bay with a glitter path running all the way to the camera and a dark tree line: the lake_glitter framing. Sun ~10 deg. |
| 2 | [Haldensee Sunset DJI.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e1/Haldensee_Sunset_DJI.jpg/330px-Haldensee_Sunset_DJI.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Haldensee_Sunset_DJI.jpg), 1920x1280 local) | Christian Namesnik, CC BY-SA 4.0, via Wikimedia Commons | A mountain lake with the sun just over a ridge and its path on the water between dark slopes: the cliff-shaded lake with a path, from above. Sun ~3 deg. |

### `ocean_sunset` (yaw 96, pitch 3, worldTime 12150)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Zoutelande (NL), Strand, Blick auf die Nordsee -- 2022 -- 4984.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b8/Zoutelande_%28NL%29%2C_Strand%2C_Blick_auf_die_Nordsee_--_2022_--_4984.jpg/330px-Zoutelande_%28NL%29%2C_Strand%2C_Blick_auf_die_Nordsee_--_2022_--_4984.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Zoutelande_(NL),_Strand,_Blick_auf_die_Nordsee_--_2022_--_4984.jpg), 1920x1440 local) | Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons | Open sea into a sun about 8 degrees up in haze, horizon just above mid-frame, one glitter path running to the camera and a sailboat for scale: the ocean_sunset framing almost exactly. Sun ~8 deg. |
| 2 | [Sunset sea Tenerife.JPG](https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d1/Sunset_sea_Tenerife.JPG/330px-Sunset_sea_Tenerife.JPG) ([file page](https://commons.wikimedia.org/wiki/File:Sunset_sea_Tenerife.JPG), 1920x2560 local) | Piotr Konieczny (Piotrus), CC BY-SA 3.0, via Wikimedia Commons | A whole frame of sun glitter from a higher sun kept out of frame: shows how glints densify toward the sun and break into points near the camera. Sun ~20 deg. |

### `sky_noon` (yaw 135, pitch -22, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [2013-05-19 15-04-20-nuages.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ae/2013-05-19_15-04-20-nuages.jpg/330px-2013-05-19_15-04-20-nuages.jpg) ([file page](https://commons.wikimedia.org/wiki/File:2013-05-19_15-04-20-nuages.jpg), 1920x1440 local) | Thomas Bresson, CC BY 3.0, via Wikimedia Commons | A field of cumulus mediocris at mid-afternoon with bright tops, grey flat bases and blue between: the sky_noon tilt-up. Sun ~50 deg. |
| 2 | [2013-05-25 13-20-11-nuages.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ef/2013-05-25_13-20-11-nuages.jpg/330px-2013-05-25_13-20-11-nuages.jpg) ([file page](https://commons.wikimedia.org/wiki/File:2013-05-25_13-20-11-nuages.jpg), 1920x1440 local) | Thomas Bresson, CC BY 3.0, via Wikimedia Commons | Scattered cumulus humilis in a deep blue sky lit from the side: cloud shape and shading without a solid deck. Sun ~60 deg. |

### `ocean_swamp` (yaw 220, pitch 8, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Confluence de l'Arve et du Rhône 2024.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/d/de/Confluence_de_l%27Arve_et_du_Rh%C3%B4ne_2024.jpg/330px-Confluence_de_l%27Arve_et_du_Rh%C3%B4ne_2024.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Confluence_de_l%27Arve_et_du_Rh%C3%B4ne_2024.jpg), 1920x2560 local) | Hadi, CC0, via Wikimedia Commons | Turquoise Rhône meeting silt-grey Arve: the colour boundary is a feathered, lobed mixing front tens of metres wide, never a line; the gradient the owner asked for at ocean-to-swamp borders. Sun ~50 deg. |
| 2 | [AnaClaudiaJatahy Econtro das Águas Manaus AM (41107583642).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/1/10/AnaClaudiaJatahy_Econtro_das_%C3%81guas_Manaus_AM_%2841107583642%29.jpg/330px-AnaClaudiaJatahy_Econtro_das_%C3%81guas_Manaus_AM_%2841107583642%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:AnaClaudiaJatahy_Econtro_das_%C3%81guas_Manaus_AM_(41107583642).jpg), 1920x993 local) | MTur Destinos, public domain, via Wikimedia Commons | Black Rio Negro beside sandy Solimões water: a dark, tannin water meeting a bright silty one, the closest real pair to swamp water next to ocean. Sun ~40 deg. |

### `river_swamp` (yaw 260, pitch 9, worldTime 6000)

| # | Photo | Credit | Why |
|---|---|---|---|
| 1 | [Converging rivers, Geneva (16197721795).jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a6/Converging_rivers%2C_Geneva_%2816197721795%29.jpg/330px-Converging_rivers%2C_Geneva_%2816197721795%29.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Converging_rivers,_Geneva_(16197721795).jpg), 1920x1280 local) | x70tjw, CC BY-SA 2.0, via Wikimedia Commons | Looking down the Rhône and Arve from the bridge: green clear water and tan silty water running side by side, mixing along a soft edge with sun glints on both. Sun ~45 deg. |
| 2 | [Confluence de l'Arve et du Rhône.jpg](https://thumb.wikimedia.org/wikipedia/commons/thumb/6/69/Confluence_de_l%27Arve_et_du_Rh%C3%B4ne.jpg/330px-Confluence_de_l%27Arve_et_du_Rh%C3%B4ne.jpg) ([file page](https://commons.wikimedia.org/wiki/File:Confluence_de_l%27Arve_et_du_Rh%C3%B4ne.jpg), 1920x1080 local) | Christian David, CC BY 4.0, via Wikimedia Commons | The wider confluence in autumn light with the mixing zone seen at a lower angle: how far the colour front stretches downstream. Sun ~25 deg. |


## Not covered

- `texture_wall`, `glass_close`: no photographic reference by design (tone-mapping and
  texture questions are judged on the owner's phone against the look bible).
- Known compromises, kept because nothing closer was openly licensed: `night_new` uses two
  moonless starfields whose land is near black (the view's land should stay readable, so judge
  the sky on them, not the ground); `lake_glitter` 2 and `ocean_swamp` 2 are drone and
  aerial views, higher than any Shader Lab camera; `shore_dusk` 1 has no water in frame;
  `leafview` 1 and `night_moon` 1 are portrait frames.

## Keeping the set current

Add a candidate to `tools/shaders/review/reference-frames.json` only after opening its file
page and reading the licence template there; record `licence_on_file_page` as the page prints
it. Re-check a file before reusing it in a round if its record is older than a few months:
Commons files get relicensed and deleted.

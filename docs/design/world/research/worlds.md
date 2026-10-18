# What makes the best game worlds great, and how to apply it to a 32k x 32k Minecraft continent

Research date: 2026-10-17. Confidence tags: **[V]** = checked against the cited source; **[S]** = secondary or fan source; **[M]** = from memory or game code knowledge, not re-checked here; **[J]** = my own judgement.

---

## 0. The scale problem comes first

| World | Approx. area | Source |
|---|---|---|
| Skyrim | 37 to 41 km² | fan estimates via GamePro [S] |
| BotW Hyrule | 62 to 84 km² (most-cited figure is about 72 to 84) | Guinness (fan calculation), GamePro [S] |
| Elden Ring, Lands Between | about 79 km² (GamePro instead gives 24 km² total, 12 km² playable) | ggrecon, GamePro [S, sources conflict] |
| Witcher 3 | Velen/Novigrad 8.5 x 8.5 km plus Skellige 8 x 8 km = about 136 km² for just those two | CDPR/Umbra slide via DualShockers [S] |
| Valheim | circle with 10 km radius = about 314 km², including ocean | cybrancee guide [S] |
| Wynncraft (hand-built MC MMO) | 4,000 x 5,000 blocks = 20 km², built by a team over 4+ years | mein-mmo [S] |
| **Your continent** | **32 x 32 km = 1,024 km²** | |

Your continent has about **13x the area of Elden Ring, 12x BotW, 25x Skyrim and 50x Wynncraft**.

Travel times across it:

| Mode | Speed | 1 km | Coast to coast (32 km) |
|---|---|---|---|
| Sprinting on foot | 5.6 m/s | 3 min | 95 min |
| Vanilla horse, best case | about 14 m/s [M] | | about 38 min |
| Jet | 56 m/s | | 9.5 min |

**Render distance is the binding constraint, not world size [M].** In Minecraft 1.7.10, nothing outside the loaded chunk radius is drawn. At 5 to 8 chunks the horizon sits 80 to 128 blocks away, and vanilla fog starts at roughly the last quarter of that. AAA worlds are built around landmarks visible from several kilometres away (Witcher 3 uses a "super-high draw distance" so "you can see all the interesting spots from far away" [V, DualShockers]). On a friend's PC, this world shows a disc only about 100 blocks across.

Two consequences shape everything below:

- The "Erdtree on the horizon" trick does not work natively.
- A jet at 56 m/s crosses that whole visible disc in about 2 seconds, so flight shows the player almost nothing in advance. It also asks a weak PC to load and generate about 3.5 chunks per second.

---

## 1. Per-game findings

### Breath of the Wild / Tears of the Kingdom (Nintendo)

These come from the CEDEC 2017 talk "Field Level Design: How the Land of Hyrule Was Made", given by Fujibayashi and Makoto Yonezu.

**Triangle rule [V].**
- Triangular hills and mountains give the player a choice: climb over or go around.
- A triangle hides what is behind it and reveals it *gradually* as you move. A rectangle (cliff, wall, tree block) hides things completely and reveals them *suddenly*.
- A hill also promises a view from its top, which builds anticipation.
- Triangles work at three scales:
  - large ones are landmarks;
  - medium ones screen landmarks and routes;
  - small ones set the pace of exploration.
- Important things (shrines, Koroks) sit near the tips of triangles, because a triangle's tip draws the eye.
- Example: the approach to a Sheikah tower is staged as hill, then bridge, then tower, so the structure is "slowly revealed".
- Sources: [Gigazine CEDEC report](https://gigazine.net/gsc_news/en/20171004-breath-of-the-wild-design-secret), [Denfaminico report](https://news.denfaminicogamer.jp/kikakuthetower/171016).

**Gravity (引力) [V].**
- Landmarks have "pull" that scales with their size and importance. Story-critical, distinctive structures pull hardest.
- Different objects pull with different strength, so the player's route bends between them.
- Stables all carry a giant horse head so they read from a distance [S].
- Source: [Denfaminico report](https://news.denfaminicogamer.jp/kikakuthetower/171016).

**Heat-map playtests [V].**
- Nintendo recorded testers' actual routes as heat maps.
- Before tuning, most testers followed similar routes and large areas went unvisited.
- After they added attraction points (using the tower as the reference point), routes spread across the map.
- Side effect: some testers then felt "guided" and called the game "too linear".
- Source: [Gigazine](https://gigazine.net/gsc_news/en/20171004-breath-of-the-wild-design-secret).

**Kyoto [S].** The map began as a topographic map of Kyoto that was then reshaped into Hyrule. Treat this as a statement about terrain scale, not a measured area; Kyoto's area does not match the cited Hyrule figures.

**Density.**
- More than 100 shrines (120 at release), each aimed at about 10 minutes of play, set by a shrine-to-field ratio (Fujibayashi interview [S], [miketendo64](https://miketendo64.com/2017/12/23/interview-zelda-devs-on-shrines-and-divine-beasts/)).
- One YouTuber timed an average of 41.8 s between "interesting moments" [S].

**Travel tiers.** Walking, then horse, then gliding from towers, then limited fast travel to shrines and towers [S].

**Tears of the Kingdom** ([Ask the Developer](https://www.nintendo.com/sg/interview/totk/03.html)) [V]:
- The team kept adding sky islands until other designers complained the sky was "messy". **Restraint was a deliberate edit.**
- Islands built at true scale looked like "specks of trash" from the ground and had to be adjusted. **Landmarks must be designed for the distance they are seen from, not for true scale.**
- The Depths were built as an inverse of the surface: dark where the surface is lit, scary rather than open, and dense with secrets ([GoNintendo/Wired](https://www.gonintendo.com/contents/20397-zelda-tears-of-the-kingdom-s-depths-were-made-to-fuel-your-sense-of-adventure)).

### Elden Ring, and Dark Souls 1's Lordran

**Elden Ring.**
- Miyazaki set out to make the world "open and vast" so as to increase the "freedom and depth of exploration", and framed the goal as a "sense of adventure" rather than combing every corner ([gematsu 2019](https://www.gematsu.com/2019/06/elden-ring-is-an-evolution-of-dark-souls-says-director-hidetaka-miyazaki), Famitsu) [S].
- The open field has a map and player-set waypoints. Legacy dungeons have no map [S].
- For the DLC he stressed density and "the ratio of legacy dungeons to open field" over raw size, and aimed for more verticality ([GamingBolt](https://gamingbolt.com/elden-ring-shadow-of-the-erdtrees-map-boasts-a-better-sense-of-verticality-miyazaki)) [S].

POIs come in three tiers ([Game Developer analysis](https://www.gamedeveloper.com/game-platforms/how-elden-ring-succeeds-by-ignoring-20-years-of-open-world-design)) [V]:

| Tier | Example |
|---|---|
| Small, single reward | ruins |
| Medium | mini-dungeons such as caves, catacombs, mines |
| Large set piece | legacy dungeons |

The same analysis also finds [V]:
- **"Far fewer diversions, but the quality of each POI is far higher."**
- "If there's something unusual in the distance, chances are there is a unique situation waiting."
- Little progress is gated by location: the player is "not forced to go somewhere to make progress" for most of the early and mid game. Caelid's danger is signposted by its look.

Guidance and hidden content:
- Each site of grace sends a golden trail of light toward the nearest point of interest, and distant structures draw the player from one POI to the next ([Vice review](https://www.vice.com/en/article/elden-ring-review)) [S].
- The best content is often hidden deliberately ([Exputer](https://exputer.com/features/elden-ring-succeed-open-world/), opinion) [S].
- **Counterpoint:** one critic argues much of the overworld is "non-specific trees-and-rocks stretches" ([Substack](https://doshmanziari.substack.com/p/overestimating-overviews-of-overworlds)) [S].

**Dark Souls 1.**
- Firelink Shrine is the hub. It connects to the Undead Burg, New Londo and the Catacombs, and shortcuts unlock back to it, such as the Undead Parish elevator ([Giant Bomb](https://giantbomb.com/wiki/Locations/Firelink_Shrine)) [S].
- The world "circles back in on itself" largely *because* there is no early fast travel ([TheGamer](https://www.thegamer.com/dark-souls-1-fromsoftwares-magnum-opus-of-interconnected-level-design/)) [S].
- Distant zones are visible from each other; for example, the Duke's Archives can be seen from the Undead Parish [S].
- Miyazaki (EDGE): the connected world "had to look natural as players walk from one area to the next" [S].
- I found no primary Miyazaki quote on shortcut design intent [unverified].

### The Witcher 3

- **"40-second rule":** the player should never go more than about 40 s without something to notice (a deer herd, enemies, an NPC with a quest).
  - It is attributed to CDPR in a 2017 video ([MuyComputer](https://www.muycomputer.com/2017/10/08/the-witcher-3-regla-cuarenta-segundos/)) [S]. I could not find the original statement.
  - An academic replay study found the rule real but "greatly influenced by playstyle" ([Jaber, academia.edu](https://hgo.academia.edu/MaherJaber)) [S].
  - One YouTuber timed an average of 32.2 s in Witcher 3 [S].
- Level designer Miles Tost: the team used painters' "traditional image composition techniques". You climb a slope and are "greeted with a nice view… carefully crafted for this one perspective" ([wccftech Q&A](https://wccftech.com/the-witcher-3-dev-answers-questions-level-design/)) [S].
- Game director Konrad Tomaszkiewicz said long distances made players forget their goals. The fix was to send players out from city hubs so they see POIs in the distance while travelling (Vice/Motherboard interview, summarized in search results; the page no longer resolves) [S].
- **Regional identity:** Velen's guiding theme was "desperation, hunger and hopelessness", based on Polish villages (environment artist Niepokólczycki) [S].
- The map was sized to hold its content, not made large for its own sake (producer Gonsierowska) [S].

### Red Dead Redemption 2

- Rob Nelson (Rockstar North): the map is much bigger than the first game's, but "bigger is better" only goes so far. *How players move* matters, because fast travel lets them skip the world. RDR2 is played at horse pace, GTA V at car speed ([GamePro](https://www.gamepro.de/artikel/red-dead-redemption-warum-die-groesse-der-map-nicht-entscheidend-ist,3335638.html)) [S].
- The world should be "believable down to the smallest detail" (mein-mmo) [S].
- RDR2 is the main exception to the 40-second pattern: it has longer quiet stretches and is still praised [S].

### Skyrim / Morrowind

- The Throat of the World is climbable; Todd Howard counted about 7,000 steps from base to peak ([fandom](https://skyrim.fandom.com/wiki/The_Throat_of_the_World_(location))) [S].
- Location count is about 340 to 370 discoverable map locations, depending on how they are counted ([UESP](https://pt.uesp.net/wiki/Categoria:Skyrim-Places-Discoverable)) [S]. On about 37 km², that is roughly **one marked location per 0.1 km², or about 330 m spacing**.
- **Modular kits:** a small set of kits (caves, Nordic ruins and so on) let designers build hundreds of dungeons. The team roughly quadrupled its level designers to give minor POIs a hand-made feel ([Burgess, GDC 2013](https://www.gamedeveloper.com/design/skyrim-s-modular-approach-to-level-design); [Giant Bomb preview](https://giantbomb.com/articles/skyrim-is-looking-like-the-elder-scrolls-evolved)) [S].
- Designers planned levels as top-down flowcharts of "beats, pacing and connectivity" (Burgess) [S].
- Todd Howard argues quiet travel time matters because it makes the exciting parts stand out [S].
- **Morrowind:** lead designer Ken Rolston described a top-down, overstuffed world with "far less polish than we could" ([UESP interview](https://content1.uesp.net/wiki/General:Ken_Rolstone_Interview)) [S]. Its famous design of verbal directions with no quest markers, plus silt striders, boats and Mages Guild teleports as a diegetic travel network, is well known [M]. I could not verify a developer statement on intent.

### Ghost of Tsushima

- **No HUD waypoint.** The Guiding Wind (swipe the touchpad) points toward the player's chosen map marker. The marker still exists; what was dropped is the HUD clutter ([Android Central interview](https://www.androidcentral.com/ghost-tsushima-creative-director-interview), [GDC 2021 wind talk](https://gdcvault.com/play/1027124/Blowing-from-the-West-Simulating)) [S].
- **Diegetic attractors:** golden birds lead to secrets, foxes to shrines, and smoke columns mark camps, villages or people in need. Dense, distinctive trees mark special places ([PlayStation guide](https://playstation.com/en-au/editorial/ghost-of-tsushima-beginners-guide)) [V].
- Parker Hamilton's GDC 2021 talk, "Letting the Island Guide You", covers how these tools "keep players looking at the world and eager to explore" ([GDC Vault](https://gdcvault.com/play/1027399/Exploration-in-Ghost-of-Tsushima)) [V, abstract only].

### Valheim

- Biomes are mostly a function of distance from the world centre: Meadows at the centre; Black Forest from about 500 to 1,000 m; Swamp and Mountain past about 2,000 m; Plains and Mistlands in the outer rings; Ashlands and Deep North at the far south and north. The world is a 10 km-radius disc ringed by ocean ([cybrancee](https://cybrancee.com/blog/how-does-valheim-world-generation-work/)) [S].
- From code [M, unverified]: Plains appear past about 3 km and Mistlands past about 6 km.
- Boss altars are placed in bands; for example, the Elder sits 1 to 7 km from the centre ([MetaBot](https://metabot.gg/en/valheim/locations/gdking)) [S].
- **Lesson:** difficulty is readable from *what the biome looks like*, and the sea separates regions so that a boat becomes a progression gate.
- Designer Svensson: narrowing from MMO scale to small groups was "probably the best design decision I've ever made" ([PCGamesN](https://www.pcgamesn.com/valheim/indie-game-works-chapter)) [S]. This matches your friends-server vision.
- Shacknews notes the game gives "no real direction on where to go". The visual biome language does that job.

### Terraria [M, not re-verified]

- Spawn is at the horizontal centre, with an ocean at each far edge. The Dungeon sits on one side and the Jungle on the other.
- Difficulty mostly rises with **depth** (surface, then underground, then caverns, then the Underworld), not horizontal distance.
- Hardmode rewrites the world with diagonal stripes of Hallow and Corruption: the same map becomes a new, harder map.
- Redigit has said he felt "locked into" the original loot and progression systems ([PC Gamer](https://www.pcgamer.com/uk/terraria-2-announced-creator-wants-to-include-infinite-worlds)) [S].
- **Lesson:** a second axis of difficulty (depth or altitude) can run alongside horizontal distance.

### Outer Wilds / Hollow Knight

- **Outer Wilds** aims to motivate exploration "without missions or explicit direction", using a diegetic, player-determined progression driven by the "intrinsic motivation" of curiosity. Progress is *knowledge*, not items ([GDC 2020 Beachum & Verneau](https://www.gdconf.com/news/attend-gdc-and-learn-how-outer-wilds-nailed-curiosity-driven-game-design), [GDC 2021 K. Beachum](https://gdcvault.com/play/1027008/Independent-Games-Summit-Sparking-Curiosity)) [S].
- **Hollow Knight:** the map must not reveal the land ahead.
  - You *buy* a rough map of each area from a cartographer, then fill it in yourself as you explore. Team Cherry called keeping discovery alive while still giving a useful map its biggest challenge ([Game Informer](https://gameinformer.com/2018/10/16/the-making-of-hollow-knight)) [S].
  - They design each space as a *physical place* first (a cavern with a lake, a ruined tower) and fill it with content afterwards. They build the map region by region, roughly one a month, with the plan kept loose ([GoNintendo](https://gonintendo.com/contents/53066-team-cherry-walks-through-the-unique-way-they-designed-hollow-knight-silksong-s)) [S].

### Minecraft-adjacent

- **RLCraft:** sources are guides only; I found no Shivaxi interview [unverified]. Recurring points:
  - waystones are deliberately scarce, so travel stays costly;
  - danger is tied to biome (for example, snow regions with dragon nests).
- **Wynncraft:** a 20 km² hand-built world. The in-game map labels each major location with its recommended level ([wiki](https://wynncraft.wiki.gg/wiki/Map)) [S]. This is the closest proven analogue to a spawn picker with difficulty labels.
- I found no credible design analysis of hand-built Minecraft adventure maps.

---

## 2. Where the sources disagree

1. **Density.** On one side: the Witcher 40-second rule (32 s measured), BotW (42 s) and Skyrim's roughly 330 m spacing. On the other: Elden Ring ("fewer, higher-quality"), RDR2 (long quiet stretches), and Todd Howard on the value of downtime. The 40-second study itself says it depends on playstyle. **Synthesis:** dense *small* stimuli, sparse *big* sites, and deliberate quiet zones.
2. **Guidance.** BotW's heat-map fix spread players out, but made some feel railroaded. "No UI" games (Ghost of Tsushima, Elden Ring) still keep map markers. What they remove is the HUD clutter, not the map.
3. **Fast travel.** Dark Souls 1 interconnects *because* it has none early. Elden Ring and BotW allow it freely. RDR2 and RLCraft keep travel costly on purpose.
4. **Map sizes** conflict badly: Elden Ring is quoted as 79 km² or 12 to 24 km², BotW as 21 to 360 km². Use them only as orders of magnitude.

**Unverified:**
- the original 40-second-rule quote;
- Miyazaki on shortcuts;
- Morrowind's intent behind its directions;
- exact Valheim biome thresholds;
- RLCraft design intent;
- Terraria developer statements;
- Ghost of Tsushima talk content beyond the abstract;
- the "Kyoto-sized" area claim.

---

## 3. Principles for the continent (applied at Minecraft scale)

All numbers are [J] starting points to tune with playtests.

### 1. Design for a 100-block horizon, then extend it artificially.

Assume friends see 80 to 128 blocks.

**Inside that disc, use real landmarks:**
- They need to rise **40 to 80 blocks above the canopy**.
- They need a **unique silhouette and material**: obsidian spire, giant dead tree, colossal statue, beacon-lit tower.
- At 120 blocks away, a 60-block-tall object fills about 25° of view and dominates the scene. Scale them to the view distance, as TotK learned.

**Beyond the disc, add a "distant landmark impostor" renderer** to qf-content, since you own that mod:
- It draws billboard silhouettes of the 10 to 20 hero landmarks at their true bearing, faded by atmosphere.
- It costs a few quads per frame, so it is cheap for weak PCs.
- It is the only way to get Erdtree or Hyrule Castle "gravity" across kilometres.
- This is an engineering proposal; feasibility is untested.

### 2. Use a three-tier POI hierarchy, sized to travel speed.

| Tier | What | Spacing | Time apart |
|---|---|---|---|
| Minor | a "noticing" every 40 s on foot: ruin, camp, odd tree, mob den, shrine | **150 to 250 blocks** along likely routes | about 40 s sprinting |
| Medium | dungeon, castle, village, roguelike entrance | **500 to 1,000 blocks** | 1.5 to 3 min on foot |
| Major | hero site per region, the "legacy dungeon" | **1 per region, about 4 to 7 km apart** | |

Hand-placing the minor tier across 1,024 km² would take tens of thousands of sites, which is impossible. Instead:
- let the mod generators (Roguelike Dungeons, Chocolate Quest, villages) supply density, Skyrim-kit style;
- hand-author the medium tier only along roads and rivers and in core regions;
- hand-author **every** major site.

### 3. Build 16 to 25 regions with one strong identity each.

At an average of 6 to 8 km across, each region is roughly the area of a whole AAA map, so region count matters less than *internal variety*.

Each region gets one theme sentence, in the style of Velen's "desperation and hunger":
- one dominant biome palette;
- one mob family (a Lycanites group, Witchery covens, OreSpawn bosses);
- one architectural style;
- one hero site.

Test: a screenshot should identify its region.

### 4. Radiate difficulty from the spawns, readable by eye.

- Place the **6 to 10 spawn points on the coast or outer rim**, each in an easy pocket about 1 to 1.5 km across.
- Raise difficulty **inward toward a central apex**: a capital, mountain or dragon peak that is the visible endgame, like Hyrule Castle seen from the Great Plateau.
- Signal danger visually before it bites, Caelid-style: blighted colours, dead trees, bones and skulls, a scary sentinel mob at a region's gate.
- Add a few **danger spikes next to easy zones**, Elden Ring's Tree Sentinel style, so the world teaches caution.
- Label each spawn in the picker with its local tier, as Wynncraft does on its map.

### 5. Make the sea a gate and the frontier read as "beyond the map".

The sea ring should be a clear threshold: boats or flight required, ideally dangerous water (sea monsters). Valheim uses the ocean as its progression gate.

The procedural land beyond should *look* different: rougher, more chaotic generation, no roads, no signage. That says "uncurated wilds".

Two choices, and the sources split:
- **Valheim model:** the outer edge is the hardest endgame. *This is what I recommend for "leaps in power without a fast plateau".*
- **Terraria model:** an edge you can reach early.

### 6. Let the land speak through triangles and rectangles.

- Wrap medium POIs in hills that reveal them gradually.
- Put loot and secrets at the tips of ridges.
- Use forest walls and cliffs (rectangles) to hide, then suddenly reveal, set pieces.
- Stage the approach to each hero site as a sequence of three reveals, like the Seeker Tower's hill, then bridge, then tower.

### 7. Use diegetic guidance instead of HUD arrows.

Ghost of Tsushima's toolkit maps onto Minecraft:

| Ghost of Tsushima | Minecraft equivalent |
|---|---|
| smoke columns | tall fire or netherrack chimneys, or particle columns from a qf-content block |
| golden birds | a passive "guide" mob or bird that flies toward an undiscovered POI |
| foxes to shrines | an animal that leads to small rewards |
| special trees | rare, conspicuous trees marking secrets |
| wind | a directional wind or particle effect |

Also make **roads and rivers** the main guidance lines: Witcher-style, routes from hubs pass POIs in view.

### 8. Use maps as earned knowledge.

- Sell or reward **regional map items or atlas pages** at hubs (Hollow Knight's cartographer); otherwise the map stays unknown.
- Lore books and NPC dialogue give Morrowind-style verbal directions ("north of the twin spires").
- Gate a few secrets on *knowledge*, Outer Wilds-style: a password, a tide or moon phase, a hidden entrance described in a book.

### 9. Put several loops and shortcuts inside each region.

Each region's hub should connect to 3 or 4 sites in loops, with one-way shortcuts back such as:
- drops;
- doors with the lever only on the far side;
- minecart lines unlocked from the destination end.

Dark Souls shows this only works if fast travel is limited. RLCraft's scarce waystones are the same choice.

### 10. Gate travel speed by progression.

| Stage | Travel |
|---|---|
| Early | on foot or horse; the world feels huge |
| Mid | rail and boat networks between hubs |
| Late | flight |

Because a 56 m/s jet makes the continent 10 minutes wide and reveals nothing ahead, give flight costs:
- airborne threats (dragons, OreSpawn flyers) over high-tier regions;
- no-fly storms or ceilings over hero sites;
- landing required to discover anything; POIs should be ground-scale.

Rob Nelson's point applies: how players move defines the world.

### 11. Vary density deliberately.

- Dense "content belts" run along roads, rivers and coastlines.
- Quiet wilderness lies between them (Todd Howard, RDR2).
- The 40-second rule should apply on the *routes*, not uniformly.
- Concentrate fidelity in the zones friends will actually play: rings around the spawns, and the main roads toward the apex.
- Outer regions can be lower fidelity at first.

A 5-person server will never see most of 1,024 km² [J].

### 12. Use verticality and depth as a second difficulty axis.

Terraria's depth layers and TotK's sky/surface/Depths show how:
- under each region: deep caves and dungeon tiers that run harder than the surface above;
- above it: rare high peaks or floating hero sites at y 180 to 250.

Vertical relief is capped by the 256-block build limit (sea level 63) [M], so pick heights carefully. Peaks help views only within the render radius.

### 13. Edit with heat-map playtests, as Nintendo did.

- Log friends' positions server-side every few seconds through the dev-server harness or a small qf-content logger.
- Render heat maps over the WorldPainter map.
- Expect routes to converge and regions to go unvisited. Add attractors (landmarks, smoke, roads) there.
- Watch for the "too linear" backlash Nintendo saw.

### 14. Practise restraint.

TotK's designers had to tell the team the sky was "messy". Every hero landmark should be unique. Do not repeat a silhouette within the same region or within sight of its twin.

---

### Key URLs

- https://gigazine.net/gsc_news/en/20171004-breath-of-the-wild-design-secret
- https://news.denfaminicogamer.jp/kikakuthetower/171016
- https://www.nintendo.com/sg/interview/totk/03.html
- https://www.gamedeveloper.com/game-platforms/how-elden-ring-succeeds-by-ignoring-20-years-of-open-world-design
- https://gdcvault.com/play/1027399/Exploration-in-Ghost-of-Tsushima
- https://www.muycomputer.com/2017/10/08/the-witcher-3-regla-cuarenta-segundos/
- https://hgo.academia.edu/MaherJaber
- https://wccftech.com/the-witcher-3-dev-answers-questions-level-design/
- https://www.gamedeveloper.com/design/skyrim-s-modular-approach-to-level-design
- https://www.gamepro.de/artikel/red-dead-redemption-warum-die-groesse-der-map-nicht-entscheidend-ist,3335638.html
- https://cybrancee.com/blog/how-does-valheim-world-generation-work/
- https://gameinformer.com/2018/10/16/the-making-of-hollow-knight
- https://www.gdconf.com/news/attend-gdc-and-learn-how-outer-wilds-nailed-curiosity-driven-game-design
- https://wynncraft.wiki.gg/wiki/Map

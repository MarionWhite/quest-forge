# Meteor showers: how they look, and rules for the shader

Round 9 research for shader-dev (ops/checkpoints/r009-shader.md, item 5). No renders were made.
Each fact is tagged **[src]** (read on the cited page this session) or **[est]** (general
knowledge or a judgement, not confirmed on a page; treat as a tunable default).

## 1. Radiant geometry

- Shower meteoroids travel on parallel paths at one speed. Perspective makes their trails appear to
  diverge from one point, the radiant, like rails converging at the horizon. [src: Wikipedia, Meteor shower]
- IMO definition: the radiant is where the backward projection of the trajectory meets the celestial
  sphere. [src: IMO glossary, https://www.imo.net/resources/glossary/]
- The radiant moves with the sky during the night (Earth's rotation) and creeps night to night
  (Earth's orbit). [src: Wikipedia, Meteor shower]
- Every streak is a great-circle arc on the sky, lying on a line through the radiant, **moving away
  from it**. A streak never points toward the radiant, and the extension of its backward path hits
  the radiant exactly. [src: definition above]
- Only a streak's direction is tied to the radiant. Its position can be anywhere in the sky,
  including the half opposite the radiant and the side where the radiant is below the horizon.
  Viewers advised to look about halfway between horizon and zenith, not at the radiant. [src: AMS FAQ, https://www.amsmeteors.org/faq/]

## 2. Streak length versus distance from the radiant

- Close to the radiant a meteor travels almost along the line of sight, so it is foreshortened:
  short, and often a near-stationary point that flashes. Farther away it crosses the line of sight
  and traces a long path. [src: AMS FAQ]
- Longest, most prominent trails are seen roughly 30-60 degrees from the radiant. [src: Wikipedia, Meteor shower]
- Geometry behind it [est]: if the real path has angular length L at 90 degrees from the radiant, the
  apparent length at angular distance d from the radiant scales about as sin(d) (foreshortening), up to a cap set by the
  atmospheric path (a typical visible track is tens of km, 80-120 km altitude [src: AMS FAQ]).
  Use `len = Lmax * sin(d)` with Lmax of a few tens of degrees on the sky.
- Meteors are mostly seen for well under a second [est: 0.2-1 s typical], so a streak is a fast
  moving head with a short fading tail, not a static line.

## 3. Rates, clustering, radiant altitude

- ZHR is the hourly rate for one observer with limiting magnitude 6.5 and the radiant at the zenith.
  Real rates are usually lower. [src: IMO glossary; AMS FAQ]
- Radiant altitude: observed rate ~ ZHR * sin(h_radiant), and a radiant under the horizon gives no
  normal shower meteors. [src: Wikipedia, Zenithal hourly rate / formula ZHR = HR*F*r^(6.5-lm)/sin(hR)]
- Strength tiers [src: AMS FAQ, Wikipedia]: minor showers a few per hour; strong majors dozens;
  Perseids and Geminids ZHR about 75, Perseids up to over 1 per minute at best; a storm is at least
  1000 per hour (Leonid storms of 1833 and 1966 passed 120,000 per hour, peaks reported near 150,000-240,000).
- Sporadic background [est]: about 5-10 per hour from a dark sky, rising before dawn (the AMS notes
  they are more numerous before dawn than in the evening [src]).
- Clustering: meteors are a Poisson process, so they arrive in random clumps and gaps, not at an
  even beat. A shower peaks and falls off smoothly over days (rates rise toward a maximum then drop). [est]
  Storms and outbursts are short, with rates changing over minutes to hours. [est]

## 4. Brightness distribution

- Population index r is the ratio of the counts between successive magnitudes: each magnitude
  fainter has about r times more meteors. Typical r is about 2.0-3.0; examples 2.4-2.7
  for Quadrantids (2025 analysis) and about 2.5 for Orionids. [src: Wikipedia ZHR page and search results on r, see sources]
- Consequence: with r = 2.5 there are about 6 times as many meteors two magnitudes fainter. Most
  are faint, barely there; few are bright. Fireballs are -4 magnitude or brighter. [src: IMO glossary]
- Sampling rule [est]: draw magnitude from an exponential with ratio r per magnitude, then map to
  brightness (about 2.5x per magnitude) and tail length. Faint ones are short, dim, white.

## 5. Colour

- Colour comes from the ablating metal atoms plus atmospheric gas. Common mapping [src: search
  results, unverified single-source charts, observers differ]:
  sodium orange-yellow, iron yellow, magnesium blue-green, calcium violet, nitrogen/oxygen red.
- Observers overstate colour, and perception adds noise. Most faint meteors look white or
  pale yellow-white. [est] Saturated colour belongs to bright ones. Speed and size
  change which lines dominate (faster and larger = more intense colour). [src: search results]
- Entry speed 11-72 km/s [src: AMS FAQ], average about 20 km/s for orbit-matching dust, up to about 42
  km/s for prograde (Earth moves about 29.6 km/s) [src: Wikipedia, Meteoroid]. Faster showers (Perseids, Leonids)
  read as brief and bright, slower ones (Draconids) as lazy.

## 6. Persistent trains

- IMO: remaining glow from ionisation in the upper atmosphere after passage. [src: IMO glossary]
- Brief afterglow lasts a few seconds. A persistent train is the longer emission that outlasts it
  after a bright fireball. [src: NASA Leonid pages, leonid.arc.nasa.gov]
- Duration: 1-30 minutes, typically 4-6, at roughly +4 to +5 magnitude (dim, near faint star
  level); up to an hour in survey data; one Perseid fireball train about 1 minute to the eye. [src: NASA Leonid page; Science News 2024 survey]
- Trains come from meteors reaching down to about 90 km altitude, not simply the brightest or
  fastest. [src: 2024 survey, Science News]
- Appearance [est]: a faint greenish or white line that drifts, kinks and widens with high-altitude winds.
  Rare: only a small fraction of meteors, nearly all fireballs.

## 7. Rules for shader-dev

All numbers are defaults to tune against frames. Keep the pass cheap (per-pixel, no extra taps,
night sky only, off when the sun is up). Perf constraint from the checkpoint: nothing that raises High or Low cost.

1. **One radiant per night**, direction fixed in world sky space, rotating with the star field (same
   rotation as the stars). Hide streaks while the radiant is below the horizon; scale rate by sin(radiant altitude).
2. **Direction:** every streak moves along the great circle through the radiant to its start point,
   away from the radiant. Never random headings.
3. **Start points** are uniform over the sky, but weight to 25-90 degrees away from the radiant (hide
   or shrink inside ~10 degrees).
4. **Length** = `Lmax * sin(d)` where d is the angular distance of the start from the radiant; Lmax around 20-30 degrees of sky.
   Near the radiant draw a short dot with a flash.
5. **Time:** each streak lives 0.3-1.0 s (shorter for fast showers). The head moves at a constant angular
   speed, with a bright head and a linear fade tail about 30-60% of its length. Smooth brightness envelope, no popping.
6. **Rate:** hash-based events per time slot (Poisson style, random gaps and clumps), not a metronome.
   Base about 6/h sporadic at random headings (the only random-heading allowance, small), shower
   about 30-75/h compressed in real time for a game feel (a visible one every few seconds to ~20 s when at peak); a rare storm night
   hundreds per minute as a special event only.
7. **Brightness:** magnitude drawn with r = 2.5; most streaks faint and thin, ~1 in 6 clearly bright, ~1 in 100
   a fireball with a wide glow, a brief flash lighting the sky slightly.
8. **Colour:** faint ones white-to-pale-yellow. Bright ones tint: orange-yellow, green-blue, occasionally
   violet, with a white-hot head. Saturation rises with brightness.
9. **Persistent train:** only on fireballs (about 1 in 100 streaks, at most one alive). Faint green-white, +4 to +5 magnitude
   dim, a line along the path, lasts 20-60 s of game time, fading, slowly widening and drifting sideways with a slight kink.
10. **Occlusion:** moon, cloud and horizon haze dim them; no streaks beneath terrain/depth, and faint streaks vanish under bright skies, as the rate drops in twilight and under a full moon.

## Sources

- IMO glossary: https://www.imo.net/resources/glossary/
- AMS meteor FAQ: https://www.amsmeteors.org/faq/
- Wikipedia, Meteor shower: https://en.wikipedia.org/wiki/Meteor_shower
- Wikipedia, Meteoroid: https://en.wikipedia.org/wiki/Meteoroid
- Wikipedia, Zenithal hourly rate: https://en.wikipedia.org/wiki/Zenithal_hourly_rate
- NASA Leonid pages: https://leonid.arc.nasa.gov/meteor.html
- Science News, trails lasting up to an hour: https://www.sciencenews.org/?p=3141914
- Colour mapping (secondary, observers disagree): https://www.iflscience.com/what-do-meteors-colors-tell-us-71928
- Sky & Telescope, advanced meteor observing: https://skyandtelescope.org/observing/advanced-meteor-observing/

Gaps: sporadic rate, streak duration, and the sin(d) foreshortening form are not confirmed on a
fetched page (tagged [est]). The colour chart is secondary. Detail pages were not read in full
(Wikipedia articles were truncated at 100k chars).

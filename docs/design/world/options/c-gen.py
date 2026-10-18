import math


def P(a, r):
    return [round(r * math.cos(math.radians(a))), round(r * math.sin(math.radians(a)))]


radii = [12600, 13200, 12200, 12900, 13400, 12400, 12800, 13300, 12100, 12700,
         13000, 12300, 13500, 12600, 12000, 12900, 13200, 12500, 12800, 13100]
coast = [P(i * 18, r) for i, r in enumerate(radii)]
L = []
w = L.append
w("# Option C: the Inland Sea. A ring continent round a central inland sea (about 10k across).")
w("# Render: py -3.10 tools/world/plan.py render docs/design/world/options/c-inland-sea.yaml PLANDIR")
w("# +x east, +z south; angles 0 = east, 90 = south. Earlier regions win.")
w("size: 32768\nseed: 77\ncoast_warp: 1000\nregion_warp: 1400\nblend_px: 16\nshore_width: 900\nshelf_width: 1500\n")
w("coast:")
for p in coast:
    w(f"  - {p}")
w("""
# The inland sea, and the western strait (cliffs on both sides) linking it to the ocean.
lakes:
  - {circle: [0, 0, 5000]}
  - {polygon: [[-13800, -320], [-4700, -260], [-4700, 340], [-13800, 300]]}
islands:
  - {circle: [0, 0, 1250]}                 # the central plateau-island
  - {ring: [2900, 1300, 820, 560]}         # broken ring round the maelstrom basin
  - {circle: [180, 4250, 300]}             # stepping-stone islands: a broken land bridge
  - {circle: [-160, 3500, 320]}            #   from the south shore to the central island
  - {circle: [220, 2750, 300]}
  - {circle: [0, 1950, 260]}
  - {circle: [14600, -7600, 700]}          # vanilla Mushroom Island, east
  - {circle: [3200, -15200, 750]}          # BoP Glacier isle, far north
  - {ring: [7600, 14300, 950, 560]}        # coral atoll, south

surfaces:
  - {material: black_sand, circle: [0, 0, 1400]}

# Centrepiece: a sheer plateau-island in the middle of the inland sea.
plateaus:
  - {circle: [0, 0, 1050], top: 175, wall: 60, top_relief: 14, relief: 70, biome: 250, tier: 5}

regions:
  # Centre and approaches (T4-T5)
  - {tier: 5, biomes: [[250, 2], [77, 1]], base: 90, relief: 100, circle: [0, 0, 1400]}
  - {tier: 4, biome: 77, base: 80, relief: 120, circle: [2900, 1300, 950]}
  - {tier: 4, biomes: [[77, 2], [60, 1]], base: 72, relief: 60, circle: [180, 4250, 400]}
  - {tier: 4, biomes: [[77, 2], [60, 1]], base: 72, relief: 60, circle: [-160, 3500, 420]}
  - {tier: 4, biomes: [[77, 2], [60, 1]], base: 72, relief: 60, circle: [220, 2750, 400]}
  - {tier: 4, biomes: [[77, 2], [60, 1]], base: 72, relief: 60, circle: [0, 1950, 360]}""")
spawns = [(200, [[187, 2], [78, 1]]), (135, [[79, 1]]), (90, [[194, 1]]),
          (45, [[251, 2], [78, 1]]), (0, [[78, 2], [187, 1]]), (270, [[192, 1], [89, 1]])]
w("  # A T3 zone in sight of every T1 spawn")
for a, b in spawns:
    c = P(a, 11000)
    w(f"  - {{tier: 3, biomes: {b}, base: 74, relief: 50, circle: [{c[0]}, {c[1]}, 450]}}")
w("""  # Islands
  - {tier: 2, biome: 14, base: 68, relief: 30, circle: [14600, -7600, 850]}
  - {tier: 2, biomes: [[89, 2], [192, 1]], base: 80, relief: 60, circle: [3200, -15200, 900]}
  - {tier: 1, biome: 224, base: 66, relief: 15, circle: [7600, 14300, 1150]}
  # Small hidden biomes
  - {tier: 2, biome: 185, base: 78, relief: 40, circle: [-7600, -5200, 550]}
  - {tier: 2, biome: 197, base: 90, relief: 40, circle: [5800, -6800, 450]}
  - {tier: 1, biome: 147, base: 72, relief: 20, circle: [-6800, 9400, 650]}
  - {tier: 2, biome: 186, base: 70, relief: 8, circle: [8600, 6900, 500]}

  # Seas: climate bands, the inland sea (RWG Wet Ocean), reefs and kelp on the shelf
  - {biome: 211, sea: true, polygon: [[-16384, -16384], [16384, -16384], [16384, -6500], [-16384, -6500]]}
  - {biome: 210, sea: true, polygon: [[-16384, -16384], [16384, -16384], [16384, -13600], [-16384, -13600]]}
  - {biome: 212, sea: true, polygon: [[-16384, -6500], [16384, -6500], [16384, 5000], [-16384, 5000]]}
  - {biome: 213, sea: true, polygon: [[-16384, 5000], [16384, 5000], [16384, 16384], [-16384, 16384]]}
  - {biome: 75, sea: true, shallow: true, polygon: [[-16384, 7000], [16384, 7000], [16384, 16384], [-16384, 16384]]}
  - {biome: 144, sea: true, shallow: true, polygon: [[-16384, -9000], [-9000, -9000], [-9000, 6000], [-16384, 6000]]}
  - {biome: 214, sea: true, circle: [0, 0, 5300]}
  - {biome: 75, sea: true, shallow: true, polygon: [[-5300, 1500], [5300, 1500], [5300, 5300], [-5300, 5300]]}
  - {biome: 24, sea: true, circle: [2900, 1300, 600]}
  - {biome: 75, sea: true, circle: [7600, 14300, 600]}""")
outer = [(270, "[[239, 3], [66, 2]]", "[8, 120, 400]", 70, 90),
         (315, "[[247, 3], [61, 1], [66, 1]]", "[14, 150, 550]", 68, 30),
         (225, "[[66, 2], [74, 2], [89, 1]]", "[8, 120, 400]", 72, 80),
         (180, "[[196, 3], [243, 2]]", "[4, 100, 300]", 76, 70),
         (135, "[[73, 2], [188, 1], [85, 1]]", "[4, 100, 300]", 72, 45),
         (90, "[[246, 2], [153, 2], [195, 1]]", "[4, 80, 250]", 66, 30),
         (45, "[[2, 3], [148, 1], [190, 1]]", None, 72, 40),
         (0, "[[193, 2], [242, 2], [236, 1]]", "[3, 100, 300]", 70, 35)]
middle = [(247, "[[86, 2], [66, 1]]", "[6, 100, 350]", 80, 70),
          (292, "[[89, 2], [247, 1]]", "[6, 120, 400]", 82, 80),
          (337, "[[142, 2], [183, 2]]", "[10, 80, 300]", 88, 70),
          (22, "[[138, 2], [253, 1]]", "[4, 120, 400]", 74, 45),
          (67, "[[190, 2], [37, 1], [2, 1]]", None, 80, 70),
          (112, "[[245, 3], [62, 1]]", "[6, 120, 350]", 70, 80),
          (157, "[[159, 2], [84, 1]]", "[14, 60, 250]", 63, 8),
          (202, "[[154, 2], [80, 2]]", "[6, 100, 350]", 76, 50)]
inner = [(270, "[[60, 2], [192, 1], [89, 1]]", 100, 130), (330, "[[77, 2], [60, 1]]", 96, 120),
         (30, "[[251, 2], [78, 1]]", 80, 60), (90, "[[250, 1], [251, 1], [77, 1]]", 84, 90),
         (150, "[[187, 2], [79, 1]]", 72, 50), (210, "[[78, 2], [187, 1]]", 76, 60)]
w("  # Outer coast (T1), climate by latitude: frozen north, temperate east and west, hot south")
for a, b, lk, base, rel in outer:
    c = P(a, 11300)
    lks = f", lakes: {lk}" if lk else ""
    w(f"  - {{tier: 1, biomes: {b}, base: {base}, relief: {rel}{lks}, at: [{c[0]}, {c[1]}]}}")
w("  # Middle band (T2)")
for a, b, lk, base, rel in middle:
    c = P(a, 8600)
    lks = f", lakes: {lk}" if lk else ""
    w(f"  - {{tier: 2, biomes: {b}, base: {base}, relief: {rel}{lks}, at: [{c[0]}, {c[1]}]}}")
w("  # Inland shore (T3): the danger rises toward the inland sea")
for a, b, base, rel in inner:
    c = P(a, 6300)
    w(f"  - {{tier: 3, biomes: {b}, base: {base}, relief: {rel}, at: [{c[0]}, {c[1]}], size: 0.9}}")
w("""
ponds:
  - {at: [8600, 6900], r: 170, biome: 186}

ridges:
  # Cliffs guarding the western strait
  - {points: [[-11500, -1000], [-8500, -900], [-5800, -850]], height: 150, width: 1000, relief: 200}
  - {points: [[-11500, 1000], [-8500, 950], [-5800, 900]], height: 150, width: 1000, relief: 200}
  # The northern arc's mountains, above the inland shore
  - {points: [[-6500, -6200], [-3000, -7400], [1000, -7200], [4500, -6700], [6800, -5200]], height: 210, width: 2000, relief: 220, biome: 60, biome_above: 0.55}
  # Southern mesas and the western coastal range
  - {points: [[4600, 7600], [6800, 8400], [8600, 9800]], height: 115, width: 900, relief: 230}
  - {points: [[-11800, -5200], [-12200, -3000]], height: 130, width: 1100, relief: 160}

rivers:
  # North: frozen, forked, out to the cold sea
  - {points: [[-500, -8400], [400, -10200], [-200, -13000]], width: 40, biome: 11}
  - {points: [[-2300, -9400], [-800, -10700], [400, -10200]], width: 28, biome: 11}
  - {points: [[2400, -9200], [1500, -10200], [400, -10200]], width: 28, biome: 11}
  # East, to the ocean
  - {points: [[7800, 1200], [10400, 1700], [13400, 2000]], width: 40}
  - {points: [[9000, 3600], [9700, 2500], [10400, 1700]], width: 28}
  - {points: [[9200, -1500], [9900, 200], [10400, 1700]], width: 28}
  # South: a wide tropical river (BoP Lush River) to the hot sea, with tributaries
  - {points: [[-600, 7600], [300, 10200], [-300, 13200]], width: 72, meander: 320, valley: 220, biome: 150}
  - {points: [[2200, 8900], [1300, 9900], [300, 10200]], width: 32, biome: 150}
  - {points: [[-2600, 9100], [-1300, 9900], [300, 10200]], width: 32, biome: 150}
  # West, through the redwoods
  - {points: [[-8200, -3600], [-10600, -4200], [-13300, -4600]], width: 40}
  - {points: [[-9400, -6200], [-10000, -5000], [-10600, -4200]], width: 28}
  # Rivers draining inward to the inland sea
  - {points: [[7400, -5000], [5900, -4100], [4300, -3000]], width: 36}
  - {points: [[-7400, 5000], [-5900, 4000], [-4300, 2900]], width: 36}
  - {points: [[-6000, 6600], [-5900, 4000]], width: 24}
  # A dry riverbed through the southeastern desert (BoP Dry River)
  - {points: [[7200, 5600], [8800, 7600], [9600, 10200]], width: 28, biome: 82, dry: true}

points:""")
for a, _ in spawns:
    c = P(a, 11800)
    w(f"  - {{kind: spawn, tier: 1, x: {c[0]}, z: {c[1]}}}")
w("  - {name: Strait, kind: landmark, x: -9000, z: 0}")
w("  - {name: Maelstrom, kind: landmark, x: 2900, z: 1300}")
open(r"C:\dev\quest-forge\docs\design\world\options\c-inland-sea.yaml", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("written")

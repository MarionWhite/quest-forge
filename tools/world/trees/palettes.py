"""Block palettes: role -> Minecraft block, per species.

A palette entry is a list of (block, meta, weight). `block` is either a numeric 1.7.10 ID or a
registry name such as 'BiomesOPlenty:logs3'; names are resolved at export time through an ID map
read from a world's level.dat (`--idmap`), because modded IDs are only fixed per world.

Logs (any block listed in LOG_BLOCKS) get their axis bits added on export: +0 up, +4 east-west,
+8 north-south, +12 bark on all sides. Write the base meta (wood type) only.
Leaves: give the no-decay meta explicitly (vanilla: type | 4).

Palette sets:
  vanilla        default. Vanilla 1.7.10 blocks only (IDs 0-175); every canopy is real leaves.
  vanilla-wool   same, but the autumn and cherry canopies are dyed wool and stained clay. Opt-in
                 only: wool is an opaque full cube, so mobs spawn on the canopy tops at night,
                 punching drops free dyed wool, and nothing shows through the crown.
  vanilla-leaves old name for `vanilla`.
  bop            Biomes O' Plenty woods and leaves (needs --idmap). Meta values are from BoP 2.1
                 for 1.7.10 and must be checked in game (F3 / NEI) before a real export.
"""

LOG_BLOCKS = {17, 162, 'BiomesOPlenty:logs1', 'BiomesOPlenty:logs2', 'BiomesOPlenty:logs3',
              'BiomesOPlenty:logs4'}

# vanilla shorthands
OAK, SPRUCE, BIRCH, JUNGLE = (17, 0), (17, 1), (17, 2), (17, 3)
ACACIA, DARKOAK = (162, 0), (162, 1)
L_OAK, L_SPRUCE, L_BIRCH, L_JUNGLE = (18, 4), (18, 5), (18, 6), (18, 7)
L_ACACIA, L_DARKOAK = (161, 4), (161, 5)
WOOL = {c: (35, i) for i, c in enumerate(
    'white orange magenta light_blue yellow lime pink gray light_gray cyan purple blue brown green red black'.split())}
CLAY = {c: (159, i) for c, (_, i) in WOOL.items()}
GLASS = {c: (95, i) for c, (_, i) in WOOL.items()}
STONE, COBBLE, MOSSY_COBBLE = (1, 0), (4, 0), (48, 0)
BRICK, MOSSY_BRICK, CRACKED_BRICK, CHISELED = (98, 0), (98, 1), (98, 2), (98, 3)
ICE, PACKED_ICE, SNOW_BLOCK, GLOWSTONE = (79, 0), (174, 0), (80, 0), (89, 0)


def w(*items):
    """w((id, meta), weight, (id, meta), weight, ...) -> [(id, meta, weight), ...]"""
    out = []
    for i in range(0, len(items), 2):
        out.append((items[i][0], items[i][1], items[i + 1]))
    return out


def one(b):
    return [(b[0], b[1], 1)]


VANILLA = {
    'redwood': {
        'trunk': one(SPRUCE), 'branch': one(SPRUCE), 'root': one(SPRUCE), 'bark': one(SPRUCE),
        'leaf': w(L_SPRUCE, 5, L_DARKOAK, 1), 'leaf2': one(L_SPRUCE),
        'accent': one(L_OAK),                    # epicormic sprouts on the trunk (lighter green)
    },
    'mangrove': {
        'trunk': one(OAK), 'branch': one(OAK), 'root': w(OAK, 3, JUNGLE, 1), 'bark': one(OAK),
        'leaf': w(L_JUNGLE, 2, L_OAK, 2, L_DARKOAK, 1), 'leaf2': one(L_DARKOAK),
    },
    'baobab': {
        'trunk': one(ACACIA), 'branch': one(ACACIA), 'root': one(ACACIA), 'bark': one(ACACIA),
        'leaf': one(L_ACACIA), 'leaf2': one(L_OAK),
    },
    'ice': {
        'trunk': one(PACKED_ICE), 'branch': one(PACKED_ICE), 'root': w(PACKED_ICE, 3, SNOW_BLOCK, 1),
        'bark': one(PACKED_ICE), 'core': one(ICE),
        'leaf': w(GLASS['light_blue'], 3, GLASS['white'], 2),
        'leaf2': w(GLASS['cyan'], 2, GLASS['light_blue'], 1),
        'leaf3': w(GLASS['magenta'], 1, GLASS['purple'], 1),
        'leaf4': w(GLASS['white'], 3, GLASS['light_blue'], 1),
        'accent': one(ICE),                      # icicles and crystal cores
        'accent2': one(PACKED_ICE),              # crystal shards
        'glow': one(GLOWSTONE),                  # a few hidden lights inside the canopy
        'snow': one(SNOW_BLOCK),
    },
    'eucalyptus': {
        'trunk': one(BIRCH), 'branch': one(BIRCH), 'root': w(BIRCH, 3, OAK, 1), 'bark': one(BIRCH),
        'leaf': w(L_BIRCH, 3, L_SPRUCE, 1), 'leaf2': w(L_SPRUCE, 1, L_BIRCH, 1),
    },
    'petrified': {
        'trunk': w(STONE, 5, BRICK, 2, CRACKED_BRICK, 2, COBBLE, 1),
        'branch': w(STONE, 3, COBBLE, 3, CRACKED_BRICK, 1),
        'root': w(COBBLE, 3, MOSSY_COBBLE, 3, MOSSY_BRICK, 1),
        'bark': w(MOSSY_BRICK, 2, MOSSY_COBBLE, 2),
        'core': one(STONE),
    },
    'autumn': {
        'trunk': one(OAK), 'branch': one(OAK), 'root': one(OAK), 'bark': one(BIRCH),   # bark = aspen
        # wool reads softer than terracotta; terracotta gives the shaded depth inside the crown
        'leaf': w(WOOL['red'], 4, CLAY['red'], 1),
        'leaf2': w(WOOL['orange'], 4, CLAY['orange'], 1),
        'leaf3': w(WOOL['yellow'], 4, CLAY['yellow'], 1),
        'leaf4': w(L_OAK, 2, L_DARKOAK, 1),      # last green leaves inside the crown
        'accent': w(CLAY['brown'], 2, WOOL['brown'], 1),
    },
    'cherry': {
        'trunk': one(DARKOAK), 'branch': one(DARKOAK), 'root': one(DARKOAK), 'bark': one(DARKOAK),
        'leaf': w(WOOL['pink'], 1),
        'leaf2': w(WOOL['white'], 2, WOOL['pink'], 1),
        'leaf3': w(CLAY['white'], 1, WOOL['magenta'], 1),   # shaded underside / deeper pink
        'leaf4': w(L_OAK, 1),                    # fresh green leaves among the blossom
    },
}

# leaves-only canopies (the default). Oak, dark-oak and acacia leaves take the biome foliage
# colour; birch and spruce leaves have a fixed colour, so birch gives the lighter "yellow" clumps
# and spruce the dark ones whatever the biome.
VANILLA_LEAVES = {k: dict(v) for k, v in VANILLA.items()}
VANILLA_LEAVES['autumn'].update({
    'leaf': w(L_DARKOAK, 1), 'leaf2': w(L_ACACIA, 1), 'leaf3': w(L_BIRCH, 1), 'leaf4': w(L_OAK, 1),
    'accent': w(L_SPRUCE, 1)})
VANILLA_LEAVES['cherry'].update({
    'leaf': w(L_BIRCH, 1), 'leaf2': w(L_BIRCH, 2, L_OAK, 1), 'leaf3': w(L_OAK, 1), 'leaf4': w(L_OAK, 1)})

# Biomes O' Plenty (1.7.10, BoP 2.1). Names resolve through --idmap; meta = wood/leaf type.
# Leaves: BoP sets "no decay" differently from vanilla - confirm the meta in game before use.
B = 'BiomesOPlenty:'
BOP = {k: dict(v) for k, v in VANILLA.items()}
BOP['redwood'].update({'trunk': [(B + 'logs3', 0, 1)], 'branch': [(B + 'logs3', 0, 1)],
                       'root': [(B + 'logs3', 0, 1)], 'bark': [(B + 'logs3', 0, 1)],
                       'leaf': [(B + 'colorizedLeaves1', 3, 1)], 'leaf2': [(B + 'colorizedLeaves1', 3, 1)]})
BOP['mangrove'].update({'trunk': [(B + 'logs2', 2, 1)], 'branch': [(B + 'logs2', 2, 1)],
                        'root': [(B + 'logs2', 2, 1)], 'bark': [(B + 'logs2', 2, 1)],
                        'leaf': [(B + 'colorizedLeaves1', 1, 1)]})
BOP['eucalyptus'].update({'leaf': [(B + 'colorizedLeaves2', 0, 1), (18, 6, 1)]})   # willow-grey, verify
BOP['autumn'].update({'leaf': [(B + 'leaves3', 2, 1)],         # maple (red)
                      'leaf2': [(B + 'leaves2', 3, 1)],        # orange autumn
                      'leaf3': [(B + 'leaves1', 0, 1)],        # yellow autumn
                      'accent': [(B + 'leaves2', 0, 1)]})      # dead leaves
BOP['cherry'].update({'trunk': [(B + 'logs1', 1, 1)], 'branch': [(B + 'logs1', 1, 1)],
                      'root': [(B + 'logs1', 1, 1)], 'bark': [(B + 'logs1', 1, 1)],
                      'leaf': [(B + 'leaves3', 1, 1)],         # pink cherry
                      'leaf2': [(B + 'leaves3', 3, 1)],        # white cherry
                      'leaf3': [(B + 'leaves3', 1, 1)]})
BOP['petrified'] = dict(VANILLA['petrified'])
BOP['ice'] = dict(VANILLA['ice'])

PALETTES = {'vanilla': VANILLA_LEAVES, 'vanilla-leaves': VANILLA_LEAVES, 'vanilla-wool': VANILLA, 'bop': BOP}


def load_idmap(path):
    """Registry name -> numeric block ID from a level.dat's FML ItemData (blocks start with \\x01)."""
    import nbtlib
    lvl = nbtlib.load(path)
    out = {}
    for e in lvl['FML']['ItemData']:
        k = str(e['K']); v = int(e['V'])
        if k.startswith('\x01'):
            out[k[1:]] = v
    return out

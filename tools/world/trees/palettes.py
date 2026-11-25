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
  bop            Biomes O' Plenty 2.1.0.2308 woods and leaves, metas read from the jar. Names resolve
                 through the pinned registry (docs/survey/block-ids.tsv) or --idmap. Adds the BoP-only
                 variants in VARIANTS (dead, dark, jacaranda).
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

# Biomes O' Plenty 2.1.0.2308 for 1.7.10. Metas read from the jar: BOPBlocks registers logs1-4,
# leaves1-4 and colorizedLeaves1-2 as categories CAT1-4; each block's type is meta & 3 and its
# texture index is category * 4 + type; the order comes from the static name arrays in BlockBOPLog,
# BlockBOPLeaves and BlockBOPColorizedLeaves and matches en_US.lang:
#   logs1  0 sacredoak  1 cherry   2 dark      3 fir           (axis bits +4 / +8 as vanilla)
#   logs2  0 ethereal   1 magic    2 mangrove  3 palm
#   logs3  0 redwood    1 willow   2 dead      3 bigflowerstem
#   logs4  0 pine       1 hellbark 2 jacaranda 3 mahogany
#   leaves1 0 yellowautumn 1 bamboo     2 magic  3 dark
#   leaves2 0 dead (dying) 1 fir        2 ethereal 3 orangeautumn
#   leaves3 0 origin       1 pinkcherry 2 maple  3 whitecherry
#   leaves4 0 hellbark     1 jacaranda
#   colorizedLeaves1 0 sacredoak 1 mangrove 2 palm     3 redwood     (biome-tinted)
#   colorizedLeaves2 0 willow    1 pine     2 mahogany 3 flowering
# Leaf decay works as in vanilla (updateTick decays only if meta & 8 and not meta & 4), so the
# no-decay meta is type | 4. Names resolve to numbers through the pinned registry
# (docs/survey/block-ids.tsv, from C:/qfs/v0) unless --idmap names another world.
B = 'BiomesOPlenty:'

BOP_LOG = {n: (B + b, m) for n, (b, m) in {
    'sacredoak': ('logs1', 0), 'cherry': ('logs1', 1), 'dark': ('logs1', 2), 'fir': ('logs1', 3),
    'ethereal': ('logs2', 0), 'magic': ('logs2', 1), 'mangrove': ('logs2', 2), 'palm': ('logs2', 3),
    'redwood': ('logs3', 0), 'willow': ('logs3', 1), 'dead': ('logs3', 2),
    'pine': ('logs4', 0), 'hellbark': ('logs4', 1), 'jacaranda': ('logs4', 2), 'mahogany': ('logs4', 3)}.items()}
BOP_LEAF = {n: (B + b, t | 4) for n, (b, t) in {
    'yellowautumn': ('leaves1', 0), 'bamboo': ('leaves1', 1), 'magic': ('leaves1', 2), 'dark': ('leaves1', 3),
    'dying': ('leaves2', 0), 'fir': ('leaves2', 1), 'ethereal': ('leaves2', 2), 'orangeautumn': ('leaves2', 3),
    'origin': ('leaves3', 0), 'pinkcherry': ('leaves3', 1), 'maple': ('leaves3', 2), 'whitecherry': ('leaves3', 3),
    'hellbark': ('leaves4', 0), 'jacaranda': ('leaves4', 1),
    'sacredoak': ('colorizedLeaves1', 0), 'mangrove': ('colorizedLeaves1', 1), 'palm': ('colorizedLeaves1', 2),
    'redwood': ('colorizedLeaves1', 3), 'willow': ('colorizedLeaves2', 0), 'pine': ('colorizedLeaves2', 1),
    'mahogany': ('colorizedLeaves2', 2), 'flowering': ('colorizedLeaves2', 3)}.items()}


def wood(log):
    return {r: one(BOP_LOG[log]) for r in ('trunk', 'branch', 'root', 'bark')}


BOP = {k: dict(v) for k, v in VANILLA_LEAVES.items()}
BOP['redwood'] = {**wood('redwood'),
                  'leaf': w(BOP_LEAF['redwood'], 5, BOP_LEAF['pine'], 1), 'leaf2': one(BOP_LEAF['redwood']),
                  'accent': one(L_OAK)}                                  # epicormic sprouts stay oak-green
BOP['mangrove'] = {**wood('mangrove'),
                   'leaf': w(BOP_LEAF['mangrove'], 4, L_JUNGLE, 1), 'leaf2': one(BOP_LEAF['mangrove'])}
BOP['eucalyptus'].update({                                              # BoP 1.7.10 has no eucalyptus wood
    'leaf': w(BOP_LEAF['willow'], 3, L_BIRCH, 1), 'leaf2': w(BOP_LEAF['willow'], 1, L_SPRUCE, 1)})
BOP['autumn'].update({'leaf': one(BOP_LEAF['maple']),                    # red
                      'leaf2': one(BOP_LEAF['orangeautumn']),
                      'leaf3': one(BOP_LEAF['yellowautumn']),
                      'leaf4': w(BOP_LEAF['orangeautumn'], 2, L_OAK, 1),  # last green among the turning
                      'accent': one(BOP_LEAF['dying'])})
BOP['cherry'] = {**wood('cherry'),
                 'leaf': one(BOP_LEAF['pinkcherry']),
                 'leaf2': w(BOP_LEAF['whitecherry'], 2, BOP_LEAF['pinkcherry'], 1),
                 'leaf3': one(BOP_LEAF['pinkcherry']),
                 'leaf4': w(BOP_LEAF['pinkcherry'], 3, L_OAK, 1)}
# petrified stays stone (BoP has no petrified wood), ice stays ice, baobab stays acacia.

# BoP-only variants: an existing growth model re-skinned with another BoP wood. treegen writes them
# under their own name; they exist only in the `bop` palette.
VARIANTS = {'dead': 'petrified', 'dark': 'autumn', 'jacaranda': 'cherry'}
BOP['dead'] = {**wood('dead'), 'core': one(BOP_LOG['dead'])}            # petrified shapes in BoP dead wood
BOP['dark'] = {**wood('dark'),
               'leaf': one(BOP_LEAF['dark']), 'leaf2': w(BOP_LEAF['dark'], 3, L_DARKOAK, 1),
               'leaf3': one(BOP_LEAF['dark']), 'leaf4': one(L_DARKOAK), 'accent': one(BOP_LEAF['dying'])}
BOP['jacaranda'] = {**wood('jacaranda'),
                    'leaf': one(BOP_LEAF['jacaranda']), 'leaf2': one(BOP_LEAF['jacaranda']),
                    'leaf3': one(BOP_LEAF['jacaranda']), 'leaf4': w(BOP_LEAF['jacaranda'], 3, L_OAK, 1)}

# Preview colours for BoP blocks: the mean of each texture's opaque pixels (log *_side, leaves
# *_fancy) in the 2308 jar, leaves brightened about 1.35x like the vanilla preview colours; the grey
# biome-tinted leaves (colorizedLeaves) get a temperate foliage tint instead.
BOP_COLOURS = {
    BOP_LOG['sacredoak']: (88, 89, 52), BOP_LOG['cherry']: (100, 56, 43), BOP_LOG['dark']: (65, 52, 63),
    BOP_LOG['fir']: (97, 85, 69), BOP_LOG['ethereal']: (94, 110, 73), BOP_LOG['magic']: (94, 99, 107),
    BOP_LOG['mangrove']: (198, 184, 159), BOP_LOG['palm']: (101, 75, 46), BOP_LOG['redwood']: (104, 63, 39),
    BOP_LOG['willow']: (77, 82, 51), BOP_LOG['dead']: (63, 57, 48), BOP_LOG['pine']: (91, 72, 55),
    BOP_LOG['hellbark']: (105, 79, 59), BOP_LOG['jacaranda']: (111, 95, 89), BOP_LOG['mahogany']: (106, 80, 64),
    BOP_LEAF['yellowautumn']: (177, 138, 38), BOP_LEAF['bamboo']: (186, 230, 61), BOP_LEAF['magic']: (104, 150, 198),
    BOP_LEAF['dark']: (47, 49, 68), BOP_LEAF['dying']: (134, 105, 57), BOP_LEAF['fir']: (76, 123, 86),
    BOP_LEAF['ethereal']: (69, 127, 88), BOP_LEAF['orangeautumn']: (174, 92, 42), BOP_LEAF['origin']: (80, 230, 54),
    BOP_LEAF['pinkcherry']: (232, 159, 195), BOP_LEAF['maple']: (150, 50, 50), BOP_LEAF['whitecherry']: (219, 195, 209),
    BOP_LEAF['hellbark']: (127, 97, 31), BOP_LEAF['jacaranda']: (113, 90, 150),
    BOP_LEAF['sacredoak']: (72, 132, 44), BOP_LEAF['mangrove']: (70, 128, 46), BOP_LEAF['palm']: (78, 140, 46),
    BOP_LEAF['redwood']: (62, 112, 50), BOP_LEAF['willow']: (86, 126, 66), BOP_LEAF['pine']: (60, 100, 56),
    BOP_LEAF['mahogany']: (78, 128, 44), BOP_LEAF['flowering']: (84, 136, 52),
}
BOP_LEAFY = {k[0] for k in BOP_LEAF.values()}

PALETTES = {'vanilla': VANILLA_LEAVES, 'vanilla-leaves': VANILLA_LEAVES, 'vanilla-wool': VANILLA, 'bop': BOP}


def load_idmap(path=None):
    """Registry name -> numeric block ID: from a level.dat's FML ItemData (blocks start with \\x01),
    or with no path from the pinned registry docs/survey/block-ids.tsv (tools/world/blockids.py)."""
    if path is None:
        import os
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from blockids import load_tsv
        return load_tsv()
    import nbtlib
    lvl = nbtlib.load(path)
    out = {}
    for e in lvl['FML']['ItemData']:
        k = str(e['K']); v = int(e['V'])
        if k.startswith('\x01'):
            out[k[1:]] = v
    return out

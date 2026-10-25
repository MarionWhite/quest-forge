"""Dead-item census: every item in the pack that the data says a player cannot obtain,
or can obtain but has no use for, with the evidence per item.

    py -3.10 -I tools/items/dead_items.py            # writes docs/reference/dead-items.{json,md}
    py -3.10 -I tools/items/dead_items.py --no-jars  # skip the read-only look into the mod jars

It is pure data work: nothing here launches the game. It joins

- the item dump (site/items/data/items.json, recipes.json): every creative-menu stack,
  every readable crafting and furnace recipe, every ChestGenHooks chest table;
- the per-item research (tools/items/descriptions.json): each "how to get it" line is
  classified by sentence into drop / loot / worldgen / mod crafting / trade / use, or into
  creative / technical / disabled when the sentence says so;
- the quest book (pack/config/betterquesting/DefaultQuests.json via tools/quests/qb.py):
  what each quest asks for, hands out or shows, checked against registry.json;
- the pack's own loot configs: Lucky Block drops, ChocolateQuest chest and dungeon props,
  Doomlike chests, Surprise Eggs, the Loot Bags blacklist, the CraftTweaker scripts;
- the ore survey (pack/reports/ore-rates.json): which blocks measurably generate.

What it cannot see is listed in the output under `notRead`: mob drops and dungeon loot
rolled in mod code (Lycanites, OreSpawn, TragicMC, Roguelike, Legends ...), machine
recipes outside the vanilla registries, and the 99 recipe objects whose output the dump
could not read. A "no known source" verdict here means the data saw nothing, not that
nothing exists; the per-item description is the best witness and is quoted beside it.
"""
import argparse, collections, datetime, glob, json, os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'tools', 'quests'))
import qb  # noqa: E402

DATA = os.path.join(REPO, 'site', 'items', 'data')
CONFIG = os.path.join(REPO, 'pack', 'config')
OUT_JSON = os.path.join(REPO, 'docs', 'reference', 'dead-items.json')
OUT_MD = os.path.join(REPO, 'docs', 'reference', 'dead-items.md')
MODS_DIR = os.path.join(os.environ.get('APPDATA', ''), '.crazycraft4', 'mods')

FLAGS = {
    'recipe': 'output of a readable crafting or furnace recipe (CraftTweaker scripts applied)',
    'recipe-special': "output of a mod's own IRecipe class: the output is known, the grid is not readable",
    'ingredient': 'input of some crafting or furnace recipe, directly or through the ore dictionary',
    'quest-task': 'a quest asks for it (retrieval task)',
    'quest-reward': 'a quest hands it out (guaranteed item reward)',
    'quest-choice': 'a quest offers it (choice reward)',
    'quest-icon': 'a quest or quest line shows it as its icon',
    'chest-loot': 'in a ChestGenHooks chest table the dump read (dungeon, mineshaft, temple, stronghold, blacksmith, Railcraft)',
    'loot-bag': 'the Loot Bags mod can roll it (it is in a chest table and its mod is not blacklisted in lootbags.cfg)',
    'lucky-block': 'named in the Lucky Block drop table (pack/config/lucky)',
    'cq-chest': 'in a ChocolateQuest chest table (pack/config/Chocolate/ChestConfig)',
    'cq-structure': 'a block a ChocolateQuest dungeon builds with (pack/config/Chocolate/DungeonConfig)',
    'doomlike-chest': 'in a Doomlike Dungeons chest table (pack/config/DLDungeonsJBG/chests.cfg)',
    'surprise-egg': 'a Surprise Eggs mob-egg prize (pack/config/surpriseeggs)',
    'worldgen-survey': 'a block the ore survey counted in generated chunks (pack/reports/ore-rates.json)',
    'desc:drop': 'its description says a mob or block drops it',
    'desc:loot': 'its description names a chest, dungeon, loot bag, lucky block or gift',
    'desc:worldgen': 'its description says it generates, grows or lies in the world',
    'desc:craft': "its description says it is made in a mod's own machine, altar, table or process",
    'desc:trade': 'its description says it is bought or traded',
    'desc:use': 'its description says it comes from using, placing or throwing another item',
    'desc:season': 'its description says it exists only on calendar dates',
    'desc:command': 'its description names a player command that gives it (/bp, /tokens, /credits, /bq_user)',
    'desc:admin': 'its description says /give, admin or op only',
    'spawn-egg': 'a spawn egg or spawner item with no recipe or loot entry: creative only by nature',
    'desc:creative': 'its description says creative only',
    'desc:technical': 'its description says technical, not obtainable or no recipe/drop',
    'desc:disabled': 'its description says its recipe or source is disabled in this pack or version',
    'desc:quest-only': 'its description says a quest is its only source',
    'tab-creative': "its creative tab is a mod's Creative tab",
    'no-tab': 'no creative tab: hidden from the creative menu and from the default NEI listing',
    'untranslated': 'its display name is a raw language key',
    'blank-icon': 'its icon could not be drawn at the title screen',
    'script-removed': 'pack/scripts removes its recipe (recipes.remove)',
    'script-added': 'pack/scripts adds a recipe for it (recipes.addShaped/addShapeless)',
    'registered': 'registered in the pack world registry (tools/quests/registry.json)',
    'blocklisted': "on qb.py's quest blocklist",
}
SOURCE_FLAGS = {'recipe', 'recipe-special', 'chest-loot', 'lucky-block', 'cq-chest', 'cq-structure',
                'doomlike-chest', 'surprise-egg', 'worldgen-survey', 'script-added',
                'desc:drop', 'desc:loot', 'desc:worldgen', 'desc:craft', 'desc:trade', 'desc:use', 'desc:season',
                'desc:command'}
HARD_SOURCE = SOURCE_FLAGS - {f for f in SOURCE_FLAGS if f.startswith('desc:')}
SPAWN_EGG = re.compile(r'spawn_?eggs?|spawner|egg$', re.I)
STATUS_TEXT = collections.OrderedDict([
    ('ok', 'has a source'),
    ('quest-only', 'a quest hands it out and nothing else does'),
    ('no-source', 'visible in the creative menu, no source in any data read here'),
    ('disabled', 'its description says its recipe or source is disabled in this pack'),
    ('creative', 'creative only (tab or description)'),
    ('technical', 'technical block or item (description, or hidden and untranslated)'),
    ('hidden', 'no creative tab and no description: probably technical, unresearched'),
])

# -- description sentence classes -------------------------------------------------------
NEGATIVE = re.compile(r"creative|technical|unobtain|\bnot?\b|never|cannot|can't|disabled|unused|removed|nothing|"
                      r"misconfigured|wrong name|does not|doesn't", re.I)
SENTENCE_CLASSES = [
    ('desc:drop', re.compile(r"\bdrop|dropped|\bkill|\bslain|\bshed\b|laid by|\blays\b|harvested|\bcaught|\bfished|"
                             r"sheared|\bmilk|butcher|\bdies\b|\bdeath\b|showered|\byields?\b|\d+ ?%|left behind", re.I)),
    ('desc:loot', re.compile(r"\bchests?\b|\bloot\b|dungeon|treasure|lucky block|loot bag|surprise egg|\bgift\b|"
                             r"bonus chest|stronghold|temple|mineshaft|blacksmith chest|castle|\bship\b", re.I)),
    ('desc:worldgen', re.compile(r"generat|\bgrows?\b|\bgrown\b|\bwild\b|found (in|on|at|under|near)|lies on|spawns? in|"
                                 r"forms? on|\bmined?\b|\bore\b|biome|placed (in|at|around|by)|\boccurs|naturally|"
                                 r"in the (overworld|nether|end|twilight)|underground|on the (surface|floor|ground)|"
                                 r"\btrees?\b|\bbush|\bplants?\b|\bcrops?\b|\bvein|\bsapling|\bvillage|\bislands?\b|"
                                 r"\bdimension|\bcave|\blake|\bpool|tall grass|forms? (in|on|at)|\bcreated\b|\bappears?\b|"
                                 r"\bevent\b|ripen", re.I)),
    ('desc:craft', re.compile(r"made (at|in|on|by|with|from)|built (at|in|on)|build it|brewed|distill|cooked|smelt|"
                              r"\bcraft|infuse|\baltar|cauldron|kettle|\boven|spinning|typesetting|countertop|chisel|"
                              r"assembly|\banvil|workbench|\bforge\b|\bpress|juicer|\bmash|\bstill\b|smithing|"
                              r"\btable\b|machine|refine|\bcut (from|at|with|on)|\bsaw\b|combine|shapeless|shaped|"
                              r"recipe|furnace|condenser|transmut|philosopher|upgrade|repair|\bdye\b|\bdyed\b|"
                              r"\bbrew\b|\bbake|\bgrind|\bmill|\bcarve|\bweave|\bsew|\bforged|\bfill|heated|microwave|"
                              r"blender|extract|microscope|engrav|^enhance|^attach|^apply|\bsmelter|crucible|processor", re.I)),
    ('desc:trade', re.compile(r"bought|\bsold|\btrade|\bbuy\b|purchase|\bshop|merchant|villager|blacksmith trades|"
                              r"\btokens?\b|for emeralds|\bcosts?\b|\bbarter", re.I)),
    ('desc:use', re.compile(r"^use |^using |\buses?\b|right-click|left-click|\bthrow|^place|^placed|\bsummon|^given|"
                            r"^break|^pick|picked up|^empty|^wear|^equip|^open|^activate|^sneak|^shoot|^fire|^hit |"
                            r"^tame|^ride|^feed|^read|^write|^click|^hold|^carry|^eat|^drink|^spawn|left (after|over)|"
                            r"\btaken? (from|out)|\bcollect|^cut\b|deploy|\breleased?\b|\bsuit\b|switch|\bwhen you\b|"
                            r"\bcomes? from\b|\bobtained\b", re.I)),
    ('desc:command', re.compile(r"/(?!give\b)[a-z_]{2,}", re.I)),
    ('desc:season', re.compile(r"december|holiday|halloween|easter|christmas|petmas|new year|april", re.I)),
]
NEG_CLASSES = [
    ('desc:creative', re.compile(r"\bcreative\b", re.I)),
    ('desc:technical', re.compile(r"\btechnical\b|not obtainable|unobtainable|no recipe or drop|no recipe, loot or drop|"
                                  r"not craftable|no natural source|no recipe or natural source|not buildable|"
                                  r"never (drops|dropped|spawns|generates)|not placed by world generation|"
                                  r"not obtainable in survival|not in survival", re.I)),
    ('desc:disabled', re.compile(r"disabled in this pack|recipe is disabled|removed in this pack|not in this pack|"
                                 r"in this version|exists only when|misconfigured|wrong name|never (hold|spawns)", re.I)),
    ('desc:admin', re.compile(r"/give|\badmin\b|\bop only|command block", re.I)),
]
QUEST_ONLY = re.compile(r"\bquest\b", re.I)
NO_FUNCTION = re.compile(r"no function|does nothing|no use\b|\bprop\b|unused|placeholder|nothing (else|more|in)|"
                         r"no effect|non-?functional|not implemented|\bNYI\b|unfinished|does not work|no purpose|"
                         r"purely (decorative|cosmetic)|\bcosmetic\b", re.I)

NOT_READ = [
    "Mob drops coded in mod jars (Lycanites, OreSpawn, TragicMC, Legends, Twilight Forest, HEE, Witchery ...): "
    "only what the descriptions say.",
    "Dungeon loot rolled in mod code (Roguelike Dungeons, Recurrent Complex, OreSpawn and TragicMC dungeons, "
    "Twilight Forest hollow hills and towers, Battle Towers): only ChestGenHooks tables and the pack's own "
    "loot configs were read.",
    "Machine, altar, cauldron and other non-vanilla recipes (Witchery, Railcraft rolling machine, ProjectE "
    "transmutation, Psychedelicraft, Legends Suit Assembly): only what the descriptions say.",
    "The 99 IRecipe objects whose getRecipeOutput() was null in the dump: the dump directory with their class "
    "names (unreadableTypes) is gone; only the count survives in recipes.json.",
    "MobProperties (224 mob files) adds no custom drops in this pack (every 'drops' list is empty), and "
    "Lycanites' custom-drop config lines are all blank; both were read, neither adds a source.",
    "Recipes a mod registers only once a world is open: the dump ran at the title screen, so Sync's core "
    "recipe (Sync.cfg hardcoreMode=2 decides it per world) is missing, and any other world-time registration "
    "with it.",
    "Mods the dump saw no crafting recipe for at all, although they have items: ChocolateQuest (its weapons and "
    "staffs are shop and dungeon loot by design), Recurrent Complex (creative tools), and Transformers, which "
    "is the suspicious one: its jar's TFRecipes class calls GameRegistry.addRecipe, addShapelessRecipe and "
    "addSmelting, so vanilla recipes exist in the mod, yet the dump holds none (its RecipeClearConfig class "
    "suggests a config can clear them, or they were registered after the dump ran). Its 44 'no-source' items "
    "are a dump gap to re-check in-game, not dead items.",
    "Mod jars were opened read-only for file listings only (Witchery's recipe class names, MCHeli's "
    "aircraft definitions); no class was decompiled.",
]

# What the "Mod recipe" classes are, for the (c) table.
SPECIAL_NOTES = {
    'RecipeShapelessHidden': "ProjectE's hidden Philosopher's Stone conversions (block <-> ingot, dye cycling)",
    'RecipeAlchemyBag': "ProjectE Alchemy Bag dye recipes",
    'RecipeConvertFluidContainer': "Psychedelicraft: pour one drink container into another",
    'RecipeFillDrink': "Psychedelicraft: fill a bottle or glass",
    'RecipeActionRepresentation': "Psychedelicraft action placeholder",
    'KnightArmourRecipie': "Battlegear heraldic armour: any armour piece plus a crest",
    'LocomotivePaintingRecipe': "Railcraft: locomotive plus dyes",
    'LocomotiveEmblemRecipe': "Railcraft: locomotive plus emblem",
    'EmblemPostEmblemRecipe': "Railcraft emblem post plus emblem",
    'EmblemPostColorRecipe': "Railcraft emblem post plus dye",
    'RoutingTicketCopyRecipe': "Railcraft: copy a routing ticket",
    'BigDoorRecipe': "Malisis Doors: carriage and medieval doors from a door plus frame material",
    'TemplateRecipe': "Storage Drawers upgrade template",
    'MicroRecipe$': "Forge Microblocks: saw plus any block (every microblock)",
    'EnderStorageRecipe': "Ender Storage: chest/pouch colour from three wool",
    'QuiverRecipie2': "Battlegear quiver filling",
    'ShieldRemoveArrowRecipie': "Battlegear: pull arrows out of a shield",
}


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def norm_id(tok, default_ns='minecraft'):
    tok = tok.strip().strip('"\'')
    if not tok:
        return None
    if ':' not in tok:
        tok = default_ns + ':' + tok
    return tok


def classify_get(text):
    """Classes a 'how to get it' line fires. Sentences with a negative word count only
    for the negative classes, so 'Creative only. Worn, never dropped, by guards' is not a drop."""
    out = set()
    if not text:
        return out
    for sent in re.split(r'[.;]\s+|[.;]$', text):
        sent = sent.strip()
        if not sent:
            continue
        neg = bool(NEGATIVE.search(sent))
        for cls, rx in NEG_CLASSES:
            if rx.search(sent):
                out.add(cls)
        if neg:
            continue
        for cls, rx in SENTENCE_CLASSES:
            if rx.search(sent):
                out.add(cls)
    if QUEST_ONLY.search(text) and not (out & SOURCE_FLAGS):
        out.add('desc:quest-only')
    return out


def family_rows(ids):
    """Collapse 'legends:dynamicHorrorBlock1..100' into one row. Returns [(label, ids)]."""
    groups = collections.OrderedDict()
    for iid in sorted(ids):
        m = re.match(r'^(.*?)(\d+)$', iid)
        prefix = m.group(1) if m else iid
        groups.setdefault(prefix, []).append(iid)
    rows = []
    for prefix, members in groups.items():
        if len(members) >= 4 and prefix != members[0]:
            nums = sorted(int(re.match(r'^.*?(\d+)$', x).group(1)) for x in members)
            rows.append(('%s%d..%d (%d items)' % (prefix, nums[0], nums[-1], len(members)), members))
        else:
            for x in members:
                rows.append((x, [x]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', default=OUT_JSON)
    ap.add_argument('--md', default=OUT_MD)
    ap.add_argument('--no-jars', action='store_true', help='do not list recipe classes from the mod jars')
    a = ap.parse_args()

    # -- the dump ------------------------------------------------------------------------------
    site = load(os.path.join(DATA, 'items.json'))
    rec = load(os.path.join(DATA, 'recipes.json'))
    mods = site['mods']
    kinds = site['kinds']
    tabs = site['tabs']
    loot_cats = site['lootCats']
    rows = site['items']

    items = collections.OrderedDict()  # iid -> record
    for idx, r in enumerate(rows):
        base = r['k'].split('#')[0]
        iid, meta = base.rsplit('@', 1)
        it = items.get(iid)
        if it is None:
            it = items[iid] = {'name': r['n'], 'mod': mods[r['m']]['id'], 'modName': mods[r['m']]['name'],
                               'kind': kinds[r['c']], 'variants': 0, 'metas': set(), 'flags': set(),
                               'tabs': set(), 'rows': [], 'get': '', 'desc': '', 'descSrc': None, 'loot': []}
        it['variants'] += 1
        it['metas'].add(meta)
        it['rows'].append(idx)
        if 't' in r:
            it['tabs'].add(tabs[r['t']])
        else:
            it['flags'].add('no-tab')
        if r.get('u'):
            it['flags'].add('untranslated')
        if r.get('b'):
            it['flags'].add('blank-icon')
        if 'lt' in r:
            it['flags'].add('chest-loot')
            for ci, pct, lo, hi in r['lt']:
                it['loot'].append([loot_cats[ci], pct])
    for it in items.values():
        if it['tabs'] and all('creative' in t.lower() for t in it['tabs']):
            it['flags'].add('tab-creative')
    known_ids = set(items)

    # -- recipes --------------------------------------------------------------------------------
    special_of = collections.defaultdict(set)
    recipe_out = set()
    ingredient_keys = set()
    ores = rec['ores']
    for x in rec['crafting']:
        oid = x['out'].rsplit('@', 1)[0]
        if x['type'] == 'special':
            special_of[oid].add(x['class'])
        else:
            recipe_out.add(oid)
        for i in x.get('in', []):
            if not i:
                continue
            if i.startswith('ore:'):
                for m in ores.get(i[4:], []):
                    ingredient_keys.add(m.rsplit('@', 1)[0])
            else:
                ingredient_keys.add(i.rsplit('@', 1)[0])
    for x in rec['smelting']:
        recipe_out.add(x['out'].rsplit('@', 1)[0])
        for i in x.get('in', []):
            if i:
                ingredient_keys.add(i.rsplit('@', 1)[0])
    for iid, it in items.items():
        if iid in recipe_out:
            it['flags'].add('recipe')
        if iid in special_of:
            it['flags'].add('recipe-special')
            it['specialClasses'] = sorted(special_of[iid])
        if iid in ingredient_keys:
            it['flags'].add('ingredient')

    # -- CraftTweaker scripts -----------------------------------------------------------------
    scripts = {}
    for path in sorted(glob.glob(os.path.join(REPO, 'pack', 'scripts', '*.zs'))):
        txt = read(path)
        for verb, flag in (('remove', 'script-removed'), ('add(?:Shaped|Shapeless)', 'script-added')):
            for m in re.finditer(r'recipes\.%s\(<([^>]+)>' % verb, txt):
                parts = m.group(1).split(':')
                iid = parts[0] + ':' + parts[1]
                scripts.setdefault(iid, set()).add(flag.split('-')[1])
                if iid in items:
                    items[iid]['flags'].add(flag)
    script_rows = sorted((k, sorted(v)) for k, v in scripts.items())

    # -- the pack's loot configs -------------------------------------------------------------
    anomalies = []

    # Lucky Block
    lucky_ids = set()
    lucky_path = os.path.join(CONFIG, 'lucky', 'LuckyBlockProperties.txt')
    lucky_note = 'no Lucky Block config'
    if os.path.exists(lucky_path):
        txt = read(lucky_path)
        for m in re.finditer(r'\b(?:ID|id)=([A-Za-z0-9_:.|-]+)', txt):
            iid = norm_id(m.group(1))
            if iid in known_ids:
                lucky_ids.add(iid)
        m = re.search(r'^spawnrate=(\d+)', txt, re.M)
        lucky_note = 'Lucky Blocks spawn 1 in %s chunks and drop %d distinct items' % (m.group(1) if m else '?', len(lucky_ids))
    for iid in lucky_ids:
        items[iid]['flags'].add('lucky-block')

    # ChocolateQuest chests
    cq_ids = set()
    for path in sorted(glob.glob(os.path.join(CONFIG, 'Chocolate', 'ChestConfig', '*.prop'))):
        rel = os.path.relpath(path, REPO).replace('\\', '/')
        for line in read(path).splitlines():
            m = re.match(r'^\s*(\w+)\s*=\s*([A-Za-z0-9_]+:[A-Za-z0-9_]+)(\s*)(.*)$', line)
            if not m:
                continue
            iid, rest = m.group(2), m.group(4)
            if not rest.startswith(','):
                anomalies.append('%s: `%s` is malformed (a space where a comma should be), so this chest entry '
                                 'never rolls' % (rel, line.strip()))
                continue
            if iid not in known_ids:
                anomalies.append('%s: `%s` names an item that does not exist (%s), so this chest entry never '
                                 'rolls' % (rel, line.strip(), iid))
                continue
            cq_ids.add(iid)
    for iid in cq_ids:
        items[iid]['flags'].add('cq-chest')

    # ChocolateQuest dungeon build blocks (only dungeons with chance > 0)
    cq_struct = set()
    for path in sorted(glob.glob(os.path.join(CONFIG, 'Chocolate', 'DungeonConfig', '*.prop'))):
        txt = read(path)
        m = re.search(r'^\s*chance\s*=\s*(\d+)', txt, re.M)
        if m and int(m.group(1)) == 0:
            continue
        for m in re.finditer(r'\b([A-Za-z0-9_]+:[A-Za-z0-9_]+)\b', txt):
            if m.group(1) in known_ids:
                cq_struct.add(m.group(1))
    for iid in cq_struct:
        items[iid]['flags'].add('cq-structure')

    # Doomlike Dungeons chests
    dl_ids = set()
    dl_path = os.path.join(CONFIG, 'DLDungeonsJBG', 'chests.cfg')
    if os.path.exists(dl_path):
        for line in read(dl_path).splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 5:
                iid = norm_id(re.sub(r'\(\d+\)$', '', parts[2]))  # minecraft:potion(8229) = meta 8229
                if iid in known_ids:
                    dl_ids.add(iid)
                else:
                    anomalies.append('pack/config/DLDungeonsJBG/chests.cfg: `%s` names an unknown item' % line)
    for iid in dl_ids:
        items[iid]['flags'].add('doomlike-chest')

    # Surprise Eggs
    se_ids = set()
    se_cfg = os.path.join(CONFIG, 'surpriseeggs', 'surpriseeggs.cfg')
    se_props = os.path.join(CONFIG, 'surpriseeggs', 'se-properties.txt')
    se_active = False
    if os.path.exists(se_cfg):
        se_active = any(int(v) > 0 for v in re.findall(r'ChanceOutOf100=(\d+)', read(se_cfg)))
    if se_active and os.path.exists(se_props):
        for m in re.finditer(r'\bid\s*=\s*([A-Za-z0-9_:]+)', read(se_props)):
            iid = norm_id(m.group(1))
            if iid in known_ids:
                se_ids.add(iid)
    for iid in se_ids:
        items[iid]['flags'].add('surprise-egg')

    # Loot Bags: general loot is the ChestGenHooks tables minus a mod blacklist
    bag_black = set()
    lb_path = os.path.join(CONFIG, 'lootbags.cfg')
    if os.path.exists(lb_path):
        m = re.search(r'"Global Blacklist"\s*<([^>]*)>', read(lb_path), re.S)
        if m:
            bag_black = set(x.strip() for x in m.group(1).split() if x.strip())
    for iid, it in items.items():
        if 'chest-loot' in it['flags'] and it['mod'] not in bag_black and iid.split(':')[0] not in bag_black:
            it['flags'].add('loot-bag')

    # -- the ore survey: blocks that measurably generate -----------------------------------
    survey_blocks = set()
    survey_path = os.path.join(REPO, 'pack', 'reports', 'ore-rates.json')
    if os.path.exists(survey_path):
        for dim in load(survey_path).values():
            for e in dim.get('blocks', []) + dim.get('bulk_terrain', []):
                b = e.get('block') if isinstance(e, dict) else None
                if b:
                    survey_blocks.add(b)
    for iid in survey_blocks:
        if iid in items:
            items[iid]['flags'].add('worldgen-survey')

    # -- registry ---------------------------------------------------------------------------
    reg = qb.load_registry()
    reg_names = set(reg['items']) | set(reg['blocks'])
    for iid, it in items.items():
        if iid in reg_names:
            it['flags'].add('registered')
    reg_not_dump = collections.OrderedDict()
    for n in sorted(reg_names):
        if n not in known_ids:
            reg_not_dump.setdefault(n.split(':')[0], []).append(n)

    # -- descriptions -----------------------------------------------------------------------
    desc = {k: v for k, v in load(os.path.join(HERE, 'descriptions.json')).items() if not k.startswith('_')}
    desc_src = load(os.path.join(HERE, 'descriptions-sources.json'))
    described = 0
    for iid, it in items.items():
        keys = [iid] + ['%s@%s' % (iid, m) for m in sorted(it['metas'], key=lambda s: int(s) if s.isdigit() else 0)]
        gets, ds, srcs = [], [], []
        for k in keys:
            v = desc.get(k)
            if v is None:
                continue
            if isinstance(v, str):
                ds.append(v)
            else:
                if v.get('d'):
                    ds.append(v['d'])
                if v.get('get'):
                    gets.append(v['get'])
            s = desc_src.get(k)
            if s:
                srcs.append(s if isinstance(s, str) else json.dumps(s))
        if gets or ds:
            described += 1
        it['get'] = ' / '.join(dict.fromkeys(gets))
        it['desc'] = ds[0] if ds else ''
        it['descSrc'] = ','.join(sorted(set(srcs))) if srcs else None
        classes = set()
        for g in gets:
            classes |= classify_get(g)
        if not gets:
            # No "how to get" line: a description that itself says technical/creative still counts.
            for d in ds:
                for cls, rx in NEG_CLASSES[:2]:
                    if rx.search(d):
                        classes.add(cls)
        it['flags'] |= classes

    # -- the quest book ---------------------------------------------------------------------
    book = qb.load('pack')
    line_of = book.line_of()
    qname = {qid: qb.name(q) for qid, q in book.quests.items()}
    qline = {qid: (qb.strip(book.line_name(line_of[qid][0])) if line_of.get(qid) else '') for qid in book.quests}
    quest_refs = collections.defaultdict(list)  # iid -> [(qid, kind)]
    for qid, q in sorted(book.quests.items()):
        ic = qb.props(q).get('icon:10')
        if ic:
            quest_refs[ic['id:8']].append((qid, 'icon'))
        for t in qb.tasks(q):
            for s in qb.stacks_of(t):
                quest_refs[s['id:8']].append((qid, 'task'))
        for r in qb.rewards(q):
            kind = 'reward' if r['rewardID:8'] == 'bq_standard:item' else 'choice'
            for s in qb.stacks_of(r):
                quest_refs[s['id:8']].append((qid, kind))
    for l in book.lines:
        ic = l['properties:10']['betterquesting:10'].get('icon:10')
        if ic:
            quest_refs[ic['id:8']].append(('line %d' % l['lineID:3'], 'icon'))
    for iid, refs in quest_refs.items():
        if iid in items:
            for qid, kind in refs:
                items[iid]['flags'].add('quest-' + kind)
            items[iid]['quests'] = sorted(set((str(q), k) for q, k in refs), key=lambda x: (x[1], x[0]))

    # -- blocklist ---------------------------------------------------------------------------
    for iid, it in items.items():
        why = qb.blocked(iid, 'any')
        if why:
            it['flags'].add('blocklisted')
            it['blocklist'] = why

    # -- status -------------------------------------------------------------------------------
    for iid, it in items.items():
        f = it['flags']
        hidden = 'no-tab' in f and not it['tabs']
        if it['kind'] == 'item' and not (f & HARD_SOURCE) and (it['name'].startswith('Spawn ') or SPAWN_EGG.search(iid)):
            f.add('spawn-egg')
        if f & SOURCE_FLAGS:
            status = 'ok'
        elif 'quest-reward' in f or 'quest-choice' in f:
            status = 'quest-only'
        elif 'desc:creative' in f or 'spawn-egg' in f:
            status = 'creative'
        elif 'desc:technical' in f:
            status = 'technical'
        elif 'desc:disabled' in f:
            status = 'disabled'
        elif 'tab-creative' in f:
            status = 'creative'
        elif hidden and not (it['get'] or it['desc']):
            status = 'hidden'
        elif hidden:
            status = 'technical'
        else:
            status = 'no-source'
        it['status'] = status
        # use: an ingredient, a quest task, a thing with intrinsic use (gear, food, block), or a described function
        has_use = ('ingredient' in f or 'quest-task' in f or it['kind'] != 'item')
        it['noFunction'] = bool(it['desc'] and NO_FUNCTION.search(it['desc']))
        it['noUse'] = status == 'ok' and not has_use and (not it['desc'] or it['noFunction'])
        it['unusedIngredient'] = status == 'ok' and not has_use  # looser: nothing consumes it, no quest asks

    # -- quests: references that cannot be satisfied -------------------------------------
    problems = []
    for qid, q in sorted(book.quests.items()):
        refs = []
        ic = qb.props(q).get('icon:10')
        if ic:
            refs.append(('icon', ic))
        for t in qb.tasks(q):
            for s in qb.stacks_of(t):
                refs.append(('task', s))
        for r in qb.rewards(q):
            kind = 'reward' if r['rewardID:8'] == 'bq_standard:item' else 'choice'
            for s in qb.stacks_of(r):
                refs.append((kind, s))
        for kind, s in refs:
            iid = s['id:8']
            why = qb.blocked(iid, {'task': 'task', 'reward': 'reward', 'choice': 'reward', 'icon': 'icon'}[kind])
            if why:
                problems.append({'quest': qid, 'kind': kind, 'item': iid, 'problem': 'blocklisted: ' + why})
            if iid not in reg_names:
                problems.append({'quest': qid, 'kind': kind, 'item': iid,
                                 'problem': 'not registered in the pack (tools/quests/registry.json)'})
                continue
            if iid not in items:
                problems.append({'quest': qid, 'kind': kind, 'item': iid,
                                 'problem': 'registered, but absent from the item dump: the dump client did not '
                                            'register it (MCHeli loads aircraft from assets/mcheli; see the note)'})
                continue
            it = items[iid]
            st = it['status']
            if kind == 'task' and st != 'ok':
                problems.append({'quest': qid, 'kind': kind, 'item': iid,
                                 'problem': 'asks for an item the census calls "%s"' % st})
            elif kind == 'task' and 'recipe-special' in it['flags'] and not (it['flags'] & (SOURCE_FLAGS - {'recipe-special'})):
                problems.append({'quest': qid, 'kind': kind, 'item': iid,
                                 'problem': 'its only recipe is a mod recipe class whose grid the dump cannot read'})
            if kind in ('reward', 'choice') and st in ('creative', 'technical', 'hidden'):
                problems.append({'quest': qid, 'kind': kind, 'item': iid,
                                 'problem': 'hands out an item the census calls "%s"' % st})
    hunt = qb.check_hunt(book)
    for e in hunt.errors:
        problems.append({'quest': None, 'kind': 'hunt/location', 'item': '', 'problem': e})
    creative_rewards = [p for p in problems if p['kind'] in ('reward', 'choice')]
    problems = [p for p in problems if p['kind'] not in ('reward', 'choice')]

    # -- the unreadable recipes ----------------------------------------------------------------
    special_classes = collections.Counter()
    for x in rec['crafting']:
        if x['type'] == 'special':
            special_classes[x['class']] += 1
    special_only = sorted(iid for iid, it in items.items()
                          if 'recipe-special' in it['flags'] and 'recipe' not in it['flags'])
    witchery_classes = []
    mcheli_defs = None
    if not a.no_jars and os.path.isdir(MODS_DIR):
        wj = os.path.join(MODS_DIR, 'Witchery.jar')
        if os.path.exists(wj):
            with zipfile.ZipFile(wj) as z:
                witchery_classes = sorted(n[len('com/emoniph/witchery/'):-len('.class')] for n in z.namelist()
                                          if n.startswith('com/emoniph/witchery/crafting/Recipe') and '$' not in n)
        mz = os.path.join(MODS_DIR, 'MCHeli.zip')
        live_assets = os.path.join(os.path.dirname(MODS_DIR), 'assets', 'mcheli', 'helicopters')
        if os.path.exists(mz):
            with zipfile.ZipFile(mz) as z:
                in_zip = sum(1 for n in z.namelist()
                             if re.match(r'assets/mcheli/(helicopters|planes|vehicles)/.*\.txt$', n))
            mcheli_defs = {'inZip': in_zip, 'liveAssetsFolder': os.path.isdir(live_assets),
                           'bell47gInLiveAssets': os.path.exists(os.path.join(live_assets, 'bell47g.txt'))}

    # -- counts -------------------------------------------------------------------------------
    by_status = collections.Counter(it['status'] for it in items.values())
    counts = collections.OrderedDict([
        ('stacks', len(rows)), ('items', len(items)), ('mods', len(mods)),
        ('described', described), ('undescribed', len(items) - described),
    ])
    for st in STATUS_TEXT:
        counts[st] = by_status.get(st, 0)
    counts['noUse'] = sum(1 for it in items.values() if it['noUse'])
    counts['unusedIngredient'] = sum(1 for it in items.values() if it['unusedIngredient'])
    counts['specialOnly'] = len(special_only)
    counts['nullOutputRecipes'] = rec.get('unreadable', 0)
    counts['questProblems'] = len(problems)
    counts['creativeRewards'] = len(creative_rewards)
    counts['registryNotInDump'] = sum(len(v) for v in reg_not_dump.values())
    counts['configAnomalies'] = len(anomalies)

    # -- JSON ---------------------------------------------------------------------------------
    out_items = collections.OrderedDict()
    for iid, it in sorted(items.items(), key=lambda kv: (kv[1]['mod'].lower(), kv[0].lower())):
        rec_ = collections.OrderedDict([
            ('name', it['name']), ('mod', it['mod']), ('kind', it['kind']), ('variants', it['variants']),
            ('status', it['status']), ('flags', sorted(it['flags'])),
        ])
        if it['noUse']:
            rec_['noUse'] = True
        elif it['unusedIngredient']:
            rec_['unused'] = True
        if it['get']:
            rec_['get'] = it['get']
        if it['descSrc']:
            rec_['descSrc'] = it['descSrc']
        if it.get('quests'):
            rec_['quests'] = [list(x) for x in it['quests']]
        if it.get('specialClasses'):
            rec_['recipeClasses'] = it['specialClasses']
        if it.get('loot'):
            rec_['chestLoot'] = it['loot']
        if it.get('blocklist'):
            rec_['blocklist'] = it['blocklist']
        out_items[iid] = rec_
    out = collections.OrderedDict([
        ('built', datetime.date.today().isoformat()),
        ('dump', site['built']),
        ('counts', counts),
        ('statuses', STATUS_TEXT),
        ('flags', FLAGS),
        ('notRead', NOT_READ),
        ('configAnomalies', anomalies),
        ('scripts', script_rows),
        ('registryNotInDump', reg_not_dump),
        ('unreadableRecipes', collections.OrderedDict([
            ('nullOutput', rec.get('unreadable', 0)),
            ('specialClasses', collections.OrderedDict(special_classes.most_common())),
            ('specialOnlyItems', special_only),
            ('witcheryRecipeClasses', witchery_classes),
        ])),
        ('mcheli', mcheli_defs),
        ('questProblems', problems),
        ('creativeRewards', creative_rewards),
        ('items', out_items),
    ])
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
        f.write('\n')

    write_md(a.md, out, items, qname, qline, lucky_note, se_active, bag_black)
    print('%d stacks -> %d items from %d mods; %s' % (len(rows), len(items), len(mods),
          ', '.join('%s %d' % (k, counts[k]) for k in list(STATUS_TEXT) + ['noUse'])))
    print('%d quest problems, %d creative/technical rewards, %d registry ids not in the dump, %d config anomalies'
          % (len(problems), len(creative_rewards), counts['registryNotInDump'], len(anomalies)))
    print('wrote', os.path.relpath(a.json, REPO), 'and', os.path.relpath(a.md, REPO))


# -- Markdown ---------------------------------------------------------------------------------

def esc(s):
    return (s or '').replace('|', '\\|').replace('\n', ' ').strip()


def short(s, n=110):
    s = esc(s)
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def flag_words(flags):
    skip = {'registered', 'blank-icon'}
    return ', '.join(f for f in sorted(flags) if f not in skip)


def write_md(path, out, items, qname, qline, lucky_note, se_active, bag_black):
    c = out['counts']
    L = []
    w = L.append
    w('# Dead items: what a player cannot get, and what has no use')
    w('')
    w('Generated by `tools/items/dead_items.py` on %s from the %s item dump; the full table with every '
      'flag per item is `dead-items.json` beside this file. Written for the quest writers: what not to ask '
      'for, what not to hand out, and what the texture ranking can leave for last.' % (out['built'], out['dump']))
    w('')
    w('> **Read this first.** A "no known source" here means none of the data read by the script shows a '
      'way to get the item. The script does not read mob drops or dungeon loot coded inside mod jars, nor '
      'machine recipes outside the vanilla crafting registry, so the per-item research line ("how to get it") '
      'is quoted beside each verdict and is the better witness where the two disagree. "What the data cannot '
      'see" lists the blind spots.')
    w('')
    w('## Counts')
    w('')
    w('| | |')
    w('|---|---|')
    w('| Stacks in the creative menu | %d |' % c['stacks'])
    w('| Distinct items (id without meta) | %d from %d mods |' % (c['items'], c['mods']))
    w('| With a researched description | %d (%d without) |' % (c['described'], c['undescribed']))
    w('| **Has a source** (recipe, loot, drop, worldgen, trade, mod crafting ...) | **%d** |' % c['ok'])
    w('| **(a) No known source, visible in the creative menu** | **%d** |' % c['no-source'])
    w('| (a) Source disabled in this pack (description says so) | %d |' % c['disabled'])
    w('| (a) Only a quest hands it out | %d |' % c['quest-only'])
    w('| (a) Creative only (creative tab, or the research says so) | %d |' % c['creative'])
    w('| (a) Technical blocks and items (research says so, or hidden with a description) | %d |' % c['technical'])
    w('| (a) Hidden, unresearched (no creative tab, no description) | %d |' % c['hidden'])
    w('| **(b) Has a source but no use** (plain item: not an ingredient, not asked by a quest, described as having '
      'no function or not described) | **%d** |' % c['noUse'])
    w('| (b) looser: has a source, nothing consumes it and no quest asks for it (gear, food and blocks excluded) | %d |'
      % c['unusedIngredient'])
    w('| **(c) Items whose only recipe is an unreadable mod recipe class** | **%d** (plus %d recipe objects with no '
      'readable output at all) |' % (c['specialOnly'], c['nullOutputRecipes']))
    w('| **(d) Quest references the pack cannot satisfy** | **%d** |' % c['questProblems'])
    w('| **(e) Rewards that are creative-only or technical** | **%d** |' % c['creativeRewards'])
    w('| Registered ids the dump never saw | %d (see the MCHeli note) |' % c['registryNotInDump'])
    w('| Loot config lines that never fire | %d |' % c['configAnomalies'])
    w('')
    w('Statuses: ' + '; '.join('**%s** = %s' % (k, v) for k, v in out['statuses'].items()) + '.')
    w('')

    # -- data gaps / MCHeli --------------------------------------------------------------
    w('## What the data cannot see')
    w('')
    for n in out['notRead']:
        w('- ' + n)
    rnd = out['registryNotInDump']
    if rnd:
        w('')
        w('**Registered in the world but absent from the item dump** (%d ids). These are not dead: the dump '
          'client never registered them, or they are blocks with no item form.' % sum(len(v) for v in rnd.values()))
        w('')
        for mod, ids in sorted(rnd.items(), key=lambda kv: -len(kv[1])):
            sample = ', '.join('`%s`' % x for x in ids[:6]) + (' …' if len(ids) > 6 else '')
            w('- `%s`: %d (%s)' % (mod, len(ids), sample))
        mc = out.get('mcheli')
        if mc:
            w('')
            w('**MCHeli.** %d aircraft and vehicle definitions ship inside `MCHeli.zip`; the live client %s an '
              '`assets/mcheli` folder beside `mods/`, and `bell47g.txt` %s there, with `AddRecipe = " G ", "IXI", '
              '" I "` (glass, iron ingots, one iron block). The quest-book audit found that a dedicated trial '
              'server did not register `mcheli:bell47g`, and the play server at `C:\\qfs\\friends` has no '
              '`assets/mcheli` folder and no world yet to read a registry from. So the Bell 47G is craftable on '
              'the client and *unverified* on the server; quest 33 needs a server-side check (`/qfcensus` or the '
              'server world\'s `level.dat` registry) before it is called broken or fine.'
              % (mc['inZip'], 'has' if mc['liveAssetsFolder'] else 'lacks', 'is' if mc['bell47gInLiveAssets'] else 'is not'))
    if out['configAnomalies']:
        w('')
        w('**Loot config lines that never fire:**')
        w('')
        for x in out['configAnomalies']:
            w('- ' + x)
    w('')
    w('Loot configs read: %s; Surprise Eggs are %s; Loot Bags roll the vanilla chest tables minus the blacklisted '
      'mods (%s); Doomlike chests hold vanilla gear only; ChocolateQuest chests hold vanilla items plus its own '
      'weapons and staffs; Roguelike Dungeons keeps its loot in its jar (not read).'
      % (lucky_note, 'active (mob eggs)' if se_active else 'inactive', ', '.join(sorted(bag_black)) or 'none'))
    w('')

    # -- (a) per mod ---------------------------------------------------------------------
    by_mod = collections.defaultdict(lambda: collections.defaultdict(list))
    for iid, it in items.items():
        by_mod[(it['mod'], it['modName'])][it['status']].append(iid)

    def table(ids, cap=None):
        w('| Item | Name | Kind | Evidence | How to get it (research) |')
        w('|---|---|---|---|---|')
        frows = family_rows(ids)
        more = 0
        if cap and len(frows) > cap:
            more = len(frows) - cap
            frows = frows[:cap]
        for label, members in frows:
            it = items[members[0]]
            nm = it['name'] if len(members) == 1 else '%s …' % it['name']
            var = '' if len(members) > 1 or it['variants'] == 1 else ' (%d variants)' % it['variants']
            w('| `%s`%s | %s | %s | %s | %s |' % (esc(label), var, short(nm, 40), it['kind'],
                                               flag_words(it['flags']) or '—', short(it['get'] or it['desc'], 120) or '—'))
        if more:
            w('| … | %d more rows | | | see dead-items.json |' % more)

    w('## (a) Items with no known source')
    w('')
    w('Per mod, most affected first. **Visible, no known source** rows are in the creative menu and nothing read '
      'here gives them to a player: these are the ones to research, give a recipe, or keep out of quests. '
      'Disabled, quest-only, creative, technical and hidden rows follow for completeness, collapsed into '
      'families where the names run `Block1..Block100`.')
    w('')
    order = sorted(by_mod.items(), key=lambda kv: (-sum(len(v) for s, v in kv[1].items() if s != 'ok'), kv[0][1].lower()))
    for (mod, mod_name), st in order:
        dead = {s: v for s, v in st.items() if s != 'ok'}
        if not dead:
            continue
        total = sum(len(v) for v in st.values())
        w('### %s (`%s`): %d of %d items without a source' % (mod_name, mod, sum(len(v) for v in dead.values()), total))
        w('')
        for status, title in (('no-source', 'Visible, no known source'), ('disabled', 'Source disabled in this pack'),
                              ('quest-only', 'Only a quest hands it out'), ('creative', 'Creative only'),
                              ('technical', 'Technical'), ('hidden', 'Hidden and unresearched')):
            ids = dead.get(status)
            if not ids:
                continue
            w('**%s** (%d)' % (title, len(ids)))
            w('')
            table(sorted(ids), cap=None if status in ('no-source', 'disabled', 'quest-only') else 40)
            w('')

    # -- (b) ----------------------------------------------------------------------------
    w('## (b) Items with a source but no use')
    w('')
    w('Plain items (not gear, food or blocks, which have a use by nature) that no recipe consumes, no quest asks '
      'for, and whose description says they do nothing or is missing. Per mod. An undescribed item lands here '
      'because nobody has researched it yet, not because it is known to be useless: MCHeli\'s rows are its real '
      'gear (Stinger and Javelin launchers, parachute, chain, UAV stations) whose names the dump could not '
      'translate.')
    w('')
    nouse = collections.defaultdict(list)
    for iid, it in items.items():
        if it['noUse']:
            nouse[(it['mod'], it['modName'])].append(iid)
    for (mod, mod_name), ids in sorted(nouse.items(), key=lambda kv: (-len(kv[1]), kv[0][1].lower())):
        w('### %s (`%s`): %d' % (mod_name, mod, len(ids)))
        w('')
        w('| Item | Name | Source | Description |')
        w('|---|---|---|---|')
        for label, members in family_rows(sorted(ids)):
            it = items[members[0]]
            src = ', '.join(sorted(it['flags'] & SOURCE_FLAGS))
            w('| `%s` | %s | %s | %s |' % (esc(label), short(it['name'], 40), src, short(it['desc'] or it['get'], 120) or '—'))
        w('')

    # -- (c) ----------------------------------------------------------------------------
    ur = out['unreadableRecipes']
    w('## (c) Items whose recipe the dump cannot read')
    w('')
    w('The dump reads vanilla shaped and shapeless recipes (and their ore-dictionary forms) plus furnace recipes. '
      'Two kinds escape it:')
    w('')
    w('1. **%d recipe objects whose output is null** until crafted (`getRecipeOutput()` returns nothing): the '
      'item browser cannot even say what they make. The dump recorded their class names in a file that was not '
      'kept; the one surviving note says most were Witchery\'s. Witchery\'s jar holds these dynamic-output '
      'recipe classes: %s. They dye, repair, attach taglocks to, or add keys and potions to an existing item, so '
      'none of them is the only way to get something.' % (ur['nullOutput'], ', '.join('`%s`' % x for x in ur['witcheryRecipeClasses']) or '(jar not read)'))
    w('2. **%d recipe objects of a mod\'s own class with a readable output** ("Mod recipe" in the browser). '
      'By class:' % sum(ur['specialClasses'].values()))
    w('')
    w('| Recipe class | Recipes | What it is |')
    w('|---|---|---|')
    for cls, n in ur['specialClasses'].items():
        w('| `%s` | %d | %s |' % (cls, n, SPECIAL_NOTES.get(cls.rsplit('.', 1)[-1], '')))
    w('')
    w('**Items whose only recipe is one of these** (%d): a quest can still ask for them, but the item page shows '
      'no grid, so the quest text has to explain the craft.' % len(ur['specialOnlyItems']))
    w('')
    w('| Item | Name | Recipe class | Other sources |')
    w('|---|---|---|---|')
    for label, members in family_rows(ur['specialOnlyItems']):
        it = items[members[0]]
        other = ', '.join(sorted((it['flags'] & SOURCE_FLAGS) - {'recipe-special'})) or '—'
        w('| `%s` | %s | %s | %s |' % (esc(label), short(it['name'], 40),
                                       ', '.join(x.rsplit('.', 1)[-1] for x in it.get('specialClasses', [])), other))
    w('')

    # -- (d) ----------------------------------------------------------------------------
    w('## (d) Quests that reference things the pack cannot deliver')
    w('')
    w('Every quest reference re-checked against `tools/quests/registry.json` (the pack world registry), the item '
      'dump and this census; hunt targets and location dimensions against `entities.json` (`qb.py check hunt`).')
    w('')
    if out['questProblems']:
        w('| Quest | Line | Ref | Item | Problem |')
        w('|---|---|---|---|---|')
        for p in out['questProblems']:
            q = p['quest']
            w('| %s | %s | %s | `%s` | %s |' % (
                ('%d %s' % (q, esc(qname.get(q, '')))) if isinstance(q, int) else '—',
                esc(qline.get(q, '')) if isinstance(q, int) else '', p['kind'], esc(p['item']), esc(p['problem'])))
    else:
        w('None.')
    w('')
    w('`qb.py check` passes on both books; the rows above are what its `ids` check does not test: whether a '
      'registered item is actually obtainable. Verify in-game before editing a quest: a title-screen dump misses '
      'recipes a mod registers only once a world is open (Sync\'s core recipe), and a description that says '
      '"creative only" is research, not a test.')
    w('')

    # -- (e) ----------------------------------------------------------------------------
    w('## (e) Creative-only or technical items handed out as rewards')
    w('')
    if out['creativeRewards']:
        w('| Quest | Line | Reward | Item | Census |')
        w('|---|---|---|---|---|')
        for p in out['creativeRewards']:
            q = p['quest']
            w('| %d %s | %s | %s | `%s` | %s |' % (q, esc(qname.get(q, '')), esc(qline.get(q, '')), p['kind'],
                                                   esc(p['item']), esc(p['problem'])))
    else:
        w('None. The WP-1 hotfixes already replaced the Sword and Bow of Justice and the Infinity Egg '
          '(`tools/quests/patches/wp1_hotfixes.py`), and `qb.py check ids` blocklists them.')
    w('')
    qo = sorted(iid for iid, it in items.items() if it['status'] == 'quest-only')
    if qo:
        w('Items whose **only** source is a quest reward (fine as rewards, never as tasks): %s.'
          % ', '.join('`%s`' % x for x in qo))
        w('')

    # -- scripts ------------------------------------------------------------------------
    w('## Recipes the CraftTweaker scripts touch')
    w('')
    w('`pack/scripts/crazycraft_gating.zs` removes and re-adds these recipes, so none is left without one; the dump '
      'was taken with the scripts applied and shows the gated grids.')
    w('')
    for iid, what in out['scripts']:
        w('- `%s`: %s' % (iid, ' and '.join(what)))
    w('')

    # -- what to do -----------------------------------------------------------------------
    w('## What to do with this')
    w('')
    w('**A good quest ask is obtainable, visible and in tier.** Obtainable: status `ok` here, and ideally with a '
      '`recipe`, `chest-loot`, `worldgen-survey` or a description that names the mob or structure, so the item page '
      'tells the player how. Visible: it has a creative tab (no `no-tab`) and a real name (no `untranslated`), so it '
      'shows in NEI and the item browser; and it has an icon (`blank-icon` items render as a letter on the site and '
      'often as nothing in the quest book). In tier: the chapter order in `qb.py path` and the boss gates in '
      '`crazycraft_gating.zs` decide when a Twilight, OreSpawn or ProjectE item is reasonable to ask for.')
    w('')
    w('- **Never ask for** anything in (a): `no-source`, `disabled`, `creative`, `technical`, `hidden`, or '
      '`quest-only`. Never ask for an MCHeli aircraft until the server check in (d) is done.')
    w('- **Candidates for a recipe or a loot entry** (then a quest): the (a) `no-source` rows whose research line '
      'is empty or says "no recipe" rather than "creative" or "technical": finished items the pack simply never '
      'hands out. Fix at the source (a CraftTweaker recipe in `pack/scripts`, a Lucky Block or loot-bag whitelist '
      'line) rather than by inflating quest rewards; balance changes wait for approval.')
    w('- **Candidates for a quest** (a reason to exist): the (b) rows with a real source and no use: trophies, '
      'props, coins, decorative items. A collection quest or a "show it" icon gives them a role without a recipe.')
    w('- **Candidates for removal or hiding**: the (a) `technical` and `hidden` families (placeholder block slots, '
      'crop stages, lit or burning variants, spawner blocks). They clutter NEI and the texture queue; the texture '
      'ranking can treat every id with a status other than `ok` as its tail.')
    w('- **Items whose only recipe is unreadable** (c): the quest text must explain the craft, since the item page '
      'cannot show it.')
    w('- **Rewards**: anything in (e) must go; `qb.py check ids` already blocks the three known cases. Items that '
      'are `quest-only` are fine to hand out but never to ask for.')
    w('')
    w('To re-run: `py -3.10 -I tools/items/dead_items.py` after any change to the dump, the descriptions, the quest '
      'book or the loot configs; commit both outputs.')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()

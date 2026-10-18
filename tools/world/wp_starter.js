// WorldPainter script (wpscript.exe, WorldPainter 2.27.1): build the empty starter world the author
// paints the decision-0003 continent into.
//   wpscript.exe tools/world/wp_starter.js <flat.png> <docs/survey/biome-ids.tsv> <out .world> [canvasHalf] [borderTiles]
// flat.png is a uniform 8-bit image (value = seafloor height) as wide as the canvas.
// Defaults: a 20,480-block canvas (+-10,240) inside a 16-tile (2,048-block) water border, so the
// export is 24,576 blocks edge to edge (docs/design/world/sizing.md: the most a 16 GB Mac can paint).
// Every BoP, RWG and Welcome to the Jungle biome is declared as a custom biome with its pinned ID,
// so the GUI's biome brush offers them by name. Populate is on and WorldPainter's own ores are off:
// the game decorates painted chunks (docs/design/world/poc.md).
var flat = arguments[0], tsv = arguments[1], out = arguments[2];
var half = arguments.length > 3 ? parseInt(arguments[3]) : 10240;
var border = arguments.length > 4 ? parseInt(arguments[4]) : 16;
var platform = wp.getMapFormat().withId("org.pepsoft.anvil").go();   // "Minecraft 1.2 - 1.12"

var hm = wp.getHeightMap().fromFile(flat).go();
var world = wp.createWorld().fromHeightMap(hm)
    .fromLevels(0, 255).toLevels(0, 255)
    .shift(-half, -half)
    .withWaterLevel(62)
    .withMapFormat(platform)
    .go();
world.setName("qf-continent");
var dim = world.getDimension(0);
dim.setPopulate(true);
dim.setBorder(Packages.org.pepsoft.worldpainter.Dimension.Border.WATER);
dim.setBorderLevel(62);
dim.setBorderSize(border);   // in tiles of 128 blocks

// Same fix as wp_build_island.js: a scripted world keeps modern ore settings and dies on export.
var res = Packages.org.pepsoft.worldpainter.layers.Resources.INSTANCE;
dim.clearLayerData(res);
var rs = dim.getLayerSettings(res);
if (rs != null) {
    rs.setPlatform(platform);
    rs.setMinimumLevel(0);
    var it = rs.getMaterials().iterator();
    while (it.hasNext()) rs.setChance(it.next(), 0);
}

// Map colour by name so the biome map reads at a glance; anything unmatched gets WorldPainter's pick.
var palette = [
    [/snow|frost|glacier|polar|arctic|ice|alps|tundra|frozen/i, 0xE8F0F8],
    [/redwood|sequoia/i, 0x7A2E1E],
    [/desert|dune|mesa|badland|canyon|outback|savanna|steppe|xeric|arid|wasteland|volcan/i, 0xD9B56A],
    [/swamp|bog|fen|marsh|moor|bayou|wetland|sludge|mangrove/i, 0x4A5E3A],
    [/jungle|tropic|rainforest|bamboo|rain forest/i, 0x2E8B2E],
    [/ocean|sea|coral|kelp|reef|lagoon|beach|shore|oasis|lake|river/i, 0x3A6FC2],
    [/mountain|peak|crag|cliff|hill|highland|ridge|plateau/i, 0x8C8C8C],
    [/taiga|pine|conifer|boreal|spruce|fir/i, 0x2F5D4A],
    [/forest|wood|grove|thicket|orchard|maple|birch|cherry|seasonal/i, 0x3F7F2F],
    [/plain|prairie|meadow|field|grass|heath|shrub|lavender|flower/i, 0x8DB360]
];
function colourFor(name, id) {
    for (var i = 0; i < palette.length; i++) if (palette[i][0].test(name)) return palette[i][1];
    return Packages.org.pepsoft.worldpainter.biomeschemes.CustomBiome.pickColour(id);
}
var prefix = { "Biomes O' Plenty": "BoP", "Realistic World Gen": "RWG", "Welcome to the Jungle": "Jungle" };
var list = new java.util.ArrayList();
var lines = java.nio.file.Files.readAllLines(java.nio.file.Paths.get(tsv));
for (var i = 0; i < lines.size(); i++) {
    var line = String(lines.get(i));
    if (line.charAt(0) == "#" || line.indexOf("id\t") == 0) continue;
    var f = line.split("\t");
    var p = prefix[f[2]];
    if (!p) continue;
    var id = parseInt(f[0]);
    list.add(new Packages.org.pepsoft.worldpainter.biomeschemes.CustomBiome(p + ": " + f[1], id, colourFor(f[1], id)));
}
dim.setCustomBiomes(list);

wp.saveWorld(world).toFile(out).go();
print("saved " + out + ": " + dim.getTileCount() + " tiles, border " + border + " tiles, "
      + list.size() + " custom biomes");

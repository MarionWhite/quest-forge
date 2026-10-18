// Shared setup for the decision-0003 WorldPainter scripts. Load with load(".../wp_common.js").

var QF_PLATFORM = wp.getMapFormat().withId("org.pepsoft.anvil").go();   // "Minecraft 1.2 - 1.12"

// Populate on and WorldPainter's own ores off: the game decorates painted chunks
// (docs/design/world/poc.md). A scripted world also keeps Resources settings made for a modern
// platform, and export then dies on "Cannot store modern material copper_ore ... in pre-1.13
// Anvil chunk"; the GUI does not hit this.
function qfSetupDimension(dim) {
    dim.setPopulate(true);
    var res = Packages.org.pepsoft.worldpainter.layers.Resources.INSTANCE;
    dim.clearLayerData(res);
    var rs = dim.getLayerSettings(res);
    if (rs != null) {
        rs.setPlatform(QF_PLATFORM);
        rs.setMinimumLevel(0);
        var it = rs.getMaterials().iterator();
        while (it.hasNext()) rs.setChance(it.next(), 0);
    }
}

// Declare every BoP, RWG and Welcome to the Jungle biome as a custom biome with its pinned ID,
// so the GUI's biome brush offers them by name. Colours by name, so the biome view reads at a glance.
var QF_PALETTE = [
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
var QF_PREFIX = { "Biomes O' Plenty": "BoP", "Realistic World Gen": "RWG", "Welcome to the Jungle": "Jungle" };

function qfDeclareBiomes(dim, tsv) {
    var CustomBiome = Packages.org.pepsoft.worldpainter.biomeschemes.CustomBiome;
    var list = new java.util.ArrayList();
    var lines = java.nio.file.Files.readAllLines(java.nio.file.Paths.get(tsv));
    for (var i = 0; i < lines.size(); i++) {
        var line = String(lines.get(i));
        if (line.charAt(0) == "#" || line.indexOf("id\t") == 0) continue;
        var f = line.split("\t");
        var p = QF_PREFIX[f[2]];
        if (!p) continue;
        var id = parseInt(f[0]), colour = CustomBiome.pickColour(id);
        for (var k = 0; k < QF_PALETTE.length; k++)
            if (QF_PALETTE[k][0].test(f[1])) { colour = QF_PALETTE[k][1]; break; }
        list.add(new CustomBiome(p + ": " + f[1], id, colour));
    }
    dim.setCustomBiomes(list);
    return list.size();
}

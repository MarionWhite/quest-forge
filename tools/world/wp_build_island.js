// WorldPainter script (wpscript.exe, WorldPainter 2.27.1): build the decision-0003 test
// island from make_test_island.py's PNGs and export it for Minecraft 1.2-1.12 (Anvil).
//   wpscript.exe tools/world/wp_build_island.js <dir with height.png biome.png> <export parent dir> [half]
// The world lands in <export parent dir>/qf-poc-island; the .world file next to it opens in the GUI.
// The biome map's pixel values are written straight into the Biomes layer, so any ID 0-254
// works -- modded IDs included; the GUI needs them declared under Edit > Custom Biomes.
// "Allow Minecraft to populate" is switched on, so every chunk is exported with
// TerrainPopulated=0 and the game decorates it on first load.
var dir = arguments[0], out = arguments[1];
var half = arguments.length > 2 ? parseInt(arguments[2]) : 1280;
var platform = wp.getMapFormat().withId("org.pepsoft.anvil").go();   // "Minecraft 1.2 - 1.12"

var height = wp.getHeightMap().fromFile(dir + "/height.png").go();
var world = wp.createWorld().fromHeightMap(height)
    .fromLevels(0, 255).toLevels(0, 255)
    .shift(-half, -half)
    .withWaterLevel(62)
    .withMapFormat(platform)
    .go();
world.setName("qf-poc-island");

var biomes = wp.getHeightMap().fromFile(dir + "/biome.png").go();
var biomeLayer = wp.getLayer().withName("Biomes").go();
wp.applyHeightMap(biomes).toWorld(world).shift(-half, -half)
    .applyToLayer(biomeLayer).fromLevels(0, 255).toLevels(0, 255).go();

var dim = world.getDimension(0);
dim.setPopulate(true);
// No WorldPainter ores: the game's own population must place them (that is what is being
// tested). A scripted createWorld() also keeps Resources settings made for a modern
// platform, and the export then dies on "Cannot store modern material copper_ore ... in
// pre-1.13 Anvil chunk" -- the GUI does not hit this.
var res = Packages.org.pepsoft.worldpainter.layers.Resources.INSTANCE;
dim.clearLayerData(res);
var rs = dim.getLayerSettings(res);
if (rs != null) {
    rs.setPlatform(platform);
    rs.setMinimumLevel(0);
    var it = rs.getMaterials().iterator();
    while (it.hasNext()) rs.setChance(it.next(), 0);
}
print("platform " + world.getPlatform() + ", populate " + dim.isPopulate()
      + ", tiles " + dim.getTileCount());
wp.saveWorld(world).toFile(out + "/qf-poc-island.world").go();
wp.exportWorld(world).toDirectory(out).go();
print("exported to " + out);

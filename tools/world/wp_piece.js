// WorldPainter script (wpscript.exe, WorldPainter 2.27.1): turn one piece from
// `plan.py expand` into a .world file the author refines by hand, and optionally export it.
//   wpscript.exe tools/world/wp_piece.js <piece dir> <docs/survey/biome-ids.tsv> <out .world> [export dir]
// The piece dir holds height.png (16-bit, y * 257), biome.png (8-bit biome IDs) and origin.txt.
// Pieces have no WorldPainter border: the sea ring is part of the plan, and
// tools/world/stitch.py joins the exported pieces into one world.
load(new java.io.File(scriptDir, "wp_common.js").getPath());   // wpscript defines scriptDir, not __DIR__
var dir = arguments[0], tsv = arguments[1], out = arguments[2];
var exportDir = arguments.length > 3 ? arguments[3] : null;
var origin = String(java.nio.file.Files.readAllLines(java.nio.file.Paths.get(dir + "/origin.txt")).get(0)).trim().split(" ");
var x0 = parseInt(origin[0]), z0 = parseInt(origin[1]);

var height = wp.getHeightMap().fromFile(dir + "/height.png").go();
var world = wp.createWorld().fromHeightMap(height)
    .fromLevels(0, 65535).toLevels(0, 255)
    .shift(x0, z0)
    .withWaterLevel(62)
    .withMapFormat(QF_PLATFORM)
    .go();
height = null;
var name = new java.io.File(out).getName().replace(/\.world$/, "");
world.setName(name);
var dim = world.getDimension(0);
qfSetupDimension(dim);
var nb = qfDeclareBiomes(dim, tsv);

var biomes = wp.getHeightMap().fromFile(dir + "/biome.png").go();
var biomeLayer = wp.getLayer().withName("Biomes").go();
wp.applyHeightMap(biomes).toWorld(world).shift(x0, z0)
    .applyToLayer(biomeLayer).fromLevels(0, 255).toLevels(0, 255).go();
biomes = null;

wp.saveWorld(world).toFile(out).go();
print("saved " + out + ": origin " + x0 + "," + z0 + ", " + dim.getTileCount() + " tiles, " + nb + " custom biomes");
if (exportDir != null) {
    wp.exportWorld(world).toDirectory(exportDir).go();
    print("exported to " + exportDir + "/" + name);
}

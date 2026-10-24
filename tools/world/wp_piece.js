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

// Lakes and rivers above sea level: water.png holds each block's water level (0 = the world's
// 62). water_tiles.json lists the 512-block tiles holding any (older pieces: lakes.json bounds).
var tilesFile = new java.io.File(dir, "water_tiles.json");
var lakesFile = new java.io.File(dir, "lakes.json");
var raised = 0;
if (tilesFile.exists()) {
    var tiles = JSON.parse(String(new java.lang.String(java.nio.file.Files.readAllBytes(tilesFile.toPath()), "UTF-8")));
    var wimg = javax.imageio.ImageIO.read(new java.io.File(dir, "water.png")).getRaster();
    for (var i = 0; i < tiles.length; i++) {
        var tx = tiles[i][0], tz = tiles[i][1];
        for (var pz = tz; pz < tz + 512; pz++)
            for (var px = tx; px < tx + 512; px++) {
                var lvl = wimg.getSample(px, pz, 0);
                if (lvl > 0) { dim.setWaterLevelAt(x0 + px, z0 + pz, lvl); raised++; }
            }
    }
} else if (lakesFile.exists()) {
    var lakes = JSON.parse(String(new java.lang.String(java.nio.file.Files.readAllBytes(lakesFile.toPath()), "UTF-8")));
    var wimg = javax.imageio.ImageIO.read(new java.io.File(dir, "water.png")).getRaster();
    var size = wimg.getWidth();
    for (var i = 0; i < lakes.length; i++) {
        var L = lakes[i];
        var ax = Math.max(0, Math.floor(L.x - L.r - x0)), bx = Math.min(size - 1, Math.ceil(L.x + L.r - x0));
        var az = Math.max(0, Math.floor(L.z - L.r - z0)), bz = Math.min(size - 1, Math.ceil(L.z + L.r - z0));
        for (var pz = az; pz <= bz; pz++)
            for (var px = ax; px <= bx; px++) {
                var lvl = wimg.getSample(px, pz, 0);
                if (lvl > 0) { dim.setWaterLevelAt(x0 + px, z0 + pz, lvl); raised++; }
            }
    }
}
print("raised water blocks: " + raised);

wp.saveWorld(world).toFile(out).go();
print("saved " + out + ": origin " + x0 + "," + z0 + ", " + dim.getTileCount() + " tiles, " + nb + " custom biomes");
if (exportDir != null) {
    wp.exportWorld(world).toDirectory(exportDir).go();
    print("exported to " + exportDir + "/" + name);
}

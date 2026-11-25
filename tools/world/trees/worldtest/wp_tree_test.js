// WorldPainter script (WorldPainter 2.27.1): a flat tree-test world with one Custom Objects
// layer per plot, exported in the "Minecraft 1.2 - 1.12" (Anvil) format.
//   java -Xmx2g -cp "<WorldPainter>/lib/*" org.pepsoft.worldpainter.tools.ScriptingTool \
//        wp_tree_test.js <plan dir> <export parent dir>
// (wpscript.exe works too, but its vmoptions ask for an 8 GB heap.)
// The plan dir holds height.png (8-bit, flat), biome.png (8-bit biome IDs) and plan.json from
// build_test_world.py: for each plot its schematic files, painted rectangle, grid spacing and
// rotation mode.
var dir = arguments[0], out = arguments[1];
var plan = JSON.parse(String(new java.lang.String(java.nio.file.Files.readAllBytes(
    java.nio.file.Paths.get(dir, "plan.json")), "UTF-8")));
var platform = wp.getMapFormat().withId("org.pepsoft.anvil").go();     // Minecraft 1.2 - 1.12

var height = wp.getHeightMap().fromFile(dir + "/height.png").go();
var world = wp.createWorld().fromHeightMap(height).fromLevels(0, 255).toLevels(0, 255)
    .withWaterLevel(40).withMapFormat(platform).go();
world.setName(plan.name);
var dim = world.getDimension(0);
dim.setPopulate(false);                 // only our objects: no vanilla trees or grass on top
var res = Packages.org.pepsoft.worldpainter.layers.Resources.INSTANCE;  // see wp_common.js
dim.clearLayerData(res);
var rs = dim.getLayerSettings(res);
if (rs != null) {
    rs.setPlatform(platform); rs.setMinimumLevel(0);
    var it = rs.getMaterials().iterator();
    while (it.hasNext()) rs.setChance(it.next(), 0);
}
var biomes = wp.getHeightMap().fromFile(dir + "/biome.png").go();
var biomeLayer = wp.getLayer().withName("Biomes").go();
wp.applyHeightMap(biomes).toWorld(world).applyToLayer(biomeLayer)
    .fromLevels(0, 255).toLevels(0, 255).go();

var WPObject = Packages.org.pepsoft.worldpainter.objects.WPObject;
var Tube = Packages.org.pepsoft.worldpainter.layers.bo2.Bo2ObjectTube;
var Bo2Layer = Packages.org.pepsoft.worldpainter.layers.Bo2Layer;
var layers = new java.util.ArrayList();
for (var i = 0; i < plan.plots.length; i++) {
    var p = plan.plots[i];
    var files = new java.util.ArrayList();
    for (var k = 0; k < p.files.length; k++) files.add(new java.io.File(p.files[k]));
    var tube = Tube.load(p.name, files);
    var objs = tube.getAllObjects();
    for (var k = 0; k < objs.size(); k++) {
        var o = objs.get(k);
        // rotation: "both" = WorldPainter's default random rotation + mirroring,
        // "rotate" = rotation only, "none" = as authored
        o.setAttribute(WPObject.ATTRIBUTE_RANDOM_ROTATION, p.rotation == "both");
        o.setAttribute(WPObject.ATTRIBUTE_RANDOM_ROTATION_ONLY, p.rotation == "rotate");
        o.setAttribute(WPObject.ATTRIBUTE_RANDOM_MIRRORING_ONLY, false);
        o.setAttribute(WPObject.ATTRIBUTE_COLLISION_MODE, java.lang.Integer.valueOf(p.collision));
        if (k == 0) print(p.name + ": " + objs.size() + " objects, first offset " + o.getOffset()
                          + " dims " + o.getDimensions());
    }
    var layer = new Bo2Layer(tube, "tree test " + p.name, new java.awt.Color(0x30A030 + i * 0x101010));
    layer.setName(p.name);
    layer.setDensity(1);                // 1 + value^2 >= 64 * density: every grid point gets an object
    layer.setGridX(p.grid); layer.setGridY(p.grid);
    layer.setRandomDisplacement(0);     // exact grid points, so the checker knows where each tree stands
    layers.add(layer);
    var r = p.rect;                     // [x0, z0, x1, z1) painted at full intensity
    for (var z = r[1]; z < r[3]; z++)
        for (var x = r[0]; x < r[2]; x++)
            dim.setLayerValueAt(layer, x, z, 15);
}
dim.setCustomLayers(layers);
wp.saveWorld(world).toFile(out + "/" + plan.name + ".world").go();
wp.exportWorld(world).toDirectory(out).go();
print("exported " + out + "/" + plan.name + ", tiles " + dim.getTileCount());

"""Build a ~1024 x 1024 flat WorldPainter test world with one Custom Objects plot per tree species
(plus one downloaded pack), export it for Minecraft 1.2-1.12, ready for check_test_world.py.

  py -3.10 build_test_world.py --wp <WorldPainter dir> [--out C:\qf-world\trees\test]
        [--trees C:\qf-world\trees\generated] [--pack DIR] [--pack-count 40] [--java java.exe]

Writes <out>/plan/{height.png, biome.png, plan.json}, <out>/world/qf-tree-test.world and the
exported map <out>/world/qf-tree-test/. The WorldPainter run is capped at a 2 GB heap.
"""
import argparse, glob, json, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from schematic import read_schematic    # noqa: E402

SIZE, PLOT, GAP, GROUND = 1024, 320, 16, 64
# plot -> vanilla biome ID (colours the grass and leaves the way that biome would in game)
BIOME = {'redwood': 32, 'mangrove': 6, 'baobab': 35, 'ice': 12, 'eucalyptus': 4, 'petrified': 2,
         'autumn': 4, 'cherry': 27, 'pack': 4}
SPECIES = ['redwood', 'mangrove', 'baobab', 'ice', 'eucalyptus', 'petrified', 'autumn', 'cherry']
JDK = r'C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin\java.exe'


def footprint(files):
    m = 0
    for f in files:
        ids, _ = read_schematic(f)
        m = max(m, ids.shape[1], ids.shape[2])
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wp', required=True, help='WorldPainter install dir (holds lib/WPGUI.jar)')
    ap.add_argument('--out', default=r'C:\qf-world\trees\test')
    ap.add_argument('--trees', default=r'C:\qf-world\trees\generated')
    ap.add_argument('--pack', default=r'C:\qf-world\trees\h2co3-1k-treepack\trees-1.7.10')
    ap.add_argument('--pack-count', type=int, default=40)
    ap.add_argument('--java', default=JDK)
    ap.add_argument('--rotation', default='both', choices=['both', 'rotate', 'none'])
    a = ap.parse_args()
    plan_dir = os.path.join(a.out, 'plan'); world_dir = os.path.join(a.out, 'world')
    os.makedirs(plan_dir, exist_ok=True); os.makedirs(world_dir, exist_ok=True)

    sets = [(s, sorted(glob.glob(os.path.join(a.trees, s, '*.schematic')))) for s in SPECIES]
    sets.append(('pack', sorted(glob.glob(os.path.join(a.pack, '*.schematic')))[:a.pack_count]))
    biome = np.ones((SIZE, SIZE), np.uint8)                      # plains
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    rng = np.random.default_rng(3)
    for _ in range(6):                                          # a few forest / meadow patches between plots
        cx, cz, r = rng.integers(0, SIZE), rng.integers(0, SIZE), rng.integers(40, 110)
        biome[(xx - cx) ** 2 + (yy - cz) ** 2 < r * r] = rng.choice([4, 132, 27])
    plots = []
    for k, (name, files) in enumerate(sets):
        if not files:
            sys.exit(f'no schematics for {name}')
        col, row = k % 3, k // 3
        x0, z0 = GAP + col * (PLOT + GAP), GAP + row * (PLOT + GAP)
        fp = footprint(files)
        grid = fp + 3
        m = fp // 2 + 2
        rect = [x0 + m, z0 + m, x0 + PLOT - m, z0 + PLOT - m]
        biome[z0:z0 + PLOT, x0:x0 + PLOT] = BIOME[name]
        plots.append(dict(name=name, files=files, grid=grid, rect=rect, plot=[x0, z0, x0 + PLOT, z0 + PLOT],
                          rotation=a.rotation, collision=2, biome=BIOME[name], footprint=fp))
        print(f'{name:11s} {len(files):3d} objects  footprint {fp:3d}  grid {grid}  rect {rect}')
    Image.fromarray(np.full((SIZE, SIZE), GROUND, np.uint8)).save(os.path.join(plan_dir, 'height.png'))
    Image.fromarray(biome).save(os.path.join(plan_dir, 'biome.png'))
    plan = dict(name='qf-tree-test', ground=GROUND, plots=plots)
    with open(os.path.join(plan_dir, 'plan.json'), 'w') as f:
        json.dump(plan, f, indent=1)
    cmd = [a.java, '-Xmx2g', '-cp', os.path.join(a.wp, 'lib', '*'), 'org.pepsoft.worldpainter.tools.ScriptingTool',
           os.path.join(HERE, 'wp_tree_test.js'), plan_dir, world_dir]
    print(' '.join(cmd))
    sys.exit(subprocess.call(cmd))


if __name__ == '__main__':
    main()

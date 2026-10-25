"""Web-sized copies of the pack's art for the homepage (site/home/img/), and the site icon.

    py -3.10 -I tools/site/make_home_images.py

The sources are committed already: the main-menu backgrounds the resourcepack
ships, the loading-screen plates in tools/branding/loading-plates/finish/, the
pack icon, and the shader renders the Shader Lab published in its latest round.
Re-run after any of them changes. The output is committed like the rest of
site/, because GitHub Pages serves the folder as it is.

site/home/ is the site root, so favicon.png is /favicon.png and img/ is /img/;
every other page refers to them as ../favicon.png and ../img/.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MENU = os.path.join(REPO, 'pack', 'resourcepack', 'assets', 'custommenu')
PLATES = os.path.join(REPO, 'tools', 'branding', 'loading-plates', 'finish', '1280')
ICON = os.path.join(REPO, 'pack', 'resourcepack', 'pack.png')
ROUNDS = os.path.join(REPO, 'site', 'shaders', 'rounds')
OUT = os.path.join(REPO, 'site', 'home')

# The homepage's "Light and air" stills: our own renders, never a reference photo.
# (round, option image) -> name under img/shaders/. Update the round when a newer
# one shows the same scenes better.
STILLS = {
    'water-sunset': ('r006', 'water-sunset-A.jpg'),
    'forest-light': ('r006', 'forest-light-B.jpg'),
    'golden': ('r006', 'golden-A.jpg'),
    'lake-sunset': ('r006', 'lake-sunset-A.jpg'),
}


def save(img, path, width, quality):
    img = img.convert('RGB')
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    img.save(path, quality=quality, optimize=True, progressive=True)
    return os.path.getsize(path)


def icon(size, path):
    img = Image.open(ICON).convert('RGBA').resize((size, size), Image.LANCZOS)
    img.save(path, optimize=True)
    return os.path.getsize(path)


def main():
    img = os.path.join(OUT, 'img')
    os.makedirs(os.path.join(img, 'plates'), exist_ok=True)
    os.makedirs(os.path.join(img, 'shaders'), exist_ok=True)
    total = 0
    hero = Image.open(os.path.join(MENU, 'background-wordmark.jpg'))
    total += save(hero, os.path.join(img, 'hero.jpg'), 1920, 84)
    total += save(hero, os.path.join(img, 'hero-960.jpg'), 960, 82)
    for f in sorted(os.listdir(PLATES)):
        if f.endswith('.png'):
            total += save(Image.open(os.path.join(PLATES, f)),
                          os.path.join(img, 'plates', f[:-4] + '.jpg'), 720, 80)
    for name, (rnd, src) in STILLS.items():
        total += save(Image.open(os.path.join(ROUNDS, rnd, src)),
                      os.path.join(img, 'shaders', name + '.jpg'), 1280, 80)
    total += icon(64, os.path.join(OUT, 'favicon.png'))
    total += icon(180, os.path.join(OUT, 'apple-touch-icon.png'))
    print('wrote %s (%.1f MB)' % (OUT, total / 1e6))


if __name__ == '__main__':
    main()

"""Web-sized copies of the pack's art for the homepage (site/home/img/).

    py -3.10 -I tools/site/make_home_images.py

The sources are committed already: the main-menu backgrounds the resourcepack
ships, and the loading-screen plates in tools/branding/loading-plates/finish/.
Re-run after either changes. The output is committed like the rest of site/,
because GitHub Pages serves the folder as it is.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MENU = os.path.join(REPO, 'pack', 'resourcepack', 'assets', 'custommenu')
PLATES = os.path.join(REPO, 'tools', 'branding', 'loading-plates', 'finish', '1280')
OUT = os.path.join(REPO, 'site', 'home', 'img')


def save(img, path, width, quality):
    img = img.convert('RGB')
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    img.save(path, quality=quality, optimize=True, progressive=True)
    return os.path.getsize(path)


def main():
    os.makedirs(os.path.join(OUT, 'plates'), exist_ok=True)
    total = 0
    hero = Image.open(os.path.join(MENU, 'background-wordmark.jpg'))
    total += save(hero, os.path.join(OUT, 'hero.jpg'), 1920, 84)
    total += save(hero, os.path.join(OUT, 'hero-960.jpg'), 960, 82)
    for f in sorted(os.listdir(PLATES)):
        if f.endswith('.png'):
            total += save(Image.open(os.path.join(PLATES, f)),
                          os.path.join(OUT, 'plates', f[:-4] + '.jpg'), 720, 80)
    print('wrote %s (%.1f MB)' % (OUT, total / 1e6))


if __name__ == '__main__':
    main()

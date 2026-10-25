# Player cards and First Kills (player_cards.py)

`player_cards.py` builds `site/players/data/players.json` for the Players page from a
play server's folder. Python 3, standard library only.

    py -3.10 -I tools/server/player_cards.py --server <server folder> --world world --out site/players/data/players.json
    py -3.10 -I tools/server/player_cards.py --server <server folder> --demo     # print only

Read the docstring at the top of the script for the input files, the output shape and
which parts are confirmed against real data. In short: the QuestProgress shape and the
boss list are confirmed; the completed-entry shape, the playerdata location of the Level
Up class and the level are not, until a real save is read.

To put the page on the live feed, set `feed` in `site/players/config.json` to a URL that
serves the same JSON. The page then fetches that URL with `cache: "no-store"`.

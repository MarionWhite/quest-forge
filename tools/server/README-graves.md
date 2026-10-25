# The Wall of Graves: the feed from the server log

`graves_from_log.py` reads the server's death messages and writes `graves.json`. The page at
`site/graves/` reads that file. Stdlib only, Python 3.10 or newer.

## Run it

Run it on the server host, from the server folder, in isolated mode:

    python3 -I tools/server/graves_from_log.py --out site/graves/data/graves.json \
        --usercache usercache.json logs/latest.log logs/*.log.gz

On Windows: `py -3.10 -I tools\server\graves_from_log.py --out ... logs\latest.log`.

It is safe to run again and again. Each death is keyed by (time, player, message), so a line
already in the JSON is not added twice, and a rotated copy of a log that was already read adds
nothing.

To look at what it would add, without writing:

    python3 -I tools/server/graves_from_log.py --demo logs/latest.log

That prints one line per death: the UTC time, the cause category, the source file and the
original message. Use it to check the parser on a real log before the first write.

Options:

- `--out PATH` the JSON to read and update. Required unless `--demo`.
- `--usercache PATH` the server's `usercache.json`. Maps names to uuids, and marks a killer who is
  a known player as cause `player`.
- `--date YYYY-MM-DD` the date for a file whose name carries no date.
- `--demo` print the parsed lines and write nothing.

## How the date is found

The log lines carry only a time (`[20:14:33]`), so the date comes from, in order:

1. a `YYYY-MM-DD` in the file name. Vanilla rotates to `2026-10-24-1.log.gz`, so rotated logs
   are dated correctly with no flag.
2. `--date`, for a file that has no date in its name.
3. the file's modification time. This is right for `latest.log` if the server is read the same day.

Inside one file, a time that goes backwards means midnight has passed, and the date moves on by a
day. Times in the log are the host's local time. They are written as UTC (`...Z`).

## What it reads

Only lines from the `Server thread/INFO` thread whose text starts with a player name and then a
vanilla 1.7.10 death message. The templates are the `death.attack.*` keys of
`assets/minecraft/lang/en_US.lang` in the 1.7.10 server jar (33 keys, copied from that file). Chat
lines (`<name> ...`), WARN lines, `[Rcon]` lines and lines like `Name: slain by ...` are skipped.

Each death gets:

- `killer`: the name the template gives (`slain by X`, `shot by X`, `blown up by X`), or null.
- `cause`: `mob`, `player` (the killer is a known player name), `explosion`, `lava`, `drown`,
  `fall` or `other`. The default comes from the template.

Not written, because the vanilla death line has none of it: `dimension` and `pos` are always null.
The page then shows "position not logged". To fill them, a server-side mod or plugin has to log
the death with its coordinates; the feed's fields are already there for it.

## Publish the feed to the page

The page reads `site/graves/data/graves.json` from the repository while `site/graves/config.json`
has an empty `feed`. The site is static, so the server cannot push into it. Two ways to get the
server's copy in front of visitors:

1. Commit the file to the repository and let the site publish it. This is the simplest, but it
   needs a commit each time.
2. Put the file on a host that sends CORS headers, and set `feed` in `site/graves/config.json`
   to its URL. The page fetches it with `cache: "no-store"` on every visit.

A GitHub Gist works for option 2. Create it once, then update it after each run:

    gh gist create --public -f graves.json site/graves/data/graves.json     # once, prints the id
    gh gist edit <id> -f graves.json site/graves/data/graves.json            # after each run

The raw URL is `https://gist.githubusercontent.com/<user>/<id>/raw/graves.json`. Before relying on
it, check that the response carries `Access-Control-Allow-Origin` (`curl -sI <url>`). This was not
checked here.

## Run it on a schedule

Run the command above every few minutes from a scheduled task, or from the supervisor if it has a
hook for periodic jobs (`tools/server/supervisor.py` was not read for this section and is not
changed by it). Then publish the file as in option 1 or 2.

## Tests

Run on a fake log, not the friends' server. The log had 17 death lines in it, covering the
templates for mob, shot, pummeled, explosion, lava, drowning, falling, fire, starving, wither,
magic, suffocation and falling out of the world, plus a player killed by a player. Each of these
was parsed under the right category. Four lines were skipped, as they should be: a chat line
shaped like a death, a WARN line, an `[Rcon]` line and a `Name: slain by` line. A second run over
the same log added 0 entries. A rotated copy of the same lines, dated from its name, added 0 entries.
The date rollover past midnight was checked.

# "Why was I refused?"

The Quest Forge server checks every player's pack when they join. Mod configs
decide which number means which potion, enchantment, biome or dimension, and
Minecraft never compares them. If yours differ from the server's, you join
fine and then drink the wrong potions and break the world for everyone. So
the server disconnects you instead, and the screen says why.

The game shows its pack version in the top-right corner of the main menu and
on the F3 screen. It reads like `Quest Forge pack 2026-10-17 - 3f7f089e6508`:
the release date, then a fingerprint of the configs that matter.

| The screen says | What to do |
|---|---|
| **Your Quest Forge client is out of date.** | Install the current release from the link on the screen. Replace the whole instance, not single mods. |
| **This server runs an older Quest Forge pack than yours.** | You are ahead of the host. Tell them; they need to update the server. |
| **Your Quest Forge configs differ from the server's.** | Same release, but the files it names were edited or damaged. Reinstall the release's `config` folder, or undo your edits to those files. |
| **Your mods differ from the server's.** | A mod named on the screen has a different version from the server's. Reinstall the release, rather than updating that mod alone. |
| **The server could not check your Quest Forge pack.** | Your qf-content is too old to answer the check. Install the current release. |
| **Mod rejections [FMLMod:qfcontent{1.1.0+...}]** (or another mod) | The login handshake refused your copy of that mod before the pack check ran. The version shown is the server's. Install the current release. |

Changes you are free to make never get you refused: video settings, key
bindings, shaders, resource packs, sounds, the minimap, and any setting in a
"client-side" section of a config.

When asking the host for help, send `logs/latest.log` from your instance, not a
screenshot. The refusal text is in it (search for `packcheck`).

For hosts: [`hosting-a-server.md`](hosting-a-server.md), "The pack check".

# Building the mods on Windows

Four steps. Nothing in the repository needs editing.

`qf-content` needs only the first three. `transformers` needs the fourth as
well, because it compiles against four jars this repository does not
redistribute.

## 1. Install two JDKs

| | why | get it |
|---|---|---|
| **JDK 25** | RetroFuturaGradle 2.0.3 is compiled for Java 25, so *Gradle itself* runs on it | [Adoptium 25](https://adoptium.net/) or `winget install EclipseAdoptium.Temurin.25.JDK` |
| **JDK 8** | the mods compile to Java 8 bytecode, because the game runs on 8 | [Adoptium 8](https://adoptium.net/temurin/releases/?version=8) or `winget install EclipseAdoptium.Temurin.8.JDK` |

Any vendor's Java 8 works on Windows. Note the install paths — you need them next.

## 2. Write one file

`%USERPROFILE%\.gradle\gradle.properties` — create it if it doesn't exist:

```properties
org.gradle.java.home=C:/Program Files/Eclipse Adoptium/jdk-25.0.4.7-hotspot
org.gradle.java.installations.paths=C:/Program Files/Eclipse Adoptium/jdk-8.0.432.6-hotspot
qfJava8Vendor=any
```

Substitute your real paths. **Forward slashes**, even on Windows — Gradle reads
these as Java properties, where `\` is an escape character.

What each line does:

- `org.gradle.java.home` — the JVM Gradle runs on. Must be 25.
- `org.gradle.java.installations.paths` — where to find Java 8. The project
  turns auto-detection off, because the Mac has six Java 8 installs and needs
  disambiguating, so the path has to be given explicitly.
- `qfJava8Vendor=any` — drops the Azul vendor pin. That pin is a Mac
  workaround (Azul is the only vendor shipping Java 8 for macOS arm64) and it
  would otherwise reject your perfectly good Temurin 8.

Gradle reads this file **after** the project's `gradle.properties` and these
values win, so nothing here affects the Mac or gets committed.

## 3. Build

```powershell
cd mods\qf-content
.\gradlew build
```

The jar lands in `build\libs\QuestForgeContent-1.0.0.jar`. Copy it into the
instance's `mods\`, replacing what is there.

The first build decompiles Minecraft and takes a few minutes; later ones take
seconds.

## 4. For transformers only: stage the four compile-only jars

```powershell
cd ..\..
python tools\stage_transformers_libs.py --instance "<instance dir>"
cd mods\transformers
.\gradlew build
```

→ `build\libs\TransformersMod-0.6.3-qf1.jar`.

`mods\transformers\libs\` is empty in a fresh clone and the build fails on its
first import without this. The mod declares NEI, CodeChickenLib,
CodeChickenCore and Waila as `compileOnly`, deliberately using **the pack's own
jars** rather than the GTNH forks on maven — GTNH's NEI generified
`TemplateRecipeHandler`, so the mod's four recipe handlers do not compile
against it, and had they compiled they would have been built against signatures
the pack does not ship. Those four jars are other people's work, so they are not
committed; the script copies them out of a live instance instead.

It is worth a script rather than four `copy` commands because CodeChickenLib is
not beside the others — Prism keeps it in `mods\1.7.10\`, the version-scoped
subfolder, under a versioned filename that has to be renamed on the way in.

Re-run it any time those mods are updated. It is idempotent and reports
`unchanged` when there is nothing to do.

## Check it worked

```powershell
python tools\verify_pack.py --instance <instance dir> --repo .
```

Expect `0 failed`. It compares the installed jars against `build\libs`, so a jar
you built but forgot to copy shows up as a failure rather than as a confusing
bug in game.

It also reads each custom jar's own `sounds.json` and requires every sound it
declares to be present in the jar. That check exists because a `.gitignore`
rule written for generated music renders once excluded the Transformers mod's
shipped sound effects too: the jar built, loaded, ran, and was silently mute,
and the only symptom was a size 630 KB short of what it should have been. A
clean checkout is verified to build byte-identical jars now, but the check
stays, because that failure was invisible.

## When it doesn't work

**`No matching toolchains found for requested specification: {languageVersion=8, vendor=AZUL}`**
You missed `qfJava8Vendor=any`, or the file is not at
`%USERPROFILE%\.gradle\gradle.properties`.

**`No matching toolchains found ... {languageVersion=8, vendor=any}`**
Gradle cannot see your Java 8. Check the path in
`org.gradle.java.installations.paths` — it must be the JDK's root, the folder
containing `bin\java.exe`, not `bin` itself.

**`Unsupported class file major version` or a Gradle plugin crash on startup**
`org.gradle.java.home` is not pointing at a JDK 25.

**A path with a space fails.** Do not quote it; Gradle takes the whole line as
the value. `C:/Program Files/...` is fine unquoted.

**Build succeeds, game unchanged.** You built but didn't copy the jar. Run the
verifier — that is exactly what it catches.

**`package fiskfille.tf.nei does not exist`, or errors about `GuiRecipe`,
`ItemInfo`, `IWailaDataProvider`.** You skipped step 4. `mods\transformers\libs\`
is empty.

**`stage_transformers_libs.py` says AMBIGUOUS.** Your instance carries two
copies of that mod — usually a versioned and an unversioned one. Delete the
stale one; the script refuses to guess, because compiling against a jar the game
does not load produces a mod that builds and then crashes on a `NoSuchMethodError`.

**`'gradlew' is not recognized`.** You are in the repository root. `cd` into
`mods\qf-content` or `mods\transformers` first — each mod is its own Gradle
build.

## Debug tooling

`mods/qf-content` carries an unattended render-capture harness at
`com/questforge/content/debug/AutoShot.java`. Given `-Dqf.autoshot=<world>` it
loads that world, waits for the shader framebuffers and tile entity renderers to
settle, writes `screenshots/<name>.png`, and quits. It exists because a render
bug that only appears under one shader pack costs a person a launch, a look and a
description every time it is asked about, and a screenshot answers it exactly.

Options: `qf.autoshot.name`, `qf.autoshot.delay` (ticks, default 200),
`qf.autoshot.armor=<class substring>` to equip a chestplate, `qf.autoshot.unequip=1`
to strip one, `qf.autoshot.place=1` to drop a Tower Speaker in front of the player.
Armour is set on the integrated server, not just the client, or the next inventory
sync silently undoes it. It logs `CHEST SLOT:` at capture, because reading a
hotbar icon as worn armour once invalidated a whole verification run.

**It is not in release jars.** The `jar` task excludes the package, and
`ClientProxy` looks the class up by name, so its absence is the normal case:

```powershell
.\gradlew build                       # release -- no debug tooling
.\gradlew build -PqfDebugTools=true   # includes AutoShot
```

Build the release variant before deploying to the live pack, or `verify_pack.py`
will flag the size mismatch -- which is the check working, not a fault.

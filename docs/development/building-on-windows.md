# Building the mods on Windows

Three steps. Nothing in the repository needs editing.

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

Same for `mods\transformers` → `TransformersMod-0.6.3-qf1.jar`.

The first build decompiles Minecraft and takes several minutes; later ones are
quick.

## Check it worked

```powershell
python tools\verify_pack.py --instance <instance dir> --repo .
```

Expect `0 failed`. It compares the installed jars against `build\libs`, so a jar
you built but forgot to copy shows up as a failure rather than as a confusing
bug in game.

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

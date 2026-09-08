# Armour probe

Runs the **real** `net.minecraftforge.common.ISpecialArmor.ArmorProperties.ApplyArmor`
against real `ItemStack`s, from the deobfuscated Forge jar in `build/rfg`. Nothing
in here reimplements or transcribes the algorithm — it calls it.

Written because the simulation's armour numbers were disputed, and a transcription
is only as good as the person who read the source.

## Run it

```sh
cd ~/Desktop/QuestForge-Mods
./gradlew -q -I tools/armor-probe/dumpcp.gradle dumpProbeClasspath   # edit the output path first
J8=/Library/Java/JavaVirtualMachines/zulu-8.jdk/Contents/Home
CP=$(cat tools/armor-probe/cp.txt)
$J8/bin/javac -nowarn -cp "$CP" -d tools/armor-probe tools/armor-probe/*.java
$J8/bin/java -cp "$CP:tools/armor-probe" ArmorProbe
```

Java 8 is required: `EnumHelper.addArmorMaterial` uses `sun.reflect.ReflectionFactory`
internals that changed after 8. The game runs on 8 anyway.

## What it showed

Holding armour points fixed at 25 and changing only the durability factor, a single
175-damage hit lands for 163.84 at durability 5 and 0.00 at durability 300. Same
points, same reductions, same hit. The mechanism is the `AbsorbMax` cap in
`StandardizeList` — a piece absorbs at most `remaining_durability / 25` damage from
any one hit — and that bytecode is present in the pack's own
`forge-1.7.10-10.13.4.1558-1.7.10-universal.jar`.

The cap only binds when the hit is large relative to remaining durability. For a
fresh diamond chestplate it binds above about 66 raw damage, which is why it is
invisible in ordinary play and very visible against this pack's bosses.

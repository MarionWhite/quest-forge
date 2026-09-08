# 1.7.10 cookbook

Patterns for this workspace. **1.7.10 is not modern Forge** — almost every tutorial
you find online targets 1.12+ and will not compile here. Blocks are addressed by
`(world, x, y, z)` ints rather than `BlockPos`, there is no `IBlockState`, models
are `.png` textures stitched into an atlas rather than JSON models, and
registration is manual rather than via registry events.

Everything below is verified to compile against this workspace — see
`src/test/java/com/questforge/content/CookbookExamples.java`, which is compiled by
`./gradlew build` but never shipped in the jar.

## Items

```java
Item myItem = new Item()
        .setUnlocalizedName("my_item")                  // -> item.my_item.name in en_US.lang
        .setTextureName(MODID + ":my_item")             // -> textures/items/my_item.png
        .setCreativeTab(ModCreativeTab.INSTANCE)
        .setMaxStackSize(16);
GameRegistry.registerItem(myItem, "my_item");           // registry name: qfcontent:my_item
```

An item that does something when right-clicked needs a subclass:

```java
public class ItemSpark extends Item {
    @Override
    public ItemStack onItemRightClick(ItemStack stack, World world, EntityPlayer player) {
        if (!world.isRemote) {                          // server side only
            player.addChatMessage(new ChatComponentText("Spark!"));
            stack.stackSize--;
        }
        return stack;
    }
}
```

`world.isRemote` is `true` on the **client**. Gameplay effects belong in the
`!world.isRemote` branch, or they will desync.

## Blocks

`Block`'s constructor is protected, so every block needs a subclass — see
`BlockForge.java`. Behaviour goes in the subclass:

```java
public class BlockAltar extends Block {
    public BlockAltar() {
        super(Material.rock);
        setHardness(3.0F);
        setStepSound(Block.soundTypeStone);
        setHarvestLevel("pickaxe", 1);                  // 0 wood, 1 stone, 2 iron, 3 diamond
        setLightLevel(0.5F);                            // 0.0-1.0, not 0-15
    }

    @Override
    public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player,
                                    int side, float hitX, float hitY, float hitZ) {
        if (!world.isRemote) {
            player.addChatMessage(new ChatComponentText("Altar at " + x + "," + y + "," + z));
        }
        return true;                                    // true = consumed the click
    }
}
```

Registration, with the item form:

```java
GameRegistry.registerBlock(block, ItemBlock.class, "my_block");
```

Dropping something other than itself:

```java
@Override
public Item getItemDropped(int meta, Random random, int fortune) {
    return ModItems.forgeShard;
}

@Override
public int quantityDropped(Random random) {
    return 2 + random.nextInt(3);
}
```

A block with a different texture per face:

```java
setBlockTextureName(MODID + ":my_block");               // then provide
// textures/blocks/my_block.png                          (all faces), or override:
@Override
public IIcon getIcon(int side, int meta) {              // side 0=bottom 1=top 2-5=sides
    return side == 1 ? topIcon : sideIcon;
}

@Override
public void registerBlockIcons(IIconRegister reg) {
    topIcon  = reg.registerIcon(MODID + ":my_block_top");
    sideIcon = reg.registerIcon(MODID + ":my_block_side");
}
```

`registerBlockIcons` is client-only in spirit but is *not* annotated as such in a
way you must replicate — the base method is `@SideOnly(Side.CLIENT)`, so mark your
override the same way if you hit a server crash.

## Recipes

```java
// Shaped. Each string is a row; chars map to Item, Block or ItemStack.
GameRegistry.addRecipe(new ItemStack(result),
        "ABA",
        " C ",
        'A', Items.iron_ingot,
        'B', Blocks.stone,
        'C', ModItems.forgeShard);

// Shapeless
GameRegistry.addShapelessRecipe(new ItemStack(result, 2),
        Items.iron_ingot, Items.redstone);

// Smelting: input, output, experience
GameRegistry.addSmelting(ModBlocks.forgeBlock, new ItemStack(ModItems.forgeShard, 3), 0.7F);

// Ore-dictionary recipe: accepts any mod's copper ingot
GameRegistry.addRecipe(new ShapedOreRecipe(new ItemStack(result),
        "XX", "XX", 'X', "ingotCopper"));
```

Register your own items into the ore dictionary so other mods' recipes accept them:

```java
OreDictionary.registerOre("shardForge", ModItems.forgeShard);
```

**In a 113-mod pack, prefer ore dictionary recipes.** A shaped recipe on a literal
`Items.iron_ingot` will silently conflict with other mods far more often.

## Events

Two separate buses in 1.7.10, and putting a handler on the wrong one means it
never fires:

```java
MinecraftForge.EVENT_BUS.register(new MyHandler());        // world/entity/player events
FMLCommonHandler.instance().bus().register(new MyHandler()); // tick events, config changes
```

```java
public class MyHandler {
    @SubscribeEvent
    public void onBreak(BlockEvent.BreakEvent event) {
        if (event.block == ModBlocks.forgeBlock) {
            event.getPlayer().addChatMessage(new ChatComponentText("You broke it."));
        }
    }
}
```

Note `@SubscribeEvent` is `cpw.mods.fml.common.eventhandler.SubscribeEvent`, not
the `net.minecraftforge` one you would import in modern versions.

## Config

```java
@Mod.EventHandler
public void preInit(FMLPreInitializationEvent event) {
    Configuration cfg = new Configuration(event.getSuggestedConfigurationFile());
    cfg.load();
    boolean enableThing = cfg.getBoolean("enableThing", Configuration.CATEGORY_GENERAL,
                                         true, "Turn the thing on");
    int amount = cfg.getInt("amount", Configuration.CATEGORY_GENERAL, 3, 1, 64,
                            "How many");
    if (cfg.hasChanged()) cfg.save();
}
```

The file lands in the instance's `config/` folder, alongside every other mod's.

## Tile entities

```java
GameRegistry.registerTileEntity(TileAltar.class, MODID + "_altar");   // prefix the name
```

The registration name is global across all mods — always prefix it with your modid
or you will collide with another mod in a pack this size.

## Commands

```java
@Mod.EventHandler
public void serverStarting(FMLServerStartingEvent event) {
    event.registerServerCommand(new CommandBase() {
        @Override public String getCommandName() { return "qf"; }
        @Override public String getCommandUsage(ICommandSender s) { return "/qf"; }
        @Override public void processCommand(ICommandSender sender, String[] args) {
            sender.addChatMessage(new ChatComponentText("hello"));
        }
    });
}
```

## Talking to the pack's other mods

Two approaches, in order of preference:

1. **Ore dictionary + vanilla APIs.** No compile dependency, cannot break when the
   other mod updates. Covers most integration.
2. **Compile against the mod's jar.** Copy it into `libs/` and add
   `implementation(rfg.deobf(project.files("libs/TheMod.jar")))` to
   `build.gradle.kts`. Then guard every use with
   `@Optional.Method(modid = "theirmodid")` or a `Loader.isModLoaded("theirmodid")`
   check, and declare the relationship in `@Mod(dependencies = "after:theirmodid")`
   so load order is right.

Do not compile against a mod you have not declared a dependency on — it will work
on your machine and crash for anyone whose pack lacks it.

## Coremods (ASM)

Needed only when there is no Forge event for what you want to hook — a slot
click, for instance. See `ContainerTransformer`, `ReachTransformer` and
`QFLoadingPlugin`.

**Check whether Forge already opened it up before you write any of this.** Reach
looked like two bytecode patches: the client's targeting range and the server's
distance checks. It turned out Forge had already replaced the server's *block*
reach checks with `ItemInWorldManager.getBlockReachDistance()`, which has a public
setter — so that half became a one-line API call from the player tick
(`ReachUpkeep`) and only the entity check, still a raw `36.0D`, needed ASM. Read
the patched MCP sources before assuming a constant is hardcoded:

    unzip -p build/rfg/mcp_patched_minecraft-sources.jar \
      net/minecraft/network/NetHandlerPlayServer.java | less

**Verify transformers offline.** `./gradlew checkTransformers` runs every
transformer against the real classes and checks three things: that it matched
anything at all (a transformer that finds no target returns the input unchanged
and looks exactly like success), that ASM's analysis passes, and that the JVM
verifier accepts the result. That last one is the check that catches a missing
stackmap frame. This matters most for classes that only load once you are in a
world — `PlayerControllerMP` and `NetHandlerPlayServer` both do, so without it a
broken patch stays invisible until minutes into a manual test. See
`src/test/java/TransformerCheck.java`.

Five things that cost real time:

1. **Match methods by descriptor, not name.** In a dev workspace methods carry
   MCP names (`slotClick`); in a real instance they carry SRG names
   (`func_75144_a`). If a descriptor is unique within the class, matching on it
   works in both with nothing to keep in sync. Log the name you matched so you
   can confirm which environment you are in.

2. **Stackmap frames.** Any injection that adds a branch target needs a frame
   there, or the JVM throws
   `VerifyError: Expecting a stackmap frame at branch target N`.
   `ClassWriter.COMPUTE_MAXS` does not generate them. If the locals and stack at
   your label match method entry, insert `new FrameNode(Opcodes.F_SAME, 0, null,
   0, null)` immediately after the label. `COMPUTE_FRAMES` also works but must
   resolve common superclasses through the launch classloader, which needs a
   custom `ClassWriter` subclass to avoid `ClassNotFoundException`.

3. **The manifest attribute is `FMLCorePluginContainsFMLMod`** — note the `FML`
   in the middle. The obvious-looking `FMLCorePluginContainsMod` is silently
   ignored: FML loads the coremod and runs your transformer, then skips the jar
   during mod discovery, so the patch applies but your `@Mod` never loads. The
   giveaway in the log is `Skipping already parsed coremod or tweaker`, and the
   mod count being one lower than expected. Defined at `CoreModManager:60`.

4. **In a dev workspace there is no jar manifest**, so `runClient` needs
   `-Dfml.coreMods.load=your.plugin.Class` or the transformer never runs. This
   workspace sets it via `minecraft.extraRunJvmArguments`.

5. **A hook can take `this` as `java.lang.Object`.** `ReachTransformer` needs the
   `NetHandlerPlayServer`'s player, whose field is `playerEntity` in dev and
   `field_147369_b` in the pack. Rather than emit either name, it pushes `ALOAD 0`
   and declares the hook as `(Ljava/lang/Object;)D`; the hook finds the field
   reflectively by *type*, once, and caches it. Descriptors with obfuscated class
   or field names are the main reason a transformer works in dev and fails in the
   pack — passing `Object` sidesteps the whole problem.

Also: a hook called from a hot vanilla method must never throw. `slotClick`
handles every inventory click in the game, so an escaping exception breaks all
inventory interaction — catch `Throwable` and fall back to vanilla.

## Things that will bite you

- **Registry names are permanent.** Renaming `qfcontent:forge_shard` after a world
  has saved orphans every existing copy.
- **`world.isRemote`** — `true` means client. Gameplay logic goes in the `!isRemote`
  branch.
- **Light level is 0.0–1.0**, not 0–15.
- **Textures must be 16x16** (or a power of two) or the atlas stitch fails.
- **`en_US.lang` uses `item.<unlocalizedName>.name`** — and blocks use `tile.`, not
  `block.`.
- Unlocalized name and registry name are two different strings that happen to match
  in this template. Keep them matching; it saves confusion later.
- **Generating a chunk does not place ore.** Ore comes from *populate*, and
  `Chunk.populateChunk` silently does nothing until the `+1/+1` neighbours already
  exist. Load an isolated chunk and you get bare terrain and no error. If you need
  populated chunks, generate a contiguous patch and use only its interior.
- **A private nested class costs you a synthetic `Outer$1`.** javac reaches a
  private nested class's implicit constructor through a generated accessor class.
  Anonymous classes produce one too. Both loaded fine offline but threw
  `NoClassDefFoundError` under `LaunchClassLoader` on the dedicated server, killing
  the tick loop. Dropping `private` (package-private) emits no synthetic at all.
  Worth avoiding anonymous and private nested classes in server-tick paths.
- **A cached `Chunk` reference goes stale.** `loadChunk` hands you an object, but
  populate runs later -- it waits on the +1/+1 neighbours -- and by then the
  provider may return a DIFFERENT instance for the same coordinates. Reading
  `isTerrainPopulated` off the reference you kept says "not populated" while the
  live chunk is fully populated. Re-fetch with `chunkExists` + `provideChunk` at
  the moment you read. This silently discarded two thirds of every nether patch.
- **Anything on the server tick needs a catch-all.** An exception escaping a
  `ServerTickEvent` handler takes the whole server down. A convenience feature
  should switch itself off, not crash the world.

## Measure the same thing twice

Every measurement bug in the ore survey was found by two independent instruments
disagreeing, and none was visible in either one alone -- the wrong numbers all
looked completely plausible on their own.

The survey counts ore blocks in finished chunks, AND hooks the generator to record
veins as they are placed. They reconcile through the fill ratio:

    blocks_per_chunk  ~=  veins_per_chunk * vein_size * fill      (fill: 0.44-0.58)

`tools/cross-check-survey.py` flags anything outside that band. It caught a vein
count divided by a cumulative total from before the recorder existed (13x too
low), and a populated-chunk check reading a stale reference (about 2x too high, in
one dimension only).

Two habits that made this work:

- **Keep a known-exact value in the data.** Vanilla coal is `genStandardOre1(20,
  coalGen, 0, 128)`, so any overworld run MUST report 20.000 veins/chunk. A
  systematic error announces itself instead of hiding among plausible numbers.
- **Never report a number that has not passed a check it could have failed.**
  "It looks about right" is not a check.

## Testing without a client

`./gradlew runServer` boots a headless dedicated server, and **its console reads
stdin** — so a whole session can be scripted and run unattended:

```bash
( sleep 145; echo "qfsurvey start 300"
  sleep 45;  echo "qfsurvey show"
  sleep 8;   echo "stop"; sleep 40 ) | ./gradlew runServer --console=plain -q > /tmp/run.log 2>&1
```

Needs `run/eula.txt` containing `eula=true` and a `run/server.properties` (set
`level-seed` to make runs reproducible). This tests anything that isn't rendering,
without the client's manual world-entry step — and for server-side features it is
the *honest* test, since it proves no client is involved. It also sidesteps the
one-Minecraft-at-a-time OpenAL limit on this Mac: a dedicated server has no audio.

## Two coremods patching the same class

Two mods patching the same vanilla class is normal and usually fine. Two mods
patching the same *method* is where it gets interesting, and the failure is
silent in both directions — so check the bytecode rather than the log.

Legends Mod and FiskFille's Transformers Mod are the worked example, because
Legends' ASM layer is derived from FiskFille's: the transformer classes have
near-identical names (`TransformerModelBiped` vs `ClassTransformerModelBiped`)
and the *hook methods have identical names too* (`renderBipedPre`,
`renderBipedPost`, `applyPlayerRenderTranslation`, `getScaledSneakOffset`).
That similarity makes a name-based audit useless: matching strings tell you
nothing about which calls were actually emitted.

Order is decided by filename, not by declaration. Neither plugin sets a
`@SortingIndex`, so FML falls back to discovery order — which is why the Legends
jar is called `1Legends-…jar`. It patches clean bytecode; everyone else patches
the result.

Three outcomes, all observed in one launch:

* **`ModelBiped` — nested correctly.** Both inject around the same `render`
  call and the result is TF-pre → Legends-pre → body → Legends-post → TF-post.
  Wrapping injections compose.
* **`Entity` — disjoint.** They target different methods of the same class
  (Legends `getEntityScale`/`shouldProduceSprintParticles`, TF
  `getBrightnessForRender`). No interaction at all.
* **`RenderPlayer` — one patch silently lost.** TF's `renderLivingAt` injection
  scans for an `INVOKEVIRTUAL` of `(LAbstractClientPlayer;DDD)V`. Legends had
  already *replaced* that instruction with an `INVOKESTATIC` to its own hook, so
  TF's pattern no longer matched and its hook was never inserted.

The trap is the third case combined with how these transformers report success.
`ClassTransformerBase` logs `Patching Class X done` when `processMethods`
returns true — but `processMethods` sets its flag on *finding the method*, not
on matching the injection pattern. So a patch that did nothing still logs
`done`, and a patch that did nothing is indistinguishable from one that worked
if you only read the log.

What actually answers the question: these transformers dump every class they
rewrite to `debug/` in the instance directory. Disassemble the dump and list the
emitted calls.

    javap -p -c "debug/RenderPlayer (bop).class" \
      | grep -oE '(com/tihyo|fiskfille)[A-Za-z/]*\.[A-Za-z]+' | sort | uniq -c

Two hooks in the output means both patches landed. One means the other was lost,
whatever the log said. Structural injections (wrap a call, insert at method
entry) survive being patched twice; injections that *scan for a specific
instruction* are the fragile ones, because the first mod to run can rewrite the
very instruction the second one is looking for.

## The survey nodes do not all share their mods

`nodes/n1`, `n2` and `n3` symlink `mods` at the shared
`QF-Survey-Server/mods`, so dropping a jar there reaches all three. `n4` was
added later and has a **real `mods` directory of its own**. Copying a jar to the
shared folder does not reach it, and neither does copying to `n4` reach the
others.

That asymmetry is quiet in exactly the wrong way. A node running a stale
`QuestForgeContent` still starts, still accepts `/qfsurvey`, still surveys six
thousand chunks and still writes a perfectly valid `qfcontent-oresurvey.txt` —
it simply never writes `qfcontent-oreveins.txt`, because that build predates the
vein recorder. The run looks successful in the log and in the block counts; the
only symptom is a file that is not there.

Check before starting a run, not after:

    ls -la nodes/*/mods/QuestForgeContent-1.0.0.jar   # sizes must match
    ls -ld nodes/*/mods                               # which are symlinks

and after a run that was supposed to record veins, assert the file exists rather
than assuming it does. `Survey stopped and saved` refers to the block survey and
is printed whether or not any vein data was captured.

## Removing a mod from measured ore data

Two things make this less mechanical than deleting rows.

**Rates mostly do not need recomputing -- but "mostly" is the whole problem.**
An ore's veins-per-chunk is a loop bound inside its own mod, and no other mod can
reach it. That reasoning is sound and it holds for the majority: in a controlled
A/B (same seed, same terrain, hbm the only variable) **34 of 35 fixed-loop-bound
ores came back bit-identical**, coal at exactly 20.000 veins of size 16.00 both
times.

It is also not enough, and three mechanisms break it:

* **Competition for stone.** `WorldGenMinable` only replaces its target block, so
  ores displace one another. Removing hbm raised other ores' block density about
  4% overall and coal by 6% -- two to three times the estimate from hbm's share of
  the whole column, because its ores concentrated in the shallow band where most
  others live. Estimate this per depth band, not per chunk.
* **Generators that are not `WorldGenMinable` at all.** VoltzEngine's ores never
  appear in the vein data in either run; its custom generator is invisible to the
  ASM hook. Its block counts swung up to 95%.
* **Generators that lose to the competition.** Railcraft's poor ores rose *up to
  sixtyfold* (0.014 -> 0.887 veins/chunk) once hbm stopped consuming the stone
  they seam through. Nothing about filtering rows could have produced that.

There is also a fourth, harmless one worth knowing: removing a mod deletes its
`rand.nextInt` calls from chunk population, which shifts the shared RNG stream for
every generator that runs after it. Individual random-rate ores then wobble a few
percent in both directions -- across 124 of them the mean shift was -0.009%, so it
is noise, not bias.

So: filtering is a stopgap that keeps the exact rows honest. **Re-survey after any
mod that generates ore is added or removed.** It is cheaper than it sounds -- and
removing a big ore mod makes it cheaper still, since worldgen throughput here went
from 6.7 to 51 chunks/second once hbm was gone.

**Display names are not owned by one mod.** The survey files key on registry
names (`hbm:tile.ore_copper:0`), so filtering them is exact. The *atlas* was
built from a report that grouped by display name, and several names are shared —
"Copper Ore" belongs to hbm, Legends and VoltzEngine at once. Deleting those rows
would silently delete the survivors too.

Worse, such a row is a **sum**. Overworld "Copper Ore" read 28 veins at size 7.1,
which is Legends' 16 at size 8 plus hbm's 12 at size 6 — a non-integer size on a
row where every contributor is exact is the tell that a row is composite. Those
rows must be split, not dropped:

    new_rate   = rate - removed_rate
    new_size   = (rate * size - removed_rate * removed_size) / new_rate

Better still, rebuild the row by summing the surviving blocks straight from the
vein file; the subtraction above inherits the rounding of whatever precision the
page stored (it gave size 7.9 where the true answer was 8.0).

To decide whether a name is exclusive, ask the pack rather than guessing —
concatenate every remaining mod's `en_US.lang` and look the display string up. If
no installed mod produces it, every row carrying it belonged to the departed mod:

    for j in mods/*.jar; do
      unzip -p "$j" '*/lang/en_US.lang' 2>/dev/null | sed "s|^|$(basename $j)\t|"
    done > all.tsv

Do this *before* the jar is deleted, or keep a copy of its lang file — you need
the departing mod's names to know what to look for.

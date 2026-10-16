package com.questforge.content.census;

import java.io.File;
import java.lang.reflect.Constructor;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityList;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.attributes.IAttributeInstance;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.projectile.EntityArrow;
import net.minecraft.init.Items;
import net.minecraft.item.ItemStack;
import net.minecraft.world.ChunkCoordIntPair;
import net.minecraft.world.WorldServer;

import net.minecraftforge.common.ForgeChunkManager;

import com.questforge.content.QuestForgeContent;
import com.questforge.content.ench.CombatState;
import com.questforge.content.ench.Cooldowns;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.EnchantTap;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.QFEnchantments;
import com.questforge.content.ench.TickedEffects;

/**
 * /qfcensus combat -- what each enchantment is worth in a fight.
 *
 * <h3>Why this exists rather than another simulation</h3>
 *
 * There is already a Python model of the dispatcher in {@code tools/balance}. It
 * is a second implementation of rules that live in Java, which means it can be
 * right on the day it is written and quietly wrong a commit later, and nothing
 * about its output would look any different. {@code ENCHANT-GROUND-TRUTH.md} was
 * written specifically because its conclusions stopped being trusted.
 *
 * So this measures instead. Every number it writes came from a real swing at a
 * real entity through {@code EnchantEventBridge} and {@code EnchantDispatcher} --
 * the shipping code, in the running game, with the pack's mobs and the pack's
 * gear. Nothing here re-implements an enchantment or predicts what one will do.
 *
 * <h3>How a number is produced</h3>
 *
 * Every measurement is <b>paired against a control</b>: the identical fight with
 * the identical weapon carrying no custom enchantment at all. What gets reported
 * is the difference. That is what makes the figures comparable across a pack
 * whose weapons run from a wooden sword's 4 damage to well over 700 -- a flat
 * "+6 damage" means nothing on its own, and "+31% over control" means the same
 * thing at both ends.
 *
 * Three separate quantities are recorded because they answer different questions
 * and routinely disagree:
 *
 * <ul>
 * <li><b>Sustained damage per second</b> over a fixed window. The tuning number.</li>
 * <li><b>Time to kill</b> a real target that is allowed to die. The felt number,
 *     and the one where health-scaling effects like Colossus and Executioner
 *     stop resembling their DPS figure.</li>
 * <li><b>Observed proc rate</b>, counted by {@link EnchantTap} at the point of
 *     dispatch. This is a check on the code rather than on the balance: if an
 *     enchantment documented at 24% fires at 8%, that is a bug, and no amount of
 *     tuning the effect will fix it.</li>
 * </ul>
 *
 * <h3>What this deliberately does not do</h3>
 *
 * It does not decide anything. It writes TSV. Rarity, level curves and loot
 * weights are judgement calls that belong to a person reading the output, and
 * the file is designed to be read next to {@code ENCHANT-TUNING.md} rather than
 * to replace it.
 *
 * @see CensusProbe#pumpTick for why a fight has to be driven a tick at a time
 */
public class CombatCensus {

    private CombatCensus() {}

    // ---- Dials ------------------------------------------------------------

    /** Ticks of sustained combat per cell. 400 = 20 seconds. */
    private static final int WINDOW_TICKS = 400;

    /**
     * Ticks between the probe's swings.
     *
     * Vanilla 1.7.10 has no attack cooldown, so the real limit on melee is the
     * target's twenty ticks of invulnerability. Ten ticks is a fast player who is
     * not wasting many swings into i-frames. The exact value matters less than it
     * looks: control and treatment use the same one, so it cancels out of every
     * marginal figure, and it is recorded in the file header so a reader can see
     * what was assumed.
     */
    private static final int SWING_INTERVAL = 10;

    /**
     * Ticks between incoming attacks from the target during an offensive cell.
     *
     * Mob AI never engages the probe -- it is not in the world's player list, so
     * nothing targets it -- which would leave Riposte and Bulwark permanently
     * untriggered and measured at zero. Driving one incoming hit every two
     * seconds is roughly a mob's own cadence and makes "if you were hurt recently"
     * a condition that is sometimes true, as it is in a real fight.
     */
    private static final int INCOMING_INTERVAL = 40;

    /**
     * Targets spawned per cell. More than one so cleave effects -- Arc above all
     * -- have somewhere to land; a single-target census would record Arc as
     * contributing nothing at all.
     */
    private static final int SWARM = 3;

    /** Probe health for defensive cells. A real player's, so triggers behave. */
    private static final float DEFENSIVE_HEALTH = 20.0F;

    /** Probe health everywhere else: high enough that nothing can end a cell early. */
    private static final float PROBE_HEALTH = 1000000.0F;

    /** Incoming swings per defensive cell. */
    private static final int DEFENSIVE_SWINGS = 60;

    /**
     * The share of its health a wounded probe is held at.
     *
     * Low enough that missing-health scaling is well into its range, high enough
     * that a single incoming hit does not end the cell.
     */
    private static final float WOUNDED_FRACTION = 0.3F;

    /** Blocks between the probe and its target in a bow cell. */
    private static final double BOW_STANDOFF = 10.0D;

    /**
     * Raw damage per incoming hit in a defensive cell, before armour.
     *
     * Fixed on purpose; see advanceDefense. Eight is chosen so a 20-health probe
     * in full diamond survives a useful number of hits rather than one or
     * hundreds: enough for Bulwark's missing-health scaling and Cockroach's
     * low-health trigger to come into range, and enough that the difference
     * between a good armour enchantment and none is many hits rather than a
     * rounding error.
     */
    private static final float DEFAULT_INCOMING_DAMAGE = 8.0F;

    /**
     * The incoming magnitude actually in force, settable per run with "hit=40".
     *
     * Two different questions want two different values, and one run cannot
     * answer both. Mitigation is a ratio, so it comes out the same at any
     * magnitude and is cleanest where the numbers are small. Survivability is a
     * count of hits taken before dying, and at 8 raw through full diamond a
     * 20-health probe takes about seventeen hits to die -- three deaths in a
     * sixty-hit cell, which puts every armour enchantment in the pack between 57
     * and 59 and resolves nothing. Around 40 raw, near what this pack's bosses
     * actually swing for once MobProperties has scaled them, the probe dies every
     * few hits and the differences become visible.
     */
    private static float incomingDamage = DEFAULT_INCOMING_DAMAGE;

    // ---- Model ------------------------------------------------------------

    /** Which side of a fight a cell measures. */
    private enum Mode { MELEE, BOW, DEFENSE }

    /**
     * Everything a run can be told to do, in one place.
     *
     * A census is launched from a console, from a JVM flag, or by hand, and the
     * argument list had grown past what a method signature could carry without
     * every call site guessing which boolean was which.
     */
    public static class Options {
        /** Offensive cells fought at 30% health. */
        public boolean wounded;
        /** Raw damage per incoming hit in defensive cells; 0 = default. */
        public float incoming;
        /** Every pair of offensive enchantments, as stacked cells. */
        public boolean pairs;
        /** Every triple. Only sane with a small {@link #only} set. */
        public boolean triples;
        /** Restrict the enchantment set to these display keys, or null for all. */
        public java.util.Set<String> only;
        /** Restrict to these modes, or null for all. */
        public java.util.Set<String> modes;
        /** This node's share of the queue: index and count. 1/1 = everything. */
        public int shardIndex = 0;
        public int shardCount = 1;

        public String describe() {
            StringBuilder sb = new StringBuilder();
            if (wounded) sb.append(" wounded");
            if (incoming > 0F) sb.append(" hit=").append(incoming);
            if (pairs) sb.append(" pairs");
            if (triples) sb.append(" triples");
            if (only != null) sb.append(" only=").append(only);
            if (modes != null) sb.append(" modes=").append(modes);
            if (shardCount > 1) sb.append(" shard=").append(shardIndex).append('/').append(shardCount);
            return sb.length() == 0 ? " (defaults)" : sb.toString();
        }
    }

    private static Options options = new Options();

    /** One enchantment at one level, or the empty control. */
    private static class Loadout {
        final String label;
        final List<QFEnchantment> enchants = new ArrayList<QFEnchantment>();
        final List<Integer> levels = new ArrayList<Integer>();

        Loadout(String label) {
            this.label = label;
        }

        Loadout with(QFEnchantment e, int level) {
            enchants.add(e);
            levels.add(Integer.valueOf(level));
            return this;
        }

        boolean isControl() {
            return enchants.isEmpty();
        }

        /** "colossus:3 + rupture:3", for the output. */
        String describe() {
            if (isControl()) return "(control)";
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < enchants.size(); i++) {
                if (i > 0) sb.append(" + ");
                sb.append(enchants.get(i).displayKey()).append(':').append(levels.get(i));
            }
            return sb.toString();
        }
    }

    /** One measurement: a loadout, a mode, and a target to try it on. */
    private static class Cell {
        Loadout loadout;
        Mode mode;
        String targetName;
        /** Set for stacked cells so the report can separate them from isolated ones. */
        boolean stacked;
    }

    /** What one cell produced. */
    private static class Result {
        double damageDealt;
        int swings;
        /** Swings that actually reduced the target's health. */
        int hitsLanded;
        /** The primary's invulnerability timer when the cell ended. */
        int lastResistTime;
        /** The primary's own tick counter: zero means the world is not updating it. */
        int targetTicks;
        /** Whether the world still had the primary in its entity list. */
        boolean targetInWorld;
        int kills;
        final List<Integer> killTicks = new ArrayList<Integer>();
        double damageTaken;
        int incomingSwings;
        int probeDeaths;
        int hitsSurvived;
        long procRolls;
        long procFires;
        double attributedDamage;
        String note = "";

        double dps(int ticks) {
            return ticks <= 0 ? 0 : damageDealt / (ticks / 20.0D);
        }
    }

    // ---- Run state --------------------------------------------------------

    private static boolean running;
    private static File configDir;
    private static WorldServer world;
    private static CensusFile out;
    private static CensusFile procs;
    private static CensusFile failures;

    private static List<Cell> queue;
    private static int index;

    /**
     * Whether offensive cells are fought by a probe held at low health.
     *
     * Berserk, Riposte, Bulwark, Cockroach and Sacrifice all key off the
     * WIELDER's health, and an offensive cell normally runs a probe with a
     * million hit points so nothing can end the window early. Every one of them
     * therefore measured zero. Setting this runs the same measurements with the
     * probe held near death, which is the situation those enchantments were
     * written for, against a control fought the same way.
     */
    private static boolean wounded;

    private static ItemStack weaponTemplate;
    private static ItemStack bowTemplate;
    private static ItemStack[] armourTemplate;

    private static double px, py, pz;

    /**
     * The health and damage every spawn of a given target is pinned to.
     *
     * MobProperties multiplies each spawn's maxHealth by 1+U(3,9) and its
     * attackDamage by 1+U(0.5,2), so two mobs of the same species differ by up to
     * ten times. That is the pack as played, and it is also fatal to a paired
     * measurement: a cell and its control fight different distributions, and the
     * difference between them drowns the enchantment being measured. Measured
     * empirically on the first full pack run, enchantments that can only be worth
     * exactly zero came out anywhere between -16% and +17%.
     *
     * So the first spawn of each target in a run sets the reference, and every
     * later spawn of that target is pinned to it. The value is still one the pack
     * really produced -- nothing invented -- and it is recorded in the file
     * header. What changes is that every cell now fights the same opponent, which
     * is what makes the comparison a comparison.
     */
    private static final java.util.Map<String, double[]> REFERENCE =
            new java.util.HashMap<String, double[]>();

    /** Keeps the arena ticking. See {@link #acquireArena}. */
    private static ForgeChunkManager.Ticket arenaTicket;

    /**
     * Set when the run was started automatically, so the server shuts itself down
     * once the census is written. A detached run has nobody to type "stop".
     */
    private static boolean shutdownWhenFinished;
    /** Forge only issues tickets to a mod that has registered a callback. */
    private static boolean callbackRegistered;
    private static final Random rand = new Random(0xC0FFEE);

    /** Control results, keyed "mode/target", filled in before the enchanted cells. */
    private static final java.util.Map<String, Result> CONTROLS =
            new java.util.HashMap<String, Result>();

    // Current cell in flight.
    private static Cell cell;
    private static Result result;
    private static int cellTick;
    private static final List<EntityLivingBase> spawned = new ArrayList<EntityLivingBase>();
    private static double[] lastHealth = new double[0];
    private static int trialStartTick;

    public static boolean isRunning() {
        return running;
    }

    /**
     * Asks the server to stop once this census finishes.
     *
     * Only for automated runs. The output files are closed by {@link #stop},
     * which runs first, so the TSV is complete before the shutdown begins.
     */
    public static void stopServerWhenFinished() {
        shutdownWhenFinished = true;
    }

    public static String status() {
        if (!running) return "not running";
        return "combat census: " + index + "/" + queue.size() + " cells"
                + (cell == null ? "" : " (running " + cell.loadout.describe()
                        + " vs " + cell.targetName + ", tick " + cellTick + "/" + WINDOW_TICKS + ")");
    }

    // ---- Lifecycle --------------------------------------------------------

    /**
     * @param weapon the melee weapon to measure with, or null for a diamond sword.
     *               Taken from the operator's hand so the pack's real endgame
     *               weapons can be measured without hard-coding any of them.
     * @param targets entity registry names to fight, or empty for the defaults.
     */
    public static void start(WorldServer target, File dir, ItemStack weapon,
            List<String> targets, Options opts) {
        if (running) return;
        options = opts == null ? new Options() : opts;
        wounded = options.wounded;
        incomingDamage = options.incoming > 0F ? options.incoming : DEFAULT_INCOMING_DAMAGE;

        world = target;
        configDir = dir;
        index = 0;
        cell = null;
        result = null;
        CONTROLS.clear();
        REFERENCE.clear();
        HEALTH_OVERRIDE.clear();
        spawned.clear();

        weaponTemplate = weapon != null && weapon.getItem() != null
                ? weapon.copy()
                : new ItemStack(Items.diamond_sword);
        bowTemplate = new ItemStack(Items.bow);
        armourTemplate = new ItemStack[] {
                new ItemStack(Items.diamond_boots),
                new ItemStack(Items.diamond_leggings),
                new ItemStack(Items.diamond_chestplate),
                new ItemStack(Items.diamond_helmet),
        };

        px = target.getSpawnPoint().posX + 0.5D;
        pz = target.getSpawnPoint().posZ + 0.5D;
        py = target.getTopSolidOrLiquidBlock((int) px, (int) pz) + 1;

        List<String> resolved = resolveTargets(targets);

        queue = buildQueue(resolved);

        out = new CensusFile(dir, "combat",
                "What each combat enchantment is worth in a real fight, measured by driving the "
              + "shipping dispatcher rather than modelling it. Every row is paired against a control "
              + "row of the same weapon with no custom enchantment, and marginal_pct is the number to "
              + "read. Window " + WINDOW_TICKS + " ticks, one swing every " + SWING_INTERVAL
              + " ticks, one incoming hit every " + INCOMING_INTERVAL + " ticks; defensive cells "
              + "take a fixed " + CensusFile.num(incomingDamage) + " raw per hit so the attacker's "
              + "own rolled damage cannot swamp the armour being measured; " + SWARM
              + " targets per cell. Options:" + options.describe()
              + ". Weapon: " + describeStack(weaponTemplate) + ".\n"
              + "# hits_landed is melee-only: an arrow damages on impact, not when it is loosed, so "
              + "bow rows read 0 and their damage appears in damage_dealt.\n"
              + "# damage_dealt counts health actually lost, so overkill is discarded. Against a "
              + "target that dies in a few hits the figure quantises to its health per kill and "
              + "unrelated enchantments can tie; use the pack's bosses for anything you tune on.\n"
              + "# attributed_damage is only the change made to the hit in flight. Bleeds, chains "
              + "and summons land elsewhere and are counted in damage_dealt. Do not add the two.\n"
              + (wounded ? "# WOUNDED RUN: the probe fights at 30% health so enchantments keyed to "
                        + "the wielder being hurt can fire. Not comparable with a full-health run.\n"
                         : "")
              + "# Every spawn of a target is pinned to the health and damage the first one rolled, "
              + "so each cell fights the same opponent as its control. Without it MobProperties' "
              + "per-spawn 4-10x health roll swamps the effect being measured. The reference values "
              + "are in the log.",
                new String[] {
                    "loadout", "kind", "mode", "rarity", "level", "category", "target",
                    "swings", "hits_landed", "damage_dealt", "dps", "marginal_dps", "marginal_pct",
                    "kills", "ttk_mean_ticks", "ttk_min_ticks", "ttk_max_ticks", "marginal_ttk_pct",
                    "damage_taken", "incoming_swings", "mitigation_pct", "hits_survived",
                    "proc_rolls", "proc_fires", "observed_proc_pct", "expected_proc_pct",
                    "attributed_damage", "note"
                });

        procs = new CensusFile(dir, "combat-procs",
                "Every proc roll the dispatcher made during the census, by enchantment and trigger. "
              + "observed_pct is measured; expected_pct is what getProcChance returns. A gap between "
              + "them is a bug in the enchantment, not a balance problem. attributed_damage is only "
              + "the change made to the hit in flight -- bleeds, chains and summons land elsewhere "
              + "and are counted in the combat file's damage_dealt instead.",
                new String[] {
                    "enchant", "trigger", "rolls", "fires", "observed_pct", "expected_pct",
                    "replays_multistrike", "attributed_damage", "largest_single"
                });

        failures = new CensusFile(dir, "combat-failed",
                "Cells that could not be measured, and why. An enchantment that appears here has NOT "
              + "been balanced, whatever the tuning document says.",
                new String[] { "loadout", "target", "stage", "error" });

        acquireArena();

        EnchantTap.start();
        running = true;
        QuestForgeContent.log.info("[census] combat census started: " + queue.size()
                + " cells over targets " + resolved);
    }

    public static void stop() {
        if (!running) return;
        despawnAll();
        releaseArena();
        restoreProbe();
        EnchantTap.stop();
        if (out != null) out.close();
        if (procs != null) procs.close();
        if (failures != null) failures.close();
        QuestForgeContent.log.info("[census] combat census finished -> "
                + (out == null ? "?" : out.file().getName()));
        running = false;
        queue = null;
        world = null;
        cell = null;

        if (shutdownWhenFinished) {
            shutdownWhenFinished = false;
            QuestForgeContent.log.info("[census] automatic run complete; stopping the server.");
            try {
                net.minecraft.server.MinecraftServer.getServer().initiateShutdown();
            } catch (Throwable t) {
                QuestForgeContent.log.error("[census] could not stop the server", t);
            }
        }
    }

    // ---- Building the run -------------------------------------------------

    /**
     * The targets to fight.
     *
     * Defaults are deliberately mixed: a vanilla zombie because it is the one
     * entity guaranteed to exist and whose numbers are known independently, and
     * the pack's benchmark bosses because balance at 20 health says nothing about
     * balance at four thousand. Anything not registered is skipped and recorded,
     * which is what lets the same command run in a bare dev client and in the
     * full pack.
     */
    private static List<String> resolveTargets(List<String> requested) {
        List<String> wanted = new ArrayList<String>();
        if (requested != null && !requested.isEmpty()) {
            wanted.addAll(requested);
        } else {
            wanted.add("Zombie");
            wanted.add("TwilightForest.Hydra");
            wanted.add("mobzilla");
            wanted.add("Rahovart");
        }

        List<String> found = new ArrayList<String>();
        for (String spec : wanted) {
            // "Zombie@400" pins that target's effective max health to 400.
            String name = spec;
            int at = spec.indexOf('@');
            Double override = null;
            if (at > 0) {
                name = spec.substring(0, at);
                try {
                    override = Double.valueOf(spec.substring(at + 1));
                } catch (NumberFormatException e) {
                    failures.row("(target)", spec, "resolve",
                            "health override after '@' is not a number");
                    continue;
                }
            }
            String match = matchEntity(name);
            if (match != null && override != null) {
                HEALTH_OVERRIDE.put(match, override);
                QuestForgeContent.log.info("[census] target " + match
                        + " pinned to " + CensusFile.num(override.doubleValue()) + " health");
            }
            if (match != null) {
                found.add(match);
            } else {
                failures.row("(target)", name, "resolve", "no entity registered under that name");
                QuestForgeContent.log.warn("[census] combat target not registered, skipping: " + name);
            }
        }
        if (found.isEmpty()) found.add("Zombie");
        return found;
    }

    /**
     * Health overrides from a "Name@Health" target spec, keyed by entity name.
     *
     * A boss that cannot die measures sustained damage beautifully and tells you
     * nothing about any enchantment whose condition is the target being nearly
     * dead -- Executioner measured exactly zero against Rahovart for that reason.
     * Pinning a target to a chosen health gives a dummy that dies on a known
     * schedule, so those conditions are actually reached, without reintroducing
     * the per-spawn health roll that made the zombie unusable.
     */
    private static final java.util.Map<String, Double> HEALTH_OVERRIDE =
            new java.util.HashMap<String, Double>();

    /** Registry lookup that tolerates the case and prefixing differences between mods. */
    private static String matchEntity(String name) {
        if (EntityList.stringToClassMapping.containsKey(name)) return name;
        for (Object key : EntityList.stringToClassMapping.keySet()) {
            String k = String.valueOf(key);
            if (k.equalsIgnoreCase(name) || k.toLowerCase().endsWith("." + name.toLowerCase())) {
                return k;
            }
        }
        return null;
    }

    /**
     * Every cell the run will measure: a control per mode and target, then one
     * cell per combat enchantment at its maximum level, then the stacked
     * loadouts.
     *
     * Maximum level because that is the case the loot table has to be safe for.
     * A level 1 figure can be inferred from the code's own scaling once the level
     * 3 one is trusted; the reverse is not true for anything with a cap in it.
     */
    private static List<Cell> buildQueue(List<String> targets) {
        List<Cell> cells = new ArrayList<Cell>();

        for (String target : targets) {
            for (Mode mode : new Mode[] { Mode.MELEE, Mode.BOW, Mode.DEFENSE }) {
                cells.add(cell(new Loadout("control"), mode, target, false));
            }
        }

        List<QFEnchantment> all = new ArrayList<QFEnchantment>(QFEnchantments.all());
        Collections.sort(all, new java.util.Comparator<QFEnchantment>() {
            public int compare(QFEnchantment a, QFEnchantment b) {
                return a.displayKey().compareTo(b.displayKey());
            }
        });

        List<QFEnchantment> offensive = new ArrayList<QFEnchantment>();
        for (QFEnchantment ench : all) {
            if (ench == null) continue;
            Mode mode = modeFor(ench);
            if (mode == null) continue;   // not a combat enchantment
            if (options.only != null && !options.only.contains(ench.displayKey())) continue;
            if (options.modes != null && !options.modes.contains(mode.name())) continue;
            if (mode == Mode.MELEE) offensive.add(ench);
            for (String target : targets) {
                cells.add(cell(new Loadout(ench.displayKey()).with(ench, ench.getMaxLevel()),
                        mode, target, false));
            }
        }

        boolean meleeWanted = options.modes == null || options.modes.contains("MELEE");

        if (options.pairs && meleeWanted) {
            // Every pair. This is the "what does a player end up holding" question
            // asked exhaustively rather than by a curated list: n enchantments give
            // n(n-1)/2 pairs, so it is only ever run sharded across several nodes,
            // and only over the offensive set -- a utility enchantment paired with
            // a damage one measures the damage one, which the singles already did.
            for (int i = 0; i < offensive.size(); i++) {
                for (int j = i + 1; j < offensive.size(); j++) {
                    QFEnchantment a = offensive.get(i), b = offensive.get(j);
                    for (String target : targets) {
                        cells.add(cell(new Loadout(a.displayKey() + " + " + b.displayKey())
                                .with(a, a.getMaxLevel()).with(b, b.getMaxLevel()),
                                Mode.MELEE, target, true));
                    }
                }
            }
        }

        if (options.triples && meleeWanted) {
            for (int i = 0; i < offensive.size(); i++) {
                for (int j = i + 1; j < offensive.size(); j++) {
                    for (int k = j + 1; k < offensive.size(); k++) {
                        QFEnchantment a = offensive.get(i), b = offensive.get(j), c = offensive.get(k);
                        for (String target : targets) {
                            cells.add(cell(new Loadout(a.displayKey() + " + " + b.displayKey()
                                    + " + " + c.displayKey())
                                    .with(a, a.getMaxLevel()).with(b, b.getMaxLevel())
                                    .with(c, c.getMaxLevel()), Mode.MELEE, target, true));
                        }
                    }
                }
            }
        }

        if (!options.pairs && !options.triples && meleeWanted) {
            // The curated stacks, for a run that is not exhaustive.
            for (String target : targets) {
                for (Loadout stack : stackedLoadouts()) {
                    cells.add(cell(stack, Mode.MELEE, target, true));
                }
            }
        }

        // Sharding. Every node runs every control -- a marginal figure is computed
        // against the control that ran in the same process, and a node without
        // one would write NaN for everything -- and then its share of the rest,
        // taken round-robin so the shards are the same length and each mixes
        // targets and modes rather than getting all of one.
        if (options.shardCount > 1) {
            List<Cell> controls = new ArrayList<Cell>();
            List<Cell> rest = new ArrayList<Cell>();
            for (Cell c : cells) {
                (c.loadout.isControl() ? controls : rest).add(c);
            }
            List<Cell> mine = new ArrayList<Cell>(controls);
            for (int i = 0; i < rest.size(); i++) {
                if (i % options.shardCount == options.shardIndex) mine.add(rest.get(i));
            }
            QuestForgeContent.log.info("[census] shard " + options.shardIndex + "/"
                    + options.shardCount + ": " + mine.size() + " of " + cells.size() + " cells");
            cells = mine;
        }

        return cells;
    }

    private static Cell cell(Loadout loadout, Mode mode, String target, boolean stacked) {
        Cell c = new Cell();
        c.loadout = loadout;
        c.mode = mode;
        c.targetName = target;
        c.stacked = stacked;
        return c;
    }

    /**
     * The combinations worth checking, chosen because each is a plausible way for
     * the numbers to compound rather than add.
     */
    private static List<Loadout> stackedLoadouts() {
        List<Loadout> out = new ArrayList<Loadout>();

        // Multi Strike doubles every multipliable proc, so it is the multiplier on
        // everything else and belongs in most of these.
        add(out, "multistrike + rupture + accelerant", "multistrike", "rupture", "accelerant");
        add(out, "multistrike + colossus + executioner", "multistrike", "colossus", "executioner");
        add(out, "cultist + berserk + riposte", "cultist", "berserk", "riposte");
        add(out, "momentum + assassinate + rage", "momentum", "assassinate", "rage");
        add(out, "venomous + poisonous + accelerant", "venomous", "poisonous", "accelerant");
        add(out, "excalibur + multistrike", "excalibur", "multistrike");
        add(out, "arc + rupture + feast", "arc", "rupture", "feast");

        return out;
    }

    private static void add(List<Loadout> into, String label, String... names) {
        Loadout l = new Loadout(label);
        for (String name : names) {
            QFEnchantment e = QFEnchantments.byName(name);
            if (e == null) return;   // a disabled enchantment: drop the whole combo
            l.with(e, e.getMaxLevel());
        }
        into.add(l);
    }

    /**
     * Which kind of fight an enchantment belongs in, or null if it has no combat
     * behaviour worth measuring.
     *
     * Decided from the category rather than from a hand-written list, so an
     * enchantment added later is picked up without anyone remembering to add it
     * here.
     */
    private static Mode modeFor(QFEnchantment ench) {
        EnchantCategory c = ench.category;
        if (c == null) return null;
        switch (c) {
            case WEAPON:
            case SWORD:
            case AXE:
                return Mode.MELEE;
            case BOW:
                return Mode.BOW;
            case ARMOR:
            case HELMET:
            case CHESTPLATE:
            case LEGGINGS:
            case BOOTS:
                return Mode.DEFENSE;
            case ANY:
                // "Anything enchantable" is a statement about what it can be put
                // on, not about whether it fights. Multi Strike and Demon Forged
                // are both ANY, and Multi Strike is the single most consequential
                // enchantment in the system -- it replays every multipliable proc.
                // Skipping it because of its category left the loot table with no
                // figure at all for the enchantment most likely to break it.
                // Measured on a weapon, which is where it matters.
                return Mode.MELEE;
            default:
                // TOOL, DIGGER, PICKAXE, SHOVEL: mining and utility. They have no
                // combat path, and a combat census that reported zeroes for them
                // would be reporting the absence of a measurement as a measurement.
                return null;
        }
    }

    // ---- Driving ----------------------------------------------------------

    /**
     * One server tick.
     *
     * A fight advances exactly one game tick per server tick, and that is not
     * negotiable: potion durations, bleed intervals, cooldowns and i-frames are
     * all counted in ticks by the code being measured, and running the loop
     * faster than the world would measure a different game. The cost is wall
     * clock -- a full run is tens of minutes -- which is why status() exists.
     */
    public static void tick() {
        if (!running) return;

        if (cell == null) {
            if (index >= queue.size()) {
                writeProcs();
                stop();
                return;
            }
            beginCell(queue.get(index++));
            return;
        }

        try {
            advance();
        } catch (Throwable t) {
            failures.row(cell.loadout.describe(), cell.targetName, "run", describe(t));
            QuestForgeContent.log.error("[census] combat cell failed: "
                    + cell.loadout.describe() + " vs " + cell.targetName, t);
            endCell();
            return;
        }

        if (cellTick >= windowFor(cell)) {
            endCell();
        }
    }

    private static int windowFor(Cell c) {
        return c.mode == Mode.DEFENSE ? DEFENSIVE_SWINGS * SWING_INTERVAL : WINDOW_TICKS;
    }

    private static void beginCell(Cell c) {
        cell = c;
        result = new Result();
        cellTick = 0;
        trialStartTick = 0;

        EnchantTap.reset();

        EntityPlayer probe = CensusProbe.player(world);
        if (probe == null) {
            failures.row(c.loadout.describe(), c.targetName, "probe", "no probe player");
            endCell();
            return;
        }

        clearProbeState(probe);
        // Melee stands next to the target; a bow has to stand back. An arrow
        // spawns at the shooter and a target 1.5 blocks away is already inside
        // its own hitbox, so a plain arrow passes straight through without ever
        // registering a hit -- which is why every bow control measured zero while
        // Homing, which steers, scored. Ten blocks gives the arrow a real flight.
        double standoff = (c.mode == Mode.BOW) ? BOW_STANDOFF : 1.5D;
        CensusProbe.reset(probe, px + standoff, py, pz);

        if (c.mode == Mode.DEFENSE) {
            setProbeHealth(probe, DEFENSIVE_HEALTH);
            CensusProbe.wear(probe, armourFor(c.loadout));
            CensusProbe.hold(probe, null);
            fillGrantedHealth(probe);
        } else {
            // Explicitly restored, because a DEFENSE cell lowers it to 20 and an
            // offensive cell run on a 20 HP probe is a different experiment.
            if (wounded) {
                setProbeHealth(probe, DEFENSIVE_HEALTH);
                probe.setHealth(DEFENSIVE_HEALTH * WOUNDED_FRACTION);
            } else {
                setProbeHealth(probe, PROBE_HEALTH);
            }
            CensusProbe.wear(probe, null);
            CensusProbe.hold(probe, weaponFor(c.loadout, c.mode));
        }

        if (!spawnSwarm()) {
            failures.row(c.loadout.describe(), c.targetName, "spawn",
                    "could not spawn " + c.targetName);
            endCell();
        }
    }

    private static void advance() {
        EntityPlayer probe = CensusProbe.player(world);
        if (probe == null) return;

        cellTick++;

        // The probe experiences a tick. Without this the mod's per-tick code never
        // runs for it; see CensusProbe.pumpTick.
        CensusProbe.pumpTick(probe);

        // The mod's world-tick work: bleeds, venom, cripple timers, summons. In a
        // normal game the bridge drives this from WorldTickEvent, which does fire
        // here too -- so this is NOT called again, or every damage-over-time effect
        // in the census would tick twice as fast as it does in play.

        for (EntityLivingBase mob : spawned) {
            if (mob != null && mob.isBurning()) mob.extinguish();
        }

        if (cell.mode == Mode.DEFENSE) {
            advanceDefense(probe);
        } else {
            advanceOffense(probe);
        }
    }

    /**
     * Holds the arena's chunks in memory for as long as the census runs.
     *
     * This is not an optimisation, it is the difference between measuring and not
     * measuring, and the failure it prevents is completely silent.
     *
     * {@code World.updateEntityWithOptionalForce} (World.java:2266-2290) only
     * ticks an entity when {@code checkChunksExist} is true for a 32-block radius
     * around it. A census has no real players, so once the spawn region prepared
     * at startup drifts out of memory -- about a minute in -- the chunks
     * neighbouring the arena unload. The arena's own chunk survives, because
     * spawn chunks are protected, so {@code spawnEntityInWorld} still succeeds and
     * the mob is still in {@code loadedEntityList}. It simply never ticks again,
     * and because the repair that would re-register it with its chunk lives inside
     * the same {@code canUpdate} branch, it never recovers either.
     *
     * A target that never ticks never loses its invulnerability frames, so exactly
     * one hit of a fight lands and vanilla discards every later swing under its
     * "not bigger than the last hit" rule. The cell still runs its full window and
     * still writes a tidy row saying the enchantment is worth -97%. This was found
     * by a diagnostic, not by the numbers looking wrong.
     *
     * The fix uses the escape hatch vanilla already has. That same method opens
     * with {@code isForced = getPersistentChunks().containsKey(...)} and then
     * {@code b0 = isForced ? 0 : 32}: a chunk force-loaded through Forge's
     * {@link ForgeChunkManager} shrinks the required radius to zero, so the target
     * ticks as long as its own chunk is present. Requesting a ticket is therefore
     * both the supported API and the one that addresses the actual condition.
     * {@code loadChunk} alone is not enough -- it keeps chunks resident but does
     * nothing about the 32-block test, which is what this originally tried.
     */
    private static void acquireArena() {
        releaseArena();
        int cx = ((int) px) >> 4;
        int cz = ((int) pz) >> 4;
        try {
            // Forge refuses a ticket to a mod with no loading callback registered
            // ("attempted to request a ticket without a listener in place"), so it
            // is registered here, on first use, rather than at mod init -- nothing
            // outside the census force-loads anything. There is deliberately
            // nothing to restore: a ticket held by a measurement run has no meaning
            // after a restart, and re-forcing those chunks would leave a finished
            // census pinning part of somebody's world forever.
            if (!callbackRegistered) {
                ForgeChunkManager.setForcedChunkLoadingCallback(
                        QuestForgeContent.instance,
                        new ForgeChunkManager.LoadingCallback() {
                            @Override
                            @SuppressWarnings("rawtypes")
                            public void ticketsLoaded(java.util.List tickets,
                                    net.minecraft.world.World w) {
                                // Intentionally empty; see above.
                            }
                        });
                callbackRegistered = true;
            }

            arenaTicket = ForgeChunkManager.requestTicket(
                    QuestForgeContent.instance, world, ForgeChunkManager.Type.NORMAL);
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[census] could not request a chunk ticket: " + t);
            arenaTicket = null;
        }
        if (arenaTicket == null) {
            QuestForgeContent.log.warn("[census] no chunk-loading ticket available; targets may "
                    + "not tick and the run will report degenerate cells.");
            return;
        }
        // The arena is a few blocks wide, but the ticket also has to cover the
        // chunk each target stands in, so take the immediate neighbourhood.
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                ForgeChunkManager.forceChunk(arenaTicket, new ChunkCoordIntPair(cx + dx, cz + dz));
            }
        }
        QuestForgeContent.log.info("[census] arena chunks force-loaded around " + cx + "," + cz);
    }

    private static void releaseArena() {
        if (arenaTicket == null) return;
        try {
            ForgeChunkManager.releaseTicket(arenaTicket);
        } catch (Throwable ignored) {}
        arenaTicket = null;
    }

    // ---- Offensive cells --------------------------------------------------

    private static void advanceOffense(EntityPlayer probe) {
        accumulateDamage();

        // A target that died: record the kill, then put a fresh one in its place so
        // the window keeps measuring instead of trailing off into an empty arena.
        for (int i = 0; i < spawned.size(); i++) {
            EntityLivingBase mob = spawned.get(i);
            if (mob == null || !mob.isDead && mob.getHealth() > 0F) continue;

            result.kills++;
            if (i == 0) {
                result.killTicks.add(Integer.valueOf(cellTick - trialStartTick));
                trialStartTick = cellTick;
            }
            replace(i);
        }

        if (cellTick % SWING_INTERVAL == 0) {
            EntityLivingBase primary = primary();
            if (primary != null) {
                faceToward(probe, primary);
                float healthBefore = primary.getHealth();
                if (cell.mode == Mode.BOW) {
                    fireArrow(probe, primary);
                } else {
                    // Not attackTargetEntityWithCurrentItem directly: in this pack
                    // a mod cancels the attack event outright. See CensusProbe.swing.
                    CensusProbe.swing(probe, primary);
                }
                result.swings++;
                if (primary.getHealth() < healthBefore || primary.isDead) {
                    result.hitsLanded++;
                }
                result.lastResistTime = primary.hurtResistantTime;
                result.targetTicks = primary.ticksExisted;
                result.targetInWorld = world.loadedEntityList.contains(primary);
            }
        }

        // Something has to hit the probe, or every "were you hurt recently"
        // condition in the mod is permanently false. See INCOMING_INTERVAL.
        //
        // A wounded run cannot do it by being hit. The probe is at 30% of twenty
        // health -- six -- and this pack's bosses swing for eighteen and up, so
        // every incoming hit kills it. Each death then runs the full death path
        // (our DeathHandler, Sacrifice's veto, Soulbound's inventory sweep,
        // whatever gravestone mod is listening) dozens of times per cell, and the
        // run slowed from 155 cells an hour to ten. So the state those
        // enchantments actually read is set directly instead: the wound is held,
        // and "was hurt recently" is recorded without a corpse.
        if (wounded) {
            if (cellTick % INCOMING_INTERVAL == 0) {
                CombatState.recordHurt(probe);
                result.incomingSwings++;
            }
            probe.setHealth(probe.getMaxHealth() * WOUNDED_FRACTION);
        } else if (cellTick % INCOMING_INTERVAL == 0) {
            EntityLivingBase primary = primary();
            if (primary != null) {
                float before = probe.getHealth();
                probe.hurtResistantTime = 0;
                try {
                    primary.attackEntityAsMob(probe);
                } catch (Throwable ignored) {}
                result.damageTaken += Math.max(0F, before - probe.getHealth());
                result.incomingSwings++;
                // The probe is a measuring instrument in an offensive cell, not a
                // subject; keep it alive so the fight runs the whole window. A
                // wounded run puts it back to the same fraction instead of to
                // full, because the wound is the experiment.
                probe.setHealth(probe.getMaxHealth());
            }
        }
    }

    /**
     * Damage the swarm has lost since the previous tick.
     *
     * Sampled every tick rather than around each swing because most of the
     * interesting damage in this mod does not arrive on the swing: Rupture bleeds
     * a second later, Arc lands on a different entity entirely, Venomous ticks for
     * eleven seconds. Anything that measured only the returned value of a hit
     * would credit those enchantments with nothing.
     */
    private static void accumulateDamage() {
        for (int i = 0; i < spawned.size(); i++) {
            EntityLivingBase mob = spawned.get(i);
            if (mob == null) continue;
            double now = mob.isDead ? 0.0D : mob.getHealth();
            double delta = lastHealth[i] - now;
            // Negative means it healed or was replaced; not damage we dealt.
            if (delta > 0) result.damageDealt += delta;
            lastHealth[i] = now;
        }
    }

    private static void fireArrow(EntityPlayer probe, EntityLivingBase target) {
        // The five-argument constructor is the one skeletons use: it aims at the
        // target rather than at wherever the shooter happens to be facing.
        // Spawning it fires EntityJoinWorldEvent, which is where the bridge tags
        // the arrow with the bow that fired it -- so the bow's enchantments are
        // found later, on hit, exactly as they are in play.
        EntityArrow arrow = new EntityArrow(world, probe, target, 2.0F, 0.0F);
        arrow.setDamage(2.0D);
        world.spawnEntityInWorld(arrow);
    }

    // ---- Defensive cells --------------------------------------------------

    private static void advanceDefense(EntityPlayer probe) {
        if (cellTick % SWING_INTERVAL != 0) return;

        EntityLivingBase attacker = primary();
        if (attacker == null) return;

        faceToward(probe, attacker);

        float before = probe.getHealth();
        probe.hurtResistantTime = 0;   // measure every swing, not one in two
        try {
            // A fixed amount, not attacker.attackEntityAsMob.
            //
            // MobProperties re-rolls every spawn's attackDamage over 1.5x-3x, so
            // asking a mob to hit the probe means each cell is struck by a
            // different opponent from its control. Measured on the first pack
            // run, that put the noise band on armour mitigation at +/-34 points
            // with a systematic +21 offset -- larger than every armour
            // enchantment in the pack, so nothing was measurable and one
            // enchantment that cannot mitigate anything read +17%.
            //
            // The damage source is still the attacker, so anything keyed to being
            // hit by a mob still behaves, and it still goes through
            // attackEntityFrom, so armour points, resistance, Turtle's floor and
            // every custom onDamaged hook apply exactly as in play. What is fixed
            // is only the magnitude -- and how hard the pack's mobs actually hit
            // is a question the mob census already answers, separately, without
            // this variance in the way.
            probe.attackEntityFrom(
                    net.minecraft.util.DamageSource.causeMobDamage(attacker),
                    incomingDamage);
        } catch (Throwable t) {
            result.note = "incoming damage threw: " + describe(t);
            return;
        }

        float taken = Math.max(0F, before - probe.getHealth());
        result.damageTaken += taken;
        result.incomingSwings++;

        if (probe.getHealth() <= 0F || probe.isDead) {
            result.probeDeaths++;
            // Back to full for the next run of hits. hits_survived is the count
            // that reached this point, which is the survivability figure.
            probe.isDead = false;
            probe.deathTime = 0;
            setProbeHealth(probe, DEFENSIVE_HEALTH);
            clearProbeState(probe);
            CensusProbe.wear(probe, armourFor(cell.loadout));
            fillGrantedHealth(probe);
        } else {
            result.hitsSurvived++;
        }
    }

    // ---- Gear -------------------------------------------------------------

    private static ItemStack weaponFor(Loadout loadout, Mode mode) {
        ItemStack stack = (mode == Mode.BOW ? bowTemplate : weaponTemplate).copy();
        for (int i = 0; i < loadout.enchants.size(); i++) {
            stack.addEnchantment(loadout.enchants.get(i), loadout.levels.get(i).intValue());
        }
        return stack;
    }

    /**
     * The armour set for a defensive cell.
     *
     * A slot-locked enchantment goes on its one piece; a per-piece one goes on all
     * four, because that is how it is worn and the compounded figure is the one
     * that matters. {@code category.accepts} makes that decision, so the census
     * and the game agree about it by construction rather than by a list kept in
     * two places.
     */
    private static ItemStack[] armourFor(Loadout loadout) {
        ItemStack[] set = new ItemStack[4];
        for (int i = 0; i < 4; i++) {
            set[i] = armourTemplate[i].copy();
        }
        for (int i = 0; i < loadout.enchants.size(); i++) {
            QFEnchantment ench = loadout.enchants.get(i);
            int level = loadout.levels.get(i).intValue();
            for (int slot = 0; slot < 4; slot++) {
                if (ench.category != null && ench.category.accepts(set[slot])) {
                    set[slot].addEnchantment(ench, level);
                }
            }
        }
        return set;
    }

    // ---- Targets ----------------------------------------------------------

    private static boolean spawnSwarm() {
        despawnAll();
        lastHealth = new double[SWARM];
        for (int i = 0; i < SWARM; i++) {
            EntityLivingBase mob = spawnOne(i);
            spawned.add(mob);
            lastHealth[i] = mob == null ? 0.0D : mob.getHealth();
        }
        return primary() != null;
    }

    private static EntityLivingBase spawnOne(int slot) {
        Class<?> cls = (Class<?>) EntityList.stringToClassMapping.get(cell.targetName);
        if (cls == null || !EntityLivingBase.class.isAssignableFrom(cls)) return null;
        try {
            Constructor<?> ctor = cls.getConstructor(net.minecraft.world.World.class);
            ctor.setAccessible(true);
            EntityLivingBase mob = (EntityLivingBase) ctor.newInstance(world);
            // Spread them out enough that they are distinct targets but well inside
            // Arc's five-block search. The ground height is resolved per slot: a
            // single shared y drops one mob into a hillside, where it suffocates
            // and dies to something that is not the enchantment being measured.
            double x = px + (slot * 2.0D);
            double y = world.getTopSolidOrLiquidBlock((int) x, (int) pz) + 1;
            mob.setPosition(x, y, pz);
            // Spawning is what fires EntityJoinWorldEvent, where this pack rewrites
            // mob stats. A mob measured before that has the wrong health.
            world.spawnEntityInWorld(mob);
            // After spawning, because EntityJoinWorldEvent is where the pack
            // applies its own scaling; pinning before it would be overwritten.
            pinToReference(mob);
            return mob;
        } catch (Throwable t) {
            failures.row(cell.loadout.describe(), cell.targetName, "spawn", describe(t));
            return null;
        }
    }

    /**
     * Holds a freshly spawned target to the run's reference stats for its species.
     * The first one measured sets them. See {@link #REFERENCE}.
     */
    private static void pinToReference(EntityLivingBase mob) {
        try {
            IAttributeInstance health =
                    mob.getEntityAttribute(SharedMonsterAttributes.maxHealth);
            IAttributeInstance attack =
                    mob.getEntityAttribute(SharedMonsterAttributes.attackDamage);
            double[] ref = REFERENCE.get(cell.targetName);

            if (ref == null) {
                // getAttributeValue(), not getBaseValue(). MobProperties applies
                // its scaling as attribute MODIFIERS, so the base is the
                // unmodified vanilla number and reading it captures none of the
                // pack's scaling. The first version of this pinned base to base
                // and therefore did nothing at all, while claiming in a comment
                // that it had fixed the variance.
                Double override = HEALTH_OVERRIDE.get(cell.targetName);
                ref = new double[] {
                        override != null ? override.doubleValue()
                                : (health == null ? Double.NaN : health.getAttributeValue()),
                        attack == null ? Double.NaN : attack.getAttributeValue() };
                REFERENCE.put(cell.targetName, ref);
                QuestForgeContent.log.info("[census] reference target " + cell.targetName
                        + ": maxHealth " + CensusFile.num(ref[0])
                        + ", attackDamage " + CensusFile.num(ref[1])
                        + (override != null ? " (health pinned by request)"
                                            : " (effective, as the pack rolled it)"));
                pinAttribute(health, ref[0]);
                pinAttribute(attack, ref[1]);
            } else {
                pinAttribute(health, ref[0]);
                pinAttribute(attack, ref[1]);
            }
            mob.setHealth(mob.getMaxHealth());
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[census] could not pin target stats: " + t);
        }
    }

    /**
     * Forces an attribute to an exact effective value.
     *
     * Setting the base is not enough while modifiers are attached, so the
     * modifiers are removed first. That is the whole trick, and getting it wrong
     * is silent: the attribute keeps its rolled value and every measurement built
     * on it keeps its variance.
     */
    private static void pinAttribute(IAttributeInstance attr, double value) {
        if (attr == null || Double.isNaN(value)) return;
        try {
            for (Object o : new ArrayList<Object>(attr.func_111122_c())) {
                attr.removeModifier((net.minecraft.entity.ai.attributes.AttributeModifier) o);
            }
        } catch (Throwable ignored) {
            // Mapping differences are not worth failing a run over; the base set
            // below still moves the value in the right direction.
        }
        attr.setBaseValue(value);
    }

    private static void replace(int slot) {
        EntityLivingBase old = spawned.get(slot);
        if (old != null) {
            try {
                old.setDead();
                world.removeEntity(old);
            } catch (Throwable ignored) {}
        }
        EntityLivingBase fresh = spawnOne(slot);
        spawned.set(slot, fresh);
        lastHealth[slot] = fresh == null ? 0.0D : fresh.getHealth();
    }

    private static EntityLivingBase primary() {
        for (EntityLivingBase mob : spawned) {
            if (mob != null && !mob.isDead && mob.getHealth() > 0F) return mob;
        }
        return null;
    }

    /**
     * Removes arrows still in flight.
     *
     * A bow cell looses an arrow every ten ticks and some never hit anything.
     * Left alone they carry their bow's enchantments into the following cells and
     * keep dispatching ARROW_TICK there, which is both a contaminated measurement
     * and a contaminated proc count.
     */
    private static void clearArrows() {
        for (net.minecraft.entity.projectile.EntityArrow arrow
                : com.questforge.content.ench.ArrowTracker.tracked()) {
            try {
                com.questforge.content.ench.ArrowTracker.forget(arrow);
                arrow.setDead();
                if (world != null) world.removeEntity(arrow);
            } catch (Throwable ignored) {}
        }
    }

    private static void despawnAll() {
        clearArrows();
        for (EntityLivingBase mob : spawned) {
            if (mob == null) continue;
            try {
                mob.setDead();
                if (world != null) world.removeEntity(mob);
            } catch (Throwable ignored) {}
        }
        spawned.clear();
    }

    // ---- Finishing a cell -------------------------------------------------

    private static void endCell() {
        if (cell != null && result != null) {
            try {
                collectProcs();
                // MELEE only. A bow cell legitimately reports no landed hits --
                // an arrow damages on impact, not when it is loosed -- and a
                // defensive cell never swings at all, so neither is degenerate.
                if (cell.mode == Mode.MELEE && result.swings > 0 && result.hitsLanded <= 1) {
                    diagnoseCell();
                }
                writeRow();
            } catch (Throwable t) {
                QuestForgeContent.log.error("[census] could not write combat row", t);
            }
        }
        despawnAll();
        EntityPlayer probe = CensusProbe.player(world);
        if (probe != null) {
            clearProbeState(probe);
            CensusProbe.hold(probe, null);
            CensusProbe.wear(probe, null);
        }
        cell = null;
        result = null;
    }

    /**
     * Records the state of every target when a cell produced a degenerate result.
     *
     * A cell where nothing landed is a broken measurement, and the useful thing to
     * write down is not the zero but the reason for it -- which slot was alive,
     * whether the world was ticking it, and what its invulnerability timer was
     * doing.
     */
    private static void diagnoseCell() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < spawned.size(); i++) {
            EntityLivingBase mob = spawned.get(i);
            if (i > 0) sb.append("; ");
            sb.append('[').append(i).append("] ");
            if (mob == null) {
                sb.append("null (spawn failed)");
                continue;
            }
            sb.append("hp=").append(CensusFile.num(mob.getHealth()))
              .append(" dead=").append(mob.isDead)
              .append(" ticks=").append(mob.ticksExisted)
              .append(" iframe=").append(mob.hurtResistantTime)
              .append(" burning=").append(mob.isBurning())
              .append(" inWorld=").append(world.loadedEntityList.contains(mob))
              .append(" y=").append(CensusFile.num(mob.posY));
        }
        failures.row(cell.loadout.describe(), cell.targetName, "degenerate", sb.toString());
    }

    /**
     * The cell's proc totals -- counting only the enchantments the cell is
     * measuring.
     *
     * This used to sum every counter in the tap, which is wrong whenever anything
     * else in the world is still running enchantment code. Arrows left in flight
     * by an earlier bow cell keep dispatching ARROW_TICK for the bow that fired
     * them, once per arrow per tick, and those rolls landed in whatever cell
     * happened to be running. It inflated Poisonous to a reported 98% proc rate
     * against a declared 30%, which reads exactly like a bug in Poisonous. The
     * per-trigger file, which was always keyed by enchantment, showed 29.4% and
     * gave the game away.
     */
    private static void collectProcs() {
        for (EnchantTap.Counts c : EnchantTap.snapshot()) {
            if (!measures(c.enchant)) continue;
            result.procRolls += c.rolls;
            result.procFires += c.fires;
            result.attributedDamage += c.attributedDamage;
        }
    }

    /** Whether this cell's loadout contains the named enchantment. */
    private static boolean measures(String displayKey) {
        for (QFEnchantment e : cell.loadout.enchants) {
            if (e.displayKey().equals(displayKey)) return true;
        }
        return false;
    }

    private static void writeRow() {
        int window = windowFor(cell);
        Result control = CONTROLS.get(controlKey(cell));

        if (cell.loadout.isControl()) {
            CONTROLS.put(controlKey(cell), result);
        }

        QFEnchantment single = cell.loadout.enchants.size() == 1
                ? cell.loadout.enchants.get(0) : null;

        double dps = result.dps(window);
        double marginalDps = Double.NaN;
        double marginalPct = Double.NaN;
        if (control != null && !cell.loadout.isControl()) {
            double base = control.dps(window);
            marginalDps = dps - base;
            marginalPct = base > 0 ? (100.0D * marginalDps / base) : Double.NaN;
        }

        double ttkMean = mean(result.killTicks);
        double marginalTtkPct = Double.NaN;
        if (control != null && !cell.loadout.isControl()) {
            double baseTtk = mean(control.killTicks);
            if (baseTtk > 0 && ttkMean > 0) {
                marginalTtkPct = 100.0D * (baseTtk - ttkMean) / baseTtk;
            }
        }

        double mitigationPct = Double.NaN;
        if (control != null && !cell.loadout.isControl() && cell.mode == Mode.DEFENSE) {
            double basePerHit = control.incomingSwings > 0
                    ? control.damageTaken / control.incomingSwings : 0;
            double perHit = result.incomingSwings > 0
                    ? result.damageTaken / result.incomingSwings : 0;
            if (basePerHit > 0) mitigationPct = 100.0D * (basePerHit - perHit) / basePerHit;
        }

        double observed = result.procRolls == 0
                ? Double.NaN : (100.0D * result.procFires) / result.procRolls;
        double expected = single == null
                ? Double.NaN : single.getProcChance(single.getMaxLevel());

        out.row(
                cell.loadout.describe(),
                cell.loadout.isControl() ? "control" : (cell.stacked ? "stacked" : "isolated"),
                cell.mode,
                single == null ? "" : single.rarity,
                single == null ? "" : String.valueOf(single.getMaxLevel()),
                single == null ? "" : String.valueOf(single.category),
                cell.targetName,
                result.swings,
                result.hitsLanded,
                CensusFile.num(result.damageDealt),
                CensusFile.num(dps),
                CensusFile.num(marginalDps),
                CensusFile.num(marginalPct),
                result.kills,
                CensusFile.num(ttkMean),
                result.killTicks.isEmpty() ? "" : String.valueOf(Collections.min(result.killTicks)),
                result.killTicks.isEmpty() ? "" : String.valueOf(Collections.max(result.killTicks)),
                CensusFile.num(marginalTtkPct),
                CensusFile.num(result.damageTaken),
                result.incomingSwings,
                CensusFile.num(mitigationPct),
                result.hitsSurvived,
                result.procRolls,
                result.procFires,
                CensusFile.num(observed),
                CensusFile.num(expected),
                CensusFile.num(result.attributedDamage),
                result.note + (cell.mode == Mode.MELEE && result.swings > 0
                                && result.hitsLanded <= 1
                        ? " [only " + result.hitsLanded + " of " + result.swings
                          + " swings landed; target invulnerability timer ended at "
                          + result.lastResistTime + ", target ticksExisted "
                          + result.targetTicks + ", in world " + result.targetInWorld + "]"
                        : ""));
    }

    private static String controlKey(Cell c) {
        return c.mode + "/" + c.targetName;
    }

    /**
     * The proc file, written once at the end from the tap's own totals.
     *
     * Deliberately separate from the combat file: this is a correctness check on
     * the enchantments, and mixing it into the balance sheet invites reading a
     * broken proc rate as a design decision.
     */
    private static void writeProcs() {
        for (EnchantTap.Counts c : EnchantTap.totals()) {
            QFEnchantment ench = QFEnchantments.byName(c.enchant);
            double expected = ench == null
                    ? Double.NaN : ench.getProcChance(ench.getMaxLevel());
            procs.row(c.enchant, c.trigger, c.rolls, c.fires,
                    CensusFile.num(c.observedPercent()), CensusFile.num(expected),
                    c.replays, CensusFile.num(c.attributedDamage),
                    CensusFile.num(c.largestSingle));
        }
    }

    // ---- Probe housekeeping -----------------------------------------------

    /**
     * Forgets everything the previous cell taught the probe.
     *
     * The probe is a single reused entity, and the mod's combat memory is keyed on
     * the entity. Without this, a Momentum streak, a Riposte window or a Crushing
     * Blow cooldown earned in one cell is still there at the start of the next,
     * and the contaminated result is indistinguishable from a clean one.
     */
    private static void clearProbeState(EntityPlayer probe) {
        CombatState.forget(probe);
        Cooldowns.forget(probe);
        TickedEffects.forget(probe);
        try {
            probe.clearActivePotions();
        } catch (Throwable ignored) {}
        for (EntityLivingBase mob : spawned) {
            if (mob != null) TickedEffects.forget(mob);
        }
    }

    /**
     * Tops the probe up to whatever its armour just made its maximum.
     *
     * Vigor grants max health as an attribute modifier, which AttributeUpkeep
     * applies on the next tick. Setting health to twenty and then putting the
     * armour on left the probe at twenty of twenty-six: the extra health existed
     * and was never filled, and Vigor measured as identical to nothing for five
     * runs. The upkeep is run here explicitly and the gap closed.
     */
    private static void fillGrantedHealth(EntityPlayer probe) {
        try {
            com.questforge.content.ench.AttributeUpkeep.update(probe);
        } catch (Throwable ignored) {}
        probe.setHealth(probe.getMaxHealth());
    }

    private static void setProbeHealth(EntityPlayer probe, float max) {
        IAttributeInstance attr = probe.getEntityAttribute(SharedMonsterAttributes.maxHealth);
        if (attr != null) attr.setBaseValue(max);
        probe.setHealth(max);
    }

    /** Puts the probe back the way the rest of the census expects to find it. */
    private static void restoreProbe() {
        EntityPlayer probe = CensusProbe.player(world);
        if (probe == null) return;
        clearProbeState(probe);
        CensusProbe.hold(probe, null);
        CensusProbe.wear(probe, null);
        setProbeHealth(probe, PROBE_HEALTH);
    }

    private static void faceToward(EntityPlayer probe, Entity target) {
        double dx = target.posX - probe.posX;
        double dz = target.posZ - probe.posZ;
        probe.rotationYaw = (float) (Math.atan2(dz, dx) * 180.0D / Math.PI) - 90.0F;
        probe.rotationPitch = 0.0F;
    }

    // ---- Small helpers ----------------------------------------------------

    private static double mean(List<Integer> xs) {
        if (xs.isEmpty()) return 0;
        long sum = 0;
        for (Integer x : xs) sum += x.intValue();
        return (double) sum / xs.size();
    }

    private static String describeStack(ItemStack stack) {
        if (stack == null || stack.getItem() == null) return "none";
        try {
            return stack.getDisplayName();
        } catch (Throwable t) {
            return String.valueOf(stack.getItem());
        }
    }

    private static String describe(Throwable t) {
        String message = t.getMessage();
        return t.getClass().getSimpleName() + (message == null ? "" : ": " + message);
    }
}

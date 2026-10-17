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

    /**
     * Health bands an offensive cell sweeps its target through, as shares of max.
     *
     * A real fight takes a boss from full to dead. Measuring only the opening
     * twenty seconds at full health is blind to every enchantment that cares how
     * hurt the target is -- Executioner read zero for that reason -- and says
     * nothing about how long the fight takes. Each band sets the target's health
     * and measures damage per second there; integrating across the bands gives a
     * time-to-kill for the whole fight without spending ten minutes on it.
     */
    private static final float[] BANDS = { 1.00F, 0.75F, 0.50F, 0.25F, 0.10F };
    /** The share of the health bar each band stands for when integrating. */
    private static final float[] BAND_WIDTH = { 0.25F, 0.25F, 0.25F, 0.15F, 0.10F };
    private static final int BAND_TICKS = 160;

    /**
     * Ticks between a mob's melee hits. EntityMob's attackTime is twenty, and the
     * player's own invulnerability window is twenty, so this is also the fastest a
     * full hit can land. The old defensive cadence of ten, with the probe's
     * i-frames zeroed, struck twice as often as anything in the game can.
     */
    private static final int MOB_INTERVAL = 20;

    /**
     * A full-draw bow shot: twenty ticks to charge, velocity 3.0, critical.
     * The old figures -- a shot every ten ticks at velocity 2.0 -- fired twice as
     * often as a person can and each arrow at two-thirds of real speed.
     */
    private static final int BOW_INTERVAL = 20;
    private static final float BOW_VELOCITY = 3.0F;

    /**
     * Spawns sampled to find a target's median stats.
     *
     * Fifteen, because seven put two runs of the same Naga at 1,531 and 1,661
     * health. A campaign split over several servers must fight the same boss on
     * every one of them, so it samples once and passes the result to each shard
     * as Name@health/attack, which skips sampling entirely.
     */
    private static final int REFERENCE_SAMPLES = 15;

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
        /**
         * Targets per cell. One by default, because a boss fight is one target;
         * spawning three bosses gave Arc and every cleave effect two free victims
         * that no player fighting that boss ever has. Raise it for a deliberate
         * group-fight scenario against ordinary mobs.
         */
        public int swarm = 1;
        /** The wielder's health as a share of a real player's twenty, held per band. */
        public float hpFraction = 1.0F;
        /** Measure singles at every level, not only the maximum. */
        public boolean levelsAll;
        /** Control repeats per mode and target; their spread is the noise floor. */
        public int controlReps = 3;
        /** Sweep the target through health bands (offence, single target). */
        public boolean bands = true;
        /** Worn armour for defensive cells, boots first; null = diamond. */
        public ItemStack[] armour;
        /** On a multipart target, the part to strike (e.g. enyvilEye); null = the nearest. */
        public String part;

        public String describe() {
            StringBuilder sb = new StringBuilder();
            if (wounded) sb.append(" wounded");
            if (incoming > 0F) sb.append(" hit=").append(incoming);
            if (pairs) sb.append(" pairs");
            if (triples) sb.append(" triples");
            if (only != null) sb.append(" only=").append(only);
            if (modes != null) sb.append(" modes=").append(modes);
            if (shardCount > 1) sb.append(" shard=").append(shardIndex).append('/').append(shardCount);
            sb.append(" swarm=").append(swarm);
            if (hpFraction < 1.0F) sb.append(" hp=").append(hpFraction);
            if (levelsAll) sb.append(" levels=all");
            sb.append(" controls=").append(controlReps);
            if (!bands) sb.append(" bands=off");
            if (part != null) sb.append(" part=").append(part);
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
        /** Damage dealt inside each health band. */
        final double[] bandDamage = new double[BANDS.length];
        int lastBand = -1;
        /** Mean raw damage of the incoming hits the probe took. */
        double incomingRaw;
        /** Whether the cell's targets have settled and measurement has begun. */
        boolean started;
        int settleWait;
        /** Tick at which the last band's health is checked to have held. */
        int bandCheckTick = -1;
        /** Bands whose health the target undid. Non-zero makes the TTK unreliable. */
        int bandsReverted;
        /** Times a pinned target was found re-scaled by something else and pinned again. */
        int repins;
        /** Times a target was made an InfernalMobs elite and turned back into a plain one. */
        int infernalStripped;
        /** A shielded boss whose shields the census held down; see dropShields. */
        boolean shieldsHeld;
        /** A reflecting boss whose reflection the census held down; see dropReflection. */
        boolean reflectionHeld;
        /**
         * Targets that left the world with health left: a teleport (Lord of
         * Torment at 50%), a despawn, or Forge deleting an entity whose tick threw
         * (removeErroringEntities). Not kills, and not damage dealt.
         */
        int removedAlive;
        /** Attacks on the probe from the arena outside the scheduled hit, cancelled; see blocksAttack. */
        int aiHitsBlocked;
        /** The lowest health the probe stood at during the cell, outside a scheduled hit. */
        float probeHpMin = Float.MAX_VALUE;
        /** Consecutive melee swings that took no health; logged once when it reaches five. */
        int dryStreak;

        double bandDps(int b) {
            return bandDamage[b] / (BAND_TICKS / 20.0D);
        }

        /**
         * Seconds to take the target from full to dead, integrated across the
         * bands. Infinite when any band dealt nothing: a fight that stalls at one
         * health level does not end, whatever the others say.
         */
        double ttkSeconds(double maxHealth) {
            double t = 0;
            for (int b = 0; b < BANDS.length; b++) {
                double dps = bandDps(b);
                if (dps <= 1e-6) return Double.POSITIVE_INFINITY;
                t += BAND_WIDTH[b] * maxHealth / dps;
            }
            return t;
        }

        double dps(int ticks) {
            return ticks <= 0 ? 0 : damageDealt / (ticks / 20.0D);
        }
    }

    // ---- Run state --------------------------------------------------------

    private static boolean running;
    /** Set while the census itself delivers a hit to the probe; see blocksAttack. */
    private static boolean scheduledHit;
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
    /** One line per run each: a boss melee that threw, and a boss that carried the probe. */
    private static boolean incomingThrowLogged, carryLogged;
    private static final Random rand = new Random(0xC0FFEE);

    /** Control results, keyed "mode/target", filled in before the enchanted cells. */
    private static final java.util.Map<String, Result> CONTROLS =
            new java.util.HashMap<String, Result>();

    // Current cell in flight.
    private static Cell cell;

    /**
     * Ticks a fresh spawn is left alone before its stats are read or pinned.
     *
     * MobProperties scales a mob during its first update, not when it is
     * spawned. Every census run before this read a target's stats immediately
     * after spawnEntityInWorld and so saw vanilla numbers: the Naga at 200 health
     * and 6 attack, where the mob census -- which waits a tick -- measures 1,363
     * and 11-17. Worse, pinning at that moment stripped modifiers the pack had not
     * yet added, so it then scaled the "pinned" mob on top. Two ticks is the
     * margin the mob census already uses.
     */
    private static final int SETTLE_TICKS = 2;

    /** Ticks at the start of a cell before anything is measured, so targets settle. */
    private static final int WARMUP = SETTLE_TICKS + 1;

    /** Spawned targets still waiting for their first update before being pinned. */
    private static final java.util.Set<EntityLivingBase> PENDING_PIN =
            java.util.Collections.newSetFromMap(
                    new java.util.IdentityHashMap<EntityLivingBase, Boolean>());

    /** Reference samples in flight, and how long they have existed. */
    private static List<EntityLivingBase> samples;
    private static int sampleAge;
    private static Result result;
    private static int cellTick;
    private static final List<EntityLivingBase> spawned = new ArrayList<EntityLivingBase>();
    /** Entities a target brought with it when spawned (Enyvil's Dark Crystal); removed with it. */
    private static final List<net.minecraft.entity.Entity> companions =
            new ArrayList<net.minecraft.entity.Entity>();
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
        CensusProbe.preferredPart = options.part;
        wounded = options.wounded;
        incomingDamage = options.incoming > 0F ? options.incoming : DEFAULT_INCOMING_DAMAGE;

        world = target;
        configDir = dir;
        index = 0;
        cell = null;
        result = null;
        CONTROLS.clear();
        CONTROL_RUNS.clear();
        REFERENCE.clear();
        HEALTH_OVERRIDE.clear();
        ATTACK_OVERRIDE.clear();
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
        if (options.armour != null) {
            for (int i = 0; i < 4; i++) {
                if (options.armour[i] != null) armourTemplate[i] = options.armour[i].copy();
            }
        }

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
              + (options.hpFraction < 1.0F ? "# WOUNDED RUN: the wielder starts every band at "
                        + CensusFile.num(options.hpFraction * 100) + "% of a twenty-health bar, so "
                        + "enchantments keyed to being hurt can fire. Compare only with a run at "
                        + "the same hp_fraction.\n" : "")
              + "# The wielder has a real player's twenty health. Incoming hits are the target's "
              + "own melee every 20 ticks, absorbed without death; damage-over-time debuffs are "
              + "stripped after each.\n"
              + "# Every spawn of a target is pinned to the median health and attack of "
              + REFERENCE_SAMPLES + " fresh spawns, so each cell fights the same, typical "
              + "opponent as its control. Values are in the log and in target_hp.\n"
              + "# Offensive cells sweep the target through health bands (100/75/50/25/10%); "
              + "band_dps is damage per second in each, and ttk_est_s integrates them into a "
              + "full-fight time to kill. Bows fire a full-draw critical arrow every 20 ticks.",
                new String[] {
                    "loadout", "kind", "mode", "rarity", "level", "category", "target",
                    "swings", "hits_landed", "damage_dealt", "dps", "marginal_dps", "marginal_pct",
                    "kills", "ttk_mean_ticks", "ttk_min_ticks", "ttk_max_ticks", "marginal_ttk_pct",
                    "damage_taken", "incoming_swings", "mitigation_pct", "hits_survived",
                    "proc_rolls", "proc_fires", "observed_proc_pct", "expected_proc_pct",
                    "attributed_damage", "note",
                    "hp_fraction", "band_dps", "ttk_est_s", "marginal_ttk_est_pct", "target_hp",
                    "probe_hp_min", "ai_hits_blocked"
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

        incomingThrowLogged = carryLogged = false;
        EnchantTap.start();
        running = true;
        CensusGuard.register();
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
            // "Zombie@400" pins that target's effective max health to 400;
            // "Zombie@400/9.5" pins its attack as well.
            String name = spec;
            int at = spec.indexOf('@');
            Double override = null;
            Double attack = null;
            if (at > 0) {
                name = spec.substring(0, at);
                String[] parts = spec.substring(at + 1).split("/", 2);
                try {
                    override = Double.valueOf(parts[0]);
                    if (parts.length > 1) attack = Double.valueOf(parts[1]);
                } catch (NumberFormatException e) {
                    failures.row("(target)", spec, "resolve",
                            "override after '@' is not health[/attack]");
                    continue;
                }
            }
            String match = matchEntity(name);
            if (match != null && override != null) {
                HEALTH_OVERRIDE.put(match, override);
                if (attack != null) ATTACK_OVERRIDE.put(match, attack);
                QuestForgeContent.log.info("[census] target " + match
                        + " pinned to " + CensusFile.num(override.doubleValue()) + " health"
                        + (attack != null ? ", " + CensusFile.num(attack.doubleValue())
                        + " attack" : ""));
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

    /** Attack overrides from a "Name@Health/Attack" target spec. */
    private static final java.util.Map<String, Double> ATTACK_OVERRIDE =
            new java.util.HashMap<String, Double>();

    /** Registry lookup that tolerates the case and prefixing differences between mods. */
    private static String matchEntity(String name) {
        if (EntityList.stringToClassMapping.containsKey(name)) return name;
        // "The_King" for "The King": several of this pack's bosses have spaces in
        // their registry names, and an argument list split on whitespace cannot
        // carry one.
        if (name.indexOf('_') >= 0) {
            String spaced = matchEntity(name.replace('_', ' '));
            if (spaced != null) return spaced;
        }
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

        // Controls repeated: the spread between identical controls is the
        // instrument's own noise, measured rather than assumed.
        for (String target : targets) {
            for (Mode mode : new Mode[] { Mode.MELEE, Mode.BOW, Mode.DEFENSE }) {
                if (options.modes != null && !options.modes.contains(mode.name())) continue;
                for (int r = 0; r < Math.max(1, options.controlReps); r++) {
                    cells.add(cell(new Loadout("control"), mode, target, false));
                }
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
            int lowest = options.levelsAll ? 1 : ench.getMaxLevel();
            for (int level = lowest; level <= ench.getMaxLevel(); level++) {
                for (String target : targets) {
                    cells.add(cell(new Loadout(ench.displayKey()).with(ench, level),
                            mode, target, false));
                }
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

        if (samples != null) {
            ++sampleAge;
            boolean all = true;
            for (EntityLivingBase m : samples) all &= settled(m);
            if (all || sampleAge >= SETTLE_TIMEOUT) finishSampling();
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
        if (c.mode == Mode.DEFENSE) return WARMUP + DEFENSIVE_SWINGS * MOB_INTERVAL;
        return WARMUP + (banded() ? BAND_TICKS * BANDS.length : WINDOW_TICKS);
    }

    private static boolean banded() {
        return options.bands && options.swarm == 1;
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
            // A real player's twenty, not a million. The million kept the probe
            // alive but made every enchantment that reads the wielder's health
            // see a full bar, and turned Cultist's self-damage -- capped at a
            // share of max health -- into a rounding error, so Cultist's synergy
            // with Berserk and Riposte was measured on a player nobody is.
            // Incoming hits are absorbed without death instead; see absorbHit.
            setProbeHealth(probe, DEFENSIVE_HEALTH);
            // In the tier's armour, as a player is. Bare, the probe took four
            // times a real player's damage from every boss swing, which is what
            // Riposte, Rage and anything else keyed to being hurt react to.
            CensusProbe.wear(probe, armourFor(c.loadout));
            fillGrantedHealth(probe);
            probe.setHealth(probe.getMaxHealth() * options.hpFraction);
            CensusProbe.hold(probe, weaponFor(c.loadout, c.mode));
        }

        sweepArena();
        if (!REFERENCE.containsKey(c.targetName)
                && HEALTH_OVERRIDE.containsKey(c.targetName)
                && ATTACK_OVERRIDE.containsKey(c.targetName)) {
            // Both given: this is a campaign shard and the reference was sampled
            // once, elsewhere. Sampling again here would fight a different boss.
            REFERENCE.put(c.targetName, new double[] {
                    HEALTH_OVERRIDE.get(c.targetName).doubleValue(),
                    ATTACK_OVERRIDE.get(c.targetName).doubleValue() });
        }
        if (!REFERENCE.containsKey(c.targetName)) {
            startSampling();
            return;
        }
        spawnOrFail();
    }

    private static void spawnOrFail() {
        if (!spawnSwarm()) {
            failures.row(cell.loadout.describe(), cell.targetName, "spawn",
                    "could not spawn " + cell.targetName);
            endCell();
        }
    }

    /**
     * Spawns several of the target and lets them live long enough for the pack
     * to scale them. See SETTLE_TICKS for why reading them at once is wrong.
     */
    private static void startSampling() {
        samples = new ArrayList<EntityLivingBase>();
        sampleAge = 0;
        Class<?> cls = (Class<?>) EntityList.stringToClassMapping.get(cell.targetName);
        for (int i = 0; cls != null && i < REFERENCE_SAMPLES; i++) {
            try {
                Constructor<?> ctor = cls.getConstructor(net.minecraft.world.World.class);
                EntityLivingBase mob = (EntityLivingBase) ctor.newInstance(world);
                double x = px + (i % 3) * 3.0D;
                double z = pz + (i / 3) * 3.0D;
                mob.setPosition(x, world.getTopSolidOrLiquidBlock((int) x, (int) z) + 1, z);
                initialiseAsSpawned(mob);
                world.spawnEntityInWorld(mob);
                samples.add(mob);
            } catch (Throwable ignored) {}
        }
    }

    /** Reads the settled samples' medians, removes them, and starts the cell. */
    private static void finishSampling() {
        List<Double> hp = new ArrayList<Double>();
        List<Double> atk = new ArrayList<Double>();
        for (EntityLivingBase mob : samples) {
            IAttributeInstance h = mob.getEntityAttribute(SharedMonsterAttributes.maxHealth);
            IAttributeInstance a = mob.getEntityAttribute(SharedMonsterAttributes.attackDamage);
            if (h != null) hp.add(Double.valueOf(h.getAttributeValue()));
            if (a != null) atk.add(Double.valueOf(a.getAttributeValue()));
            try {
                mob.setDead();
                world.removeEntity(mob);
            } catch (Throwable ignored) {}
        }
        samples = null;
        sweepArena();   // anything the samples summoned while they lived

        Double override = HEALTH_OVERRIDE.get(cell.targetName);
        if (hp.isEmpty()) {
            failures.row(cell.loadout.describe(), cell.targetName, "reference",
                    "no sample could be spawned");
            endCell();
            return;
        }
        Collections.sort(hp);
        Collections.sort(atk);
        double[] ref = {
                override != null ? override.doubleValue() : hp.get(hp.size() / 2).doubleValue(),
                atk.isEmpty() ? Double.NaN : atk.get(atk.size() / 2).doubleValue() };
        REFERENCE.put(cell.targetName, ref);
        QuestForgeContent.log.info("[census] reference target " + cell.targetName
                + ": median of " + hp.size() + " settled spawns -> maxHealth "
                + CensusFile.num(ref[0]) + " (range " + CensusFile.num(hp.get(0).doubleValue())
                + ".." + CensusFile.num(hp.get(hp.size() - 1).doubleValue()) + "), attackDamage "
                + CensusFile.num(ref[1]) + (atk.isEmpty() ? "" : " (range "
                + CensusFile.num(atk.get(0).doubleValue()) + ".."
                + CensusFile.num(atk.get(atk.size() - 1).doubleValue()) + ")")
                + (override != null ? "; health pinned by request" : ""));
        spawnOrFail();
    }

    /**
     * Removes every non-player creature near the arena.
     *
     * Bosses summon. Rahovart calls minions, Lycanites and TragicMC bosses spawn
     * adds, and despawnAll only knows about the entities the census spawned
     * itself. Without this, a cell's minions are still standing in the next
     * cell, soaking hits and swinging at the probe, and the contamination grows
     * all run.
     */
    /**
     * What every natural spawn, spawn egg and summoning item does and a bare
     * constructor does not: EntityLiving.onSpawnWithEgg. TragicMC's Enyvil builds
     * its Dark Crystal there; without it every hit on Enyvil was halved and its
     * crystal abilities were off (anomalies #1b). DeathReaper and Polaris also
     * initialise there. Called after the position is set and before
     * spawnEntityInWorld, as ItemMonsterPlacer does. Anything it spawns is
     * tracked as a companion and removed with the target.
     */
    private static void initialiseAsSpawned(EntityLivingBase mob) {
        if (!(mob instanceof net.minecraft.entity.EntityLiving)) return;
        try {
            ((net.minecraft.entity.EntityLiving) mob).onSpawnWithEgg(null);
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[census] " + mob.getClass().getSimpleName()
                    + ".onSpawnWithEgg threw; spawned without it: " + describe(t));
        }
    }

    private static void sweepArena() {
        try {
            net.minecraft.util.AxisAlignedBB box = net.minecraft.util.AxisAlignedBB.getBoundingBox(
                    px - 48, py - 24, pz - 48, px + 48, py + 48, pz + 48);
            for (Object o : world.getEntitiesWithinAABB(EntityLivingBase.class, box)) {
                if (o instanceof EntityPlayer) continue;
                EntityLivingBase e = (EntityLivingBase) o;
                e.setDead();
                world.removeEntity(e);
            }
        } catch (Throwable ignored) {}
    }

    private static void advance() {
        EntityPlayer probe = CensusProbe.player(world);
        if (probe == null) return;

        // Nothing is measured until this cell's targets have been scaled and
        // pinned: a fight against a mob the pack has not finished with yet is a
        // fight against vanilla stats.
        pinPending();
        if (result.started) {
            keepPinned();
            leash();
        }
        if (!result.started) {
            if (!PENDING_PIN.isEmpty() && result.settleWait++ < SETTLE_TIMEOUT) return;
            if (!PENDING_PIN.isEmpty()) result.note += " [targets never settled; measured unscaled]";
            result.started = true;
        }
        cellTick++;

        // The probe experiences a tick. Without this the mod's per-tick code never
        // runs for it; see CensusProbe.pumpTick.
        CensusProbe.pumpTick(probe);
        if (cellTick <= WARMUP) return;

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
        // So drift in the wielder's health can never hide again.
        result.probeHpMin = Math.min(result.probeHpMin, probe.getHealth());
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
        // Two chunks each way: the flattened arena reaches ARENA_RADIUS from the
        // centre, which can straddle three chunks on either side of it.
        for (int dx = -2; dx <= 2; dx++) {
            for (int dz = -2; dz <= 2; dz++) {
                ForgeChunkManager.forceChunk(arenaTicket, new ChunkCoordIntPair(cx + dx, cz + dz));
            }
        }
        QuestForgeContent.log.info("[census] arena chunks force-loaded around " + cx + "," + cz);
        flattenArena();
    }

    /** Half-width of the flattened arena: leash plus bow standoff, with margin. */
    private static final int ARENA_RADIUS = 26;
    /** Clear air above the floor; Mobzilla is twenty-five blocks tall. */
    private static final int ARENA_HEADROOM = 40;

    /**
     * Levels the arena to a stone floor with open air above.
     *
     * The census used to fight on whatever the world generated at spawn. A bow
     * cell kited onto a hillside and every arrow buried itself in the slope four
     * blocks out: zero damage, measured as the bow being worthless. Trees, water
     * and slopes also differ between nodes, each of which generates its own
     * world. A level floor gives every cell, mode and node the same ground and
     * every archer a line of sight, which is how a boss arena is built anyway.
     */
    private static void flattenArena() {
        int x0 = (int) Math.floor(px), z0 = (int) Math.floor(pz), y0 = (int) Math.floor(py);
        net.minecraft.block.Block stone = net.minecraft.init.Blocks.stone;
        net.minecraft.block.Block air = net.minecraft.init.Blocks.air;
        for (int x = x0 - ARENA_RADIUS; x <= x0 + ARENA_RADIUS; x++) {
            for (int z = z0 - ARENA_RADIUS; z <= z0 + ARENA_RADIUS; z++) {
                for (int y = y0 - 3; y < y0; y++) world.setBlock(x, y, z, stone, 0, 2);
                for (int y = y0; y < y0 + ARENA_HEADROOM && y < 256; y++) {
                    if (!world.isAirBlock(x, y, z)) world.setBlock(x, y, z, air, 0, 2);
                }
            }
        }
        QuestForgeContent.log.info("[census] arena flattened: " + (2 * ARENA_RADIUS + 1) + " blocks square"
                + " at y " + y0);
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
        // Band change: put the target at this band's share of its health. The
        // drop is not damage dealt, so the sampler's baseline moves with it.
        int band = banded()
                ? Math.min(BANDS.length - 1, (cellTick - WARMUP - 1) / BAND_TICKS) : -1;
        if (band >= 0 && band != result.lastBand) {
            result.lastBand = band;
            EntityLivingBase target = primary();
            if (target != null) setBandHealth(target, band);
            // The wielder starts each band at the run's health share. Within a
            // band it is left alone, so Cultist's self-damage accumulates as it
            // would in a fight.
            probe.setHealth(probe.getMaxHealth() * options.hpFraction);
        }

        double before = result.damageDealt;
        accumulateDamage();
        if (band >= 0) result.bandDamage[band] += result.damageDealt - before;

        // A target that died: record the kill, then put a fresh one in its place so
        // the window keeps measuring instead of trailing off into an empty arena.
        for (int i = 0; i < spawned.size(); i++) {
            EntityLivingBase mob = spawned.get(i);
            if (mob == null || !mob.isDead && mob.getHealth() > 0F) continue;

            // Dead only if its health truly reached zero. A target removed with
            // health left was not killed: counting it as one booked its whole
            // remaining health as damage, which is how the EnderDemon "died" to
            // every swing and Lord of Torment's lower bands read as instant kills.
            if (mob.getHealth() > 0F && mob.deathTime <= 0) {
                if (result.removedAlive++ == 0) {
                    QuestForgeContent.log.warn("[census] " + cell.targetName + " (id " + mob.getEntityId()
                            + ") left the world alive at cell tick " + cellTick + ", health "
                            + CensusFile.num(mob.getHealth()) + "/" + CensusFile.num(mob.getMaxHealth())
                            + "; not a kill (logged once per cell)");
                }
                if (i == 0) trialStartTick = cellTick;
                replace(i);
                if (band >= 0 && i == 0 && spawned.get(0) != null) {
                    setBandHealth(spawned.get(0), band);
                }
                continue;
            }

            result.kills++;
            if (i == 0) {
                result.killTicks.add(Integer.valueOf(cellTick - trialStartTick));
                trialStartTick = cellTick;
            }
            replace(i);
            if (band >= 0 && i == 0 && spawned.get(0) != null) {
                setBandHealth(spawned.get(0), band);
            }
        }

        // Within a band the target is held at the band's health: whatever a hit
        // took is counted above, then given back. Without this the low bands kill
        // the target part-way through, and the respawn -- which must wait for the
        // pack to scale it before it can be hit -- is counted as time spent dealing
        // nothing, which understates exactly the enchantments that care about a
        // nearly dead boss. Only a drop is undone; a boss healing back up is left
        // for the reversion check to report.
        if (band >= 0) {
            EntityLivingBase target = primary();
            if (target != null && !PENDING_PIN.contains(target)
                    && target.getHealth() < target.getMaxHealth() * BANDS[band] - 0.01F) {
                holdHealth(target, target.getMaxHealth() * BANDS[band]);
            }
        }

        // A band whose health did not hold was not measured at that health. Some
        // bosses actively undo large health drops (see setBandHealth), and the
        // figures for a band that silently reverted to full would be reported
        // as if they described a nearly dead boss.
        if (band >= 0 && result.bandCheckTick == cellTick) {
            EntityLivingBase target = primary();
            if (target != null) {
                float wanted = target.getMaxHealth() * BANDS[band];
                if (target.getHealth() > wanted * 1.05F + 1.0F) result.bandsReverted++;
            }
        }

        int interval = cell.mode == Mode.BOW ? BOW_INTERVAL : SWING_INTERVAL;
        if (cellTick % interval == 0) {
            EntityLivingBase primary = primary();
            if (primary != null && !PENDING_PIN.contains(primary)) {
                faceToward(probe, primary);
                float healthBefore = primary.getHealth();
                if (cell.mode == Mode.BOW) {
                    kite(probe, primary);
                    fireArrow(probe, primary);
                } else {
                    chase(probe, primary);
                    // Not attackTargetEntityWithCurrentItem directly: in this pack
                    // a mod cancels the attack event outright. See CensusProbe.swing.
                    CensusProbe.swing(probe, primary);
                }
                result.swings++;
                if (result.swings == 1 && cell.mode == Mode.MELEE) {
                    logFirstSwing(probe, healthBefore - primary.getHealth());
                }
                if (primary.getHealth() < healthBefore) {
                    result.hitsLanded++;
                    result.dryStreak = 0;
                } else if (cell.mode == Mode.MELEE && ++result.dryStreak == 5) {
                    logDryStreak(probe, primary);
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
        if (cellTick % MOB_INTERVAL == 0) {
            EntityLivingBase primary = primary();
            // Only within the boss's reach. A kiting archer is not struck every
            // second; one standing in melee is.
            if (primary != null && probe.getDistanceToEntity(primary) <= 3.0F + primary.width) {
                absorbHit(probe, primary);
            }
        }

        // A last guard, for damage that does not come through absorbHit -- a boss
        // that reflects melee, an aura. A dead probe ends a measurement in the
        // middle, and a probe at zero is not the health the run asked for.
        if (probe.getHealth() < 1.0F) probe.setHealth(1.0F);
    }

    /**
     * Whether the pack has finished scaling this mob.
     *
     * MobProperties does not scale on spawn. It marks the mob ("MP|Init" = -1 in
     * its entity data) and queues it, then works through that queue at most nine
     * mobs per server tick. In a hundred-mod world that queue has a backlog, so a
     * fixed wait is a guess; the mob is settled when the mod says so (a positive
     * flag), or when the mod never queued it at all and it has lived a couple of
     * ticks. Every census run before this read stats before that happened and
     * fought bosses at their vanilla health.
     */
    private static boolean settled(EntityLivingBase mob) {
        byte init;
        try {
            init = mob.getEntityData().getByte("MP|Init");
        } catch (Throwable t) {
            init = 0;
        }
        if (init > 0) return true;
        return init == 0 && mob.ticksExisted >= SETTLE_TICKS;
    }

    /** Ticks to wait for the pack's scaling before measuring regardless. */
    private static final int SETTLE_TIMEOUT = 400;

    /**
     * Re-pins a target whose stats something changed after it was pinned.
     *
     * One control in three of a pilot fought a Naga at 203 health against a
     * reference of 1,661 -- the pack's vanilla number -- and dealt a fifth of the
     * damage. Whatever re-scales a mob after the census has pinned it, the row it
     * produces is about a different opponent. So the pin is checked every tick
     * and restored, keeping the target's share of its health, and the first time
     * it happens the target's modifiers are logged so the cause can be found.
     */
    private static void keepPinned() {
        double[] ref = REFERENCE.get(cell.targetName);
        if (ref == null || Double.isNaN(ref[0]) || ref[0] <= 0) return;
        for (int i = 0; i < spawned.size(); i++) {
            EntityLivingBase mob = spawned.get(i);
            if (mob == null || mob.isDead || PENDING_PIN.contains(mob)) continue;
            dropShields(mob);
            dropReflection(mob);
            if (stripInfernal(mob)) {
                result.infernalStripped++;
                QuestForgeContent.log.info("[census] " + cell.targetName + " (id " + mob.getEntityId()
                        + ") was made an InfernalMobs elite at cell tick " + cellTick + "; stripped");
            }
            if (Math.abs(mob.getMaxHealth() - ref[0]) <= 0.01D * ref[0]) continue;
            if (result.repins++ == 0) {
                StringBuilder mods = new StringBuilder();
                IAttributeInstance h = mob.getEntityAttribute(SharedMonsterAttributes.maxHealth);
                if (h != null) {
                    mods.append("base ").append(CensusFile.num(h.getBaseValue()));
                    for (Object o : h.func_111122_c()) {
                        net.minecraft.entity.ai.attributes.AttributeModifier m =
                                (net.minecraft.entity.ai.attributes.AttributeModifier) o;
                        mods.append("; ").append(m.getName()).append(" op").append(m.getOperation())
                                .append(' ').append(CensusFile.num(m.getAmount()));
                    }
                }
                byte init = 0;
                try { init = mob.getEntityData().getByte("MP|Init"); } catch (Throwable ignored) {}
                QuestForgeContent.log.warn("[census] " + cell.targetName + " (id " + mob.getEntityId()
                        + ", age " + mob.ticksExisted + ", MP|Init " + init + ") re-scaled after pinning: max health "
                        + CensusFile.num(mob.getMaxHealth()) + " vs " + CensusFile.num(ref[0])
                        + " at cell tick " + cellTick + " [" + mods + "]");
            }
            float share = mob.getMaxHealth() > 0F ? mob.getHealth() / mob.getMaxHealth() : 1F;
            pinToReference(mob);
            if (i == 0) {
                holdHealth(mob, mob.getMaxHealth() * share);
            } else if (i < lastHealth.length) {
                mob.setHealth(mob.getMaxHealth() * share);
                lastHealth[i] = mob.getHealth();
            }
        }
    }

    /** Blocks from the arena centre a target may wander before it is brought back. */
    private static final double LEASH = 12.0D;

    /**
     * Keeps targets within reach of the probe.
     *
     * The probe stands still; a player does not -- they follow the boss. Left
     * alone, a pilot's Naga crawled 106 blocks off, out of the force-loaded arena
     * chunks, and stopped being ticked: its hurt timer froze mid-countdown and
     * invulnerability frames swallowed every swing for the rest of the cell, which
     * read as the last two health bands dealing nothing. Bringing it back is what
     * the player chasing it amounts to.
     */
    private static void leash() {
        for (EntityLivingBase mob : spawned) {
            if (mob == null || mob.isDead) continue;
            double dx = mob.posX - px, dz = mob.posZ - pz;
            if (dx * dx + dz * dz <= LEASH * LEASH) continue;
            double x = px + 3.0D, z = pz;
            mob.setPositionAndUpdate(x, py, z);
            mob.motionX = mob.motionY = mob.motionZ = 0;
        }
    }

    /**
     * What the probe brought to the first swing of a cell: its attack and every
     * modifier and effect behind it. Identical controls must show identical lines;
     * a modifier or effect that appears in some and not others is state leaking
     * between cells.
     */
    private static void logFirstSwing(EntityPlayer probe, float dealt) {
        StringBuilder sb = new StringBuilder();
        IAttributeInstance a = probe.getEntityAttribute(SharedMonsterAttributes.attackDamage);
        if (a != null) {
            sb.append("attack ").append(CensusFile.num(a.getAttributeValue()))
              .append(" (base ").append(CensusFile.num(a.getBaseValue()));
            for (Object o : a.func_111122_c()) {
                net.minecraft.entity.ai.attributes.AttributeModifier m =
                        (net.minecraft.entity.ai.attributes.AttributeModifier) o;
                sb.append("; ").append(m.getName()).append(" op").append(m.getOperation())
                  .append(' ').append(CensusFile.num(m.getAmount()));
            }
            sb.append(')');
        }
        sb.append(", effects [");
        for (Object o : probe.getActivePotionEffects()) {
            net.minecraft.potion.PotionEffect e = (net.minecraft.potion.PotionEffect) o;
            sb.append(e.getEffectName()).append(" x").append(e.getAmplifier() + 1)
              .append(' ').append(e.getDuration()).append("t ");
        }
        sb.append("], dealt ").append(CensusFile.num(dealt));
        QuestForgeContent.log.info("[census] first swing of " + cell.loadout.describe() + " "
                + cell.mode + ": " + sb);
    }

    /**
     * Which LivingHurtEvent listener changes a player's hit on this target.
     *
     * A synthetic eight-damage player hit is handed to each listener in bus
     * order and every change to the amount is logged with its owner. Diagnostic:
     * listeners may act on the event (heal, apply effects), so nothing calls it
     * in a measuring run. It found KillerPacman's WeaponScaler (every non-OreSpawn
     * melee hit x1-4) and InfernalMobs zeroing a hit on an elite.
     */
    private static void walkHurtListeners(EntityPlayer probe, EntityLivingBase target) {
        StringBuilder sb = new StringBuilder();
        try {
            net.minecraftforge.event.entity.living.LivingHurtEvent ev =
                    new net.minecraftforge.event.entity.living.LivingHurtEvent(
                            target, net.minecraft.util.DamageSource.causePlayerDamage(probe), 8.0F);
            java.lang.reflect.Field f = cpw.mods.fml.common.eventhandler.EventBus.class
                    .getDeclaredField("busID");
            f.setAccessible(true);
            int bus = f.getInt(net.minecraftforge.common.MinecraftForge.EVENT_BUS);
            float last = ev.ammount;
            for (cpw.mods.fml.common.eventhandler.IEventListener l
                    : ev.getListenerList().getListeners(bus)) {
                try {
                    l.invoke(ev);
                } catch (Throwable t) {
                    sb.append(" {").append(l).append(" threw ").append(t).append('}');
                }
                if (ev.ammount != last) {
                    sb.append(" {").append(l).append(": ").append(CensusFile.num(last))
                      .append(" -> ").append(CensusFile.num(ev.ammount)).append('}');
                    last = ev.ammount;
                }
                if (ev.isCanceled()) {
                    sb.append(" {cancelled by ").append(l).append('}');
                    break;
                }
            }
            sb.insert(0, "final " + CensusFile.num(ev.ammount) + ";");
        } catch (Throwable t) {
            sb.append("walk failed: ").append(t);
        }
        net.minecraft.item.ItemStack held = probe.getHeldItem();
        QuestForgeContent.log.info("[census] hurt listeners on " + cell.targetName + " (band "
                + result.lastBand + ", held " + (held == null ? "nothing" : held.getItem().getClass().getName())
                + ", rand " + world.rand.getClass().getName() + "): " + sb);
    }

    /** Why a target that was taking hits has stopped: where everyone is, and its guards. */
    private static void logDryStreak(EntityPlayer probe, EntityLivingBase target) {
        String home = "";
        if (target instanceof net.minecraft.entity.EntityCreature) {
            net.minecraft.entity.EntityCreature c = (net.minecraft.entity.EntityCreature) target;
            net.minecraft.util.ChunkCoordinates h = c.getHomePosition();
            home = ", hasHome " + c.hasHome() + (h == null ? "" : " at " + h.posX + "," + h.posY
                    + "," + h.posZ) + " radius " + c.func_110174_bM()
                    + ", probe inside " + c.isWithinHomeDistance(
                    (int) Math.floor(probe.posX), (int) Math.floor(probe.posY),
                    (int) Math.floor(probe.posZ));
        }
        QuestForgeContent.log.warn("[census] " + cell.targetName + " stopped taking hits at cell tick "
                + cellTick + ": health " + CensusFile.num(target.getHealth()) + "/"
                + CensusFile.num(target.getMaxHealth()) + ", hurtResist " + target.hurtResistantTime
                + ", probe at " + CensusFile.num(probe.posX) + "," + CensusFile.num(probe.posY) + ","
                + CensusFile.num(probe.posZ) + ", target at " + CensusFile.num(target.posX) + ","
                + CensusFile.num(target.posY) + "," + CensusFile.num(target.posZ) + ", distance "
                + CensusFile.num(probe.getDistanceToEntity(target)) + home);
    }

    /**
     * Keeps a shielded boss's shields down.
     *
     * The Twilight Lich ignores every hit while its shields are up, and only
     * unblockable damage over two -- its own bolts, reflected -- breaks them.
     * The census cannot reflect a bolt, so a whole run measured nothing. A
     * player's weapon does its work after the shields are gone, so that is the
     * phase measured: any boss with a setShieldStrength(int) is held at zero.
     */
    private static void dropShields(EntityLivingBase mob) {
        try {
            java.lang.reflect.Method m = mob.getClass().getMethod("setShieldStrength", int.class);
            m.invoke(mob, Integer.valueOf(0));
            if (result != null && !result.shieldsHeld) {
                result.shieldsHeld = true;
                result.note += " [shields held down: the post-shield phase is measured]";
            }
        } catch (NoSuchMethodException ignored) {
        } catch (Throwable ignored) {}
    }

    /**
     * Keeps a reflecting boss in its vulnerable phase.
     *
     * TragicMC's Apis alternates 160 ticks of reflection (it takes no damage and
     * throws half of it back) with 160 vulnerable ticks. The census's bands are
     * also 160 ticks, so whether a band sat in a reflect window was a phase
     * lottery: controls ran 293-786 s, noise +/-92% (anomalies #3). As with the
     * Lich's shields, the phase where a weapon does its work is the one
     * measured: any boss with a private setReflectionTicks(int) is held at zero,
     * and its public reflectionBuffer (the vulnerable countdown) kept full so the
     * next reflect never starts. A real fight takes about twice as long, waiting
     * out the reflect.
     */
    private static void dropReflection(EntityLivingBase mob) {
        Class<?> c = mob.getClass();
        java.lang.reflect.Method m = null;
        for (Class<?> k = c; k != null && m == null; k = k.getSuperclass()) {
            try {
                m = k.getDeclaredMethod("setReflectionTicks", int.class);
            } catch (NoSuchMethodException ignored) {}
        }
        if (m == null) return;
        try {
            m.setAccessible(true);
            m.invoke(mob, Integer.valueOf(0));
            try {
                java.lang.reflect.Field buffer = c.getField("reflectionBuffer");
                if (buffer.getType() == int.class) buffer.setInt(mob, 160);
            } catch (NoSuchFieldException ignored) {}
            if (result != null && !result.reflectionHeld) {
                result.reflectionHeld = true;
                result.note += " [reflection held down: the vulnerable phase is measured]";
            }
        } catch (Throwable ignored) {}
    }

    private static java.lang.reflect.Method infernalIsRare, infernalRemove;
    private static boolean infernalLooked;

    /**
     * Turns an InfernalMobs elite back into a plain mob. True if it was one.
     *
     * InfernalMobs makes one spawn in fifteen an elite: it rewrites the base
     * health (a pilot's Naga went from 1,661 to 203 mid-fight) and attaches
     * modifiers -- Bulwark, Regen, 1UP, Vengeance -- that change how every hit
     * lands; one zeroed a hit outright. Elites are real, but they are a lottery
     * on top of the boss, and a cell that drew one measured the lottery rather
     * than the enchantment. So the census always fights the plain boss.
     */
    private static boolean stripInfernal(EntityLivingBase mob) {
        if (!infernalLooked) {
            infernalLooked = true;
            try {
                Class<?> core = Class.forName("atomicstryker.infernalmobs.common.InfernalMobsCore");
                infernalIsRare = core.getMethod("getIsRareEntity", EntityLivingBase.class);
                infernalRemove = core.getMethod("removeEntFromElites", EntityLivingBase.class);
            } catch (Throwable ignored) {}
        }
        if (infernalIsRare == null) return false;
        try {
            if (!((Boolean) infernalIsRare.invoke(null, mob)).booleanValue()) return false;
            infernalRemove.invoke(null, mob);
            mob.getEntityData().removeTag("InfernalMobsMod");
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    /** Pins every spawned target that has now been through the pack's scaling. */
    private static void pinPending() {
        for (int i = 0; i < spawned.size(); i++) {
            EntityLivingBase mob = spawned.get(i);
            if (mob == null || !PENDING_PIN.contains(mob)) continue;
            if (!settled(mob) && mob.ticksExisted < SETTLE_TIMEOUT) continue;
            if (stripInfernal(mob) && result != null) result.infernalStripped++;
            pinToReference(mob);
            PENDING_PIN.remove(mob);
            if (i < lastHealth.length) lastHealth[i] = mob.getHealth();
            if (banded() && i == 0 && result != null && result.lastBand >= 0
                    && cell.mode != Mode.DEFENSE) {
                setBandHealth(mob, result.lastBand);
            }
        }
    }

    /**
     * Puts a target at a band's share of its health, and makes it stay there.
     *
     * Rahovart (Lycanites) remembers its health from the previous tick and, if it
     * has lost more than fifty since, sets it straight back -- its defence against
     * one-shot weapons. A census lowering it to seventy-five per cent is exactly
     * such a drop and would be undone a tick later. So any field named
     * healthLastTick is moved along with the health. Bosses with a different
     * mechanism are caught by the reversion check in advanceOffense instead of
     * being guessed at here.
     */
    private static void setBandHealth(EntityLivingBase target, int band) {
        holdHealth(target, target.getMaxHealth() * BANDS[band]);
        result.bandCheckTick = cellTick + 2;
    }

    /** Sets the target's health without it counting as damage, past healthLastTick guards. */
    private static void holdHealth(EntityLivingBase target, float health) {
        target.setHealth(health);
        for (Class<?> c = target.getClass(); c != null && c != Object.class; c = c.getSuperclass()) {
            try {
                java.lang.reflect.Field f = c.getDeclaredField("healthLastTick");
                f.setAccessible(true);
                if (f.getType() == float.class) f.setFloat(target, target.getHealth());
            } catch (NoSuchFieldException ignored) {
            } catch (Throwable ignored) {
                break;
            }
        }
        lastHealth[0] = target.getHealth();
    }

    /**
     * The target's real melee hit, taken without the probe dying of it.
     *
     * The hit is real -- attackEntityAsMob, the mob's own pinned attack, its
     * knockback, the debuffs it applies on hit -- so the wielder is "hurt
     * recently" exactly when a boss would have hurt them and is Weakened when a
     * boss would have Weakened them. What is not real is death: this pack's
     * bosses hit for twenty-five and up, and a twenty-health player dies to the
     * first swing. So the probe's health is lifted for the instant of the hit and
     * put back afterwards. The offensive cell measures what the wielder deals,
     * at a controlled health; how long they survive is the defensive cell's job.
     *
     * Damage-over-time debuffs are stripped afterwards for the same reason: a
     * Wither applied to a twenty-health probe ends the cell, where a real player
     * drinks milk or heals.
     */
    /**
     * Whether an attack on the probe must be cancelled (CensusGuard calls this
     * from LivingAttackEvent).
     *
     * The probe's health is a control: each band sets it to the run's
     * hp_fraction, and incoming damage is delivered on a schedule (absorbHit,
     * advanceDefense) and undone. A boss's own AI melee was neither: it wore the
     * probe down between scheduled hits, so a run claiming full health measured
     * a wielder sliding to 1 HP. That gave Berserk 824 attributed damage on the
     * Naga at hp_fraction 1.0, and turned DeathReaper's armour on (anomalies
     * #5c). So while a cell runs, any attack on the probe that comes from
     * another entity and not from the census's own scheduled hit is cancelled.
     * Self-inflicted damage (Cultist's blood price) and sourceless damage pass.
     */
    public static boolean blocksAttack(EntityLivingBase victim, net.minecraft.util.DamageSource source) {
        if (!running || scheduledHit || cell == null || result == null || source == null) return false;
        if (victim == null || victim != CensusProbe.current()) return false;
        net.minecraft.entity.Entity from = source.getEntity();
        if (from == null || from == victim) return false;
        if (result.aiHitsBlocked++ == 0) {
            QuestForgeContent.log.info("[census] " + cell.targetName + "'s own attack (" + source.getDamageType()
                    + " from " + from.getClass().getSimpleName() + ") on the probe cancelled at cell tick "
                    + cellTick + ": only the scheduled hit lands (logged once per cell)");
        }
        return true;
    }

    private static void absorbHit(EntityPlayer probe, EntityLivingBase attacker) {
        IAttributeInstance max = probe.getEntityAttribute(SharedMonsterAttributes.maxHealth);
        float held = probe.getHealth();
        double heldMax = max == null ? DEFENSIVE_HEALTH : max.getBaseValue();
        // Back to where it stood, not to melee range: an archer knocked about by
        // a boss is still an archer.
        double hx = probe.posX, hy = probe.posY, hz = probe.posZ;
        try {
            if (max != null) max.setBaseValue(PROBE_HEALTH);
            probe.setHealth(PROBE_HEALTH);
            float before = probe.getHealth();
            scheduledHit = true;
            try {
                attacker.attackEntityAsMob(probe);
            } catch (Throwable t) {
                // Still swallowed -- a boss's swing must not end the cell -- but
                // no longer silently. A throw here abandons the rest of the
                // boss's attack, so its damage is missing from the row; the
                // Alpha Yeti's swing was lost this way, unseen, until the same
                // fault crashed the server from the Yeti's own tick.
                if (!incomingThrowLogged) {
                    incomingThrowLogged = true;
                    QuestForgeContent.log.warn("[census] " + cell.targetName
                            + "'s melee threw on the probe (logged once per run): " + describe(t), t);
                }
            } finally {
                scheduledHit = false;
            }
            if (probe.ridingEntity == attacker && !carryLogged) {
                carryLogged = true;
                QuestForgeContent.log.info("[census] " + cell.targetName + " picked the probe up"
                        + " (cell tick " + cellTick + "); it is carried and thrown as a player is");
            }
            result.damageTaken += Math.max(0F, before - probe.getHealth());
            result.incomingSwings++;
        } finally {
            if (max != null) max.setBaseValue(heldMax);
            probe.setHealth(held);
            probe.setPosition(hx, hy, hz);
            probe.motionX = probe.motionY = probe.motionZ = 0;
            int[] damaging = { net.minecraft.potion.Potion.poison.id,
                    net.minecraft.potion.Potion.wither.id, net.minecraft.potion.Potion.harm.id };
            for (int id : damaging) {
                if (probe.isPotionActive(id)) probe.removePotionEffect(id);
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
            // A target removed with health left lost nothing to us; see advanceOffense.
            double now = !mob.isDead ? mob.getHealth()
                    : mob.getHealth() > 0F && mob.deathTime <= 0 ? lastHealth[i] : 0.0D;
            double delta = lastHealth[i] - now;
            // Negative means it healed or was replaced; not damage we dealt.
            if (delta > 0) result.damageDealt += delta;
            lastHealth[i] = now;
        }
    }

    /**
     * Steps the archer back to its standoff before a shot.
     *
     * Bosses close the distance. A pilot's Mantis sat on top of the probe, so
     * arrows spawned inside its hitbox and most passed through. A player with a
     * bow backs off; this does it for them.
     */
    private static void kite(EntityPlayer probe, EntityLivingBase target) {
        if (probe.getDistanceToEntity(target) >= BOW_STANDOFF * 0.6D) return;
        double x = target.posX + BOW_STANDOFF, z = target.posZ;
        probe.setPosition(x, py, z);
        probe.motionX = probe.motionY = probe.motionZ = 0;
    }

    /**
     * Keeps a melee fighter within reach, as a player follows a boss. The swing
     * itself would land from anywhere; the boss's hits back would not.
     */
    private static void chase(EntityPlayer probe, EntityLivingBase target) {
        double reach = 1.5D + target.width * 0.5D;
        if (probe.getDistanceToEntity(target) <= reach + 1.0D) return;
        double x = target.posX + reach, z = target.posZ;
        probe.setPosition(x, py, z);
        probe.motionX = probe.motionY = probe.motionZ = 0;
    }

    /** The previous arrow loosed, for the first shots' diagnostic line. */
    private static EntityArrow lastArrow;

    private static void fireArrow(EntityPlayer probe, EntityLivingBase target) {
        // The five-argument constructor is the one skeletons use: it aims at the
        // target rather than at wherever the shooter happens to be facing.
        // Spawning it fires EntityJoinWorldEvent, which is where the bridge tags
        // the arrow with the bow that fired it -- so the bow's enchantments are
        // found later, on hit, exactly as they are in play.
        EntityArrow arrow = new EntityArrow(world, probe, target, BOW_VELOCITY, 0.0F);
        // But not its heading. That constructor lofts the shot by a fifth of the
        // horizontal distance, which is right for a skeleton's 1.6 and sends a
        // 3.0 arrow over the target: a pilot's bow control landed 22 damage in
        // forty seconds. A full-draw arrow drops a few centimetres over a fight's
        // range, so it is aimed at the body's centre, led by the target's motion
        // over the flight time -- what a player aiming at a boss does.
        double dx = target.posX - arrow.posX;
        double dz = target.posZ - arrow.posZ;
        double dy = target.boundingBox.minY + target.height * 0.5D - arrow.posY;
        double flight = Math.sqrt(dx * dx + dy * dy + dz * dz) / BOW_VELOCITY;
        dx += target.motionX * flight;
        dz += target.motionZ * flight;
        dy += 0.025D * flight * flight;   // half of gravity's 0.05 per tick squared
        arrow.setThrowableHeading(dx, dy, dz, BOW_VELOCITY, 0.0F);
        if (lastArrow != null && result.swings <= 3) {
            QuestForgeContent.log.info("[census] arrow " + result.swings + " at " + cell.targetName
                    + ": now at " + CensusFile.num(lastArrow.posX) + "," + CensusFile.num(lastArrow.posY)
                    + "," + CensusFile.num(lastArrow.posZ) + " dead " + lastArrow.isDead
                    + "; fired from " + CensusFile.num(arrow.posX) + "," + CensusFile.num(arrow.posY) + ","
                    + CensusFile.num(arrow.posZ) + " at target " + CensusFile.num(target.posX) + ","
                    + CensusFile.num(target.posY) + "," + CensusFile.num(target.posZ) + " size "
                    + CensusFile.num(target.width) + "x" + CensusFile.num(target.height)
                    + ", target health " + CensusFile.num(target.getHealth()));
        }
        lastArrow = arrow;
        arrow.setDamage(2.0D);
        // ItemBow.onPlayerStoppedUsing sets this for a full draw, and it is a
        // large share of a bow's real damage.
        arrow.setIsCritical(true);
        world.spawnEntityInWorld(arrow);
    }

    // ---- Defensive cells --------------------------------------------------

    private static void advanceDefense(EntityPlayer probe) {
        if (cellTick % MOB_INTERVAL != 0) return;

        EntityLivingBase attacker = primary();
        if (attacker == null) return;

        faceToward(probe, attacker);

        float before = probe.getHealth();
        // The probe's invulnerability frames are respected, not zeroed. At the
        // mob's own twenty-tick cadence they have just expired when each hit
        // arrives, which is what happens to a player standing in melee.
        if (options.incoming <= 0F) {
            // The target's own melee -- pinned to the species median -- with its
            // knockback and on-hit effects. This is what the boss does to a
            // player, rather than a number chosen to make the arithmetic clean.
            scheduledHit = true;
            try {
                attacker.attackEntityAsMob(probe);
            } catch (Throwable t) {
                result.note = "attacker threw: " + describe(t);
                return;
            } finally {
                scheduledHit = false;
            }
            if (result.incomingSwings == 0) {
                QuestForgeContent.log.info("[census] first defensive hit from " + cell.targetName
                        + " on " + cell.loadout.describe() + ": probe armour " + probe.getTotalArmorValue()
                        + ", health " + CensusFile.num(before) + " -> " + CensusFile.num(probe.getHealth())
                        + ", hurtResist " + probe.hurtResistantTime + ", distance "
                        + CensusFile.num(probe.getDistanceToEntity(attacker)));
            }
            probe.setPosition(px + 1.5D, py, pz);
            probe.motionX = probe.motionY = probe.motionZ = 0;
            recordDefensiveHit(probe, before);
            return;
        }
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
            scheduledHit = true;
            probe.attackEntityFrom(
                    net.minecraft.util.DamageSource.causeMobDamage(attacker),
                    incomingDamage);
        } catch (Throwable t) {
            result.note = "incoming damage threw: " + describe(t);
            return;
        } finally {
            scheduledHit = false;
        }

        recordDefensiveHit(probe, before);
    }

    private static void recordDefensiveHit(EntityPlayer probe, float before) {
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
        lastHealth = new double[options.swarm];
        for (int i = 0; i < options.swarm; i++) {
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
            int before = world.loadedEntityList.size();
            initialiseAsSpawned(mob);
            // Spawning is what fires EntityJoinWorldEvent, where this pack rewrites
            // mob stats. A mob measured before that has the wrong health.
            world.spawnEntityInWorld(mob);
            for (int k = before; k < world.loadedEntityList.size(); k++) {
                Object o = world.loadedEntityList.get(k);
                if (o != mob && o instanceof net.minecraft.entity.Entity
                        && !(o instanceof EntityPlayer)) companions.add((net.minecraft.entity.Entity) o);
            }
            // Pinned once it has settled, in pinPending -- not here. The pack
            // scales a mob on its first update, so pinning at spawn removed
            // modifiers that did not exist yet and was then scaled over.
            PENDING_PIN.add(mob);
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
        PENDING_PIN.clear();
        for (net.minecraft.entity.Entity e : companions) {
            try {
                e.setDead();
                if (world != null) world.removeEntity(e);
            } catch (Throwable ignored) {}
        }
        companions.clear();
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
                // The pin is an assumption until checked: if anything re-scaled
                // the target during the cell, this row is not about the opponent
                // the header says it is.
                EntityLivingBase t = primary();
                double[] ref = REFERENCE.get(cell.targetName);
                if (t != null && ref != null && !Double.isNaN(ref[0]) && ref[0] > 0
                        && Math.abs(t.getMaxHealth() - ref[0]) > 0.02D * ref[0]) {
                    result.note += " [target max health " + CensusFile.num(t.getMaxHealth())
                            + " at cell end, reference " + CensusFile.num(ref[0])
                            + ": pin did not hold]";
                }
                if (result.infernalStripped > 0) {
                    result.note += " [target made an InfernalMobs elite " + result.infernalStripped
                            + " time(s); stripped back to plain]";
                }
                if (result.removedAlive > 0) {
                    result.note += " [target removed while alive " + result.removedAlive
                            + " time(s): not counted as kills or damage]";
                }
                if (result.repins > 0) {
                    result.note += " [target re-scaled by the pack " + result.repins
                            + " time(s) and re-pinned]";
                }
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
        // The control is the mean of every control repeat for this mode and
        // target, so one lucky or unlucky control cannot shift a whole run.
        List<Result> controlRuns = CONTROL_RUNS.get(controlKey(cell));
        if (cell.loadout.isControl()) {
            if (controlRuns == null) {
                controlRuns = new ArrayList<Result>();
                CONTROL_RUNS.put(controlKey(cell), controlRuns);
            }
            controlRuns.add(result);
        }
        Result control = (controlRuns == null || cell.loadout.isControl())
                ? null : averaged(controlRuns);
        if (cell.loadout.isControl()) CONTROLS.put(controlKey(cell), result);

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
        int level = single == null ? 0 : cell.loadout.levels.get(0).intValue();
        double expected = single == null ? Double.NaN : single.getProcChance(level);

        double refHealth = referenceHealth();
        double ttk = banded() && cell.mode != Mode.DEFENSE ? result.ttkSeconds(refHealth) : Double.NaN;
        double marginalTtkEst = Double.NaN;
        if (control != null && banded() && cell.mode != Mode.DEFENSE) {
            double baseTtk = control.ttkSeconds(refHealth);
            if (!Double.isInfinite(baseTtk) && !Double.isInfinite(ttk) && baseTtk > 0) {
                marginalTtkEst = 100.0D * (baseTtk - ttk) / baseTtk;
            }
        }
        StringBuilder bandsOut = new StringBuilder();
        if (banded() && cell.mode != Mode.DEFENSE) {
            for (int b = 0; b < BANDS.length; b++) {
                if (b > 0) bandsOut.append(' ');
                bandsOut.append(CensusFile.num(result.bandDps(b)));
            }
        }

        out.row(
                cell.loadout.describe(),
                cell.loadout.isControl() ? "control" : (cell.stacked ? "stacked" : "isolated"),
                cell.mode,
                single == null ? "" : single.rarity,
                single == null ? "" : String.valueOf(level),
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
                        : ""),
                CensusFile.num(options.hpFraction),
                bandsOut.toString() + (result.bandsReverted > 0
                        ? " [" + result.bandsReverted + " band(s) reverted by the target]" : ""),
                CensusFile.num(ttk),
                CensusFile.num(marginalTtkEst),
                CensusFile.num(refHealth),
                CensusFile.num(result.probeHpMin == Float.MAX_VALUE ? Double.NaN : result.probeHpMin),
                result.aiHitsBlocked);
    }

    /** Every control repeat, keyed like CONTROLS. */
    private static final java.util.Map<String, List<Result>> CONTROL_RUNS =
            new java.util.HashMap<String, List<Result>>();

    /** The mean of several control repeats, field by field. */
    private static Result averaged(List<Result> runs) {
        Result m = new Result();
        int n = runs.size();
        for (Result r : runs) {
            m.damageDealt += r.damageDealt / n;
            m.damageTaken += r.damageTaken / n;
            m.incomingSwings += r.incomingSwings;
            m.hitsSurvived += r.hitsSurvived;
            m.killTicks.addAll(r.killTicks);
            for (int b = 0; b < BANDS.length; b++) m.bandDamage[b] += r.bandDamage[b] / n;
        }
        m.incomingSwings = Math.round((float) m.incomingSwings / n);
        m.hitsSurvived = Math.round((float) m.hitsSurvived / n);
        return m;
    }

    private static double referenceHealth() {
        double[] ref = REFERENCE.get(cell.targetName);
        return ref == null ? Double.NaN : ref[0];
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

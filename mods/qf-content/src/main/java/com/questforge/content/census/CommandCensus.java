package com.questforge.content.census;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.WorldServer;

import com.questforge.content.QuestForgeContent;

/**
 * /qfcensus -- measures the pack.
 *
 * Everything the enchantment balance rests on is a number about this pack: what a
 * boss hits for, what the best armour actually stops, what the strongest weapon
 * swings for. Those numbers are not in any config in a form worth trusting, and
 * they are not in the jars either once a mod scales them at runtime. So they get
 * measured, here, in the running game.
 *
 * Run "calibrate" first. It has a known answer, and if it fails then nothing else
 * this command produces means anything.
 */
public class CommandCensus extends CommandBase {

    @Override
    public String getCommandName() {
        return "qfcensus";
    }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/qfcensus <calibrate | gear | mobs | combat [entity[@health]... | modid:item | wounded | hit=N | pairs | triples | only=a+b | modes=melee+bow | shard=i/n] | find <text> | all | status | stop>";
    }

    @Override
    public int getRequiredPermissionLevel() {
        return 2;   // operators only: it spawns several hundred entities
    }

    @Override
    @SuppressWarnings("rawtypes")
    public List addTabCompletionOptions(ICommandSender sender, String[] args) {
        if (args.length == 1) {
            return getListOfStringsMatchingLastWord(args,
                    new String[] { "calibrate", "gear", "mobs", "combat", "find", "all", "status", "stop" });
        }
        return null;
    }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        String action = args.length > 0 ? args[0].toLowerCase() : "status";
        File configDir = configDir();
        WorldServer world = MinecraftServer.getServer().worldServerForDimension(0);

        if ("calibrate".equals(action)) {
            String result = CensusProbe.calibrate(world);
            QuestForgeContent.log.info("[census] calibration: " + result);
            reply(sender, result.startsWith("OK")
                    ? EnumChatFormatting.GREEN + result
                    : EnumChatFormatting.RED + result);
            return;
        }

        if ("gear".equals(action) || "all".equals(action)) {
            reply(sender, "Measuring gear...");
            String cal = CensusProbe.calibrate(world);
            QuestForgeContent.log.info("[census] calibration: " + cal);
            reply(sender, cal.startsWith("OK") ? EnumChatFormatting.GREEN + cal
                                               : EnumChatFormatting.RED + cal);
            long t0 = System.currentTimeMillis();
            GearCensus.run(configDir, CensusProbe.player(world));
            reply(sender, EnumChatFormatting.GREEN + "Gear census written in "
                    + (System.currentTimeMillis() - t0) + " ms. See config/qfcontent-census-*.tsv");
        }

        if ("mobs".equals(action) || "all".equals(action)) {
            if (MobCensus.isRunning()) {
                reply(sender, EnumChatFormatting.YELLOW + "Already running. " + MobCensus.status());
                return;
            }
            String cal = CensusProbe.calibrate(world);
            QuestForgeContent.log.info("[census] calibration: " + cal);
            if (!cal.startsWith("OK")) {
                reply(sender, EnumChatFormatting.RED
                        + "Calibration failed, refusing to run: " + cal);
                return;
            }
            reply(sender, EnumChatFormatting.GREEN + cal);
            MobCensus.start(world, configDir);
            reply(sender, "Mob census started. It spawns every registered entity one at a time; "
                    + "expect a few minutes. /qfcensus status to follow it.");
            return;
        }

        if ("combat".equals(action)) {
            if (CombatCensus.isRunning()) {
                reply(sender, EnumChatFormatting.YELLOW + "Already running. " + CombatCensus.status());
                return;
            }

            // Both calibrations, and neither is optional. The first proves the
            // probe can hit and be hit; the second proves it experiences time,
            // without which every tick-driven enchantment measures as zero and
            // says nothing about it.
            String cal = CensusProbe.calibrate(world);
            QuestForgeContent.log.info("[census] calibration: " + cal);
            if (!cal.startsWith("OK")) {
                reply(sender, EnumChatFormatting.RED + "Calibration failed, refusing to run: " + cal);
                return;
            }
            reply(sender, EnumChatFormatting.GREEN + cal);

            String tickCal = CensusProbe.calibrateTick(world);
            QuestForgeContent.log.info("[census] tick calibration: " + tickCal);
            if (tickCal.startsWith("FAILED")) {
                reply(sender, EnumChatFormatting.RED
                        + "Tick calibration failed, refusing to run: " + tickCal);
                return;
            }
            reply(sender, EnumChatFormatting.GREEN + tickCal);

            // The weapon is whatever the operator is holding, so the pack's real
            // endgame gear can be measured without naming any of it in code.
            ItemStack weapon = null;
            if (sender instanceof EntityPlayer) {
                weapon = ((EntityPlayer) sender).getHeldItem();
            }

            // Naming it works too, and is the only option from a console: a
            // headless server has no hands, so without this every automated run
            // measures a diamond sword. An argument containing a colon is a item
            // registry name ("modid:item"); everything else is a target entity.
            List<String> targets = new ArrayList<String>();
            CombatCensus.Options opts = new CombatCensus.Options();
            for (int i = 1; i < args.length; i++) {
                String arg = args[i];
                String lower = arg.toLowerCase();
                if ("wounded".equals(lower)) { opts.wounded = true; opts.hpFraction = 0.3F; continue; }
                if ("levels=all".equals(lower)) { opts.levelsAll = true; continue; }
                if ("bands=off".equals(lower)) { opts.bands = false; continue; }
                if (lower.startsWith("swarm=") || lower.startsWith("hp=")
                        || lower.startsWith("controls=")) {
                    try {
                        String v = lower.substring(lower.indexOf('=') + 1);
                        if (lower.startsWith("swarm=")) opts.swarm = Math.max(1, Integer.parseInt(v));
                        else if (lower.startsWith("hp=")) {
                            opts.hpFraction = Math.max(0.05F, Math.min(1.0F, Float.parseFloat(v)));
                            opts.wounded = opts.hpFraction < 1.0F;
                        } else opts.controlReps = Math.max(1, Integer.parseInt(v));
                    } catch (NumberFormatException e) {
                        reply(sender, EnumChatFormatting.RED + "bad number in " + arg);
                        return;
                    }
                    continue;
                }
                // armour=modid:helm+modid:chest+... -- any order; each piece goes
                // to the slot its ItemArmor.armorType says, so a set is a set.
                if (lower.startsWith("armour=") || lower.startsWith("armor=")) {
                    opts.armour = new ItemStack[4];
                    for (String piece : arg.substring(arg.indexOf('=') + 1).split("\\+")) {
                        ItemStack st = itemByName(piece);
                        if (st == null || !(st.getItem() instanceof net.minecraft.item.ItemArmor)) {
                            reply(sender, EnumChatFormatting.RED + "Not armour: '" + piece
                                    + "'; refusing to run rather than measure diamond instead.");
                            return;
                        }
                        int type = ((net.minecraft.item.ItemArmor) st.getItem()).armorType;
                        opts.armour[3 - type] = st;
                    }
                    continue;
                }
                if ("pairs".equals(lower)) { opts.pairs = true; continue; }
                if ("triples".equals(lower)) { opts.triples = true; continue; }
                if (lower.startsWith("hit=")) {
                    try {
                        opts.incoming = Float.parseFloat(arg.substring(4));
                    } catch (NumberFormatException e) {
                        reply(sender, EnumChatFormatting.RED + "hit= needs a number, e.g. hit=40");
                        return;
                    }
                    continue;
                }
                // Lists use '+' rather than ',' because a JVM property is split
                // on commas before it gets here.
                if (lower.startsWith("only=")) {
                    opts.only = new java.util.HashSet<String>(
                            Arrays.asList(lower.substring(5).split("\\+")));
                    continue;
                }
                if (lower.startsWith("modes=")) {
                    opts.modes = new java.util.HashSet<String>();
                    for (String m : lower.substring(6).split("\\+")) {
                        opts.modes.add(m.toUpperCase());
                    }
                    continue;
                }
                if (lower.startsWith("shard=")) {
                    try {
                        String[] parts = lower.substring(6).split("/");
                        opts.shardIndex = Integer.parseInt(parts[0]);
                        opts.shardCount = Integer.parseInt(parts[1]);
                        if (opts.shardCount < 1 || opts.shardIndex < 0
                                || opts.shardIndex >= opts.shardCount) throw new NumberFormatException();
                    } catch (Exception e) {
                        reply(sender, EnumChatFormatting.RED
                                + "shard= needs index/count with index < count, e.g. shard=0/4");
                        return;
                    }
                    continue;
                }
                if (arg.indexOf(':') < 0) {
                    targets.add(arg);
                    continue;
                }
                ItemStack named = itemByName(arg);
                if (named == null) {
                    reply(sender, EnumChatFormatting.RED + "No item registered as '" + arg
                            + "'; refusing to run rather than silently measuring a "
                            + "diamond sword.");
                    return;
                }
                weapon = named;
            }

            CombatCensus.start(world, configDir, weapon, targets, opts);
            reply(sender, "Combat census started" + opts.describe()
                    + (weapon == null ? " with a diamond sword" : " with " + weapon.getDisplayName())
                    + ". It fights every combat enchantment against a control and writes "
                    + "config/qfcontent-census-combat*.tsv. This runs in real game ticks and takes "
                    + "tens of minutes; /qfcensus status to follow it.");
            return;
        }

        if ("find".equals(action)) {
            // Picking a target or a weapon means knowing its registry name, and
            // in this pack those are not guessable -- "Mobzilla" is registered by
            // one mod as one thing and referred to everywhere else as another.
            // Guessing wrong costs an hour-long run, so this makes it checkable
            // in a second, from a console, without a client.
            String needle = (args.length > 1 ? args[1] : "").toLowerCase();
            if (needle.isEmpty()) {
                reply(sender, "Usage: /qfcensus find <text>");
                return;
            }

            List<String> entities = new ArrayList<String>();
            for (Object key : net.minecraft.entity.EntityList.stringToClassMapping.keySet()) {
                String name = String.valueOf(key);
                if (name.toLowerCase().contains(needle)) entities.add(name);
            }
            java.util.Collections.sort(entities);

            List<String> items = new ArrayList<String>();
            for (Object key : net.minecraft.item.Item.itemRegistry.getKeys()) {
                String name = String.valueOf(key);
                if (name.toLowerCase().contains(needle)) items.add(name);
            }
            java.util.Collections.sort(items);

            QuestForgeContent.log.info("[census] find '" + needle + "': entities=" + entities);
            QuestForgeContent.log.info("[census] find '" + needle + "': items=" + items);
            reply(sender, "entities (" + entities.size() + "): " + head(entities));
            reply(sender, "items (" + items.size() + "): " + head(items));
            return;
        }

        if ("status".equals(action)) {
            reply(sender, MobCensus.status() + " | " + CombatCensus.status());
            return;
        }

        if ("stop".equals(action)) {
            MobCensus.stop();
            CombatCensus.stop();
            reply(sender, "Stopped.");
            return;
        }

        if (!"gear".equals(action) && !"all".equals(action)) {
            reply(sender, getCommandUsage(sender));
        }
    }

    /**
     * The directory the rest of the mod writes to, captured in preInit.
     * Deriving it from the server's working directory instead gets it wrong on an
     * integrated server, which is where this will usually be run.
     */
    private static File configDir() {
        File dir = QuestForgeContent.configDir();
        return dir != null ? dir : new File(MinecraftServer.getServer().getFile("."), "config");
    }

    /**
     * An item by its registry name, or null.
     *
     * Tolerant about the modid, because in a 110-mod pack nobody remembers
     * whether OreSpawn registers as "OreSpawn" or "orespawn" and being wrong
     * costs a whole census run. An unqualified name matches the first item whose
     * own name matches, which is unambiguous in practice for weapon names.
     */
    /** The first few of a list, so a chat reply cannot run to hundreds of lines. */
    private static String head(List<String> all) {
        if (all.isEmpty()) return "(none)";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < all.size() && i < 12; i++) {
            if (i > 0) sb.append(", ");
            sb.append(all.get(i));
        }
        if (all.size() > 12) sb.append(", ... (full list in the log)");
        return sb.toString();
    }

    private static ItemStack itemByName(String name) {
        net.minecraft.item.Item item = (net.minecraft.item.Item)
                net.minecraft.item.Item.itemRegistry.getObject(name);
        if (item != null) return new ItemStack(item);

        String wanted = name.toLowerCase();
        String bare = wanted.substring(wanted.indexOf(':') + 1);
        for (Object key : net.minecraft.item.Item.itemRegistry.getKeys()) {
            String registered = String.valueOf(key);
            String lower = registered.toLowerCase();
            if (lower.equals(wanted) || lower.endsWith(":" + bare)) {
                item = (net.minecraft.item.Item)
                        net.minecraft.item.Item.itemRegistry.getObject(registered);
                if (item != null) return new ItemStack(item);
            }
        }
        return null;
    }

    private static void reply(ICommandSender sender, String message) {
        sender.addChatMessage(new ChatComponentText("[qfcensus] " + message));
    }
}

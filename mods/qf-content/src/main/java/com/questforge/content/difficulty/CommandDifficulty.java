package com.questforge.content.difficulty;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.command.WrongUsageException;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityList;
import net.minecraft.entity.EntityLiving;
import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.attributes.IAttributeInstance;
import net.minecraft.entity.passive.EntityVillager;
import net.minecraft.init.Items;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.ChunkCoordinates;
import net.minecraft.util.DamageSource;
import net.minecraft.world.World;
import net.minecraft.server.MinecraftServer;

import net.minecraftforge.event.ForgeEventFactory;

import cpw.mods.fml.common.eventhandler.Event;

import com.questforge.content.QuestForgeContent;

/**
 * {@code /qfdifficulty}: the difficulty tier where you stand, for testing.
 *
 * <pre>
 * /qfdifficulty                     tier at your position (anyone)
 * /qfdifficulty X Y Z               tier at a position (anyone; the console must give one)
 * /qfdifficulty reload              re-read qfcontent-difficulty.cfg and the grid (op)
 * /qfdifficulty test ...            op-only probes for the server trial; see testUsage()
 * </pre>
 *
 * The test probes run the real hooks: they spawn through spawnEntityInWorld (so
 * InfernalMobs and the tier stamp both run), fire Forge's CheckSpawn the way a
 * natural spawner does, and hit through attackEntityFrom. Each removes what it
 * spawned. Every answer is also written to the server log.
 */
public class CommandDifficulty extends CommandBase {

    @Override
    public String getCommandName() {
        return "qfdifficulty";
    }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/qfdifficulty [x y z] | reload | test ...";
    }

    @Override
    public int getRequiredPermissionLevel() {
        return 0;
    }

    @Override
    public boolean canCommandSenderUseCommand(ICommandSender sender) {
        return true;
    }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        if (args.length > 0 && "reload".equalsIgnoreCase(args[0])) {
            op(sender);
            say(sender, Difficulty.reload());
            return;
        }
        if (args.length > 0 && "test".equalsIgnoreCase(args[0])) {
            op(sender);
            test(sender, args);
            return;
        }
        World w = sender.getEntityWorld();
        double x, y, z;
        if (args.length >= 3) {
            ChunkCoordinates c = sender.getPlayerCoordinates();
            x = func_110666_a(sender, c.posX + 0.5, args[0]);
            y = func_110666_a(sender, c.posY, args[1]);
            z = func_110666_a(sender, c.posZ + 0.5, args[2]);
        } else if (sender instanceof Entity) {
            Entity e = (Entity) sender;
            x = e.posX;
            y = e.posY;
            z = e.posZ;
        } else {
            throw new WrongUsageException("/qfdifficulty <x> <y> <z> (the console has no position)");
        }
        report(sender, w, x, y, z);
    }

    private void report(ICommandSender sender, World w, double x, double y, double z) {
        String at = String.format("(%.0f, %.0f, %.0f)", x, y, z);
        if (!Difficulty.active()) {
            say(sender, "Difficulty tiers inactive (no tier grid in this world, or disabled): nothing is scaled. " + at);
            return;
        }
        if (!Difficulty.appliesTo(w)) {
            say(sender, "Difficulty tiers do not apply in dimension " + w.provider.dimensionId + ". " + at);
            return;
        }
        Difficulty.Where where = Difficulty.tierAt(w, x, y, z);
        DifficultyConfig.Tier s = Difficulty.config().tier(where.tier);
        say(sender, "Tier " + where + " at " + at + ", chunk (" + ((int) Math.floor(x) >> 4) + ", "
                + ((int) Math.floor(z) >> 4) + ")");
        say(sender, "  " + (s.inert() ? "no change (every setting at its default)" : s.toString()));
    }

    // ---- probes -------------------------------------------------------------------------

    private static String testUsage() {
        return "/qfdifficulty test spawn <entity> <x> <y> <z> [n] [cage] | checkspawn <entity> <x> <y> <z> [n] | "
                + "event <entity> <x> <y> <z> [eventName] | hurt <attacker> <x> <y> <z> <damage> [armoured]";
    }

    private void test(ICommandSender sender, String[] a) {
        if (a.length < 6) throw new WrongUsageException(testUsage());
        String what = a[1].toLowerCase();
        World w = MinecraftServer.getServer().worldServerForDimension(0);
        String name = a[2];
        double x = parseDouble(sender, a[3]), y = parseDouble(sender, a[4]), z = parseDouble(sender, a[5]);
        if ("spawn".equals(what)) {
            int n = a.length > 6 ? parseIntBounded(sender, a[6], 1, 2000) : 1;
            boolean cage = a.length > 7 && "cage".equalsIgnoreCase(a[7]);
            testSpawn(sender, w, name, x, y, z, n, cage);
        } else if ("checkspawn".equals(what)) {
            int n = a.length > 6 ? parseIntBounded(sender, a[6], 1, 100000) : 100;
            testCheckSpawn(sender, w, name, x, y, z, n);
        } else if ("event".equals(what)) {
            testEvent(sender, w, name, x, y, z, a.length > 6 ? a[6] : "boulderdash");
        } else if ("hurt".equals(what)) {
            if (a.length < 7) throw new WrongUsageException(testUsage());
            float dmg = (float) parseDouble(sender, a[6]);
            testHurt(sender, w, name, x, y, z, dmg, a.length > 7 && "armoured".equalsIgnoreCase(a[7]));
        } else {
            throw new WrongUsageException(testUsage());
        }
    }

    private EntityLiving make(World w, String name, double x, double y, double z) {
        Entity e = EntityList.createEntityByName(name, w);
        if (!(e instanceof EntityLiving)) throw new WrongUsageException("not a living entity: " + name);
        EntityLiving m = (EntityLiving) e;
        // spawnEntityInWorld refuses a mob in an unloaded chunk, and nobody stands there.
        w.getChunkFromBlockCoords((int) Math.floor(x), (int) Math.floor(z));
        m.setLocationAndAngles(x, y, z, 0, 0);
        m.onSpawnWithEgg(null);
        return m;
    }

    /** Spawns n through spawnEntityInWorld, reports the tier stamps and the stats they got, removes them. */
    private void testSpawn(ICommandSender s, World w, String name, double x, double y, double z, int n, boolean cage) {
        Map<String, Integer> stamps = new TreeMap<String, Integer>();
        int joined = 0, elites = 0;
        double hpRatio = 0, speedRatio = 0, xp = 0;
        String eg = "";
        List<EntityLiving> made = new ArrayList<EntityLiving>();
        for (int i = 0; i < n; i++) {
            EntityLiving m = make(w, name, x, y, z);
            if (cage) m.getEntityData().setBoolean(ModHooks.SOUL_SHARDS_TAG, true);  // exactly what the cage sets
            if (!w.spawnEntityInWorld(m)) continue;
            joined++;
            made.add(m);
            String key = "T" + Difficulty.stampedTier(m) + "/" + m.getEntityData().getString(Difficulty.TAG_HOW);
            Integer c = stamps.get(key);
            stamps.put(key, c == null ? 1 : c + 1);
            if (ModHooks.isElite(m)) elites++;
            IAttributeInstance hp = m.getEntityAttribute(SharedMonsterAttributes.maxHealth);
            IAttributeInstance sp = m.getEntityAttribute(SharedMonsterAttributes.movementSpeed);
            hpRatio += hp.getAttributeValue() / hp.getBaseValue();
            speedRatio += sp.getAttributeValue() / sp.getBaseValue();
            xp += xpOf(m);
            if (i == 0) {
                eg = String.format("first: maxHealth %.1f (base %.1f), health %.1f, speed %.3f (base %.3f), xp %d",
                        hp.getAttributeValue(), hp.getBaseValue(), m.getHealth(), sp.getAttributeValue(),
                        sp.getBaseValue(), xpOf(m));
            }
        }
        for (EntityLiving m : made) m.setDead();
        String at = Difficulty.appliesTo(w) ? Difficulty.tierAt(w, x, y, z).toString() : "inactive";
        say(s, String.format("spawn %s x%d at (%.0f, %.0f, %.0f)%s, place %s: %d joined; stamps %s; elites %d (%.1f%%); "
                        + "mean maxHealth/base %.3f, speed/base %.3f, xp %.2f", name, n, x, y, z, cage ? " [SSTOW cage tag]" : "",
                at, joined, stamps.isEmpty() ? "none" : stamps.toString(), elites,
                joined > 0 ? 100.0 * elites / joined : 0, joined > 0 ? hpRatio / joined : 0,
                joined > 0 ? speedRatio / joined : 0, joined > 0 ? xp / joined : 0));
        say(s, "  " + eg);
    }

    private static int xpOf(EntityLiving m) {
        try {
            java.lang.reflect.Field f = cpw.mods.fml.relauncher.ReflectionHelper.findField(EntityLiving.class,
                    "experienceValue", "field_70728_aV");
            return f.getInt(m);
        } catch (Throwable t) {
            return -1;
        }
    }

    /** Fires Forge's CheckSpawn n times as a natural spawner would; reports how many were allowed. */
    private void testCheckSpawn(ICommandSender s, World w, String name, double x, double y, double z, int n) {
        int deny = 0;
        EntityLiving m = make(w, name, x, y, z);
        for (int i = 0; i < n; i++) {
            Event.Result r = ForgeEventFactory.canEntitySpawn(m, w, (float) x, (float) y, (float) z);
            if (r == Event.Result.DENY) deny++;
        }
        String at = Difficulty.appliesTo(w) ? Difficulty.tierAt(w, x, y, z).toString() : "inactive";
        say(s, String.format("checkspawn %s x%d at (%.0f, %.0f, %.0f), place %s: %d allowed, %d denied (kept %.3f)",
                name, n, x, y, z, at, n - deny, deny, (n - deny) / (double) n));
    }

    /** A Lycanites mob carrying an event's mark, as its event spawner makes it; does it join? */
    private void testEvent(ICommandSender s, World w, String name, double x, double y, double z, String event) {
        EntityLiving m = make(w, name, x, y, z);
        if (!ModHooks.markLycanitesEventMob(m, event)) {
            say(s, "event: " + name + " is not a Lycanites creature (or Lycanites is not loaded)");
            return;
        }
        Event.Result r = ForgeEventFactory.canEntitySpawn(m, w, (float) x, (float) y, (float) z);
        boolean joined = w.spawnEntityInWorld(m);
        if (joined) m.setDead();
        String at = Difficulty.appliesTo(w) ? Difficulty.tierAt(w, x, y, z).toString() : "inactive";
        say(s, String.format("event %s (%s) at (%.0f, %.0f, %.0f), place %s: CheckSpawn %s, joined the world: %s",
                name, event, x, y, z, at, r, joined));
    }

    /** One hit from a freshly spawned attacker on a fresh villager (diamond armour if asked). */
    private void testHurt(ICommandSender s, World w, String name, double x, double y, double z, float dmg, boolean armoured) {
        EntityLiving attacker = make(w, name, x, y, z);
        w.spawnEntityInWorld(attacker);
        ModHooks.stripElite(attacker);  // an InfernalMobs modifier would change the hit
        // A villager: not hostile, so neither tiers nor InfernalMobs touch the target.
        EntityVillager target = new EntityVillager(w);
        target.setLocationAndAngles(x + 1, y, z, 0, 0);
        if (armoured) {
            target.setCurrentItemOrArmor(1, new ItemStack(Items.diamond_boots));
            target.setCurrentItemOrArmor(2, new ItemStack(Items.diamond_leggings));
            target.setCurrentItemOrArmor(3, new ItemStack(Items.diamond_chestplate));
            target.setCurrentItemOrArmor(4, new ItemStack(Items.diamond_helmet));
        }
        w.spawnEntityInWorld(target);
        target.getEntityAttribute(SharedMonsterAttributes.maxHealth).setBaseValue(1000);
        target.setHealth(target.getMaxHealth());
        float before = target.getHealth();
        boolean hit = target.attackEntityFrom(DamageSource.causeMobDamage(attacker), dmg);
        float lost = before - target.getHealth();
        int tier = Difficulty.stampedTier(attacker);
        attacker.setDead();
        target.setDead();
        say(s, String.format("hurt: %s (stamp T%d) hits a villager%s for %.2f: landed %s, target lost %.3f health (armour %d)",
                name, tier, armoured ? " in diamond armour" : "", dmg, hit, lost, target.getTotalArmorValue()));
    }

    private static void op(ICommandSender sender) {
        if (!sender.canCommandSenderUseCommand(2, "qfdifficulty")) {
            throw new WrongUsageException("only an operator can do that");
        }
    }

    private static void say(ICommandSender sender, String text) {
        sender.addChatMessage(new ChatComponentText(text));
        QuestForgeContent.log.info("[difficulty] " + text);
    }
}

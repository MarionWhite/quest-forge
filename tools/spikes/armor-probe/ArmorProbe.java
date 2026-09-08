import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemArmor;
import net.minecraft.item.ItemStack;
import net.minecraft.util.DamageSource;
import net.minecraftforge.common.ISpecialArmor.ArmorProperties;
import net.minecraftforge.common.util.EnumHelper;

import java.lang.reflect.Field;
import java.util.Random;

/**
 * Calls the REAL Forge ApplyArmor, from the real deobfuscated Forge jar, on real
 * ItemStacks. Nothing here is a reimplementation or a transcription.
 */
public class ArmorProbe {

    static EntityPlayer fakePlayer() throws Exception {
        Field f = Class.forName("sun.misc.Unsafe").getDeclaredField("theUnsafe");
        f.setAccessible(true);
        sun.misc.Unsafe u = (sun.misc.Unsafe) f.get(null);
        EntityPlayer p = (EntityPlayer) u.allocateInstance(ProbePlayer.class);
        set(p, EntityPlayer.class, "capabilities",
            Class.forName("net.minecraft.entity.player.PlayerCapabilities").newInstance());
        set(p, Class.forName("net.minecraft.entity.Entity"), "rand", new Random(1));
        return p;
    }

    static void set(Object target, Class<?> owner, String name, Object value) throws Exception {
        Field f = owner.getDeclaredField(name);
        f.setAccessible(true);
        f.set(target, value);
    }

    /** reductions are {helmet, chest, legs, boots}, exactly as addArmorMaterial takes them. */
    static ItemStack[] set(String name, int durability, int[] reductions, int wearPercent) {
        ItemArmor.ArmorMaterial mat =
            EnumHelper.addArmorMaterial(name, durability, reductions, 15);
        ItemStack[] inv = new ItemStack[4];
        // armorInventory order is 0 boots, 1 leggings, 2 chest, 3 helmet
        int[] typeForSlot = {3, 2, 1, 0};
        for (int slot = 0; slot < 4; slot++) {
            ItemArmor piece = new ItemArmor(mat, 0, typeForSlot[slot]);
            ItemStack stack = new ItemStack(piece);
            stack.setItemDamage((int) (piece.getMaxDamage() * (wearPercent / 100.0)));
            inv[slot] = stack;
        }
        return inv;
    }

    static int points(ItemStack[] inv) {
        int t = 0;
        for (ItemStack s : inv) t += ((ItemArmor) s.getItem()).damageReduceAmount;
        return t;
    }

    static int durabilityLeft(ItemStack[] inv) {
        int t = 0;
        for (ItemStack s : inv) t += s.getMaxDamage() + 1 - s.getItemDamage();
        return t;
    }

    public static void main(String[] args) throws Exception {
        EntityPlayer player = fakePlayer();
        DamageSource src = DamageSource.cactus;
        System.out.println("damage source \"" + src.getDamageType()
            + "\"  unblockable=" + src.isUnblockable()
            + "  (armour must apply, or this test proves nothing)\n");

        int[] diamond = {3, 8, 6, 3};      // vanilla, durability factor 33
        int[] ruby    = {4, 9, 8, 4};      // OreSpawn.cfg, durability factor 90
        int[] queen   = {9, 16, 14, 9};    // OreSpawn.cfg, durability factor 1500

        float[] hits = {10f, 40f, 175f, 350f};

        System.out.printf("%-34s %5s %8s", "set (fresh)", "pts", "dur");
        for (float h : hits) System.out.printf("%12s", "hit " + (int) h);
        System.out.println();
        System.out.println(line(100));
        row(player, src, "vanilla diamond, dur 33", diamond, 33, 0, hits);
        row(player, src, "OreSpawn Ruby, dur 90", ruby, 90, 0, hits);
        row(player, src, "OreSpawn Queen, dur 1500", queen, 1500, 0, hits);

        System.out.println("\nSame sets, but the ONLY thing changed is the durability factor.");
        System.out.println("If durability did not affect damage, every row here would be identical.");
        System.out.printf("%-34s %5s %8s", "set", "pts", "dur");
        for (float h : hits) System.out.printf("%12s", "hit " + (int) h);
        System.out.println();
        System.out.println(line(100));
        for (int d : new int[]{5, 15, 33, 90, 300, 1500}) {
            row(player, src, "25-point set, durability " + d, ruby, d, 0, hits);
        }

        System.out.println("\nOne set, one hit size, worn down further each row.");
        System.out.println("Armour points never change. Only remaining durability does.");
        System.out.printf("%-34s %5s %8s%12s%n", "OreSpawn Ruby at N% worn", "pts", "dur left", "hit 175");
        System.out.println(line(72));
        for (int w : new int[]{0, 25, 50, 75, 90, 99}) {
            ItemStack[] inv = set("PROBE_W" + w, 90, ruby, w);
            float landed = ArmorProperties.ApplyArmor(player, inv, src, 175f);
            System.out.printf("%-34s %5d %8d%12.2f%n",
                w + "% worn", points(inv), durabilityLeft(inv), Math.max(0f, landed));
        }

        System.out.println("\nDurability actually spent by one hit (proves ApplyArmor writes to the stacks):");
        ItemStack[] inv = set("PROBE_SPEND", 90, ruby, 0);
        int before = durabilityLeft(inv);
        float landed = ArmorProperties.ApplyArmor(player, inv, src, 175f);
        System.out.printf("  Ruby, fresh, one 175 hit: landed %.2f, durability %d -> %d (spent %d)%n",
            Math.max(0f, landed), before, durabilityLeft(inv), before - durabilityLeft(inv));
    }

    static void row(EntityPlayer p, DamageSource src, String label, int[] red, int dur,
                    int wear, float[] hits) {
        ItemStack[] first = set("PROBE_" + label.hashCode() + "_" + dur, dur, red, wear);
        System.out.printf("%-34s %5d %8d", label, points(first), dur);
        for (float h : hits) {
            ItemStack[] inv = set("PROBE_" + label.hashCode() + "_" + dur + "_" + (int) h,
                                  dur, red, wear);
            float landed = ArmorProperties.ApplyArmor(p, inv, src, h);
            System.out.printf("%12.2f", Math.max(0f, landed));
        }
        System.out.println();
    }

    static String line(int n) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < n; i++) b.append('-');
        return b.toString();
    }
}

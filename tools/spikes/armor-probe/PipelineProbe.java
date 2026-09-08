import net.minecraft.enchantment.Enchantment;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.InventoryPlayer;
import net.minecraft.item.ItemArmor;
import net.minecraft.item.ItemStack;
import net.minecraft.util.DamageSource;
import net.minecraftforge.common.ISpecialArmor.ArmorProperties;
import net.minecraftforge.common.util.EnumHelper;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Random;

/**
 * Every mitigation step is the game's own method, called by reflection on a real
 * EntityPlayer with real ItemStacks. Nothing is reimplemented.
 *
 * The order they are called in is EntityPlayer.damageEntity lines 1225-1236,
 * verbatim:
 *
 *     p_70665_2_ = ArmorProperties.ApplyArmor(this, inventory.armorInventory, src, amount);
 *     if (p_70665_2_ <= 0) return;
 *     p_70665_2_ = this.applyPotionDamageCalculations(src, amount);
 *     ... absorption ...
 *     this.setHealth(this.getHealth() - amount);
 *
 * Two lines of that method are deliberately left out. ForgeHooks.onLivingHurt is
 * the LivingHurtEvent, which is where this mod's own enchantments hook -- their
 * effect is measured separately in qfbench, and firing it here would need a whole
 * FML environment. Absorption is skipped because it is zero without a potion, and
 * it subtracts rather than scales.
 */
public class PipelineProbe {

    static Method applyPotionDamageCalculations;

    static sun.misc.Unsafe unsafe() throws Exception {
        Field f = Class.forName("sun.misc.Unsafe").getDeclaredField("theUnsafe");
        f.setAccessible(true);
        return (sun.misc.Unsafe) f.get(null);
    }

    static void set(Object target, Class<?> owner, String name, Object value) throws Exception {
        Field f = owner.getDeclaredField(name);
        f.setAccessible(true);
        f.set(target, value);
    }

    static EntityPlayer player(ItemStack[] armour) throws Exception {
        EntityPlayer p = (EntityPlayer) unsafe().allocateInstance(ProbePlayer.class);
        Class<?> entity = Class.forName("net.minecraft.entity.Entity");
        Class<?> living = Class.forName("net.minecraft.entity.EntityLivingBase");
        set(p, entity, "rand", new Random(7));
        set(p, EntityPlayer.class, "capabilities",
            Class.forName("net.minecraft.entity.player.PlayerCapabilities").newInstance());
        set(p, living, "activePotionsMap", new HashMap<Object, Object>());
        set(p, EntityPlayer.class, "inventory", new InventoryPlayer(p));
        System.arraycopy(armour, 0, p.inventory.armorInventory, 0, 4);
        return p;
    }

    static ItemStack[] armour(String name, int durability, int[] red, int prot, int unb) {
        ItemArmor.ArmorMaterial mat = EnumHelper.addArmorMaterial(name, durability, red, 15);
        ItemStack[] inv = new ItemStack[4];
        int[] typeForSlot = {3, 2, 1, 0};       // armorInventory: 0 boots .. 3 helmet
        for (int slot = 0; slot < 4; slot++) {
            ItemStack s = new ItemStack(new ItemArmor(mat, 0, typeForSlot[slot]));
            if (prot > 0) s.addEnchantment(Enchantment.protection, prot);
            if (unb > 0) s.addEnchantment(Enchantment.unbreaking, unb);
            inv[slot] = s;
        }
        return inv;
    }

    static float oneHit(EntityPlayer p, DamageSource src, float raw) throws Exception {
        float amount = ArmorProperties.ApplyArmor(p, p.inventory.armorInventory, src, raw);
        if (amount <= 0) return 0f;
        return (Float) applyPotionDamageCalculations.invoke(p, src, amount);
    }

    static int fight(String tag, int dur, int[] red, int prot, int unb,
                     float raw, int cap) throws Exception {
        EntityPlayer p = player(armour(tag, dur, red, prot, unb));
        DamageSource src = DamageSource.cactus;      // plain: armour and protection both apply
        float health = 20f;
        for (int s = 0; s < cap; s++) {
            health -= oneHit(p, src, raw);
            if (health <= 0f) return s + 1;
            health = Math.min(20f, health + 0.25f);  // FoodStats: 1 HP / 80 ticks, fed
        }
        return cap;
    }

    public static void main(String[] args) throws Exception {
        applyPotionDamageCalculations = Class.forName("net.minecraft.entity.EntityLivingBase")
            .getDeclaredMethod("applyPotionDamageCalculations", DamageSource.class, float.class);
        applyPotionDamageCalculations.setAccessible(true);

        int[] diamond  = {3, 8, 6, 3};
        int[] ruby     = {4, 9, 8, 4};
        int[] ultimate = {6, 12, 10, 6};
        int[] mobz     = {7, 13, 11, 7};
        int[] queen    = {9, 16, 14, 9};
        int[] royal    = {8, 14, 12, 8};

        Object[][] sets = {
            {"diamond",  33,   diamond,  4, 0},
            {"ruby",     90,   ruby,     4, 0},
            {"ultimate", 200,  ultimate, 5, 0},
            {"mobzilla", 1000, mobz,    10, 5},
            {"queen",    1500, queen,    0, 0},
            {"royal",    2000, royal,   10, 5},
        };

        System.out.println("A. Damage reaching the health bar from ONE swing on a fresh set,\n   averaged over 4000 rolls of Protection's per-hit random modifier.\n");
        int[] hits = {40, 175, 225, 350};
        System.out.printf("%-10s %4s %6s %5s %4s", "set", "pts", "dur", "prot", "unb");
        for (int h : hits) System.out.printf("%11s", h + "/hit");
        System.out.println();
        for (Object[] r : sets) {
            int[] red = (int[]) r[2];
            int pts = red[0] + red[1] + red[2] + red[3];
            System.out.printf("%-10s %4d %6d %5d %4d", r[0], pts, r[1], r[3], r[4]);
            for (int h : hits) {
                // Protection's modifier is rolled per hit, so average it.
                double sum = 0;
                for (int t = 0; t < 4000; t++) {
                    EntityPlayer p = player(armour(r[0] + "_a" + h + "_" + t, (Integer) r[1],
                                                   red, (Integer) r[3], (Integer) r[4]));
                    sum += oneHit(p, DamageSource.cactus, h);
                }
                System.out.printf("%11.2f", sum / 4000.0);
            }
            System.out.println();
        }

        System.out.println("\nB. Seconds survived, one landing hit a second, natural regen, 1800 cap.\n");
        System.out.printf("%-10s %4s %6s", "set", "pts", "dur");
        for (int h : hits) System.out.printf("%11s", h + "/hit");
        System.out.println();
        for (Object[] r : sets) {
            int[] red = (int[]) r[2];
            int pts = red[0] + red[1] + red[2] + red[3];
            System.out.printf("%-10s %4d %6d", r[0], pts, r[1]);
            for (int h : hits) {
                int s = fight(r[0] + "_b" + h, (Integer) r[1], red, (Integer) r[3],
                              (Integer) r[4], h, 1800);
                System.out.printf("%11s", s >= 1800 ? ">1800" : String.valueOf(s));
            }
            System.out.println();
        }

        System.out.println("\nC. The King's enrage. TheKing.attdam = TheKing_attack x {1,2,4,8,16} once his");
        System.out.println("   health falls below 2/3, 1/2, 1/4, 1/8 of mygetMaxHealth() -- which returns the");
        System.out.println("   CONFIG health (7000), not the MobProperties-scaled pool -- and only while");
        System.out.println("   player_hit_count < 10. That counter increments on every player hit that lands.\n");
        System.out.printf("%-10s %4s", "set", "pts");
        for (int m : new int[]{1, 2, 4, 8, 16}) System.out.printf("%12s", "x" + m + "=" + 350 * m);
        System.out.println();
        for (Object[] r : sets) {
            int[] red = (int[]) r[2];
            int pts = red[0] + red[1] + red[2] + red[3];
            System.out.printf("%-10s %4d", r[0], pts);
            for (int m : new int[]{1, 2, 4, 8, 16}) {
                int s = fight(r[0] + "_c" + m, (Integer) r[1], red, (Integer) r[3],
                              (Integer) r[4], 350f * m, 1800);
                System.out.printf("%12s", s >= 1800 ? ">1800" : String.valueOf(s));
            }
            System.out.println();
        }
    }
}

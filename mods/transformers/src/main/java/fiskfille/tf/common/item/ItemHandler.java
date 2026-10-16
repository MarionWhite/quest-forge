package fiskfille.tf.common.item;

import java.lang.reflect.Field;
import java.util.List;
import java.util.Map;

import net.minecraft.item.ItemStack;
import net.minecraft.world.World;
import net.minecraftforge.common.MinecraftForge;

import com.google.common.collect.Lists;
import com.google.common.collect.Maps;

import fiskfille.tf.common.data.TFWorldData;
import fiskfille.tf.common.event.ItemHandlerEvent;
import fiskfille.tf.common.event.ItemStitchEvent;

public class ItemHandler
{
    private static Map<Class, String> itemHandlers = Maps.newHashMap();
    public static boolean hasInit = false;

    /**
     * The sub-item ids the recipes and achievements were last built from. load() runs on
     * every world load (each dimension, every login), and the ItemStitchEvent.Post handlers
     * (TFRecipes.register is O(R^2) in the recipe list) depend only on these ids. The ids
     * can genuinely change between loads (each dimension has its own TFWorldData, and a
     * client starts from fresh ids per connection), so re-run them only when they do.
     */
    private static Map<String, Integer> stitchedIds;
    
    public static void init()
    {
        List<String> names = Lists.newLinkedList();
        List<String> domains = Lists.newLinkedList();
        
        MinecraftForge.EVENT_BUS.post(new ItemHandlerEvent.Init(itemHandlers));
        hasInit = true;
        
        for (Map.Entry<Class, String> e : itemHandlers.entrySet())
        {
            for (Field field : e.getKey().getFields())
            {
                String s = field.getType().getName();

                if (s.equals(ItemStack[].class.getName()))
                {
                    names.add(field.getName());
                    domains.add(e.getValue());
                }
            }
        }

        ItemMetaBasic.iconNames = names.toArray(new String[names.size()]);
        ItemMetaBasic.iconDomains = domains.toArray(new String[domains.size()]);
    }

    public static void load(World world)
    {
        TFWorldData data = TFWorldData.get(world);
        Map<String, Integer> ids = Maps.newHashMap();
        MinecraftForge.EVENT_BUS.post(new ItemStitchEvent.Pre(world));
        
        for (Map.Entry<Class, String> e : itemHandlers.entrySet())
        {
            for (Field field : e.getKey().getFields())
            {
                String s = field.getType().getName();

                if (s.equals(ItemStack[].class.getName()))
                {
                    try
                    {
                        ItemStack[] itemstacks = new ItemStack[65];
                        String name = field.getName();
                        int id = data.getNextAvailableId();

                        if (data.subItems.containsKey(name))
                        {
                            id = data.subItems.get(name);
                        }
                        else
                        {
                            data.subItems.put(name, id);
                        }

                        ids.put(name, id);

                        for (int amount = 0; amount < itemstacks.length; ++amount)
                        {
                            itemstacks[amount] = new ItemStack(TFItems.craftingMaterial, amount, id);
                        }

                        field.set(null, itemstacks);
                    }
                    catch (Exception exception)
                    {
                        exception.printStackTrace();
                    }
                }
            }
        }
        
        ItemMetaBasic.subItems = data.subItems;

        if (!ids.equals(stitchedIds))
        {
            stitchedIds = ids;
            MinecraftForge.EVENT_BUS.post(new ItemStitchEvent.Post(world));
        }
    }

    public static boolean matches(ItemStack itemstack, ItemStack[] item)
    {
        if (itemstack != null && item[1].getItem() == itemstack.getItem() && item[1].getItemDamage() == itemstack.getItemDamage())
        {
            return true;
        }

        return false;
    }
}

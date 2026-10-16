package fiskfille.tf;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

import net.minecraft.client.gui.inventory.GuiContainer;
import net.minecraft.client.renderer.EntityRenderer;
import net.minecraft.entity.Entity;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

public class TFReflection
{
    public static Method renderHandMethod;
    private static boolean renderHandFailed;
    public static Method drawSlotMethod;
    public static Field thirdPersonDistanceField;
    
    public static Method setSizeMethod;

    @SideOnly(Side.CLIENT)
    public static void client()
    {
        renderHandMethod = getRenderHandMethod();
        drawSlotMethod = getMethod(GuiContainer.class, "func_146977_a");
        
        thirdPersonDistanceField = getField(EntityRenderer.class, "thirdPersonDistance", "field_78490_B");
    }

    /**
     * OptiFine overloads EntityRenderer.renderHand with a variant taking extra trailing
     * boolean flags, and getMethod() returns whichever overload comes first by name, so
     * invoking it with (float, int) threw IllegalArgumentException every frame. Prefer the
     * exact vanilla signature and only fall back to the extended one.
     */
    @SideOnly(Side.CLIENT)
    private static Method getRenderHandMethod()
    {
        String[] names = {"renderHand", "func_78476_b"};

        for (String name : names)
        {
            try
            {
                Method method = EntityRenderer.class.getDeclaredMethod(name, float.class, int.class);
                method.setAccessible(true);
                return method;
            }
            catch (NoSuchMethodException e)
            {
            }
        }

        for (String name : names)
        {
            for (Method method : EntityRenderer.class.getDeclaredMethods())
            {
                Class[] params = method.getParameterTypes();

                if (method.getName().equals(name) && params.length > 2 && params[0] == float.class && params[1] == int.class)
                {
                    boolean flagsOnly = true;

                    for (int i = 2; i < params.length; ++i)
                    {
                        flagsOnly &= params[i] == boolean.class;
                    }

                    if (flagsOnly)
                    {
                        method.setAccessible(true);
                        return method;
                    }
                }
            }
        }

        TFLog.warn("Could not find EntityRenderer.renderHand; transformer first-person arms will use the vanilla hand");
        return null;
    }

    public static boolean canRenderHand()
    {
        return renderHandMethod != null && !renderHandFailed;
    }

    public static void common()
    {
        setSizeMethod = getMethod(Entity.class, "setSize", "func_70105_a");
    }

    public static Method getMethod(Class clazz, String... names)
    {
        for (String name : names)
        {
            for (Method method : clazz.getDeclaredMethods())
            {
                if (method.getName().equals(name))
                {
                    method.setAccessible(true);
                    return method;
                }
            }
        }

        return null;
    }

    public static Field getField(Class clazz, String... names)
    {
        for (String name : names)
        {
            for (Field field : clazz.getDeclaredFields())
            {
                if (field.getName().equals(name))
                {
                    field.setAccessible(true);
                    return field;
                }
            }
        }

        return null;
    }

    public static Object getField(Object obj, Field field)
    {
        try
        {
            return field.get(obj);
        }
        catch (Exception e)
        {
            e.printStackTrace();
        }

        return null;
    }

    public static void renderHand(EntityRenderer obj, float f, int i)
    {
        if (!canRenderHand())
        {
            return;
        }

        try
        {
            Object[] args = new Object[renderHandMethod.getParameterTypes().length];
            args[0] = f;
            args[1] = i;

            // Extra OptiFine flags (render item / overlay ...): draw everything, as plain renderHand does
            for (int j = 2; j < args.length; ++j)
            {
                args[j] = Boolean.TRUE;
            }

            renderHandMethod.invoke(obj, args);
        }
        catch (Exception e)
        {
            // This runs every frame; one failure means it will keep failing, so log once and stop
            renderHandFailed = true;
            TFLog.error("Disabling the transformer first-person hand hook: %s", e);
            e.printStackTrace();
        }
    }

    public static void setSize(Entity obj, float f, float f1)
    {
        try
        {
            setSizeMethod.invoke(obj, f, f1);
        }
        catch (Exception e)
        {
            e.printStackTrace();
        }
    }

    public static Object getField(Field field, Object owner)
    {
        try
        {
            return field.get(owner);
        }
        catch (Exception e)
        {
            e.printStackTrace();
        }

        return null;
    }

    public static void setField(Field field, Object owner, Object arg)
    {
        try
        {
            field.set(owner, arg);
        }
        catch (Exception e)
        {
            e.printStackTrace();
        }
    }

    public static Object getMethod(Method method, Object owner, Object... args)
    {
        try
        {
            return method.invoke(owner, args);
        }
        catch (Exception e)
        {
            e.printStackTrace();
        }

        return null;
    }

    public static void invokeMethod(Method method, Object owner, Object... args)
    {
        try
        {
            method.invoke(owner, args);
        }
        catch (Exception e)
        {
            e.printStackTrace();
        }
    }
}

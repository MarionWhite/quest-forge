package com.questforge;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import ivorius.reccomplex.json.NbtToJson;

import org.apache.logging.log4j.LogManager;

/**
 * Called from Recurrent Complex's patched NBT serializers; see RecNbtTransformer.
 */
public final class RecNbtFix {

    /** Keys of RC's "safe" NBT wrapper (NbtToJson.createSafeNBTSerializer). */
    private static final String TYPE_KEY = "nbtType";
    private static final String OBJECT_KEY = "nbt";

    /**
     * Whether the Gson in use checks an adapter's result against the requested
     * type. ToNumberPolicy arrived in Gson 2.8.9, after 2.2.4 (Forge's) and
     * before the 2.10 check; any Gson that has it gets the fix, Forge's never.
     */
    private static final boolean MODERN_GSON;

    /**
     * net.minecraft.nbt.NBTBase, looked up by name: qf-tweaks compiles against
     * the obfuscated game jar, where the class has another name. At run time
     * class names are deobfuscated before any mod code runs.
     */
    private static volatile Class<?> nbtBase;

    static {
        boolean modern;
        try {
            Class.forName("com.google.gson.ToNumberPolicy", false, JsonElement.class.getClassLoader());
            modern = true;
        } catch (Throwable t) {
            modern = false;
        }
        MODERN_GSON = modern;
        LogManager.getLogger("QuestForgeTweaks").info(modern
                ? "[QuestForgeTweaks] Recurrent Complex: Gson checks adapter results; wrapped NBT tags are "
                        + "requested as NBTBase."
                : "[QuestForgeTweaks] Recurrent Complex: Gson 2.2.x; NBT decoding unchanged.");
    }

    private RecNbtFix() {
    }

    /** Same contract as NbtToJson.getNBTTypeSmart, except for wrappers on a modern Gson. */
    @SuppressWarnings("rawtypes")
    public static Class type(JsonElement element) {
        if (MODERN_GSON && element != null && element.isJsonObject()) {
            JsonObject obj = element.getAsJsonObject();
            if (obj.has(TYPE_KEY) && obj.has(OBJECT_KEY)) {
                Class<?> base = nbtBase;
                if (base == null) {
                    try {
                        base = Class.forName("net.minecraft.nbt.NBTBase", false, RecNbtFix.class.getClassLoader());
                    } catch (ClassNotFoundException e) {
                        return NbtToJson.getNBTTypeSmart(element);
                    }
                    nbtBase = base;
                }
                return base;
            }
        }
        return NbtToJson.getNBTTypeSmart(element);
    }
}

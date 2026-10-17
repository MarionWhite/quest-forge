package com.questforge;

import java.io.IOException;
import java.io.Reader;
import java.lang.reflect.Type;
import java.util.Map;

import com.google.gson.Gson;
import com.google.gson.internal.$Gson$Types;

import org.apache.logging.log4j.LogManager;

/**
 * Called from AsieLib's patched NicknameRepository.loadNicknames; see AsieNickTransformer.
 */
public final class AsieNickFix {

    private AsieNickFix() {
    }

    /**
     * gson.fromJson(reader, type), and if that throws, the same text parsed as
     * a Map<String,String>. Either way the reader is read to the end and closed
     * (AsieLib never closed it, which kept nicknames.json open until GC).
     */
    public static Object fromJson(Gson gson, Reader reader, Type type) throws IOException {
        String text;
        try {
            StringBuilder sb = new StringBuilder();
            char[] buf = new char[4096];
            for (int n; (n = reader.read(buf)) != -1; ) {
                sb.append(buf, 0, n);
            }
            text = sb.toString();
        } finally {
            reader.close();
        }
        try {
            return gson.fromJson(text, type);
        } catch (RuntimeException e) {
            Type map = $Gson$Types.newParameterizedTypeWithOwner(null, Map.class, String.class, String.class);
            Object result = gson.fromJson(text, map);
            LogManager.getLogger("QuestForgeTweaks").info("[QuestForgeTweaks] AsieLib nicknames: Gson could not "
                    + "build {} ({}); read them as a Map<String,String> instead.", type, e.getMessage());
            return result;
        }
    }
}

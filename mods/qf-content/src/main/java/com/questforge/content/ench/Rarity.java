package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.util.EnumChatFormatting;

/**
 * Rarity drives the book's colour and the range its success/destroy chances are
 * rolled from. The chances are rolled once when a book is generated and stored on
 * that book, so two books of the same enchant are not interchangeable.
 */
public enum Rarity {

    COMMON(EnumChatFormatting.WHITE, 75, 90, 0, 5),
    UNCOMMON(EnumChatFormatting.GREEN, 65, 80, 5, 12),
    RARE(EnumChatFormatting.BLUE, 50, 70, 12, 22),
    EPIC(EnumChatFormatting.DARK_PURPLE, 35, 55, 22, 35),
    LEGENDARY(EnumChatFormatting.GOLD, 20, 40, 35, 50);

    public final EnumChatFormatting colour;
    public final int minSuccess;
    public final int maxSuccess;
    public final int minDestroy;
    public final int maxDestroy;

    Rarity(EnumChatFormatting colour, int minSuccess, int maxSuccess, int minDestroy, int maxDestroy) {
        this.colour = colour;
        this.minSuccess = minSuccess;
        this.maxSuccess = maxSuccess;
        this.minDestroy = minDestroy;
        this.maxDestroy = maxDestroy;
    }

    public int rollSuccess(Random rand) {
        return minSuccess + rand.nextInt(maxSuccess - minSuccess + 1);
    }

    public int rollDestroy(Random rand) {
        return minDestroy + rand.nextInt(maxDestroy - minDestroy + 1);
    }

    public String displayName() {
        return colour.toString() + name().charAt(0) + name().substring(1).toLowerCase();
    }
}

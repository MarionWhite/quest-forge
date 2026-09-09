package com.questforge.commands;

import net.minecraft.entity.player.EntityPlayerMP;

/** The /pv command: opens the player's own vault. */
public class VaultAccess extends Unlockable {

    public VaultAccess() {
        super("vault", "pv", "Personal Vault",
                "Opens a private 54-slot vault from anywhere.",
                "",
                "It is yours alone and exists nowhere in the world, so",
                "nothing can be stolen from it and nothing can break it.",
                "",
                "This is NOT an ender chest. It shares no slots with your",
                "ender inventory, with EnderStorage frequencies, or with",
                "anything else that reads them -- so it cannot collide",
                "with a setup you already have.",
                "",
                "Contents follow you through death and dimension changes.");
    }

    @Override
    public String run(EntityPlayerMP player, String name, String[] args) {
        player.openGui(QuestForgeCommands.instance, QuestForgeCommands.GUI_VAULT,
                player.worldObj, 0, 0, 0);
        return null;
    }
}

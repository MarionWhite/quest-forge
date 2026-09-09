package com.questforge.commands;

import com.questforge.commands.vault.GuiVault;
import com.questforge.commands.vault.VaultContainer;
import com.questforge.commands.vault.VaultInventory;

import cpw.mods.fml.common.network.IGuiHandler;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.world.World;

/**
 * Opens the vault on both sides.
 *
 * A fresh VaultInventory is built per open, which is what keeps the two sides
 * honest: the server's copy is loaded from the player's NBT and is the one that
 * saves, and the client's is a shell that the container syncs into.
 */
public class GuiHandler implements IGuiHandler {

    @Override
    public Object getServerGuiElement(int id, EntityPlayer player, World world, int x, int y, int z) {
        if (id == QuestForgeCommands.GUI_VAULT) {
            return new VaultContainer(player, new VaultInventory(player));
        }
        return null;
    }

    @Override
    public Object getClientGuiElement(int id, EntityPlayer player, World world, int x, int y, int z) {
        if (id == QuestForgeCommands.GUI_VAULT) {
            return new GuiVault(player, new VaultInventory(player));
        }
        return null;
    }
}

package com.questforge.commands.vault;

import net.minecraft.client.gui.inventory.GuiContainer;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ResourceLocation;

import org.lwjgl.opengl.GL11;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * The vault screen.
 *
 * Borrows vanilla's generic 54-slot chest texture rather than shipping its own.
 * That sheet is exactly this layout, every resource pack in existence themes it,
 * and a bespoke copy would be one more thing to keep in step with the pack's
 * branding for no visible gain.
 */
@SideOnly(Side.CLIENT)
public class GuiVault extends GuiContainer {

    private static final ResourceLocation CHEST =
            new ResourceLocation("textures/gui/container/generic_54.png");

    public GuiVault(EntityPlayer player, VaultInventory vault) {
        super(new VaultContainer(player, vault));
        this.xSize = 176;
        this.ySize = 18 + VaultInventory.ROWS * 18 + 13 + 76;
    }

    @Override
    protected void drawGuiContainerForegroundLayer(int mouseX, int mouseY) {
        this.fontRendererObj.drawString("Personal Vault", 8, 6, 0x404040);
        this.fontRendererObj.drawString("Inventory", 8, this.ySize - 94, 0x404040);
    }

    @Override
    protected void drawGuiContainerBackgroundLayer(float partialTicks, int mouseX, int mouseY) {
        GL11.glColor4f(1F, 1F, 1F, 1F);
        this.mc.getTextureManager().bindTexture(CHEST);
        int x = (this.width - this.xSize) / 2;
        int y = (this.height - this.ySize) / 2;

        drawTexturedModalRect(x, y, 0, 0, this.xSize, VaultInventory.ROWS * 18 + 17);
        drawTexturedModalRect(x, y + VaultInventory.ROWS * 18 + 17, 0, 126, this.xSize, 96);
    }
}

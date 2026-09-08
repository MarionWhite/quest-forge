import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.world.World;

/** Concrete so Unsafe can allocate it; never constructed, so no World is touched. */
public class ProbePlayer extends EntityPlayer {
    public ProbePlayer(World w) { super(w, null); }
    @Override public void addChatMessage(net.minecraft.util.IChatComponent c) {}
    @Override public boolean canCommandSenderUseCommand(int l, String s) { return false; }
    @Override public net.minecraft.util.ChunkCoordinates getPlayerCoordinates() { return null; }
}

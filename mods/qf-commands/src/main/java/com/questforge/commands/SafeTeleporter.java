package com.questforge.commands;

import net.minecraft.block.material.Material;
import net.minecraft.entity.Entity;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.ChunkCoordinates;
import net.minecraft.util.MathHelper;
import net.minecraft.world.Teleporter;
import net.minecraft.world.WorldServer;

/**
 * Puts the player down somewhere they can stand, and builds nothing.
 *
 * Vanilla's Teleporter looks for a nether portal near the destination and
 * constructs one if it cannot find it. That is wrong here twice over: a command
 * is not a portal, and quarrying a portal frame into someone's Twilight Forest
 * is a lasting change to their world in exchange for a chat message.
 *
 * So all three portal methods are refused and the arrival is chosen instead, by
 * {@link #findArrival}, which is called once by {@link DimensionTravel#refuse}
 * and the answer handed to this teleporter. Deciding up front is what lets the
 * command decline a dimension with no floor rather than dropping someone into
 * the void, and it removes any chance of the checked spot and the landed spot
 * disagreeing.
 */
public class SafeTeleporter extends Teleporter {

    /**
     * Columns to try around the target, as (x, z) offsets.
     *
     * A single column is too brittle a test: standing over a one-block gap
     * would reject a dimension that is almost entirely solid.
     */
    private static final int[][] RINGS = {
        {   0,   0 },
        {   4,   0 }, {  -4,   0 }, {   0,   4 }, {   0,  -4 },
        {  16,  16 }, { -16,  16 }, {  16, -16 }, { -16, -16 },
    };

    /** Kept here because Teleporter's own copy is private. */
    private final WorldServer world;

    private final int x;
    private final int y;
    private final int z;

    public SafeTeleporter(WorldServer world, int[] arrival) {
        super(world);
        this.world = world;
        this.x = arrival[0];
        this.y = arrival[1];
        this.z = arrival[2];
    }

    /**
     * Sends the player to this teleporter's world. Every command goes through
     * here rather than calling transferPlayerToDimension itself.
     *
     * <h3>Leaving the End</h3>
     *
     * Vanilla's transferEntityToWorld treats "coming from dimension 1" as the
     * credits-and-respawn path, and on that path it skips both placeInPortal
     * and spawnEntityInWorld. The player's world reference is switched, but
     * they are never added to the new world's entity list: the client sees
     * terrain, the server ticks nobody, and other players cannot see them --
     * a ghost until they relog. So when the trip starts in the End, the two
     * steps vanilla skipped are done here, at the spot placeInPortal would
     * have chosen, and the client is told where it actually is.
     */
    public void transfer(EntityPlayerMP player, int dimension) {
        int from = player.dimension;

        MinecraftServer.getServer().getConfigurationManager()
                .transferPlayerToDimension(player, dimension, this);

        if (from != 1) {
            return;
        }

        // Positioned before spawning, not after, so the player is filed under
        // the chunk they are going to stand in rather than the one matching
        // their old End coordinates.
        player.setLocationAndAngles(this.x + 0.5D, this.y, this.z + 0.5D,
                player.rotationYaw, player.rotationPitch);
        player.motionX = 0D;
        player.motionY = 0D;
        player.motionZ = 0D;
        player.fallDistance = 0F;

        // Checked so that a future Forge, or a coremod that already patches
        // this, does not get the player added twice -- a duplicate entry in
        // loadedEntityList means a player ticked twice per tick.
        if (!this.world.loadedEntityList.contains(player)) {
            this.world.spawnEntityInWorld(player);
            this.world.updateEntityWithOptionalForce(player, false);
        }

        player.playerNetServerHandler.setPlayerLocation(player.posX, player.posY, player.posZ,
                player.rotationYaw, player.rotationPitch);
    }

    /**
     * Where the player should come out, or null if this dimension has nowhere
     * to stand.
     *
     * Three candidates, in order of how organic the arrival feels:
     *
     * <ol>
     * <li>The coordinates a portal would have used -- the player's own
     *     position, through the movement-factor ratio, so the Nether is still
     *     eight times closer to the origin.</li>
     * <li>The dimension's entrance portal, if it names one. This is what makes
     *     the End work: its island is around the origin, so a player standing
     *     at overworld x=238 aims at open void, while vanilla has always
     *     special-cased dimension 1 to its obsidian platform.</li>
     * <li>The dimension's spawn point, which is a floor by construction almost
     *     everywhere.</li>
     * </ol>
     *
     * Chunks get generated by the search. That is unavoidable -- an ungenerated
     * chunk reads as air all the way down, indistinguishable from a dimension
     * with no ground -- and harmless, since the answer decides whether the
     * player is about to be standing in them.
     *
     * @return { x, y, z } to arrive at, or null to refuse the trip
     */
    public static int[] findArrival(EntityPlayerMP player, WorldServer to) {
        double ratio = player.worldObj.provider.getMovementFactor()
                / to.provider.getMovementFactor();

        int px = MathHelper.floor_double(
                MathHelper.clamp_double(player.posX * ratio, -29999872D, 29999872D));
        int pz = MathHelper.floor_double(
                MathHelper.clamp_double(player.posZ * ratio, -29999872D, 29999872D));

        int[] found = search(to, px, pz);

        if (found != null) {
            return found;
        }

        ChunkCoordinates entrance = to.provider.getEntrancePortalLocation();

        if (entrance != null) {
            found = search(to, entrance.posX, entrance.posZ);

            if (found != null) {
                return found;
            }
        }

        ChunkCoordinates spawn = to.getSpawnPoint();

        return spawn == null ? null : search(to, spawn.posX, spawn.posZ);
    }

    /** Scans the rings around one target, generating chunks as it goes. */
    private static int[] search(WorldServer world, int x, int z) {
        for (int[] offset : RINGS) {
            int cx = x + offset[0];
            int cz = z + offset[1];

            world.theChunkProviderServer.loadChunk(cx >> 4, cz >> 4);

            int y = scanColumn(world, cx, cz);

            if (y != Integer.MIN_VALUE) {
                return new int[] { cx, y, cz };
            }
        }

        return null;
    }

    /**
     * Top-down scan for two free blocks over something solid.
     *
     * Starts two below the ceiling rather than at it. The Nether is why: its
     * actual height is 128, so the topmost block is the bedrock roof, and the
     * two blocks "above" it are outside the world -- where getBlock answers
     * air. Scanned from the very top that roof reads as a perfect landing and
     * every trip to the Nether ends up standing on it.
     */
    private static int scanColumn(WorldServer world, int x, int z) {
        int top = Math.min(world.getActualHeight() - 1, 255);

        for (int y = top - 2; y > 1; y--) {
            if (!world.getBlock(x, y, z).getMaterial().blocksMovement()) {
                continue;
            }

            if (free(world, x, y + 1, z) && free(world, x, y + 2, z)) {
                return y + 1;
            }
        }

        return Integer.MIN_VALUE;
    }

    /**
     * Somewhere a player can occupy.
     *
     * Liquids are excluded as well as solids: lava does not block movement, so
     * without this the scan happily reports the stone under a lava lake as
     * ground and arrives the player inside the lake.
     */
    private static boolean free(WorldServer world, int x, int y, int z) {
        Material material = world.getBlock(x, y, z).getMaterial();
        return !material.blocksMovement() && !material.isLiquid();
    }

    @Override
    public void placeInPortal(Entity entity, double x, double y, double z, float rotationYaw) {
        entity.setLocationAndAngles(this.x + 0.5D, this.y, this.z + 0.5D,
                entity.rotationYaw, entity.rotationPitch);
        entity.motionX = 0D;
        entity.motionY = 0D;
        entity.motionZ = 0D;
        entity.fallDistance = 0F;
    }

    @Override
    public boolean placeInExistingPortal(Entity entity, double x, double y, double z, float rotationYaw) {
        placeInPortal(entity, x, y, z, rotationYaw);
        return true;
    }

    @Override
    public boolean makePortal(Entity entity) {
        return false;
    }

    @Override
    public void removeStalePortalLocations(long worldTime) {
    }
}

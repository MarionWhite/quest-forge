# =============================================================================
# CrazyCraft 4 - Game Balance Recipe Gating
# =============================================================================
# This script gates overpowered items behind boss drops to maintain progression
# and prevent early-game cheese.
# =============================================================================

import mods.projecte.PhiloStone;

print("[CrazyCraft4] Loading recipe gating...");

# =============================================================================
# PROJECTE GATING - These items break the game if obtained too early
# =============================================================================

# --- PHILOSOPHER'S STONE ---
# Gated behind: Twilight Lich (requires Lich Scepter)
# Original recipe removed, new recipe requires proof of boss kill

recipes.remove(<ProjectE:item.pe_philosophers_stone>);
recipes.addShaped(<ProjectE:item.pe_philosophers_stone>, [
    [<minecraft:glowstone_dust>, <minecraft:redstone>, <minecraft:glowstone_dust>],
    [<minecraft:redstone>, <TwilightForest:item.scepterZombie>, <minecraft:redstone>],
    [<minecraft:glowstone_dust>, <minecraft:redstone>, <minecraft:glowstone_dust>]
]);
# Note: TwilightForest:item.lich:1 is the Lich Scepter (Zombie)

print("[CrazyCraft4] Philosopher's Stone now requires Lich Scepter!");

# --- TRANSMUTATION TABLE ---
# Gated behind: Mobzilla (requires Mobzilla Scales)
# This is the main game-breaker - infinite resources

recipes.remove(<ProjectE:transmutation_table>);
recipes.addShaped(<ProjectE:transmutation_table>, [
    [<OreSpawn:OreSpawn_BlockMobzillaScaleBlock>, <minecraft:obsidian>, <OreSpawn:OreSpawn_BlockMobzillaScaleBlock>],
    [<minecraft:obsidian>, <ProjectE:item.pe_philosophers_stone>, <minecraft:obsidian>],
    [<OreSpawn:OreSpawn_BlockMobzillaScaleBlock>, <minecraft:obsidian>, <OreSpawn:OreSpawn_BlockMobzillaScaleBlock>]
]);

print("[CrazyCraft4] Transmutation Table now requires Mobzilla Scales!");

# --- DARK MATTER ---
# Gated behind: the Royal Guardian Sword, which The King's guardian drops.
# The King itself has no drop item in OreSpawn, so the sword is the proof of kill.
# .reuse() leaves the sword in the grid, so this gates on owning it, not spending it.
# .anyDamage() accepts a sword that has already seen combat.

recipes.remove(<ProjectE:item.pe_matter>);
recipes.addShaped(<ProjectE:item.pe_matter>, [
    [<ProjectE:fuel_block:1>, <ProjectE:fuel_block:1>, <ProjectE:fuel_block:1>],
    [<ProjectE:fuel_block:1>, <OreSpawn:OreSpawn_Royal>.anyDamage().reuse(), <ProjectE:fuel_block:1>],
    [<ProjectE:fuel_block:1>, <ProjectE:fuel_block:1>, <ProjectE:fuel_block:1>]
]);
# Note: ProjectE:fuel_block:1 is Mobius Fuel Block

print("[CrazyCraft4] Dark Matter now requires the Royal Guardian Sword (not consumed)!");

# --- RED MATTER ---
# Gated behind: The Queen (requires Queen Scales)
# Ultimate ProjectE content requires ultimate boss kill

recipes.remove(<ProjectE:item.pe_matter:1>);
recipes.addShaped(<ProjectE:item.pe_matter:1>, [
    [<ProjectE:fuel_block:2>, <ProjectE:item.pe_matter>, <ProjectE:fuel_block:2>],
    [<ProjectE:item.pe_matter>, <OreSpawn:OreSpawn_QueenScale>, <ProjectE:item.pe_matter>],
    [<ProjectE:fuel_block:2>, <ProjectE:item.pe_matter>, <ProjectE:fuel_block:2>]
]);
# Note: ProjectE:fuel_block:2 is Aeternalis Fuel Block

print("[CrazyCraft4] Red Matter now requires Queen Scale!");

# =============================================================================
# ENERGY COLLECTORS & CONDENSERS - Also need gating
# =============================================================================

# --- ENERGY COLLECTOR MK1 ---
# Requires at least Philosopher's Stone progression
recipes.remove(<ProjectE:collector_mk1>);
recipes.addShaped(<ProjectE:collector_mk1>, [
    [<minecraft:glowstone>, <minecraft:glass>, <minecraft:glowstone>],
    [<minecraft:glass>, <TwilightForest:item.fieryBlood>, <minecraft:glass>],
    [<minecraft:glowstone>, <ProjectE:item.pe_matter>, <minecraft:glowstone>]
]);

print("[CrazyCraft4] Energy Collector MK1 now requires Fiery Blood and Dark Matter!");

# --- ENERGY CONDENSER ---
# Major automation piece - requires substantial progression
recipes.remove(<ProjectE:condenser_mk1>);
recipes.addShaped(<ProjectE:condenser_mk1>, [
    [<minecraft:obsidian>, <ProjectE:item.pe_matter>, <minecraft:obsidian>],
    [<ProjectE:item.pe_matter>, <minecraft:diamond_block>, <ProjectE:item.pe_matter>],
    [<minecraft:obsidian>, <ProjectE:item.pe_matter>, <minecraft:obsidian>]
]);

print("[CrazyCraft4] Energy Condenser now requires Dark Matter!");

# =============================================================================
# KLEIN STARS - No gating needed, EMC storage is fine
# =============================================================================

# Klein Stars are fine as-is since you need the transmutation table first

# =============================================================================
# OTHER POTENTIAL GAME BREAKERS
# =============================================================================

# Uncomment these if you find other items that need gating:

# --- SUPERCHARGED GRAVITY GUN (if too OP early) ---
# recipes.remove(<GraviGun:superGravityGun>);
# recipes.addShaped(<GraviGun:superGravityGun>, [
#     [null, <minecraft:nether_star>, null],
#     [<minecraft:nether_star>, <GraviGun:gravityGun>, <minecraft:nether_star>],
#     [null, <minecraft:nether_star>, null]
# ]);

print("[CrazyCraft4] Recipe gating complete! Good luck, adventurer!");
print("[CrazyCraft4] Progression: Lich -> Mobzilla -> Royal Guardian -> Queen");


// Block IDs from block.properties -> material index (lib/common.glsl).
// The numbers are tools/shaders/gen_surface_pack.py's QF_IDS table: change both together.
// Profiles and options never change these (rule 18).

int materialFromBlockId(int id) {
    if (id == 1001) return MAT_WATER;
    if (id == 1002) return MAT_LAVA;
    if (id == 1010) return MAT_LEAVES;
    if (id == 1011) return MAT_PLANT;
    if (id == 1012) return MAT_WEB;
    if (id == 1020) return MAT_EMISSIVE;
    if (id == 1030) return MAT_GLASS;
    if (id == 1040) return MAT_METAL;
    if (id == 1041) return MAT_POLISHED;
    if (id == 1050) return MAT_ORE;
    return MAT_NONE;
}

bool isFoliage(int mat) {
    return mat == MAT_LEAVES || mat == MAT_PLANT;
}

// Debug view colours (QF_DEBUG_VIEW 1): one distinct hue per material.
vec3 materialDebugColor(int mat) {
    if (mat == MAT_WATER)    return vec3(0.1, 0.3, 1.0);
    if (mat == MAT_LAVA)     return vec3(1.0, 0.3, 0.0);
    if (mat == MAT_LEAVES)   return vec3(0.0, 0.9, 0.1);
    if (mat == MAT_PLANT)    return vec3(0.6, 1.0, 0.2);
    if (mat == MAT_WEB)      return vec3(0.9, 0.9, 0.9);
    if (mat == MAT_EMISSIVE) return vec3(1.0, 0.9, 0.2);
    if (mat == MAT_GLASS)    return vec3(0.5, 0.9, 1.0);
    if (mat == MAT_METAL)    return vec3(0.8, 0.5, 0.9);
    if (mat == MAT_POLISHED) return vec3(1.0, 0.6, 0.7);
    if (mat == MAT_ORE)      return vec3(1.0, 0.0, 0.8);
    if (mat == MAT_ENTITY)   return vec3(1.0, 0.5, 0.0);
    if (mat == MAT_FORWARD)  return vec3(0.4, 0.4, 0.4);
    return vec3(0.12);
}

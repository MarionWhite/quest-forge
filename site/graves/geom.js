// Leg geometry for the Krypt: a leg has an origin lattice point (px, pz) and a heading (N, W or E). Local a runs across
// (right is +), b along. Shared by the plan, the world builder and the dressers.
export const SLOT_STEP = 4;
export const STAIR_LANDING = 6, STAIR_LEN = 12, STAIR_DROP = 6, CHASM_DEPTH = 4, FORT_DEPTH = 2, PASSAGE_LEN = 9;

export function legMap(leg, a, b) {
  if (leg.h === "N") return [leg.px + a, leg.pz - b];
  if (leg.h === "W") return [leg.px - b, leg.pz - a];
  return [leg.px + b, leg.pz + a];
}
export function legLocal(leg, x, z) {
  if (leg.h === "N") return [x - leg.px, leg.pz - z];
  if (leg.h === "W") return [leg.pz - z, leg.px - x];
  return [z - leg.pz, x - leg.px];
}
export const legYaw = (leg) => (leg.h === "N" ? 0 : leg.h === "W" ? Math.PI / 2 : -Math.PI / 2);
export const legCell = (leg, lu, lv) => { const [x, z] = legMap(leg, lu + 0.5, lv + 0.5); return [Math.floor(x), Math.floor(z)]; };
export const legDir = (leg) => (leg.h === "N" ? [0, -1] : leg.h === "W" ? [-1, 0] : [1, 0]);
export const turnOf = (from, to) => (from === "N" ? (to === "W" ? -1 : 1) : (from === "W" ? 1 : -1));

// Floor top of leg row lv (an integer y); the stairs step down every two rows.
export function floorTop(leg, lv) {
  if (!leg.stairs) return leg.y0;
  const t = lv - leg.stairsAt;
  if (t < 0) return leg.y0;
  return leg.y0 - Math.min(STAIR_DROP, Math.floor(t / 2) + 1);
}
// Camera floor level, continuous (a ramp over the steps).
export function floorSmooth(leg, b) {
  if (!leg.stairs) return leg.y0;
  const t = (b - leg.stairsAt) / 2 - 0.5;
  return leg.y0 - Math.max(0, Math.min(STAIR_DROP, t + 0.5));
}

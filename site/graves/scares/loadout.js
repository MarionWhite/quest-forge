// The explorer's kit: the one loadout every scare's HUD, first-person hand and dropped items come from (round 8b, the
// owner: "the hotbar that appears on the screen usually doesn't match what the character has or make any sense").
// A crypt explorer's hotbar: an iron sword, an iron pickaxe, a stack of torches, bread and apples; the rest empty.
// The selected slot is what the hand holds. No scene shows a hand with nothing in it (the 1.7.10 bare arm is not
// drawn), so a scene whose hand is empty has an empty slot selected; a scene that takes an item out selects its slot
// at that moment (the Zombie Pigman's pickaxe).
//   SLOTS[i]         { item, img, n } or null (the nine hotbar slots, left to right)
//   STATS            hunger (0..20, half shanks), XP level and bar: a fed explorer some way into the crypt
//   heldAt(held, t)  the item in hand at t: held is an item id, null (empty hand), or [[t0, item], ...] in time order
//   slotOf(item)     the hotbar slot for an item (null: the empty slot an empty hand has selected)
//   HELD[id]         what each scene's hand holds, for a scene that does not say (S.held wins)
export const SLOTS = [
  { item: "sword", img: "item_iron_sword", n: 1 },
  { item: "pickaxe", img: "mc:items/iron_pickaxe", n: 1 },
  { item: "torch", img: "k:torch_on", n: 23 },
  { item: "bread", img: "item_bread", n: 6 },
  { item: "apple", img: "item_apple", n: 3 },
  null, null, null, null
];
export const EMPTY = SLOTS.indexOf(null);   // the first empty slot
export const STATS = { food: 17, xpLevel: 7, xpBar: 0.37 };
export const ITEMS = SLOTS.filter(Boolean);   // the filled slots, in order (what a blast scatters, what burns)

export function slotOf(item) {
  if (item == null) return EMPTY;
  const i = SLOTS.findIndex((s) => s && s.item === item);
  return i < 0 ? EMPTY : i;
}
export function heldAt(held, t) {
  if (!Array.isArray(held)) return held ?? null;
  let cur = null;
  for (const [t0, item] of held) { if (t < t0) break; cur = item; }
  return cur;
}
// Every scene and its hand (the audit, round 8b). Empty: nothing is drawn in the hand.
export const HELD = {
  Zombie: null, Skeleton: null, Creeper: null, Spider: null, CaveSpider: null, Enderman: null, Witch: null, Slime: null,
  Silverfish: null, Blaze: null, Ghast: null, MagmaCube: null,
  PigZombie: "pickaxe",          // pigman.js says when: empty until the pickaxe comes up for the ore (S.held)
  WitherSkeleton: "sword",       // your shadow on the wall holds the iron sword
  LavaFall: null,                // both hands on the rim
  DrownedGrab: null
};

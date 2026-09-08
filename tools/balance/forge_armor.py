"""Verbatim port of Forge 1.7.10 ISpecialArmor.ArmorProperties, plus the
durability spend it performs as a side effect.

EntityPlayer.damageEntity calls ApplyArmor; EntityLivingBase.damageEntity calls
vanilla applyArmorCalculations. Players take the first path, mobs the second.
Transcribed line-for-line from
build/rfg/minecraft-src/java/net/minecraftforge/common/ISpecialArmor.java --
including the `else` branch of StandardizeList, which applies the remaining-
durability cap even when the absorption ratios total one or less, and the
Arrays.sort that orders pieces by AbsorbMax*100/AbsorbRatio ascending.
"""
import random

MAX_DAMAGE_ARRAY = [11, 16, 15, 13]     # ItemArmor.ArmorMaterial.getDurability


class Piece:
    """One worn ItemArmor stack."""
    def __init__(self, reduce_amount, max_damage, unbreaking=0):
        self.damageReduceAmount = reduce_amount
        self.maxDamage = max_damage
        self.itemDamage = 0
        self.unbreaking = unbreaking
        self.broken = False

    def damage_item(self, amount, rng):
        """ItemStack.damageItem -> attemptDamageItem, with EnchantmentDurability."""
        if amount > 0 and self.unbreaking > 0:
            negated = 0
            for _ in range(amount):
                # negateDamage: armour rolls a 60% chance of no protection at all
                if rng.random() < 0.6:
                    continue
                if rng.randrange(self.unbreaking + 1) > 0:
                    negated += 1
            amount -= negated
            if amount <= 0:
                return
        self.itemDamage += amount
        if self.itemDamage > self.maxDamage:      # attemptDamageItem returns true
            self.broken = True
            self.itemDamage = 0


class Prop:
    __slots__ = ("Priority", "AbsorbRatio", "AbsorbMax", "Slot")

    def __init__(self, priority, ratio, mx, slot):
        self.Priority, self.AbsorbRatio, self.AbsorbMax, self.Slot = priority, ratio, mx, slot

    def sort_key(self):
        # compareTo: Priority descending, then AbsorbMax*100/AbsorbRatio ascending
        rank = 0 if self.AbsorbRatio == 0 else self.AbsorbMax * 100.0 / self.AbsorbRatio
        return (-self.Priority, int(rank))


def StandardizeList(armor, damage):
    armor.sort(key=Prop.sort_key)
    start = 0
    total = 0.0
    priority = armor[0].Priority
    pStart = 0
    pChange = False
    pFinished = False

    x = 0
    while x < len(armor):
        total += armor[x].AbsorbRatio
        if x == len(armor) - 1 or armor[x].Priority != priority:
            if armor[x].Priority != priority:
                total -= armor[x].AbsorbRatio
                x -= 1
                pChange = True
            if total > 1:
                y = start
                while y <= x:
                    newRatio = armor[y].AbsorbRatio / total
                    if newRatio * damage > armor[y].AbsorbMax:
                        armor[y].AbsorbRatio = armor[y].AbsorbMax / damage
                        total = sum(armor[z].AbsorbRatio for z in range(pStart, y + 1))
                        start = y + 1
                        x = y
                        break
                    else:
                        armor[y].AbsorbRatio = newRatio
                        pFinished = True
                    y += 1
                if pChange and pFinished:
                    damage -= damage * total
                    total = 0.0
                    start = x + 1
                    priority = armor[start].Priority
                    pStart = start
                    pChange = False
                    pFinished = False
                    if damage <= 0:
                        for y in range(x + 1, len(armor)):
                            armor[y].AbsorbRatio = 0.0
                        break
            else:
                # The branch I had missed. The durability cap binds here too.
                for y in range(start, x + 1):
                    total -= armor[y].AbsorbRatio
                    if damage * armor[y].AbsorbRatio > armor[y].AbsorbMax:
                        armor[y].AbsorbRatio = armor[y].AbsorbMax / damage
                    total += armor[y].AbsorbRatio
                damage -= damage * total
                total = 0.0
                if x != len(armor) - 1:
                    start = x + 1
                    priority = armor[start].Priority
                    pStart = start
                    pChange = False
                    if damage <= 0:
                        for y in range(x + 1, len(armor)):
                            armor[y].AbsorbRatio = 0.0
                        break
        x += 1


def apply_armor(pieces, raw, rng=None, spend=True, unblockable=False):
    """pieces: list of Piece. Returns damage that survives the armour step."""
    damage = raw * 25.0
    props = []
    for i, p in enumerate(pieces):
        if p is None or p.broken or unblockable:
            continue
        props.append(Prop(0, p.damageReduceAmount / 25.0,
                          p.maxDamage + 1 - p.itemDamage, i))
    if props:
        StandardizeList(props, damage)
        level = props[0].Priority
        ratio = 0.0
        for prop in props:
            if level != prop.Priority:
                damage -= damage * ratio
                ratio = 0.0
                level = prop.Priority
            ratio += prop.AbsorbRatio
            absorb = damage * prop.AbsorbRatio
            if absorb > 0 and spend:
                itemDamage = 1 if absorb / 25.0 < 1 else int(absorb / 25.0)
                pieces[prop.Slot].damage_item(itemDamage, rng or random)
        damage -= damage * ratio
    return damage / 25.0


def make_set(reductions, durability_factor, unbreaking=0):
    return [Piece(reductions[t], MAX_DAMAGE_ARRAY[t] * durability_factor, unbreaking)
            for t in range(4)]

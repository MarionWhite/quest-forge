"""The exact logic that goes into Mitigation.afterArmour, held next to the
verbatim transcription so the two can be differential-tested."""
import forge_armor as fa

def java_after_armour(pieces, raw):
    scaled = raw * 25.0
    ratios, caps = [], []
    for p in pieces:
        if p.broken: continue
        ratios.append(p.damageReduceAmount / 25.0)
        caps.append(p.maxDamage + 1 - p.itemDamage)
    n = len(ratios)
    if n == 0: return raw
    order = sorted(range(n), key=lambda i: int(caps[i] * 100.0 / ratios[i]) if ratios[i] else 0)
    ratios = [ratios[i] for i in order]
    caps = [caps[i] for i in order]

    start = 0
    while True:
        total = sum(ratios)
        if total > 1.0:
            capped = False
            for y in range(start, n):
                normalised = ratios[y] / total
                if normalised * scaled > caps[y]:
                    ratios[y] = caps[y] / scaled
                    start = y + 1
                    capped = True
                    break
                ratios[y] = normalised
            if not capped or start >= n:
                break
        else:
            for y in range(start, n):
                if scaled * ratios[y] > caps[y]:
                    ratios[y] = caps[y] / scaled
            break
    total = min(sum(ratios), 1.0)
    return scaled * (1.0 - total) / 25.0

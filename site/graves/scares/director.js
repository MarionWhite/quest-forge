// The scare director: pure timing, no DOM. Fed one call per whole second of ACTIVE walking
// (scroll, drag or keys that really moved the camera; idle time never counts).
//
//   first scare   eligible after FIRST_FROM s; a per-second chance of 1/(FIRST_TO - t) makes the
//                 moment uniform over 25..60 s; guaranteed by GUARANTEE s, or at DEPTH_GUARANTEE depth
//   later scares  at least COOLDOWN s of active walking after the last one, then a 1/MEAN_GAP chance per second
//   always        never the same mob twice in a session, at most MAX_PER_SESSION, nothing while reduced motion
export const CFG = {
  FIRST_FROM: 25, FIRST_TO: 60, GUARANTEE: 75, DEPTH_GUARANTEE: 0.6, DEPTH_MIN_SECONDS: 10,
  COOLDOWN: 120, MEAN_GAP: 90, MAX_PER_SESSION: 4
};

export function createDirector({ rng = Math.random, done = [], cfg = CFG } = {}) {
  const d = { done: done.slice(), lastAt: null, cfg };
  // Called once per whole second of active walking. t = total active seconds on this page, depth 0..1.
  d.second = function (t, depth = 0) {
    if (d.done.length >= cfg.MAX_PER_SESSION) return false;
    const since = d.lastAt == null ? t : t - d.lastAt;
    if (d.lastAt != null || d.done.length) {
      // a scare already happened (this page or earlier in the session)
      if (since < cfg.COOLDOWN) return false;
      return rng() < 1 / cfg.MEAN_GAP;
    }
    if (t >= cfg.GUARANTEE) return true;
    if (depth >= cfg.DEPTH_GUARANTEE && t >= cfg.DEPTH_MIN_SECONDS) return true;
    if (t < cfg.FIRST_FROM) return false;
    if (t >= cfg.FIRST_TO) return rng() < 0.5;
    return rng() < 1 / Math.max(1, cfg.FIRST_TO - t);
  };
  d.fired = function (t, mob) { d.lastAt = t; d.done.push(mob); };
  d.pick = function (all) {
    const left = all.filter((m) => !d.done.includes(m));
    return left.length ? left[Math.floor(rng() * left.length)] : null;
  };
  return d;
}

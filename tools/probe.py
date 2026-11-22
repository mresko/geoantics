"""Fast map-hardness probe: how hard can a map variant get, before the full balancer runs?
For each variant it builds the map, deals 10 layouts at the level's base settings and 10 at its
hardest settings (wide shuffle, +2 ties), and reports how many of 60 layouts land in the target band (hits).
Run inside the data folder:  python3 <repo>/tools/probe.py variants.json  > results.txt
variants.json: [{"level": "Egypt", "name": "oasis", "terrain": {"oasis": 0.2}}, ...]
Terrain keys override the level's terrain dict in levels.py."""
import sys, json, random, multiprocessing as mp
from levels import LEVELS, difficulty, TARGET
from build import build, layout, bot_rate

BY = {L['name']: (n, L) for n, L in enumerate(LEVELS, 1)}

import build as B, heapq
HEAP = (B.Sim.__init__, B.Sim.avail, B.Sim.pop, B.Sim.eat)
def use_rule(rule):
    """'fifo' = pre-v0.6 first come, first served queue (for comparison only); default = nearest bottom centre."""
    if rule != 'fifo':
        B.Sim.__init__, B.Sim.avail, B.Sim.pop, B.Sim.eat = HEAP; return
    def init(s, g, GW, GH):
        s.g = g[:]; s.GW = GW; s.GH = GH; s.q = [[] for _ in range(B.NCOL)]; s.h = [0]*B.NCOL; s.exp = bytearray(len(g)); s.left = 0
        for id, v in enumerate(s.g):
            if v >= 0:
                s.left += 1
                if s.isexp(id): s.exp[id] = 1; s.q[v].append(id)
    def eat(s, id):
        s.g[id] = -1; s.left -= 1; i, j = id % s.GW, id // s.GW
        for a, b in B.NB:
            x, y = i+a, j+b
            if 0 <= x < s.GW and 0 <= y < s.GH:
                n = y*s.GW+x
                if s.g[n] >= 0 and not s.exp[n]: s.exp[n] = 1; s.q[s.g[n]].append(n)
    def pop(s, c):
        id = s.q[c][s.h[c]]; s.h[c] += 1; s.eat(id); return id
    B.Sim.__init__, B.Sim.avail, B.Sim.pop, B.Sim.eat = init, (lambda s, c: len(s.q[c]) - s.h[c]), pop, eat

def add_colour(g, GW, GH, seed, share=0.2, scale=6, src=None):
    """Test-only 9th colour: carve smooth-noise patches (scale in cells) out of colour src
    (default: the largest non-border colour) until `share` of that colour is converted."""
    if src is None: src = max(range(1, 8), key=g.count)
    rng = random.Random(seed + 4242); nx, ny = int(GW / scale) + 3, int(GH / scale) + 3
    lat = [rng.random() for _ in range(nx * ny)]; sm = lambda t: t * t * (3 - 2 * t)
    def f(i, j):
        x, y = i / scale, j / scale; x0, y0 = int(x), int(y); fx, fy = sm(x - x0), sm(y - y0); v = lambda a, b: lat[b * nx + a]
        return v(x0, y0)*(1-fx)*(1-fy) + v(x0+1, y0)*fx*(1-fy) + v(x0, y0+1)*(1-fx)*fy + v(x0+1, y0+1)*fx*fy
    ids = sorted((f(id % GW, id // GW), id) for id, c in enumerate(g) if c == src)
    g = g[:]
    for _, id in ids[:int(len(ids) * share)]: g[id] = 8
    return g

def fog_rare(g, keys):
    """Hide every cell of the rarest non-border colour (keys stay visible, as in the game)."""
    present = [c for c in range(1, B.NCOL) if g.count(c)]
    rc = min(present, key=g.count); kset = {k['cell'] for k in keys}
    return [1 if v == rc and i not in kset else 0 for i, v in enumerate(g)]

def smart_play(g, GW, GH, cols, keys, rng, hidden=None, pgood=0.8):
    """Bot that plans with what a player can see: it holds back a colony of a locked key's colour
    unless that colony is big enough to reach the key, counting only visible cells of that colour
    that come before the key in eating order. Fogged cells are invisible until exposed."""
    km = {k['cell']: k['lock'] for k in keys}
    s = B.Sim(g, GW, GH); cs = [list(c) for c in cols]; slots = []; unlocked = set()
    vis = lambda i: not hidden or not hidden[i] or s.exp[i]
    before = {}
    while True:
        prog = True
        while prog:
            prog = False
            for sl in slots:
                while sl[1] > 0 and s.avail(sl[0]):
                    p = s.pop(sl[0]); sl[1] -= 1; prog = True
                    if p in km: unlocked.add(km[p])
            slots = [x for x in slots if x[1] > 0]
        if s.left == 0: return True
        free = B.SLOTS - len(slots)
        if free <= 0: return False
        tops = {k: cs[k][0] for k in range(len(cs)) if cs[k]}
        def ok(k):
            tr = tops[k]
            if tr[2] >= 0 and tr[2] not in unlocked: return False
            if tr[3] >= 0: return free >= 2 and any(kk != k and tops[kk][3] == tr[3] for kk in tops)
            return True
        cand = [k for k in tops if ok(k)]
        if not cand: return False
        # colours whose locked key is still uneaten, and how many visible cells of that colour come first
        ahead = {}
        tc = {tops[k][0] for k in cand}
        for cell, lk in km.items():
            if lk in unlocked or s.g[cell] < 0 or s.g[cell] not in tc: continue
            if cell not in before:
                kc = g[cell]; before[cell] = [i for i, v in enumerate(g) if v == kc and i != cell and s.key[i] < s.key[cell]]
            n_ahead = sum(1 for i in before[cell] if s.g[i] >= 0 and vis(i))
            ahead[s.g[cell]] = min(ahead.get(s.g[cell], 10**9), n_ahead)
        waste = lambda k: tops[k][0] in ahead and tops[k][1] <= ahead[tops[k][0]]
        keep = [k for k in cand if not waste(k)] or cand
        good = [k for k in keep if s.avail(tops[k][0])]
        pick = rng.choice(good) if good and rng.random() < pgood else rng.choice(keep)
        tr = cs[pick].pop(0); slots.append([tr[0], tr[1]])
        if tr[3] >= 0:
            for kk in sorted(tops):
                if kk != pick and tops[kk][3] == tr[3]:
                    t2 = cs[kk].pop(0); slots.append([t2[0], t2[1]]); break

def run(v):
    use_rule(v.get('rule'))
    B.SLOTS = v.get('slots', 5)
    n, L = BY[v['level']]
    L = dict(L, **v.get('over', {})); L['terrain'] = dict(L['terrain'], **v.get('terrain', {}))
    GW, GH, g, own = build(L)
    B.NCOL = 8
    if v.get('extra'): g = add_colour(g, GW, GH, L['seed'], **v['extra']); B.NCOL = 9
    out = {'level': v['level'], 'name': v['name'], 'target': TARGET[n-1],
           'counts': [g.count(c) for c in range(9)]}
    D0 = dict(difficulty(n, L['kind'] == 'boss'), **v.get('D', {}))
    t = TARGET[n-1]; lo, hi = max(0.05, t - 0.1), t + 0.1
    stats = {'naive': [], 'smart': []}
    for dw, dt in ((0, 0), (6, 1), (12, 2)):
        D = dict(D0, w=D0['w'] + dw, ties=D0['ties'] + dt if D0['ties'] else 0)
        for c in range(20):
            rng = random.Random(L['seed'] * 777 + c + 100 * dw)
            cols, keys = layout(g, GW, GH, D, rng)
            if not cols: continue
            hidden = fog_rare(g, keys) if v.get('fog_rare') else None
            stats['naive'].append(bot_rate(g, GW, GH, cols, keys, rng, n=30))
            stats['smart'].append(sum(smart_play(g, GW, GH, cols, keys, rng, hidden) for _ in range(30)) / 30)
    # hits: layouts whose bot rate lands in the band the balancer accepts. More hits, easier to reach the target.
    for bot, ps in stats.items():
        out[bot] = dict(mean=round(sum(ps) / len(ps), 2), hits=sum(lo <= p <= hi for p in ps), n=len(ps),
                        always=sum(p == 1 for p in ps), never=sum(p == 0 for p in ps))
    return out

if __name__ == '__main__':
    vs = json.load(open(sys.argv[1]))
    with mp.get_context('fork').Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 9) as pool:
        for r in pool.imap_unordered(run, vs):
            print(json.dumps(r), flush=True)

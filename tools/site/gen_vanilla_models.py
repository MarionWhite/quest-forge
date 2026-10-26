#!/usr/bin/env python3
"""Generate site/lib/mc/vanilla-models.js from the decompiled 1.7.10 client model classes.

A small Java-subset interpreter runs each model constructor (locals, field initialisers, super()/this(),
chained ModelRenderer calls, for loops, java.util.Random) and records every ModelRenderer: texture
offset, texture size, mirror, rotation point, rotation, boxes (x,y,z,w,h,d,inflate) and children.

    python3 -I tools/site/gen_vanilla_models.py
"""
import json, math, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'mods/qf-content/build/rfg/minecraft-src/java/net/minecraft/client/model')
OUT = os.path.join(REPO, 'site/lib/mc/vanilla-models.js')

# (key, class, ctor args)
MODELS = [
    ('biped', 'ModelBiped', []), ('zombie', 'ModelZombie', []), ('skeleton', 'ModelSkeleton', []),
    ('creeper', 'ModelCreeper', []), ('creeperArmor', 'ModelCreeper', [2.0]), ('spider', 'ModelSpider', []),
    ('enderman', 'ModelEnderman', []), ('silverfish', 'ModelSilverfish', []),
    ('slimeInner', 'ModelSlime', [16]), ('slimeOuter', 'ModelSlime', [0]), ('magmaCube', 'ModelMagmaCube', []),
    ('blaze', 'ModelBlaze', []), ('ghast', 'ModelGhast', []), ('witch', 'ModelWitch', [0.0]),
    ('villager', 'ModelVillager', [0.0]), ('pig', 'ModelPig', []), ('cow', 'ModelCow', []),
    ('chicken', 'ModelChicken', []), ('sheepWool', 'ModelSheep1', []), ('sheepBody', 'ModelSheep2', []),
    ('wolf', 'ModelWolf', []), ('ocelot', 'ModelOcelot', []), ('horse', 'ModelHorse', []),
    ('bat', 'ModelBat', []), ('squid', 'ModelSquid', []), ('ironGolem', 'ModelIronGolem', []),
    ('snowMan', 'ModelSnowMan', []), ('wither', 'ModelWither', []), ('dragon', 'ModelDragon', [0.0]),
    ('skeletonHead', 'ModelSkeletonHead', [0, 0, 64, 32]),
]

TOK = re.compile(r'\s*(?:(\d+\.\d*[fFdD]?|\.\d+[fFdD]?|\d+[fFdDL]?)|([A-Za-z_][A-Za-z_0-9]*)|("[^"]*")|(\+\+|--|\+=|-=|\*=|/=|<=|>=|==|!=|&&|\|\||[-+*/%(){}\[\].,;=<>!?:]))')

def tokenize(s):
    out, i = [], 0
    s = re.sub(r'//.*', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    while i < len(s):
        if s[i:].strip() == '': break
        m = TOK.match(s, i)
        if not m: raise ValueError('tok ' + s[i:i + 30])
        i = m.end()
        if m.group(1) is not None:
            t = m.group(1)
            if t[-1] in 'Ll': out.append(('n', int(t[:-1])))
            elif re.fullmatch(r'\d+', t): out.append(('n', int(t)))
            else: out.append(('n', float(t.rstrip('fFdD'))))
        elif m.group(2): out.append(('id', m.group(2)))
        elif m.group(3): out.append(('s', m.group(3)[1:-1]))
        else: out.append(('p', m.group(4)))
    return out

class R:  # ModelRenderer
    def __init__(self, model, name=None):
        self.model = model; self.name = None; self.boxname = name
        self.u = self.v = 0; self.tw, self.th = model.tw, model.th
        self.mirror = False; self.px = self.py = self.pz = 0.0; self.rx = self.ry = self.rz = 0.0
        self.boxes = []; self.children = []
        model.all.append(self)

class Rand:
    def __init__(self, seed): self.s = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)
    def nxt(self, bits):
        self.s = (self.s * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
        r = self.s >> (48 - bits)
        return r - (1 << bits) if r >= (1 << (bits - 1)) and bits == 32 else r
    def nextInt(self, n):
        if n & -n == n: return (n * self.nxt(31)) >> 31
        while True:
            b = self.nxt(31); v = b % n
            if b - v + (n - 1) < (1 << 31): return v

class Obj:
    def __init__(self):
        self.f = {}; self.tw = 64; self.th = 32; self.all = []; self.offsets = {}

class Cls:
    def __init__(self, path):
        src = open(path, encoding='utf-8').read()
        self.name = re.search(r'class (\w+)', src).group(1)
        m = re.search(r'extends (\w+)', src); self.parent = m.group(1) if m else None
        body = src[src.index('{', src.index('class ' + self.name)) + 1:]
        self.ctors, self.inits, self.methods = [], [], {}
        # top-level members: scan braces
        i = 0; depth = 0; start = 0
        members = []
        buf = ''
        while i < len(body):
            c = body[i]
            if c == '{':
                if depth == 0:
                    head = buf; buf = ''; j = i; d = 0
                    while True:
                        if body[j] == '{': d += 1
                        elif body[j] == '}':
                            d -= 1
                            if d == 0: break
                        j += 1
                    members.append((head, body[i + 1:j])); i = j + 1; continue
            elif c == ';' and depth == 0:
                members.append((buf, None)); buf = ''; i += 1; continue
            buf += c; i += 1
        for head, b in members:
            h = re.sub(r'/\*.*?\*/', '', head, flags=re.S); h = re.sub(r'//.*', '', h); h = re.sub(r'@\w+(\([^)]*\))?', '', h).strip()
            if b is not None and '=' in h and not re.search(r'\)\s*$', h):
                m = re.match(r'(?:(?:public|protected|private|final|static)\s+)*[\w\[\]]+\s+(\w+)\s*=\s*(.+)$', h, re.S)
                if m: self.inits.append((m.group(1), tokenize(m.group(2) + '{' + b + '}')))
                continue
            if b is not None:
                m = re.match(r'(?:public|protected|private)\s+' + self.name + r'\s*\(([^)]*)\)\s*$', h)
                if m:
                    params = [p.split()[-1] for p in m.group(1).split(',') if p.strip()]
                    self.ctors.append((params, tokenize(b)))
                else:
                    m = re.match(r'(?:(?:public|protected|private|final)\s+)*void\s+(\w+)\s*\(([^)]*)\)\s*$', h)
                    if m and not m.group(1).startswith('render') and m.group(1) != 'setRotationAngles':
                        params = [p.split()[-1] for p in m.group(2).split(',') if p.strip()]
                        self.methods[m.group(1)] = (params, tokenize(b))
            else:
                m = re.match(r'(?:(?:public|protected|private|final|static)\s+)*[\w\[\]]+\s+(\w+)\s*=\s*(.+)$', h, re.S)
                if m:
                    self.inits.append((m.group(1), tokenize(m.group(2))))

CLS = {}
def cls(n):
    if n not in CLS: CLS[n] = Cls(os.path.join(SRC, n + '.java'))
    return CLS[n]

class Interp:
    def __init__(self, obj): self.o = obj

    def construct(self, cname, args):
        if cname in ('ModelBase', None):
            return
        c = cls(cname)
        cand = [x for x in c.ctors if len(x[0]) == len(args)]
        if not cand:
            if not c.ctors and not args:
                self.construct(c.parent, []); self.run_inits(c); return
            raise ValueError('no ctor %s/%d' % (cname, len(args)))
        params, toks = cand[0]
        env = dict(zip(params, args))
        self.cur = c
        self.exec_block(toks, env, c)

    def cur_cls_chain(self, name):
        n = self.cur.name
        while n and n != 'ModelBase':
            c = cls(n)
            if name in c.methods: return c.methods[name]
            n = c.parent
        return None
    def exec_method(self, toks, env, c):
        saved = (self.t, self.i, self.env, self.c)
        for st in self.split(toks): self.exec_stmt(st, env, c, False)
        self.t, self.i, self.env, self.c = saved
    def run_inits(self, c):
        for name, toks in c.inits:
            self.o.f[name] = self.ev(toks, {}, c)

    def exec_block(self, toks, env, c):
        stmts = self.split(toks)
        first = True
        s0 = stmts[0] if stmts else None
        explicit = s0 and (s0[0] == ('id', 'super') or (s0[0] == ('id', 'this') and len(s0) > 1 and s0[1] == ('p', '(')))
        if not explicit:
            self.construct(c.parent, []); self.run_inits(c)
        for st in stmts:
            self.exec_stmt(st, env, c, first); first = False
        # no explicit super/this: run implicit
    def split(self, toks):
        out, cur, depth = [], [], 0
        i = 0
        while i < len(toks):
            t = toks[i]
            if t == ('id', 'for') and depth == 0 and not cur:
                # for ( ... ) { ... } or single stmt
                j = i + 1; d = 0
                while True:
                    if toks[j] == ('p', '('): d += 1
                    elif toks[j] == ('p', ')'):
                        d -= 1
                        if d == 0: break
                    j += 1
                head = toks[i + 2:j]; j += 1
                if toks[j] == ('p', '{'):
                    k = j; d = 0
                    while True:
                        if toks[k] == ('p', '{'): d += 1
                        elif toks[k] == ('p', '}'):
                            d -= 1
                            if d == 0: break
                        k += 1
                    body = toks[j + 1:k]; i = k + 1
                else:
                    k = j
                    while toks[k] != ('p', ';'): k += 1
                    body = toks[j:k + 1]; i = k + 1
                out.append([('for', head, body)]); continue
            if t == ('id', 'if') and depth == 0 and not cur:
                j = i + 1; d = 0
                while True:
                    if toks[j] == ('p', '('): d += 1
                    elif toks[j] == ('p', ')'):
                        d -= 1
                        if d == 0: break
                    j += 1
                cond = toks[i + 2:j]; j += 1
                def blk(j):
                    if toks[j] == ('id', 'if'):
                        k = j + 1; d = 0
                        while True:
                            if toks[k] == ('p', '('): d += 1
                            elif toks[k] == ('p', ')'):
                                d -= 1
                                if d == 0: break
                            k += 1
                        _, k = blk(k + 1)
                        if k < len(toks) and toks[k] == ('id', 'else'):
                            _, k = blk(k + 1)
                        return toks[j:k], k
                    if toks[j] == ('p', '{'):
                        k = j; d = 0
                        while True:
                            if toks[k] == ('p', '{'): d += 1
                            elif toks[k] == ('p', '}'):
                                d -= 1
                                if d == 0: break
                            k += 1
                        return toks[j + 1:k], k + 1
                    k = j
                    while toks[k] != ('p', ';'): k += 1
                    return toks[j:k + 1], k + 1
                body, i = blk(j); els = None
                if i < len(toks) and toks[i] == ('id', 'else'):
                    els, i = blk(i + 1)
                out.append([('if', cond, body, els)]); continue
            if t == ('p', '{'): depth += 1
            if t == ('p', '}'): depth -= 1
            if t == ('p', ';') and depth == 0:
                if cur: out.append(cur)
                cur = []
            else: cur.append(t)
            i += 1
        if cur: out.append(cur)
        return out

    def exec_stmt(self, st, env, c, first):
        if st[0][0] == 'for':
            _, head, body = st[0]
            parts = []; cur = []
            for t in head:
                if t == ('p', ';'): parts.append(cur); cur = []
                else: cur.append(t)
            parts.append(cur)
            self.exec_stmt(parts[0], env, c, False)
            n = 0
            while self.ev(parts[1], env, c):
                for s2 in self.split(body): self.exec_stmt(s2, env, c, False)
                self.exec_stmt(parts[2], env, c, False)
                n += 1
                if n > 1000: raise ValueError('loop')
            return
        if st[0][0] == 'if':
            _, cond, body, els = st[0]
            b = body if self.ev(cond, env, c) else els
            for s2 in self.split(b or []): self.exec_stmt(s2, env, c, False)
            return
        # super(...) / this(...)
        if st[0] == ('id', 'super') or (st[0] == ('id', 'this') and len(st) > 1 and st[1] == ('p', '(')):
            args = self.args(st[2:-1], env, c)
            if st[0][1] == 'super':
                self.construct(c.parent, args); self.run_inits(c)
            else:
                self.construct(c.name, args)
            return
        # local declaration: Type name = expr
        if len(st) > 3 and st[0][0] == 'id' and st[1][0] == 'id' and st[2] == ('p', '=') and st[0][1] not in ('this', 'return'):
            v = self.ev(st[3:], env, c)
            tp = st[0][1]
            if tp in ('byte', 'int', 'short') and isinstance(v, float): v = int(v)
            if tp == 'float' and isinstance(v, int): v = float(v)
            env[st[1][1]] = v
            self.name_r(v, st[1][1])
            return
        # assignment
        for i, t in enumerate(st):
            if t[0] == 'p' and t[1] in ('=', '+=', '-=', '*=', '/=') and i > 0:
                depth = 0
                lhs, rhs = st[:i], st[i + 1:]
                self.assign(lhs, t[1], self.ev(rhs, env, c), env, c)
                return
        if st[0][0] == 'p' and st[0][1] in ('++', '--') and len(st) > 2:
            self.assign(st[1:], '+=' if st[0][1] == '++' else '-=', 1, env, c); return
        if len(st) == 2 and st[1][0] == 'p' and st[1][1] in ('++', '--'):
            env[st[0][1]] = env[st[0][1]] + (1 if st[1][1] == '++' else -1); return
        if len(st) == 2 and st[0][1] in ('++', '--'):
            env[st[1][1]] = env[st[1][1]] + (1 if st[0][1] == '++' else -1); return
        self.ev(st, env, c)  # expression statement

    def name_r(self, v, name):
        if isinstance(v, R) and v.name is None: v.name = name

    def assign(self, lhs, op, val, env, c):
        # lhs forms: [this . f], [this . f [ idx ]], [this . f . attr], [x . attr], [x]
        toks = lhs
        if toks[0] == ('id', 'this'): toks = toks[2:]
        # find attr
        if len(toks) == 1:
            name = toks[0][1]
            if name in env: env[name] = self.combine(env[name], op, val)
            elif name in ('textureWidth',): self.o.tw = val
            elif name in ('textureHeight',): self.o.th = val
            else:
                self.o.f[name] = self.combine(self.o.f.get(name), op, val); self.name_r(val, name)
            return
        # array element or attr
        if toks[1] == ('p', '['):
            end = len(toks) - 1
            arr = self.o.f[toks[0][1]] if toks[0][1] not in env else env[toks[0][1]]
            idx = self.ev(toks[2:end], env, c)
            arr[int(idx)] = val
            self.name_r(val, toks[0][1] + str(int(idx)))
            return
        # attr on object: last '.' attr
        attr = toks[-1][1]
        base = self.ev(toks[:-2], env, c)
        if isinstance(base, R):
            m = {'rotationPointX': 'px', 'rotationPointY': 'py', 'rotationPointZ': 'pz', 'rotateAngleX': 'rx', 'rotateAngleY': 'ry', 'rotateAngleZ': 'rz', 'mirror': 'mirror'}
            if attr in m:
                setattr(base, m[attr], self.combine(getattr(base, m[attr]), op, val)); return
            return  # offsetX etc ignored
        raise ValueError('assign ' + str(lhs))

    def combine(self, old, op, val):
        if op == '=': return val
        if op == '+=': return old + val
        if op == '-=': return old - val
        if op == '*=': return old * val
        return old / val

    # ---- expressions
    def args(self, toks, env, c):
        out, cur, d = [], [], 0
        for t in toks:
            if t == ('p', '(') or t == ('p', '['): d += 1
            if t == ('p', ')') or t == ('p', ']'): d -= 1
            if t == ('p', ',') and d == 0: out.append(cur); cur = []
            else: cur.append(t)
        if cur: out.append(cur)
        return [self.ev(a, env, c) for a in out]

    def ev(self, toks, env, c):
        self.t = toks; self.i = 0; self.env = env; self.c = c
        saved = (self.t, self.i, self.env, self.c)
        v = self.p_ternary()
        return v
    # recursive descent with state saved around nested ev calls
    def peek(self): return self.t[self.i] if self.i < len(self.t) else (None, None)
    def eat(self, p=None):
        t = self.t[self.i]; self.i += 1; return t
    def p_ternary(self):
        v = self.p_or()
        if self.peek() == ('p', '?'):
            self.eat(); a = self.p_ternary(); self.eat(); b = self.p_ternary()
            return a if v else b
        return v
    def p_or(self):
        v = self.p_and()
        while self.peek() == ('p', '||'): self.eat(); r = self.p_and(); v = v or r
        return v
    def p_and(self):
        v = self.p_cmp()
        while self.peek() == ('p', '&&'): self.eat(); r = self.p_cmp(); v = v and r
        return v
    def p_cmp(self):
        v = self.p_add()
        while self.peek()[0] == 'p' and self.peek()[1] in ('<', '>', '<=', '>=', '==', '!='):
            op = self.eat()[1]; r = self.p_add()
            v = {'<': v < r, '>': v > r, '<=': v <= r, '>=': v >= r, '==': v == r, '!=': v != r}[op]
        return v
    def p_add(self):
        v = self.p_mul()
        while self.peek()[0] == 'p' and self.peek()[1] in '+-' and self.peek()[1] != '':
            op = self.eat()[1]; r = self.p_mul(); v = v + r if op == '+' else v - r
        return v
    def p_mul(self):
        v = self.p_unary()
        while self.peek()[0] == 'p' and self.peek()[1] in ('*', '/', '%'):
            op = self.eat()[1]; r = self.p_unary()
            if op == '*': v = v * r
            elif op == '%': v = math.fmod(v, r) if isinstance(v, float) or isinstance(r, float) else v % r
            else: v = int(v / r) if isinstance(v, int) and isinstance(r, int) else v / r
        return v
    def p_unary(self):
        if self.peek() == ('p', '-'): self.eat(); return -self.p_unary()
        if self.peek() == ('p', '!'): self.eat(); return not self.p_unary()
        # cast
        if self.peek() == ('p', '(') and self.i + 2 < len(self.t) and self.t[self.i + 1][0] == 'id' and self.t[self.i + 1][1] in ('float', 'int', 'byte', 'double', 'short') and self.t[self.i + 2] == ('p', ')'):
            tp = self.t[self.i + 1][1]; self.i += 3; v = self.p_unary()
            if tp in ('float', 'double'): return float(v)
            return int(v)
        return self.p_postfix()
    def p_postfix(self):
        v = self.p_primary()
        while True:
            p = self.peek()
            if p == ('p', '.'):
                self.eat(); name = self.eat()[1]
                if self.peek() == ('p', '('):
                    self.eat(); args = self.call_args(); v = self.call(v, name, args)
                else: v = self.field(v, name)
            elif p == ('p', '['):
                self.eat(); idx = self.p_ternary(); self.eat(); v = v[int(idx)]
            else: return v
    def call_args(self):
        args = []
        if self.peek() == ('p', ')'): self.eat(); return args
        while True:
            args.append(self.p_ternary())
            t = self.eat()
            if t == ('p', ')'): return args
    def p_primary(self):
        t = self.eat()
        if t[0] == 'n': return t[1]
        if t[0] == 's': return t[1]
        if t == ('p', '('):
            v = self.p_ternary(); self.eat(); return v
        if t == ('id', 'new'):
            tp = self.eat()[1]
            if self.peek() == ('p', '['):
                self.eat()
                if self.peek() == ('p', ']'):
                    self.eat()
                    while self.peek() == ('p', '['): self.eat(); self.eat()
                    return self.p_brace()
                n = self.p_ternary(); self.eat(); return [None] * int(n)
            self.eat(); args = self.call_args()
            if tp == 'ModelRenderer':
                r = R(self.o, args[1] if len(args) == 2 and isinstance(args[1], str) else None)
                if len(args) == 3: r.u, r.v = args[1], args[2]
                return r
            if tp == 'Random': return Rand(args[0])
            raise ValueError('new ' + tp)
        if t[0] == 'id':
            n = t[1]
            if n == 'this': return self.o
            if n == 'true': return True
            if n == 'false': return False
            if n == 'null': return None
            if n == 'Math': return 'Math'
            if n in self.env: return self.env[n]
            if n in self.o.f: return self.o.f[n]
            if n == 'textureWidth': return self.o.tw
            if n == 'textureHeight': return self.o.th
            return n
        raise ValueError('prim %s' % (t,))
    def p_brace(self):
        self.eat(); out = []
        while self.peek() != ('p', '}'):
            out.append(self.p_brace() if self.peek() == ('p', '{') else self.p_ternary())
            if self.peek() == ('p', ','): self.eat()
        self.eat(); return out
    def field(self, v, name):
        if v == 'Math' and name == 'PI': return math.pi
        if isinstance(v, list) and name == 'length': return len(v)
        if v is self.o:
            if name in self.o.f: return self.o.f[name]
            if name == 'textureWidth': return self.o.tw
            if name == 'textureHeight': return self.o.th
        if isinstance(v, R):
            return getattr(v, {'rotationPointX': 'px', 'rotationPointY': 'py', 'rotationPointZ': 'pz', 'rotateAngleX': 'rx', 'rotateAngleY': 'ry', 'rotateAngleZ': 'rz'}[name])
        raise ValueError('field %s' % name)
    def call(self, v, name, args):
        if isinstance(v, R):
            if name == 'setTextureSize': v.tw, v.th = args; return v
            if name == 'setTextureOffset': v.u, v.v = args; return v
            if name == 'addChild': v.children.append(args[0]); return None
            if name == 'setRotationPoint': v.px, v.py, v.pz = [float(a) for a in args]; return None
            if name == 'addBox' or name == 'func_78789_a':
                if isinstance(args[0], str):
                    key = (v.boxname or 'null') + '.' + args[0]
                    if key in self.o.offsets: v.u, v.v = self.o.offsets[key]
                    args = args[1:]
                a = [float(x) for x in args] + [0.0] * (7 - len(args))
                v.boxes.append(a[:7]); return v
            if name == 'setRotation': return None
        if v is self.o:
            k = self.cur_cls_chain(name)
            if k:
                params, toks = k
                self.exec_method(toks, dict(zip(params, args)), self.cur)
                return None
        if v is self.o and name == 'setTextureOffset':
            self.o.offsets[args[0]] = (args[1], args[2]); return None
        if v == 'Math': return getattr(math, name)(*args)
        if isinstance(v, Rand) and name == 'nextInt': return v.nextInt(args[0])
        if v is self.o and name in ('setRotation',):
            r, x, y, z = args; r.rx, r.ry, r.rz = x, y, z; return None
        if v is self.o and name == 'setRotateAngle': return None
        raise ValueError('call %s.%s' % (v, name))

def run(cname, args):
    o = Obj(); it = Interp(o)
    it.construct(cname, args)
    # keep only renderers reachable from the final fields (a field re-assigned in a subclass drops the old one)
    keep, order = {}, []
    def visit(r, name):
        if id(r) in keep: return
        keep[id(r)] = name; order.append(r)
        for i, ch in enumerate(r.children): visit(ch, ch.name if ch.name and not ch.name.startswith('_') else '%s_c%d' % (name, i))
    for k, v in o.f.items():
        if isinstance(v, R): visit(v, k)
        elif isinstance(v, list):
            for i, e in enumerate(v):
                if isinstance(e, R): visit(e, '%s%d' % (k, i))
    for r in order: r.name = keep[id(r)]
    o.all = order
    return o

def jfloat(x):
    x = round(float(x), 5)
    return int(x) if x == int(x) else x

def dump(o):
    parts = {}; kids = set()
    for r in o.all:
        for ch in r.children: kids.add(id(ch))
    for r in o.all:
        p = {'uv': [r.u, r.v], 'tex': [int(r.tw), int(r.th)], 'pivot': [jfloat(r.px), jfloat(r.py), jfloat(r.pz)]}
        if r.mirror: p['mirror'] = 1
        if r.rx or r.ry or r.rz: p['rot'] = [jfloat(r.rx), jfloat(r.ry), jfloat(r.rz)]
        p['boxes'] = [[jfloat(x) for x in b] for b in r.boxes]
        if r.children: p['children'] = [c.name for c in r.children]
        if r.boxes or r.children: parts[r.name] = p
    return {'tex': [o.tw, o.th], 'parts': parts, 'roots': [r.name for r in o.all if r.name in parts and id(r) not in kids]}

def main():
    out = {}
    for key, cn, args in MODELS:
        try:
            out[key] = dump(run(cn, args))
        except Exception as e:
            print('FAIL', key, cn, repr(e), file=sys.stderr)
    with open(OUT, 'w') as f:
        f.write('// GENERATED by tools/site/gen_vanilla_models.py from the decompiled 1.7.10 client model classes. Do not edit.\n')
        f.write('// Per model: texture size, and every ModelRenderer {uv, tex, pivot, rot, mirror, boxes [x,y,z,w,h,d,inflate], children}.\n')
        f.write('export const VANILLA_MODELS = ' + json.dumps(out, separators=(',', ':')) + ';\n')
    print('wrote', OUT, len(out), 'models')

if __name__ == '__main__':
    main()

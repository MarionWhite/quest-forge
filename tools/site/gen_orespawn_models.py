#!/usr/bin/env python3
"""Generate site/lib/mc/orespawn-models.js from OreSpawn's own client model classes.

javap -c disassembles each ModelX constructor; a small JVM stack simulator replays it (ldc/iconst/bipush/
sipush/fconst/arithmetic, new ModelRenderer, addBox, setRotationPoint, setTextureSize, setRotation helper,
addChild, putfield/getfield) and records every ModelRenderer. Render classes are scanned for the texture
resource strings and glScalef values.

    python3 -I tools/site/gen_orespawn_models.py [ORESPAWN_ZIP]
"""
import json, os, re, subprocess, sys, tempfile, zipfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, 'site/lib/mc/orespawn-models.js')
ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/Library/Application Support/crazycraft4/mods/orespawn.zip')
JAVAP = '/opt/homebrew/opt/openjdk@17/bin/javap'
MODELS = ['Mantis', 'Bee', 'Brutalfly', 'CaterKiller', 'Cephadrome', 'CloudShark', 'Coin', 'Dragon', 'EasterBunny',
          'Hammerhead', 'Robot1', 'Robot2', 'Robot3', 'Robot4', 'Robot5', 'Ant', 'Rotator', 'WormLarge', 'Godzilla',
          'Butterfly']

RFIELDS = {'field_78809_i': 'mirror', 'mirror': 'mirror', 'field_78795_f': 'rx', 'field_78796_g': 'ry', 'field_78808_h': 'rz', 'rotateAngleX': 'rx', 'rotateAngleY': 'ry', 'rotateAngleZ': 'rz', 'field_78800_c': 'px', 'field_78797_d': 'py', 'field_78798_e': 'pz'}

class R:
    def __init__(self, model, u=0, v=0):
        self.name = None; self.u, self.v = u, v; self.tw, self.th = model['tw'], model['th']
        self.mirror = False; self.p = [0, 0, 0]; self.rot = [0, 0, 0]; self.boxes = []; self.kids = []

def descr_args(desc):
    inner = desc[desc.index('(') + 1:desc.index(')')]
    out = []; i = 0
    while i < len(inner):
        c = inner[i]
        if c == 'L': j = inner.index(';', i); out.append('L'); i = j + 1
        elif c == '[':
            while inner[i] == '[': i += 1
            if inner[i] == 'L': i = inner.index(';', i) + 1
            else: i += 1
            out.append('L')
        else: out.append(c); i += 1
    return out, desc[desc.index(')') + 1:]

def simulate(text, cname):
    # constructor body (the one with most instructions that calls ModelRenderer.<init>)
    blocks = re.split(r'\n\n', text)
    best = None
    for b in blocks:
        if '"<init>"' in b and 'ModelRenderer."<init>"' in b and 'Code:' in b:
            if best is None or len(b) > len(best): best = b
    if best is None: return None
    hdr = best.split('\n')[0]
    model = {'tw': 64, 'th': 32}
    fields = {}; allr = []
    stack = []; locs = {}
    for line in best.split('\n'):
        m = re.match(r'\s*\d+:\s+(\w+)\s*(.*)$', line)
        if not m: continue
        op, rest = m.group(1), m.group(2)
        if op in ('aload_0', 'aload_1', 'aload_2', 'aload_3'):
            stack.append('this' if op == 'aload_0' else 0)
        elif op.startswith(('fload', 'iload', 'dload')): stack.append(0.0)
        elif op.startswith(('aload',)): stack.append(0)
        elif op.startswith('iconst_'): stack.append(-1 if op.endswith('m1') else int(op[-1]))
        elif op.startswith('fconst_'): stack.append(float(op[-1]))
        elif op.startswith('dconst_'): stack.append(float(op[-1]))
        elif op in ('bipush', 'sipush'): stack.append(int(rest))
        elif op in ('ldc', 'ldc_w', 'ldc2_w'):
            mm = re.search(r'// (float|double|int|String|class)\s+(.*)$', rest)
            if mm and mm.group(1) in ('float', 'double'):
                v = mm.group(2).rstrip('fd'); stack.append(float(v) if v not in ('NaN', 'Infinity') else 0.0)
            elif mm and mm.group(1) == 'int': stack.append(int(mm.group(2)))
            else: stack.append(mm.group(2) if mm else 0)
        elif op in ('fadd', 'dadd', 'iadd'): b, a = stack.pop(), stack.pop(); stack.append(a + b)
        elif op in ('fsub', 'dsub', 'isub'): b, a = stack.pop(), stack.pop(); stack.append(a - b)
        elif op in ('fmul', 'dmul', 'imul'): b, a = stack.pop(), stack.pop(); stack.append(a * b)
        elif op in ('fdiv', 'ddiv'): b, a = stack.pop(), stack.pop(); stack.append(a / b if b else 0)
        elif op in ('fneg', 'dneg', 'ineg'): stack.append(-stack.pop())
        elif op in ('i2f', 'i2d', 'f2d', 'd2f', 'f2i', 'd2i'):
            v = stack.pop(); stack.append(float(v) if op[-1] in 'fd' else int(v))
        elif op == 'new':
            stack.append('NEW:' + rest.split()[-1])
        elif op == 'dup': stack.append(stack[-1])
        elif op == 'pop': stack.pop()
        elif op == 'getfield':
            f = re.search(r'Field (?:[\w/$]+\.)?(\w+):', rest).group(1); stack.pop()
            stack.append(fields.get(f, 0))
        elif op == 'putfield':
            f = re.search(r'Field (?:[\w/$]+\.)?(\w+):', rest).group(1); v = stack.pop(); tgt = stack.pop()
            if isinstance(tgt, R) and f in RFIELDS:
                a = RFIELDS[f]
                if a == 'mirror': tgt.mirror = bool(v)
                elif a[0] == 'r': tgt.rot['xyz'.index(a[1])] = round(float(v), 5)
                else: tgt.p['xyz'.index(a[1])] = round(float(v), 5)
            elif f in ('field_78090_t', 'textureWidth'): model['tw'] = int(v)
            elif f in ('field_78089_u', 'textureHeight'): model['th'] = int(v)
            else:
                fields[f] = v
                if isinstance(v, R) and v.name is None: v.name = f
        elif op.startswith('invoke'):
            mm = re.search(r'Method (?:([\w/$]+)\.)?("?[\w<>$]+"?):(\(.*)$', rest)
            if not mm: continue
            cls, meth, desc = mm.group(1) or '', mm.group(2).strip('"'), mm.group(3)
            args, ret = descr_args(desc)
            vals = [stack.pop() for _ in args][::-1]
            obj = stack.pop() if op != 'invokestatic' else None
            if cls.endswith('ModelRenderer'):
                if meth == '<init>':
                    r = R(model)
                    if len(vals) == 3: r.u, r.v = int(vals[1]), int(vals[2])
                    # obj is the dup'd NEW marker; replace the other copy on the stack
                    for i in range(len(stack)):
                        if isinstance(stack[i], str) and stack[i].startswith('NEW:ModelRenderer') or (isinstance(stack[i], str) and stack[i].endswith('ModelRenderer') and stack[i].startswith('NEW')):
                            stack[i] = r
                    allr.append(r)
                elif meth in ('func_78789_a', 'addBox'):
                    v = [x for x in vals if not isinstance(x, str)]
                    if len(v) >= 6 and isinstance(obj, R):
                        obj.boxes.append([round(float(x), 5) for x in v[:6]] + [round(float(v[6]), 5) if len(v) > 6 else 0] + [obj.u, obj.v, 1 if obj.mirror else 0, obj.tw, obj.th])
                    if ret.startswith('L'): stack.append(obj)
                elif meth in ('func_78793_a', 'setRotationPoint') and isinstance(obj, R): obj.p = [round(float(x), 5) for x in vals]
                elif meth in ('func_78787_b', 'setTextureSize') and isinstance(obj, R):
                    obj.tw, obj.th = int(vals[0]), int(vals[1]); 
                    if ret.startswith('L'): stack.append(obj)
                elif meth in ('func_78784_a', 'setTextureOffset') and isinstance(obj, R):
                    obj.u, obj.v = int(vals[0]), int(vals[1])
                    if ret.startswith('L'): stack.append(obj)
                elif meth in ('func_78792_a', 'addChild') and isinstance(obj, R) and isinstance(vals[0], R): obj.kids.append(vals[0])
                elif ret.startswith('L') and ret != 'V': stack.append(obj)
            elif meth.lower().startswith('setrotation') and len(vals) == 4 and isinstance(vals[0], R):
                vals[0].rot = [round(float(x), 5) for x in vals[1:]]
            elif meth == '<init>': pass
            elif ret != 'V': stack.append(0)
    # mirror flag: look for field_78809_i / mirror putfield (set before addBox, ignored here), taken from text
    # name anonymous
    for i, r in enumerate(allr):
        if r.name is None: r.name = '_r%d' % i
    kids = set(id(k) for r in allr for k in r.kids)
    parts = {}
    for r in allr:
        if not r.boxes and not r.kids: continue
        p = {'pivot': r.p, 'boxes': r.boxes}
        if any(r.rot): p['rot'] = r.rot
        if r.kids: p['children'] = [k.name for k in r.kids]
        parts[r.name] = p
    return {'tex': [model['tw'], model['th']], 'parts': parts, 'roots': [r.name for r in allr if r.name in parts and id(r) not in kids]}

def main():
    tmp = tempfile.mkdtemp(prefix='osmodels')
    z = zipfile.ZipFile(ZIP)
    names = [n for n in z.namelist() if re.match(r'danger/orespawn/(Model|Render)', n)]
    for n in names: z.extract(n, tmp)
    out = {}; renders = {}
    for m in MODELS:
        try:
            txt = subprocess.run([JAVAP, '-c', '-p', '-classpath', tmp, 'danger.orespawn.Model' + m], capture_output=True, text=True).stdout
            d = simulate(txt, m)
            if d: out[m] = d
            else: print('no ctor', m, file=sys.stderr)
        except Exception as e:
            import traceback; traceback.print_exc()
    # render classes: texture strings and glScalef constants
    for n in sorted(names):
        mm = re.match(r'danger/orespawn/(Render\w+)\.class$', n)
        if not mm: continue
        txt = subprocess.run([JAVAP, '-c', '-p', '-classpath', tmp, 'danger.orespawn.' + mm.group(1)], capture_output=True, text=True).stdout
        texs = re.findall(r'// String (?:orespawn:)?([\w/.\-]+\.png)', txt)
        scales = []
        for blk in re.findall(r'glScalef[^\n]*', txt): pass
        lines = txt.split('\n'); vals = []
        for i, l in enumerate(lines):
            if 'glScalef' in l:
                vv = []
                for k in range(i - 1, max(0, i - 12), -1):
                    m2 = re.search(r'// float ([\d.\-E]+)f', lines[k]); m3 = re.search(r'fconst_(\d)', lines[k])
                    if m2: vv.append(float(m2.group(1)))
                    elif m3: vv.append(float(m3.group(1)))
                    if len(vv) == 3: break
                if vv: scales.append(vv[::-1])
        mdl = re.findall(r'new\s+#\d+\s+// class danger/orespawn/(Model\w+)', txt)
        renders[mm.group(1)] = {'tex': texs[:4], 'scale': scales[:2], 'model': sorted(set(mdl))}
    with open(OUT, 'w') as f:
        f.write('// GENERATED by tools/site/gen_orespawn_models.py from the OreSpawn jar. Do not edit.\n')
        f.write('export const OS_MODELS = ' + json.dumps(out, separators=(',', ':')) + ';\n')
        f.write('export const OS_RENDERS = ' + json.dumps(renders, separators=(',', ':')) + ';\n')
    print('wrote', OUT, len(out), 'models', len(renders), 'renders')

main()

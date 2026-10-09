"""Leitor de arquivos SketchUp 2021+ (.skp / .skb) sem SketchUp.

Formato: cabeçalho UTF-16 + ZIP. Dentro do ZIP, `model.dat` é uma árvore TLV
(tag uint16 + tamanho uint32 + conteúdo). Formato obtido por engenharia reversa;
testado com SketchUp 2024 (24.0.553) e modelos Gábster.

Unidades internas: polegadas. Tudo que sai deste módulo está em milímetros.
"""
import io
import struct
import zipfile

IN = 25.4


class N:
    __slots__ = ('tag', 'off', 'len', 'kids')

    def __init__(s, t, o, l):
        s.tag, s.off, s.len, s.kids = t, o, l, None


class SKP:
    def __init__(self, path):
        raw = open(path, 'rb').read()
        i = raw.find(b'PK\x03\x04')
        if i < 0:
            raise ValueError('Arquivo .skp sem contêiner ZIP: formato anterior ao SketchUp 2021 não é suportado.')
        self.zip = zipfile.ZipFile(io.BytesIO(raw[i:]))
        self.D = self.zip.read('model.dat')
        try:
            self.meta = self.zip.read('meta/meta.dat')
        except KeyError:
            self.meta = b''
        self.root = self._build(0, len(self.D))
        self._parse()

    # ---------------- TLV ----------------
    def _try_list(self, off, end):
        D = self.D
        out = []
        o = off
        while o < end:
            if o + 6 > end:
                return None
            t, l = struct.unpack_from('<HI', D, o)
            if t == 0 or o + 6 + l > end:
                return None
            out.append((t, o + 6, l))
            o += 6 + l
        return out if o == end else None

    def _build(self, off, end):
        lst = self._try_list(off, end)
        if lst is None:
            return None
        nodes = []
        for t, o, l in lst:
            n = N(t, o, l)
            if l >= 6:
                n.kids = self._build(o, o + l)
            nodes.append(n)
        return nodes

    @staticmethod
    def ch(n, tag):
        return [k for k in (n.kids or []) if k.tag == tag]

    def ch1(self, n, tag):
        if n is None:
            return None
        r = self.ch(n, tag)
        return r[0] if r else None

    def raw(self, n):
        return self.D[n.off:n.off + n.len]

    def ival(self, n):
        return int.from_bytes(self.raw(n), 'little') if n is not None and n.len > 0 else None

    def sval(self, n):
        return self.raw(n).decode('utf-8', 'replace') if n is not None else None

    def dvals(self, n):
        return list(struct.unpack('<%dd' % (n.len // 8), self.raw(n)))

    def attrval(self, v):
        if not v.kids:
            return None
        k = v.kids[0]
        r = self.raw(k)
        if k.tag == 0x38a9:
            return struct.unpack('<d', r)[0]
        if k.tag == 0x38a7:
            return struct.unpack('<i', r)[0] if k.len == 4 else self.ival(k)
        if k.tag == 0x38aa:
            return bool(r[0])
        if k.tag == 0x38ad:
            return self.sval(k)
        return None

    def attrs(self, base):
        out = {}
        dc = self.ch1(base, 0x5dc)
        a = self.ch1(dc, 0x5dd)
        if a is None or not a.kids:
            return out
        for b1 in self.ch(a, 0x36b1):
            for b2 in self.ch(b1, 0x36b2):
                for b3 in self.ch(b2, 0x36b3):
                    name = self.sval(self.ch1(b3, 0x36b4))
                    d = {}
                    ks = (self.ch1(b3, 0x36b5).kids or [])
                    for i in range(0, len(ks) - 1, 2):
                        if ks[i].tag == 0x36b6:
                            d[self.sval(ks[i])] = self.attrval(ks[i + 1])
                    out[name] = d
        return out

    def baseinfo(self, n):
        b = self.ch1(n, 0x7d0)
        dc = self.ch1(b, 0x5dc)
        return dict(id=self.ival(self.ch1(dc, 0x5de)), ref=self.ival(self.ch1(b, 0x7d2)), flags=self.ival(self.ch1(b, 0x7d3)) or 0), b

    def _entities(self, e):
        verts, edges, faces, insts = {}, {}, [], []
        vs = self.ch1(e, 0x1389)
        if vs:
            for v in self.ch(vs, 0x9c4):
                verts[self.ival(self.ch1(self.ch1(v, 0x5dc), 0x5de))] = self.dvals(self.ch1(v, 0x9c5))
        es = self.ch1(e, 0x138a)
        if es:
            for ed in self.ch(es, 0xbb8):
                bi, _ = self.baseinfo(ed)
                edges[bi['id']] = (self.ival(self.ch1(ed, 0xbb9)), self.ival(self.ch1(ed, 0xbba)))
        fs = self.ch1(e, 0x138b)
        if fs:
            for f in self.ch(fs, 0xdac):
                bi, _ = self.baseinfo(f)
                loops = []
                for lp in self.ch(self.ch1(f, 0xdae), 0x1194):
                    for l in self.ch(lp, 0x1195):
                        seq = []
                        for u in self.ch(l, 0xfa0):
                            a, b = edges.get(self.ival(self.ch1(u, 0xfa1)), (None, None))
                            seq.append(a if self.raw(self.ch1(u, 0xfa2))[0] else b)
                        loops.append(seq)
                faces.append(dict(loops=loops, layer=bi['ref'], flags=bi['flags']))
        cs = self.ch1(e, 0x138c)
        if cs:
            for it in self.ch(cs, 0x1964):
                bi, b = self.baseinfo(it)
                insts.append(dict(id=bi['id'], layer=bi['ref'], flags=bi['flags'], name=self.sval(self.ch1(it, 0x1965)),
                                  T=self.dvals(self.ch1(it, 0x1966)), defid=self.ival(self.ch1(it, 0x1967)), attrs=self.attrs(b)))
        return verts, faces, insts

    def _parse(self):
        top = self.root[0]
        self.materials = {}
        m = self.ch1(self.ch1(self.ch1(top, 0x1f7), 0x30d4), 0x30d5)
        for x in self.ch(m, 0x32c8) if m else []:
            self.materials[self.ival(self.ch1(self.ch1(x, 0x5dc), 0x5de))] = self.sval(self.ch1(x, 0x32cc))
        self.layers, self.hidden_layers = {}, set()
        L = self.ch1(self.ch1(self.ch1(top, 0x1f8), 0x3a98), 0x3a99)
        for l in self.ch(L, 0x3c8c) if L else []:
            lid = self.ival(self.ch1(self.ch1(l, 0x5dc), 0x5de))
            self.layers[lid] = self.sval(self.ch1(l, 0x3c8d))
            h = self.ch1(l, 0x3c8e)
            if h is not None and self.raw(h)[0] == 1:
                self.hidden_layers.add(lid)
        self.defs = {}
        ents = self.ch1(top, 0x1f9)
        for d in self.ch(self.ch1(self.ch1(ents, 0x1770), 0x1771), 0x157c):
            e = self.ch1(d, 0x1388)
            bi, b = self.baseinfo(e)
            v, f, ins = self._entities(e)
            self.defs[bi['id']] = dict(id=bi['id'], name=self.sval(self.ch1(d, 0x157e)), attrs=self.attrs(b), verts=v, faces=f, insts=ins)
        v, f, ins = self._entities(self.ch1(self.ch1(top, 0x1f6), 0x1388))
        self.rootdef = dict(id=0, name='<root>', verts=v, faces=f, insts=ins, attrs={})

    # ---------------- geometry helpers ----------------
    def is_hidden(self, inst):
        return bool(inst['flags'] & 1) or inst['layer'] in self.hidden_layers

    def dc(self, inst, d):
        a = dict(d['attrs'].get('dynamic_attributes', {}))
        a.update(inst['attrs'].get('dynamic_attributes', {}))
        return a

    def label(self, inst, d):
        a = self.dc(inst, d)
        return a.get('_name') or d['name']

    def visible_points(self, d, W, out):
        for f in d['faces']:
            if f['layer'] in self.hidden_layers:
                continue
            for lp in f['loops']:
                for vid in lp:
                    if vid in d['verts']:
                        out.append(ap(W, d['verts'][vid]))
        for ins in d['insts']:
            if self.is_hidden(ins):
                continue
            self.visible_points(self.defs[ins['defid']], mul(W, tm(ins['T'])), out)

    def visible_faces(self, d, W, out):
        for f in d['faces']:
            if f['layer'] in self.hidden_layers:
                continue
            out.append([[[c * IN for c in ap(W, d['verts'][v])] for v in lp if v in d['verts']] for lp in f['loops']])
        for ins in d['insts']:
            if self.is_hidden(ins):
                continue
            self.visible_faces(self.defs[ins['defid']], mul(W, tm(ins['T'])), out)

    def aabb(self, d, W):
        pts = []
        self.visible_points(d, W, pts)
        if not pts:
            return None
        return [[min(p[i] for p in pts) * IN for i in range(3)], [max(p[i] for p in pts) * IN for i in range(3)]]

    def walk(self, fn, d=None, W=None, path=(), visible=True):
        """fn(inst, d, W, path, visible) -> False para não descer."""
        d = d or self.rootdef
        W = W or I4
        for ins in d['insts']:
            dd = self.defs[ins['defid']]
            v = visible and not self.is_hidden(ins)
            W2 = mul(W, tm(ins['T']))
            if fn(ins, dd, W2, path, v) is False:
                continue
            self.walk(fn, dd, W2, path + (self.label(ins, dd),), v)


I4 = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def tm(T):
    x, y, z, o = T[0:3], T[3:6], T[6:9], T[9:12]
    w = T[12] if len(T) > 12 else 1.0
    return [[x[0], y[0], z[0], o[0]], [x[1], y[1], z[1], o[1]], [x[2], y[2], z[2], o[2]], [0, 0, 0, w]]


def ap(M, p):
    r = [M[i][0] * p[0] + M[i][1] * p[1] + M[i][2] * p[2] + M[i][3] for i in range(4)]
    return [r[0] / r[3], r[1] / r[3], r[2] / r[3]]

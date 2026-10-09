# Vector technical-drawing engine: axonometric + orthographic views of AABB panels and meshes -> SVG
import math

INK = '#1d1f21'
INK2 = '#55595e'
GHOST_FILL = '#eeeeec'
GHOST_STROKE = '#a3a6a9'
ACCENT = '#e8590c'
ACCENT_FILL = '#f7b088'
MAT = {
    'Manhattan': '#a3a8ad',
    'Carvalho Natural': '#dcc29b',
    'Branco': '#f8f8f6',
    'metal': '#c4c8cc',
    'none': '#ffffff',
}
FONT = "'Barlow Condensed','Barlow',Arial Narrow,Arial,sans-serif"
MONO = "'IBM Plex Mono',Consolas,monospace"


def norm(v):
    l = math.sqrt(sum(x * x for x in v))
    return [x / l for x in v]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def hex2rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def rgb2hex(c):
    return '#%02x%02x%02x' % tuple(max(0, min(255, int(round(x)))) for x in c)


def shade(h, k):
    c = hex2rgb(h)
    if k >= 0:
        return rgb2hex([x + (255 - x) * k for x in c])
    return rgb2hex([x * (1 + k) for x in c])


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def fmt(v):
    """mm value formatted pt-BR (comma decimal), max 1 decimal"""
    if abs(v - round(v)) < 0.05:
        return '%d' % round(v)
    return ('%.1f' % v).replace('.', ',')


class Obj:
    def __init__(self, kind, lo=None, hi=None, faces=None, fill='#ffffff', stroke=INK, sw=0.18, tag=None, ghost=False, dash=None):
        self.kind = kind
        self.fill = fill
        self.stroke = stroke
        self.sw = sw
        self.tag = tag
        self.ghost = ghost
        self.dash = dash
        if kind == 'box':
            self.lo = list(lo)
            self.hi = list(hi)
            self.faces3 = None
        else:
            self.faces3 = faces
            pts = [p for f in faces for lp in f[:1] for p in lp]
            self.lo = [min(p[i] for p in pts) for i in range(3)]
            self.hi = [max(p[i] for p in pts) for i in range(3)]

    def moved(self, d):
        o = Obj.__new__(Obj)
        o.__dict__.update(self.__dict__)
        o.lo = [self.lo[i] + d[i] for i in range(3)]
        o.hi = [self.hi[i] + d[i] for i in range(3)]
        if self.faces3 is not None:
            o.faces3 = [[[[p[0] + d[0], p[1] + d[1], p[2] + d[2]] for p in lp] for lp in f] for f in self.faces3]
        return o


def box(lo, hi, **kw):
    return Obj('box', lo, hi, **kw)


def mesh(faces, **kw):
    return Obj('mesh', faces=faces, **kw)


class Axo:
    """Orthographic axonometric camera. c points from the scene toward the viewer."""

    def __init__(self, c=(-0.52, -1.0, 0.62)):
        self.c = norm(c)
        up = [0, 0, 1]
        self.r = norm(cross(up, self.c))
        self.u = norm(cross(self.c, self.r))
        self.light = norm([-0.35, -0.8, 1.0])

    def p2(self, p):
        return (dot(p, self.r), -dot(p, self.u))

    def depth(self, p):
        return dot(p, self.c)


def box_faces(lo, hi):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    return [
        ([-1, 0, 0], [[x0, y0, z0], [x0, y1, z0], [x0, y1, z1], [x0, y0, z1]]),
        ([1, 0, 0], [[x1, y0, z0], [x1, y0, z1], [x1, y1, z1], [x1, y1, z0]]),
        ([0, -1, 0], [[x0, y0, z0], [x0, y0, z1], [x1, y0, z1], [x1, y0, z0]]),
        ([0, 1, 0], [[x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]]),
        ([0, 0, -1], [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0]]),
        ([0, 0, 1], [[x0, y0, z1], [x0, y1, z1], [x1, y1, z1], [x1, y0, z1]]),
    ]


def poly_normal(lp):
    n = [0, 0, 0]
    for i in range(len(lp)):
        a = lp[i]
        b = lp[(i + 1) % len(lp)]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    l = math.sqrt(dot(n, n))
    return [x / l for x in n] if l > 1e-9 else None


def pip(pt, poly):
    x, y = pt
    ins = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            ins = not ins
        j = i
    return ins


class Scene:
    def __init__(self, cam=None):
        self.cam = cam or Axo()
        self.objs = []
        self.arrows3 = []   # (p_from, p_to)
        self.dims3 = []     # (p1, p2, off, text)
        self.labels = []    # (text, obj_index or list, sub)
        self.lines3 = []    # (p1,p2,style)

    def add(self, o):
        self.objs.append(o)
        return len(self.objs) - 1

    # ---- projection of each object into 2D polygons
    def _polys(self, o):
        cam = self.cam
        out = []
        if o.kind == 'box':
            for n, q in box_faces(o.lo, o.hi):
                d = dot(n, cam.c)
                if d <= 1e-6:
                    continue
                # degenerate face check
                p2 = [cam.p2(p) for p in q]
                if abs(area2(p2)) < 1e-6:
                    continue
                k = dot(n, cam.light)
                fill = o.fill if o.ghost else face_tone(o.fill, n)
                out.append((p2, fill, q, n))
        else:
            fl = []
            for f in o.faces3:
                lp = f[0]
                if len(lp) < 3:
                    continue
                n = poly_normal(lp)
                if n is None:
                    continue
                if dot(n, cam.c) <= 0:
                    continue
                dep = sum(cam.depth(p) for p in lp) / len(lp)
                fl.append((dep, lp, n))
            fl.sort(key=lambda t: t[0])
            for dep, lp, n in fl:
                k = max(0.0, dot(n, cam.light))
                fill = o.fill if o.ghost else shade(o.fill, -0.28 + 0.38 * k)
                out.append(([cam.p2(p) for p in lp], fill, lp, n))
        return out

    def order(self):
        cam = self.cam
        n = len(self.objs)
        b2 = []
        for o in self.objs:
            pts = [cam.p2([x, y, z]) for x in (o.lo[0], o.hi[0]) for y in (o.lo[1], o.hi[1]) for z in (o.lo[2], o.hi[2])]
            b2.append((min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)))
        cen = [cam.depth([(o.lo[i] + o.hi[i]) / 2 for i in range(3)]) for o in self.objs]
        after = [set() for _ in range(n)]  # i must be drawn before j  => j in after[i]
        indeg = [0] * n
        eps = 0.05
        hulls = []
        for o in self.objs:
            pts = [cam.p2([x, y, z]) for x in (o.lo[0], o.hi[0]) for y in (o.lo[1], o.hi[1]) for z in (o.lo[2], o.hi[2])]
            hulls.append(convex_hull(pts))
        for i in range(n):
            for j in range(i + 1, n):
                a, b = b2[i], b2[j]
                if a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]:
                    continue
                if not hull_overlap(hulls[i], hulls[j]):
                    continue
                A, B = self.objs[i], self.objs[j]
                rel = None
                best = -1e9
                for k in range(3):
                    if abs(cam.c[k]) < 1e-9:
                        continue
                    # A below B on axis k
                    g1 = B.lo[k] - A.hi[k]
                    g2 = A.lo[k] - B.hi[k]
                    if g1 >= -eps and g1 > best:
                        best = g1
                        # camera on + side if c_k>0 -> B closer -> A first
                        rel = (i, j) if cam.c[k] > 0 else (j, i)
                    if g2 >= -eps and g2 > best:
                        best = g2
                        rel = (j, i) if cam.c[k] > 0 else (i, j)
                if rel is None:
                    rel = (i, j) if cen[i] < cen[j] else (j, i)
                f, t = rel
                if t not in after[f]:
                    after[f].add(t)
                    indeg[t] += 1
        res = []
        avail = [i for i in range(n) if indeg[i] == 0]
        done = [False] * n
        while len(res) < n:
            if not avail:
                rest = [i for i in range(n) if not done[i]]
                i = min(rest, key=lambda k: cen[k])
            else:
                avail.sort(key=lambda k: cen[k])
                i = avail.pop(0)
            if done[i]:
                continue
            done[i] = True
            res.append(i)
            for t in after[i]:
                indeg[t] -= 1
                if indeg[t] == 0 and not done[t]:
                    avail.append(t)
        return res

    def render(self, W, H, pad=4.0, label_cols=True, scale=None, title=None, extra_pts=None, center=True):
        """Return SVG string with viewBox in paper mm, width W, height H."""
        cam = self.cam
        order = self.order()
        polys = {i: self._polys(self.objs[i]) for i in range(len(self.objs))}
        pts = [p for i in polys for (pp, *_r) in polys[i] for p in pp]
        for (a, b, off, t) in self.dims3:
            for p in (a, b):
                q = [p[k] + off[k] * 1.35 for k in range(3)]
                pts.append(cam.p2(q))
        for (a, b) in self.arrows3:
            pts += [cam.p2(a), cam.p2(b)]
        if extra_pts:
            pts += [cam.p2(p) for p in extra_pts]
        if not pts:
            return '<svg/>'
        minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
        miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
        has_labels = bool(self.labels) and label_cols
        colw = 13.0 if has_labels else 0.0
        aw = W - 2 * pad - 2 * colw
        ah = H - 2 * pad
        s = scale if scale else min(aw / max(maxx - minx, 1e-6), ah / max(maxy - miny, 1e-6))
        ox = pad + colw + (aw - (maxx - minx) * s) / 2 - minx * s
        oy = pad + (ah - (maxy - miny) * s) / 2 - miny * s
        if not center:
            oy = pad - miny * s
        T = lambda p: (ox + p[0] * s, oy + p[1] * s)
        self._T = T
        self._s = s
        out = []
        out.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.2f %.2f" width="%.2fmm" height="%.2fmm" font-family="%s">' % (W, H, W, H, FONT.replace('"', "'")))
        out.append('<defs><marker id="ah" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="2.6" markerHeight="2.6" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0,1.5 L10,5 L0,8.5 z" fill="%s"/></marker>'
                   '<marker id="ahA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker></defs>' % (INK, ACCENT))
        drawn = []  # (obj index, 2D polys in paper coords)
        for i in order:
            o = self.objs[i]
            pl = []
            for (pp, fill, q, n) in polys[i]:
                tp = [T(p) for p in pp]
                pl.append(tp)
                d = ' '.join('%.2f,%.2f' % p for p in tp)
                dash = ' stroke-dasharray="%s"' % o.dash if o.dash else ''
                out.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%.3f" stroke-linejoin="round"%s/>' % (d, fill, o.stroke, o.sw, dash))
            drawn.append((i, pl))
        self._drawn = drawn
        # arrows (motion)
        for (a, b) in self.arrows3:
            pa, pb = T(cam.p2(a)), T(cam.p2(b))
            out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.45" stroke-dasharray="1.6 0.9" marker-end="url(#ahA)"/>' % (pa[0], pa[1], pb[0], pb[1], ACCENT))
        for (a, b, st) in self.lines3:
            pa, pb = T(cam.p2(a)), T(cam.p2(b))
            out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>' % (pa[0], pa[1], pb[0], pb[1], st))
        # dimensions
        for (a, b, off, text) in self.dims3:
            out.append(self._dim(a, b, off, text))
        # labels
        if self.labels:
            out.append(self._labels(W, H, pad, colw, label_cols))
        out.append('</svg>')
        return '\n'.join(out)

    def _dim(self, a, b, off, text):
        cam = self.cam
        T = self._T
        a2 = [a[k] + off[k] for k in range(3)]
        b2 = [b[k] + off[k] for k in range(3)]
        ext = [off[k] * 1.12 for k in range(3)]
        pa, pb = T(cam.p2(a)), T(cam.p2(b))
        qa, qb = T(cam.p2(a2)), T(cam.p2(b2))
        ea, eb = T(cam.p2([a[k] + ext[k] for k in range(3)])), T(cam.p2([b[k] + ext[k] for k in range(3)]))
        # start extension lines with a small gap from the object
        def gap(p, q, g=0.8):
            dx, dy = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dy) or 1
            return (p[0] + dx / L * g, p[1] + dy / L * g)
        ga, gb = gap(pa, ea), gap(pb, eb)
        s = []
        s.append('<g stroke="%s" stroke-width="0.14" fill="none">' % INK2)
        s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>' % (ga[0], ga[1], ea[0], ea[1]))
        s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>' % (gb[0], gb[1], eb[0], eb[1]))
        s.append('</g>')
        s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" marker-start="url(#ah)" marker-end="url(#ah)"/>' % (qa[0], qa[1], qb[0], qb[1], INK))
        mx, my = (qa[0] + qb[0]) / 2, (qa[1] + qb[1]) / 2
        ang = math.degrees(math.atan2(qb[1] - qa[1], qb[0] - qa[0]))
        if ang > 90: ang -= 180
        if ang <= -90: ang += 180
        # offset text perpendicular, away from object (direction of off)
        nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
        od = (qa[0] - pa[0], qa[1] - pa[1])
        if nx * od[0] + ny * od[1] < 0:
            nx, ny = -nx, -ny
        # text sits on the outer side of the line
        tx, ty = mx + nx * 1.6, my + ny * 1.6
        s.append('<text x="%.2f" y="%.2f" font-size="3.0" font-weight="600" fill="%s" text-anchor="middle" dominant-baseline="middle" transform="rotate(%.2f %.2f %.2f)" style="paint-order:stroke" stroke="#fff" stroke-width="0.9">%s</text>' % (tx, ty, INK, ang, tx, ty, esc(text)))
        return '\n'.join(s)

    def anchor(self, idx):
        """visible 2D anchor point (paper coords) for object idx"""
        cam = self.cam
        T = self._T
        pos = [k for k, (i, _) in enumerate(self._drawn) if i == idx][0]
        later = [pl for (i, pls) in self._drawn[pos + 1:] for pl in pls]
        my = self._drawn[pos][1]
        best = None
        # sample candidate points on own polygons, biggest polygon first
        cand = []
        for pl in sorted(my, key=lambda p: -abs(area2(p))):
            cx = sum(p[0] for p in pl) / len(pl)
            cy = sum(p[1] for p in pl) / len(pl)
            cand.append((cx, cy))
            for t in (0.25, 0.5, 0.75):
                for u in (0.25, 0.5, 0.75):
                    if len(pl) == 4:
                        a, b, c, d = pl
                        p = [(a[k] * (1 - t) * (1 - u) + b[k] * t * (1 - u) + c[k] * t * u + d[k] * (1 - t) * u) for k in range(2)]
                        cand.append(tuple(p))
            if len(cand) > 40:
                break
        for p in cand:
            if not any(pip(p, q) for q in later):
                return p
        return cand[0] if cand else (0, 0)

    def _labels(self, W, H, pad, colw, cols):
        R = 2.9
        items = []
        for (text, idxs, sub) in self.labels:
            if not isinstance(idxs, (list, tuple)):
                idxs = [idxs]
            anchors = [self.anchor(i) for i in idxs]
            items.append([text, anchors, sub])
        if not items:
            return ''
        allx = [p[0] for pl in self._drawn for poly in pl[1] for p in poly]
        x0, x1 = (min(allx), max(allx)) if allx else (pad, W - pad)
        midx = (x0 + x1) / 2
        left = [it for it in items if it[1][0][0] < midx]
        right = [it for it in items if it[1][0][0] >= midx]
        # balance
        while len(left) - len(right) > 3:
            right.append(left.pop(max(range(len(left)), key=lambda k: left[k][1][0][0])))
        while len(right) - len(left) > 3:
            left.append(right.pop(min(range(len(right)), key=lambda k: right[k][1][0][0])))
        out = []
        top, bot = pad + R, H - pad - R

        def place(group, xcol):
            group.sort(key=lambda it: it[1][0][1])
            gap = 2 * R + 1.6
            ys = [it[1][0][1] for it in group]
            for k in range(len(ys)):
                ys[k] = max(ys[k], top if k == 0 else ys[k - 1] + gap)
            if ys and ys[-1] > bot:
                ys[-1] = bot
                for k in range(len(ys) - 2, -1, -1):
                    ys[k] = min(ys[k], ys[k + 1] - gap)
            for it, y in zip(group, ys):
                text, anchors, sub = it
                for a in anchors:
                    ex = xcol + (R if xcol < a[0] else -R)
                    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.18"/>' % (ex, y, a[0], a[1], INK))
                    out.append('<circle cx="%.2f" cy="%.2f" r="0.55" fill="%s"/>' % (a[0], a[1], INK))
                out.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#fff" stroke="%s" stroke-width="0.3"/>' % (xcol, y, R, INK))
                out.append('<text x="%.2f" y="%.2f" font-size="2.75" font-weight="700" text-anchor="middle" dominant-baseline="central" fill="%s">%s</text>' % (xcol, y + 0.1, INK, esc(text)))
                if sub:
                    sx = xcol + (R + 0.6) * (1 if xcol < midx else -1)
                    anc = 'start' if xcol < midx else 'end'
                    out.append('<text x="%.2f" y="%.2f" font-size="2.3" font-weight="600" text-anchor="%s" fill="%s">%s</text>' % (sx, y - R - 0.4, anc, INK2, esc(sub)))
        lx = max(pad + R, min(x0 - 5, pad + colw - R)) if cols else x0 - 6
        rx = min(W - pad - R, max(x1 + 5, W - pad - colw + R)) if cols else x1 + 6
        place(left, lx)
        place(right, rx)
        return '\n'.join(out)


def convex_hull(pts):
    pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in pts))
    if len(pts) <= 2:
        return pts
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def hull_overlap(A, B, tol=1e-3):
    if len(A) < 3 or len(B) < 3:
        return False
    for P in (A, B):
        for k in range(len(P)):
            x1, y1 = P[k]
            x2, y2 = P[(k + 1) % len(P)]
            nx, ny = y1 - y2, x2 - x1
            L = math.hypot(nx, ny)
            if L < 1e-12:
                continue
            nx, ny = nx / L, ny / L
            pa = [nx * p[0] + ny * p[1] for p in A]
            pb = [nx * p[0] + ny * p[1] for p in B]
            if max(pa) <= min(pb) + tol or max(pb) <= min(pa) + tol:
                return False
    return True


def area2(p):
    a = 0
    for i in range(len(p)):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % len(p)]
        a += x1 * y2 - x2 * y1
    return a / 2


def face_tone(fill, n):
    if n[2] > 0.5:
        return shade(fill, 0.35)
    if n[2] < -0.5:
        return shade(fill, -0.25)
    if abs(n[0]) > 0.5:
        return shade(fill, -0.16)
    return fill


# ---------------- orthographic views ----------------
class Ortho:
    """view: 'front' (from -y), 'right' (from +x), 'left' (from -x), 'top' (from +z), 'back' (from +y)"""
    AX = {
        'front': (lambda p: (p[0], -p[2]), lambda p: -p[1]),
        'back': (lambda p: (-p[0], -p[2]), lambda p: p[1]),
        'right': (lambda p: (p[1], -p[2]), lambda p: p[0]),
        'left': (lambda p: (-p[1], -p[2]), lambda p: -p[0]),
        'top': (lambda p: (p[0], -p[1]), lambda p: p[2]),
    }

    def __init__(self, view):
        self.view = view
        self.f, self.dep = Ortho.AX[view]
        self.objs = []
        self.dims = []   # (p1(2d model), p2, side, offset, text)
        self.notes = []  # (pt2d model, text, dx, dy)
        self.clines = [] # centerlines (a2d,b2d,label)

    def add(self, o):
        self.objs.append(o)

    def rect(self, o):
        pts = [self.f([x, y, z]) for x in (o.lo[0], o.hi[0]) for y in (o.lo[1], o.hi[1]) for z in (o.lo[2], o.hi[2])]
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)

    def dim(self, a, b, orient, off, text=None):
        """a,b: 2D model points (view coords). orient 'h' or 'v'. off: offset distance (model units, signed) perpendicular"""
        self.dims.append((a, b, orient, off, text))

    def render(self, W, H, pad=6.0, scale=None, fit_extra=0):
        rects = [(self.rect(o), o) for o in self.objs]
        xs = [r[0][0] for r in rects] + [r[0][2] for r in rects]
        ys = [r[0][1] for r in rects] + [r[0][3] for r in rects]
        for (a, b, orient, off, text) in self.dims:
            if orient == 'h':
                ys.append(a[1] + off); ys.append(b[1] + off)
            else:
                xs.append(a[0] + off); xs.append(b[0] + off)
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        aw, ah = W - 2 * pad, H - 2 * pad
        s = scale if scale else min(aw / (maxx - minx), ah / (maxy - miny))
        ox = pad + (aw - (maxx - minx) * s) / 2 - minx * s
        oy = pad + (ah - (maxy - miny) * s) / 2 - miny * s
        T = lambda p: (ox + p[0] * s, oy + p[1] * s)
        self.s = s
        self.T = T
        out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.2f %.2f" width="%.2fmm" height="%.2fmm" font-family="%s">' % (W, H, W, H, FONT.replace('"', "'")),
               '<defs><marker id="oh" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="2.4" markerHeight="2.4" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0,1.5 L10,5 L0,8.5 z" fill="%s"/></marker></defs>' % INK]
        order = sorted(range(len(self.objs)), key=lambda i: min(self.dep([x, y, z]) for x in (self.objs[i].lo[0], self.objs[i].hi[0]) for y in (self.objs[i].lo[1], self.objs[i].hi[1]) for z in (self.objs[i].lo[2], self.objs[i].hi[2])))
        for i in order:
            (x0, y0, x1, y1), o = rects[i]
            a, b = T((x0, y0)), T((x1, y1))
            dash = ' stroke-dasharray="%s"' % o.dash if o.dash else ''
            out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s" stroke-width="%.3f"%s/>' % (a[0], a[1], max(b[0] - a[0], 0.05), max(b[1] - a[1], 0.05), o.fill, o.stroke, o.sw, dash))
        for (a, b, lab) in self.clines:
            pa, pb = T(a), T(b)
            out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" stroke-dasharray="4 1 0.8 1"/>' % (pa[0], pa[1], pb[0], pb[1], ACCENT))
            if lab:
                out.append('<text x="%.2f" y="%.2f" font-size="2.4" fill="%s" font-weight="600" text-anchor="end">%s</text>' % (pa[0] - 1, pa[1] + 0.8, ACCENT, esc(lab)))
        for (a, b, orient, off, text) in self.dims:
            out.append(self._dim(a, b, orient, off, text))
        for (p, text, dx, dy) in self.notes:
            q = T(p)
            out.append('<text x="%.2f" y="%.2f" font-size="2.5" fill="%s">%s</text>' % (q[0] + dx, q[1] + dy, INK2, esc(text)))
        out.append('</svg>')
        return '\n'.join(out)

    def _dim(self, a, b, orient, off, text):
        T = self.T
        if orient == 'h':
            pa, pb = (a[0], a[1]), (b[0], b[1])
            qa, qb = (a[0], a[1] + off), (b[0], a[1] + off)
            qb = (b[0], a[1] + off)
            ea, eb = (a[0], a[1] + off * 1.0), (b[0], a[1] + off)
            val = abs(b[0] - a[0])
        else:
            pa, pb = (a[0], a[1]), (b[0], b[1])
            qa, qb = (a[0] + off, a[1]), (a[0] + off, b[1])
            val = abs(b[1] - a[1])
        text = text if text is not None else fmt(val)
        A, B = T(pa), T(pb)
        QA, QB = T(qa), T(qb)
        s = []
        sg = 1 if off > 0 else -1
        ext = 1.4
        if orient == 'h':
            s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.13"/>' % (A[0], A[1] + sg * 0.8, QA[0], QA[1] + sg * ext, INK2))
            s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.13"/>' % (B[0], T(pb)[1] + sg * 0.8, QB[0], QB[1] + sg * ext, INK2))
        else:
            s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.13"/>' % (A[0] + sg * 0.8, A[1], QA[0] + sg * ext, QA[1], INK2))
            s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.13"/>' % (T(pb)[0] + sg * 0.8, B[1], QB[0] + sg * ext, QB[1], INK2))
        L = math.hypot(QB[0] - QA[0], QB[1] - QA[1])
        small = L < 7
        if small:
            s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.18"/>' % (QA[0], QA[1], QB[0], QB[1], INK))
            for P in (QA, QB):
                s.append('<circle cx="%.2f" cy="%.2f" r="0.45" fill="%s"/>' % (P[0], P[1], INK))
        else:
            s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.18" marker-start="url(#oh)" marker-end="url(#oh)"/>' % (QA[0], QA[1], QB[0], QB[1], INK))
        mx, my = (QA[0] + QB[0]) / 2, (QA[1] + QB[1]) / 2
        fs = 2.7
        if orient == 'h':
            ty = my - 1.0 if off < 0 else my + fs + 0.3
            if small:
                tx = QB[0] + 1.0 + len(text) * 0.65
                s.append('<text x="%.2f" y="%.2f" font-size="%.1f" font-weight="600" text-anchor="middle" fill="%s">%s</text>' % (tx, my - 0.8, fs, INK, esc(text)))
            else:
                s.append('<text x="%.2f" y="%.2f" font-size="%.1f" font-weight="600" text-anchor="middle" fill="%s">%s</text>' % (mx, ty, fs, INK, esc(text)))
        else:
            tx = mx - 1.0 if off < 0 else mx + 1.0 + fs * 0.75
            if small:
                s.append('<text x="%.2f" y="%.2f" font-size="%.1f" font-weight="600" text-anchor="%s" dominant-baseline="middle" fill="%s">%s</text>' % (mx + (-1.2 if off < 0 else 1.2), my, fs, 'end' if off < 0 else 'start', INK, esc(text)))
            else:
                s.append('<text x="%.2f" y="%.2f" font-size="%.1f" font-weight="600" text-anchor="middle" fill="%s" transform="rotate(-90 %.2f %.2f)">%s</text>' % (tx, my, fs, INK, tx, my, esc(text)))
        return '\n'.join(s)

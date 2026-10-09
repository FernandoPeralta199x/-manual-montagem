"""Desenhos do manual a partir de um Project (perspectivas, explodidas, etapas, vistas, peças, detalhes)."""
import re

from .draw import *  # noqa: F401,F403
from .draw import fmt as F

CAM = (-0.52, -1.0, 0.62)

WOOD = ('carvalho', 'freij', 'nogueira', 'louro', 'cedro', 'amêndoa', 'amendoa', 'rústico', 'rustico', 'madeira', 'imbuia', 'jequitib', 'teca', 'pinus', 'tauari', 'cumaru')
GREY = ('manhattan', 'cinza', 'grafite', 'titânio', 'titanio', 'chumbo', 'concreto', 'cristal')


def color_for(pj, cor):
    over = pj.spec.get('cores', {})
    if cor in over:
        return over[cor]
    c = (cor or '').lower()
    if c in ('branco', 'branco tx', 'branco ártico', 'branco artico') or c.startswith('branco'):
        return MAT['Branco']
    if any(w in c for w in WOOD):
        return MAT['Carvalho Natural']
    if any(w in c for w in GREY):
        return MAT['Manhattan']
    if 'preto' in c or 'black' in c:
        return '#6c6e70'
    return '#d9d9d6'


def pfill(pj, code):
    return color_for(pj, pj.P[code]['cor'])


def hw_objs(pj, key, ghost=False, fill=None, idx=None):
    out = []
    for j, h in enumerate(pj.hw.get(key, [])):
        if idx is not None and j not in idx:
            continue
        if h['render'] == 'box' or not h['faces']:
            out.append(box(h['box'][0], h['box'][1], fill=fill or MAT['metal'], ghost=ghost, tag=key))
        else:
            out.append(mesh(h['faces'], fill=fill or MAT['metal'], ghost=ghost, tag=key, sw=0.1))
    return out


def hw_keys(pj, mid, montado=True):
    return [k for k, h in pj.spec.get('hardware', {}).items() if h['mod'] == mid and (not montado or h.get('mostrar_montado', True))]


def module_scene(pj, mid, cam=None, include_hw=True):
    sc = Scene(cam or Axo(CAM))
    idx = {}
    for p in pj.mod_parts(mid):
        for k, b in enumerate(p['boxes']):
            idx[(p['code'], k)] = sc.add(box(b[0], b[1], fill=pfill(pj, p['code']), tag=p['code']))
    if include_hw:
        for key in hw_keys(pj, mid):
            for j, o in enumerate(hw_objs(pj, key)):
                idx[(key, j)] = sc.add(o)
    return sc, idx


def iso_dims(pj, sc, mid):
    lo, hi = pj.caixa_bbox(mid)
    flo, _ = pj.mod_bbox(mid)
    o = 0.09 * max(hi[2], hi[0])
    sc.dims3.append(([lo[0], flo[1], lo[2]], [hi[0], flo[1], lo[2]], [0, -o * 1.2, 0], F(hi[0] - lo[0])))
    sc.dims3.append(([hi[0], flo[1], lo[2]], [hi[0], flo[1], hi[2]], [o, 0, 0], F(hi[2] - lo[2])))
    sc.dims3.append(([hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]], [o, 0, 0], F(hi[1] - lo[1])))


def assembled(pj, mid, W, H, dims=True):
    sc, idx = module_scene(pj, mid, Axo(CAM))
    if dims:
        iso_dims(pj, sc, mid)
    return sc.render(W, H)


def cover_scene(pj, W, H):
    sc = Scene(Axo(CAM))
    dx = 0
    for mid in pj.mod_ids():
        lo, hi = pj.mod_bbox(mid)
        s2, _ = module_scene(pj, mid, Axo(CAM))
        for o in s2.objs:
            sc.add(o.moved([dx - lo[0], 0, 0]))
        dx += (hi[0] - lo[0]) + 160
    return sc.render(W, H, pad=2)


def _hw_offset(spec_item, j, o, mid_x):
    if 'offset_lados' in spec_item:
        left, right = spec_item['offset_lados']
        cx = (o.lo[0] + o.hi[0]) / 2
        return left if cx < mid_x else right
    return spec_item.get('offset', [0, 0, 0])


def ghost_scene(pj, mid, show, new, offsets=None, hw_show=(), hw_new=(), label_sub=None, arrow_codes=None, inst=None, labels=True, arrows=True):
    """show: códigos já instalados (cinza). new: códigos da etapa (laranja). inst: {code: [índices]} para limitar instâncias."""
    sc = Scene(Axo(CAM))
    offsets = offsets or {}
    lo, hi = pj.caixa_bbox(mid)
    mid_x = (lo[0] + hi[0]) / 2
    lab = {}
    for p in pj.mod_parts(mid):
        c = p['code']
        for k, b in enumerate(p['boxes']):
            if inst and c in inst and k not in inst[c]:
                continue
            if c in show:
                sc.add(box(b[0], b[1], fill=GHOST_FILL, stroke=GHOST_STROKE, ghost=True, sw=0.14))
            elif c in new:
                d = offsets.get(c, [0, 0, 0])
                if isinstance(d, dict) and 'lados' in d:
                    cx = (b[0][0] + b[1][0]) / 2
                    d = d['lados'][0] if cx < mid_x else d['lados'][1]
                i = sc.add(box(b[0], b[1], fill=ACCENT_FILL, stroke=INK, sw=0.2).moved(d))
                lab.setdefault(c, []).append(i)
                if arrows and any(abs(x) > 1 for x in d) and (arrow_codes is None or c in arrow_codes):
                    cen = [(b[0][j] + b[1][j]) / 2 for j in range(3)]
                    sc.arrows3.append(([cen[j] + d[j] for j in range(3)], [cen[j] + d[j] * 0.18 for j in range(3)]))
    for key in hw_show:
        for o in hw_objs(pj, key, ghost=True, fill=GHOST_FILL):
            o.stroke = GHOST_STROKE
            o.sw = 0.1
            sc.add(o)
    for item in hw_new:
        key = item['key']
        ids = []
        for j, o in enumerate(hw_objs(pj, key, fill=ACCENT_FILL, idx=item.get('idx'))):
            dd = _hw_offset(item, j, o, mid_x)
            ids.append(sc.add(o.moved(dd)))
            if arrows and any(abs(x) > 1 for x in dd):
                cen = [(o.lo[q] + o.hi[q]) / 2 for q in range(3)]
                sc.arrows3.append(([cen[q] + dd[q] for q in range(3)], [cen[q] + dd[q] * 0.15 for q in range(3)]))
        lab[key.split('_')[0]] = ids
    if labels:
        for c, ids in lab.items():
            n = len(ids)
            s = (label_sub or {}).get(c, ('×%d' % n if n > 1 else None))
            sc.labels.append((c, ids[:1], s))
    return sc


def exploded(pj, ex):
    """ex: {mod, pecas:{code: offset}, inst: k opcional, hw:[{key, idx?, offset|offset_lados, sub?}], rotulos:{code: sub}}"""
    sc = Scene(Axo(CAM))
    mid = ex['mod']
    lo, hi = pj.caixa_bbox(mid)
    mid_x = (lo[0] + hi[0]) / 2
    k_only = ex.get('inst')
    rot = ex.get('rotulos', {})
    for c, d in ex['pecas'].items():
        p = pj.P[c]
        boxes = [p['boxes'][k_only]] if k_only is not None else p['boxes']
        ids = []
        for b in boxes:
            dd = d
            if isinstance(d, dict) and 'lados' in d:
                cx = (b[0][0] + b[1][0]) / 2
                dd = d['lados'][0] if cx < mid_x else d['lados'][1]
            ids.append(sc.add(box(b[0], b[1], fill=pfill(pj, c)).moved(dd)))
        n = len(ids)
        sc.labels.append((c, [ids[n // 2]] if n > 1 else ids, rot.get(c, '×%d' % n if n > 1 else None)))
    for item in ex.get('hw', []):
        key = item['key']
        ids = []
        for j, o in enumerate(hw_objs(pj, key, idx=item.get('idx'))):
            ids.append(sc.add(o.moved(_hw_offset(item, j, o, mid_x))))
        if ids:
            sc.labels.append((key.split('_')[0], ids[:1], item.get('sub')))
    return sc


def locator(pj, mid, code, W, H):
    sc = Scene(Axo(CAM))
    for p in pj.mod_parts(mid):
        for b in p['boxes']:
            if p['code'] == code:
                sc.add(box(b[0], b[1], fill=ACCENT, stroke=INK, sw=0.12))
            else:
                sc.add(box(b[0], b[1], fill='#f3f3f1', stroke='#9b9ea1', sw=0.08, ghost=True))
    return sc.render(W, H, pad=1.0)


# ---------------------------------------------------------------- peça individual
def part_view(pj, code):
    b = pj.P[code]['boxes'][0]
    sz = [b[1][i] - b[0][i] for i in range(3)]
    thin = min(range(3), key=lambda i: sz[i])
    if thin == 0:
        return 'lateral', sz[1], sz[2], sz[0], 'left'
    if thin == 1:
        return 'frontal', sz[0], sz[2], sz[1], None
    return 'superior', sz[0], sz[1], sz[2], 'bottom'


def match_csv(pj, code):
    p = pj.P[code]
    view, hm, vm, _, _ = part_view(pj, code)
    if not p['csv']:
        return hm, vm, hm, vm, ('—', '—')
    c, l = p['csv'][0]['c'], p['csv'][0]['l']
    if abs(c - hm) + abs(l - vm) <= abs(c - vm) + abs(l - hm):
        return c, l, hm, vm, ('C', 'L')
    return l, c, hm, vm, ('L', 'C')


def part_svg(pj, code, W, H):
    p = pj.P[code]
    view, hm, vm, th, front = part_view(pj, code)
    hc, vc, hm, vm, names = match_csv(pj, code)
    pad = 9.0
    s = min((W - 2 * pad - 6) / hc, (H - 2 * pad - 6) / vc)
    w, h = hc * s, vc * s
    x0 = pad + 4 + (W - 2 * pad - 6 - w) / 2
    y0 = pad + (H - 2 * pad - 6 - h) / 2
    fill = pfill(pj, code)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.2f %.2f" width="%.2fmm" height="%.2fmm" font-family="%s">' % (W, H, W, H, FONT),
           '<defs><marker id="ph" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="2.4" markerHeight="2.4" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0,1.5 L10,5 L0,8.5 z" fill="%s"/></marker></defs>' % INK,
           '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s" stroke-width="0.35"/>' % (x0, y0, w, h, shade(fill, 0.25), INK)]
    if front == 'left':
        out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.1"/>' % (x0, y0, x0, y0 + h, ACCENT))
        out.append('<text x="%.2f" y="%.2f" font-size="2.3" font-weight="700" fill="%s" text-anchor="middle" transform="rotate(-90 %.2f %.2f)">FRENTE</text>' % (x0 + 2.6, y0 + h / 2, ACCENT, x0 + 2.6, y0 + h / 2))
    elif front == 'bottom':
        out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.1"/>' % (x0, y0 + h, x0 + w, y0 + h, ACCENT))
        out.append('<text x="%.2f" y="%.2f" font-size="2.3" font-weight="700" fill="%s" text-anchor="middle">FRENTE</text>' % (x0 + w / 2, y0 + h - 1.6, ACCENT))
    wh, wv = abs(hc - hm) > 1.5, abs(vc - vm) > 1.5
    yy = y0 + h + 5.0
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.13"/>' % (x0, y0 + h + 0.8, x0, yy + 1.2, INK))
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.13"/>' % (x0 + w, y0 + h + 0.8, x0 + w, yy + 1.2, INK))
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" marker-start="url(#ph)" marker-end="url(#ph)"/>' % (x0, yy, x0 + w, yy, INK))
    out.append('<text x="%.2f" y="%.2f" font-size="3.2" font-weight="700" text-anchor="middle" fill="%s">%s</text>' % (x0 + w / 2, yy + 4.0, ACCENT if wh else INK, F(hc) + (' ⚠' if wh else '')))
    xx = x0 - 5.0
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.13"/>' % (x0 - 0.8, y0, xx - 1.2, y0, INK))
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.13"/>' % (x0 - 0.8, y0 + h, xx - 1.2, y0 + h, INK))
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" marker-start="url(#ph)" marker-end="url(#ph)"/>' % (xx, y0, xx, y0 + h, INK))
    tx, ty = xx - 1.6, y0 + h / 2
    out.append('<text x="%.2f" y="%.2f" font-size="3.2" font-weight="700" text-anchor="middle" fill="%s" transform="rotate(-90 %.2f %.2f)">%s</text>' % (tx, ty, ACCENT if wv else INK, tx, ty, F(vc) + (' ⚠' if wv else '')))
    out.append('</svg>')
    return '\n'.join(out), view, (wh or wv), (hc, vc, hm, vm, names)


# ---------------------------------------------------------------- vistas ortográficas
def ortho(pj, mid, view, W, H, dims=True, hw=True, scale=None, detail=True):
    o = Ortho(view)
    for p in pj.mod_parts(mid):
        for b in p['boxes']:
            o.add(box(b[0], b[1], fill='#ffffff', sw=0.2))
    if hw:
        for key in hw_keys(pj, mid):
            if pj.spec['hardware'][key].get('vistas', True):
                for h in pj.hw[key]:
                    o.add(box(h['box'][0], h['box'][1], fill='#ffffff', sw=0.16))
    lo, hi = pj.caixa_bbox(mid)
    flo, fhi = pj.mod_bbox(mid)
    cot = pj.mods[mid].get('cotas', {})
    H_ = hi[2]
    Wd = hi[0] - lo[0]
    ow = -(0.045 * H_ + 40)
    oh = 0.02 * H_ + 75
    oc = 0.004 * H_ + 37
    if dims:
        if view == 'front':
            o.dim((lo[0], -H_), (hi[0], -H_), 'h', ow, F(Wd))
            o.dim((hi[0], -lo[2]), (hi[0], -H_), 'v', oh, F(H_ - lo[2]))
            if detail:
                codes = cot.get('cadeia_esquerda', [])
                if codes:
                    zs = [lo[2], H_] + cot.get('cadeia_extra', [])
                    for c in codes:
                        for b in pj.P[c]['boxes']:
                            zs += [b[0][2], b[1][2]]
                    zs = sorted(set(round(z, 2) for z in zs))
                    for a, b in zip(zs[:-1], zs[1:]):
                        o.dim((lo[0], -a), (lo[0], -b), 'v', -oc, None)
                codes = cot.get('cadeia_direita', [])
                for c in codes:
                    for b in pj.P[c]['boxes']:
                        o.dim((hi[0], -b[0][2]), (hi[0], -b[1][2]), 'v', oc + 8, None)
                if cot.get('folga_lateral'):
                    b = pj.P[cot['folga_lateral']]['boxes'][0]
                    o.dim((lo[0], -b[0][2]), (b[0][0], -b[0][2]), 'h', 30, None)
        elif view == 'right':
            o.dim((flo[1], -H_), (hi[1], -H_), 'h', ow, None)
            o.dim((lo[1], -lo[2]), (hi[1], -lo[2]), 'h', 0.03 * H_ + 18, None)
            o.dim((hi[1], -lo[2]), (hi[1], -H_), 'v', 0.02 * H_ + 45, F(H_ - lo[2]))
            if detail and cot.get('recuo_topo'):
                b = pj.P[cot['recuo_topo']]['boxes'][-1]
                o.dim((lo[1], -b[1][2]), (b[0][1], -b[1][2]), 'h', -40, None)
            if detail and cot.get('recuo_base'):
                b = pj.P[cot['recuo_base']]['boxes'][0]
                o.dim((lo[1], -lo[2]), (b[0][1], -lo[2]), 'h', 22, None)
        elif view == 'top':
            o.dim((lo[0], -hi[1]), (hi[0], -hi[1]), 'h', -50, F(Wd))
            o.dim((hi[0], -flo[1]), (hi[0], -hi[1]), 'v', 50, None)
            o.dim((lo[0], -lo[1]), (lo[0], -hi[1]), 'v', -40, None)
    svg = o.render(W, H, scale=scale)
    ortho.last_s = o.s
    return svg


def ortho_set(pj, mid, specs, detail=True):
    ss = []
    for (v, W, H) in specs:
        ortho(pj, mid, v, W, H, detail=detail)
        ss.append(ortho.last_s)
    s = min(ss)
    return [ortho(pj, mid, v, W, H, detail=detail, scale=s) for (v, W, H) in specs], s


# ---------------------------------------------------------------- detalhes
def door_detail(pj, det, W, H):
    mid = pj.P[det['porta']]['mod']
    door = pj.P[det['porta']]['boxes'][det.get('inst', 0)]
    lo, hi = pj.caixa_bbox(mid)
    cut = det.get('corte_z', door[1][2] + 60)
    o = Ortho('front')
    for c in det.get('contexto', []):
        for bb in pj.P[c]['boxes']:
            if bb[0][2] > cut:
                continue
            o.add(box(bb[0], [bb[1][0], bb[1][1], min(bb[1][2], cut)], fill='#f4f4f2', stroke='#8f9396', sw=0.16, dash='1.2 0.8'))
    o.add(box(door[0], door[1], fill='#ffffff', sw=0.3))
    x0, x1, z0, z1 = door[0][0], door[1][0], door[0][2], door[1][2]
    if det.get('puxador'):
        for h in pj.hw[det['puxador']]:
            hb = h['box']
            if x0 - 5 <= (hb[0][0] + hb[1][0]) / 2 <= x1 + 5 and z0 - 5 <= (hb[0][2] + hb[1][2]) / 2 <= z1 + 5:
                o.add(box(hb[0], hb[1], fill='#ffffff', sw=0.2))
    hz = []
    side_right = True
    if det.get('dobradicas'):
        for hh in pj.hw[det['dobradicas']]:
            hb = hh['box']
            zc = (hb[0][2] + hb[1][2]) / 2
            if not (z0 - 5 <= zc <= z1 + 5):
                continue
            xc = (hb[0][0] + hb[1][0]) / 2
            side_right = xc > (x0 + x1) / 2
            hz.append(zc)
            if side_right:
                o.clines.append(((x1 - 70, -zc), (x1 + 4, -zc), 'eixo dobradiça'))
            else:
                o.clines.append(((x0 + 70, -zc), (x0 - 4, -zc), 'eixo dobradiça'))
    hz.sort()
    xe = x1 if side_right else x0
    sg = 1 if side_right else -1
    o.dim((x0, -z1), (x1, -z1), 'h', -40, None)
    o.dim((xe, -z0), (xe, -z1), 'v', sg * 70, None)
    if hz:
        o.dim((xe, -z0), (xe, -hz[0]), 'v', sg * 40, None)
        o.dim((xe, -hz[-1]), (xe, -z1), 'v', sg * 40, None)
    xo = x0 if side_right else x1
    o.dim((xo, -lo[2]), (xo, -z0), 'v', -sg * 40, None)
    o.dim((xo, -z0), (xo, -z1), 'v', -sg * 40, None)
    o.dim((lo[0], -z0), (x0, -z0), 'h', 22, None)
    o.dim((x1, -z0), (hi[0], -z0), 'h', 22, None)
    return o.render(W, H)


def handle_detail(W, H, fw, fh, hx, hz, hlen, vertical=False, cor='#a3a8ad'):
    """Vista frontal de um painel (fw × fh) com o centro do puxador a hx da borda esq. e hz da borda sup."""
    pad = 12
    s = min((W - 2 * pad) / fw, (H - 2 * pad) / fh)
    x0 = (W - fw * s) / 2
    y0 = (H - fh * s) / 2
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.2f %.2f" width="%.2fmm" height="%.2fmm" font-family="%s">' % (W, H, W, H, FONT),
           '<defs><marker id="hh" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="2.4" markerHeight="2.4" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0,1.5 L10,5 L0,8.5 z" fill="%s"/></marker></defs>' % INK,
           '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s" stroke-width="0.35"/>' % (x0, y0, fw * s, fh * s, shade(cor, 0.45), INK)]
    cx, cy = x0 + hx * s, y0 + hz * s
    if vertical:
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="%s" stroke-width="0.2" stroke-dasharray="1 0.6"/>' % (cx - 4 * s, cy - hlen / 2 * s, 8 * s, hlen * s, INK2))
    else:
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="%s" stroke-width="0.2" stroke-dasharray="1 0.6"/>' % (cx - hlen / 2 * s, cy - 4 * s, hlen * s, 8 * s, INK2))
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" stroke-dasharray="4 1 0.8 1"/>' % (cx, y0 - 3, cx, y0 + fh * s + 3, ACCENT))
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" stroke-dasharray="4 1 0.8 1"/>' % (x0 - 3, cy, x0 + fw * s + 3, cy, ACCENT))
    out.append('<circle cx="%.2f" cy="%.2f" r="1.1" fill="none" stroke="%s" stroke-width="0.35"/>' % (cx, cy, ACCENT))

    def dimh(xa, xb, y, t):
        out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" marker-start="url(#hh)" marker-end="url(#hh)"/>' % (xa, y, xb, y, INK))
        out.append('<text x="%.2f" y="%.2f" font-size="3" font-weight="700" text-anchor="middle" fill="%s">%s</text>' % ((xa + xb) / 2, y - 1, INK, t))

    def dimv(ya, yb, x, t):
        out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" marker-start="url(#hh)" marker-end="url(#hh)"/>' % (x, ya, x, yb, INK))
        out.append('<text x="%.2f" y="%.2f" font-size="3" font-weight="700" text-anchor="middle" fill="%s" transform="rotate(-90 %.2f %.2f)">%s</text>' % (x - 1, (ya + yb) / 2, INK, x - 1, (ya + yb) / 2, t))
    dimh(x0, cx, y0 + fh * s + 6, F(hx))
    dimh(x0, x0 + fw * s, y0 - 6, F(fw))
    dimv(y0, cy, x0 + fw * s + 6, F(hz))
    dimv(y0, y0 + fh * s, x0 - 6, F(fh))
    out.append('<text x="%.2f" y="%.2f" font-size="2.6" fill="%s" font-weight="600">centro do puxador</text>' % (cx + 2, cy - 2.2, ACCENT))
    out.append('</svg>')
    return '\n'.join(out)


def handle_values(pj, item):
    """Calcula painel e centro do puxador para um item {painel, inst, hw, hw_idx}."""
    pb = pj.P[item['painel']]['boxes'][item.get('inst', 0)]
    hb = pj.hw[item['hw']][item.get('hw_idx', 0)]['box']
    c = [(hb[0][i] + hb[1][i]) / 2 for i in range(3)]
    fw, fh = pb[1][0] - pb[0][0], pb[1][2] - pb[0][2]
    sx, sz = hb[1][0] - hb[0][0], hb[1][2] - hb[0][2]
    vertical = sz > sx
    return dict(fw=fw, fh=fh, hx=c[0] - pb[0][0], hz=pb[1][2] - c[2], hlen=max(sx, sz), vertical=vertical)

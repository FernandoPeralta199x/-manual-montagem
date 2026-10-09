"""Inventário do modelo e montagem dos dados do projeto a partir do spec.json."""
import json
import os
import re

from .skp import SKP, IN
from .cutlist import read_csv, material_info

FUNCOES_CAIXA = ('caixa', 'fundo')


def _rnd(v):
    return [round(x, 2) for x in v]


def _size(bb):
    return [round(bb[1][i] - bb[0][i], 2) for i in range(3)]


def _base_name(n):
    return re.sub(r'#\d+$', '', n or '')


def _match(sel, label, defname):
    # label = nome do componente dinâmico (_name) ou, na falta dele, o nome da definição
    return sel == label or sel == _base_name(label)


# ---------------------------------------------------------------- inventário
def inventory(skp_path, csv_path=None):
    m = SKP(skp_path)
    rows = read_csv(csv_path) if csv_path else []
    out = []
    meta = m.meta.decode('latin-1', 'replace')
    ver = re.findall(r'SketchUp Client \(([^)]*)\) ([\d.]+)', meta)
    out.append('# INVENTÁRIO DO MODELO')
    out.append('arquivo: %s' % os.path.basename(skp_path))
    out.append('SketchUp: %s' % (' '.join(ver[0]) if ver else 'não identificado'))
    out.append('camadas (tags) OCULTAS: %s' % ', '.join(sorted(m.layers[l] for l in m.hidden_layers)))
    out.append('')
    out.append('## Componentes na raiz do modelo (índice · definição · rótulo · tamanho L×P×A mm · posição mín.)')
    roots = []
    for i, ins in enumerate(m.rootdef['insts']):
        d = m.defs[ins['defid']]
        bb = m.aabb(d, tm_(ins))
        lab = m.label(ins, d)
        vis = 'OCULTO ' if m.is_hidden(ins) else ''
        out.append('[%d] %s%s · %s · %s · em %s · camada=%s' % (i, vis, d['name'], lab, _size(bb) if bb else '-', _rnd(bb[0]) if bb else '-', m.layers.get(ins['layer'], '-')))
        roots.append((i, ins, d))
    out.append('')

    def csv_sugg(sz):
        s = sorted(sz, reverse=True)
        res = []
        for r in rows:
            cor, marca, esp = material_info(r['mat'])
            dims = sorted([r['c'], r['l']], reverse=True)
            if esp is None:
                continue
            if abs(dims[0] - s[0]) <= 1.5 and abs(dims[1] - s[1]) <= 1.5 and abs(esp - s[2]) <= 0.8:
                res.append('%s (%s)' % (r['id'], r['desc'][:40]))
        return res

    for i, ins, d in roots:
        if m.is_hidden(ins):
            continue
        a = m.dc(ins, d)
        out.append('## Raiz [%d] %s' % (i, d['name']))
        params = []
        for k in sorted(a):
            if k.startswith('_'):
                continue
            fl = a.get('_%s_formlabel' % k)
            opts = a.get('_%s_options' % k) or ''
            if fl or opts:
                val = a[k]
                txt = '%s = %r' % (fl or k, val)
                if opts:
                    import urllib.parse
                    op = [o for o in urllib.parse.unquote(opts, encoding='latin-1').split('&') if '=' in o]
                    hit = [o.split('=')[0] for o in op if o.split('=')[1] == str(val)]
                    if hit:
                        txt += ' → %s' % hit[0]
                params.append(txt)
        if params:
            out.append('parâmetros Gábster: ' + ' | '.join(params))
        lines = []

        def fn(sub, dd, W, path, vis):
            if not vis:
                return False
            bb = m.aabb(dd, W)
            if bb is None:
                return False
            sz = _size(bb)
            if min(sz) < 0.05 and not dd['insts']:
                return False  # grupo de uma face só
            lab = m.label(sub, dd)
            depth = len(path)
            extra = '' if _base_name(dd['name']) == lab else ' {%s}' % dd['name']
            layer = m.layers.get(sub['layer'])
            layer = '' if layer in (None, 'Layer0', 'Layer00') else ' camada=%s' % layer
            sg = csv_sugg(sz)
            lines.append('%s- %s%s%s · %s em %s%s' % ('  ' * depth, lab, extra, layer, sz, _rnd(bb[0]), ('  ≈ CSV ' + '; '.join(sg[:4])) if sg else ''))
            return True
        m.walk(fn, d, tm_(ins), (m.label(ins, d),), True)
        out += lines
        out.append('')
    if rows:
        out.append('## Lista de corte (%d linhas)' % len(rows))
        for r in rows:
            out.append('%3d · ID %s · %s × %s · %s · %s · %s · qtd %d' % (r['seq'], r['id'], r['c'], r['l'], r['mat'], r['desc'], r['lam'] or '-', r['qtd']))
    return '\n'.join(out)


def tm_(ins):
    from .skp import tm
    return tm(ins['T'])


# ---------------------------------------------------------------- projeto
class Project:
    def __init__(self, spec_path):
        self.spec_path = os.path.abspath(spec_path)
        self.dir = os.path.dirname(self.spec_path)
        self.spec = json.load(open(self.spec_path, encoding='utf-8'))
        S = self.spec
        arq = S['projeto']['arquivos']
        self.skp = SKP(os.path.join(self.dir, arq['skp']))
        self.csv = read_csv(os.path.join(self.dir, arq['csv']))
        self.csv_by_id = {r['id']: r for r in self.csv}
        self.warnings = []
        self._extract()

    def _module_roots(self, mod):
        m = self.skp
        roots = []
        for i, ins in enumerate(m.rootdef['insts']):
            d = m.defs[ins['defid']]
            lab = m.label(ins, d)
            for r in mod['raizes']:
                if (isinstance(r, int) and r == i) or (isinstance(r, str) and (r in d['name'] or r == lab)):
                    roots.append((ins, d))
                    break
        return roots

    def _find(self, roots, sels, want_faces=False):
        m = self.skp
        sels = sels if isinstance(sels, list) else [sels]
        found = []
        for ins, d in roots:
            if m.is_hidden(ins):
                continue
            W0 = tm_(ins)
            lab0 = m.label(ins, d)
            if any(_match(s if isinstance(s, str) else s['nome'], lab0, d['name']) for s in sels):
                found.append(self._item(d, W0, (), want_faces, lab0))
                continue

            def fn(sub, dd, W, path, vis):
                if not vis:
                    return False
                lab = m.label(sub, dd)
                for s in sels:
                    nome = s if isinstance(s, str) else s['nome']
                    cam = None if isinstance(s, str) else s.get('caminho')
                    if _match(nome, lab, dd['name']) and (not cam or cam in ' / '.join(path)):
                        found.append(self._item(dd, W, path, want_faces, lab))
                        return False
                return True
            m.walk(fn, d, W0, (lab0,), True)
        return [f for f in found if f['bb'] is not None]

    def _item(self, d, W, path, want_faces, lab):
        m = self.skp
        bb = m.aabb(d, W)
        faces = []
        if want_faces:
            m.visible_faces(d, W, faces)
        return dict(bb=bb, faces=faces, path=list(path), label=lab)

    def _extract(self):
        S = self.spec
        self.mods = {mod['id']: mod for mod in S['modulos']}
        self.roots = {mid: self._module_roots(mod) for mid, mod in self.mods.items()}
        for mid, r in self.roots.items():
            if not r:
                self.warnings.append('Módulo %s: nenhuma raiz encontrada para %r' % (mid, self.mods[mid]['raizes']))
        parts = []
        for p in S['pecas']:
            items = self._find(self.roots[p['mod']], p['sel'])
            if p.get('filtro_z'):
                lo, hi = p['filtro_z']
                items = [f for f in items if lo <= f['bb'][0][2] <= hi]
            if not items:
                self.warnings.append('%s: seletor %r não encontrou peça visível' % (p['code'], p['sel']))
            rows = [self.csv_by_id[i] for i in p.get('ids', []) if i in self.csv_by_id]
            for i in p.get('ids', []):
                if i not in self.csv_by_id:
                    self.warnings.append('%s: ID %s não existe na lista de corte' % (p['code'], i))
            parts.append(dict(p, items=items, csv=rows))
        # origem de cada módulo: canto frontal-esquerdo da caixa (x mín., y mín.), z do modelo
        self.orig = {}
        for mid in self.mods:
            bbs = [f['bb'] for p in parts if p['mod'] == mid and p.get('funcao') in FUNCOES_CAIXA for f in p['items']]
            if not bbs:
                bbs = [f['bb'] for p in parts if p['mod'] == mid for f in p['items']]
            oz = self.mods[mid].get('origem_z', 0.0)
            self.orig[mid] = (min(b[0][0] for b in bbs), min(b[0][1] for b in bbs), oz) if bbs else (0, 0, 0)
        loc = lambda p, mid: [round(p[i] - self.orig[mid][i], 2) for i in range(3)]
        self.parts = []
        for p in parts:
            mid = p['mod']
            items = sorted(p['items'], key=lambda f: (round(f['bb'][0][2], 1), f['bb'][0][0]))
            boxes = [[loc(f['bb'][0], mid), loc(f['bb'][1], mid)] for f in items]
            rows = p['csv']
            mats = [material_info(r['mat']) for r in rows]
            q = dict(p)
            q.pop('items')
            q.update(boxes=boxes,
                     csv=[dict(id=r['id'], c=r['c'], l=r['l'], mat=r['mat'], lam=r['lam'], qtd=r['qtd'], desc=r['desc']) for r in rows],
                     cor=mats[0][0] if mats else p.get('cor', ''),
                     esp_csv=sorted(set(x[2] for x in mats if x[2] is not None)),
                     qtd_csv=sum(r['qtd'] for r in rows), qtd_modelo=len(boxes),
                     dim_modelo=sorted([round(boxes[0][1][i] - boxes[0][0][i], 2) for i in range(3)], reverse=True) if boxes else [0, 0, 0])
            self.parts.append(q)
        self.P = {p['code']: p for p in self.parts}
        self.hw = {}
        for key, h in S.get('hardware', {}).items():
            items = self._find(self.roots[h['mod']], h['sel'], want_faces=(h.get('render', 'mesh') == 'mesh'))
            items = sorted(items, key=lambda f: (round(f['bb'][0][2], 1), f['bb'][0][0]))
            mid = h['mod']
            self.hw[key] = [dict(box=[loc(f['bb'][0], mid), loc(f['bb'][1], mid)], render=h.get('render', 'mesh'),
                                 faces=[[[loc(pt, mid) for pt in lp] for lp in face] for face in f['faces']], name=f['label']) for f in items]
            if not items:
                self.warnings.append('Ferragem %s: seletor %r não encontrou geometria visível' % (key, h['sel']))

    # ------------------------------------------------------------ helpers
    def mod_parts(self, mid):
        return [p for p in self.parts if p['mod'] == mid]

    def mod_ids(self):
        return [m['id'] for m in self.spec['modulos']]

    def checks(self):
        """Checagens automáticas: retorna lista de (nivel, texto)."""
        out = [('AVISO', w) for w in self.warnings]
        used = {}
        for p in self.parts:
            for r in p['csv']:
                used.setdefault(r['id'], []).append(p['code'])
        for r in self.csv:
            if r['id'] not in used:
                out.append(('ERRO', 'Linha da lista de corte sem código: ID %s (%s)' % (r['id'], r['desc'])))
            elif len(used[r['id']]) > 1:
                out.append(('ERRO', 'ID %s associado a mais de um código: %s' % (r['id'], used[r['id']])))
        for p in self.parts:
            if p['qtd_modelo'] != p['qtd_csv']:
                out.append(('DIVERGE', '%s %s: qtd. modelo %d × lista %d' % (p['code'], p['nome'], p['qtd_modelo'], p['qtd_csv'])))
            if p['csv'] and p['boxes']:
                dm = p['dim_modelo']
                for r in p['csv']:
                    dc = sorted([r['c'], r['l']], reverse=True)
                    if abs(dc[0] - dm[0]) > 1.5 or abs(dc[1] - dm[1]) > 1.5:
                        out.append(('DIVERGE', '%s %s: medida lista %d × %d · modelo %s × %s (ID %s)' % (p['code'], p['nome'], r['c'], r['l'], dm[0], dm[1], r['id'])))
                    _, _, esp = material_info(r['mat'])
                    if esp is not None and abs(esp - dm[2]) > 0.75:
                        out.append(('DIVERGE', '%s %s: espessura lista %s · modelo %s (ID %s)' % (p['code'], p['nome'], esp, dm[2], r['id'])))
        return out

    def medidas(self):
        """Medidas calculadas úteis para escrever textos (posições, folgas, centros)."""
        out = []
        for mid in self.mod_ids():
            out.append('## %s — origem no modelo (x, y, z): %s' % (mid, _rnd(self.orig[mid])))
            lo, hi = self.caixa_bbox(mid)
            flo, fhi = self.mod_bbox(mid)
            out.append('caixa: L %.1f × P %.1f × A %.1f · com frentes/portas P %.1f · com ferragens P %.1f' % (
                hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], hi[1] - flo[1], hi[1] - self.mod_bbox(mid, hw=True)[0][1]))
            for p in self.mod_parts(mid):
                for k, b in enumerate(p['boxes']):
                    out.append('  %s[%d] %-34s x %7.2f–%7.2f · y %7.2f–%7.2f · z %7.2f–%7.2f · tam %s' % (
                        p['code'], k, p['nome'][:34], b[0][0], b[1][0], b[0][1], b[1][1], b[0][2], b[1][2], _size(b)))
            for key, items in self.hw.items():
                if self.spec['hardware'][key]['mod'] != mid:
                    continue
                for k, h in enumerate(items):
                    b = h['box']
                    c = [(b[0][i] + b[1][i]) / 2 for i in range(3)]
                    out.append('  %s[%d] %-30s centro x %.2f y %.2f z %.2f · tam %s' % (key, k, h['name'][:30], c[0], c[1], c[2], _size(b)))
            # frentes: folgas e centros de ferragens relativos
            fr = [(p['code'], k, b) for p in self.mod_parts(mid) if p.get('funcao') == 'frente' for k, b in enumerate(p['boxes'])]
            fr.sort(key=lambda t: t[2][0][2])
            for i in range(len(fr) - 1):
                g = fr[i + 1][2][0][2] - fr[i][2][1][2]
                if 0 <= g < 30:
                    out.append('  folga vertical %s[%d]→%s[%d]: %.2f' % (fr[i][0], fr[i][1], fr[i + 1][0], fr[i + 1][1], g))
            for code, k, b in fr:
                out.append('  %s[%d] afastamento esq. %.2f · dir. %.2f · topo da caixa − topo da frente %.2f' % (code, k, b[0][0] - lo[0], hi[0] - b[1][0], hi[2] - b[1][2]))
                for key, items in self.hw.items():
                    if self.spec['hardware'][key]['mod'] != mid:
                        continue
                    for j, h in enumerate(items):
                        hb = h['box']
                        c = [(hb[0][i] + hb[1][i]) / 2 for i in range(3)]
                        if b[0][0] - 40 <= c[0] <= b[1][0] + 40 and b[0][2] - 1 <= c[2] <= b[1][2] + 1 and c[1] <= b[1][1] + 30:
                            pos = 'na frente' if c[1] <= b[1][1] + 5 else 'atrás'
                            out.append('     %s[%d] (%s) centro: %.2f da borda esq. · %.2f da borda dir. · %.2f da borda inf. · %.2f da borda sup. · (centro da peça a %.2f)' % (
                                key, j, pos, c[0] - b[0][0], b[1][0] - c[0], c[2] - b[0][2], b[1][2] - c[2], (b[1][0] - b[0][0]) / 2))
        return '\n'.join(out)

    def caixa_bbox(self, mid):
        bbs = [b for p in self.mod_parts(mid) if p.get('funcao') in FUNCOES_CAIXA for b in p['boxes']] or [b for p in self.mod_parts(mid) for b in p['boxes']]
        return [min(b[0][i] for b in bbs) for i in range(3)], [max(b[1][i] for b in bbs) for i in range(3)]

    def mod_bbox(self, mid, hw=False):
        bbs = [b for p in self.mod_parts(mid) for b in p['boxes']]
        if hw:
            bbs += [h['box'] for k, v in self.hw.items() if self.spec['hardware'][k]['mod'] == mid for h in v]
        return [min(b[0][i] for b in bbs) for i in range(3)], [max(b[1][i] for b in bbs) for i in range(3)]

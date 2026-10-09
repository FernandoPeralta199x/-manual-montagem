"""Gera o manual (HTML paginado A4 paisagem) a partir de um Project + spec.json."""
import base64
import os
import re

from .views import *  # noqa: F401,F403
from .views import F
from .draw import esc
from .cutlist import lam_expand

ASSETS = os.path.join(os.path.dirname(__file__), 'assets')
MARCA_PADRAO = {'nome': 'Luciano Lâminas', 'logo': 'luciano-laminas.png', 'cor': '#00258A'}
TAGS = {'E': 'Encontrado no projeto', 'C': 'Calculado a partir do modelo', 'I': 'Inferido — confirmar', 'A': 'Ausente / não identificado'}


def tg(k):
    return '<span class="tg t%s" title="%s">%s</span>' % (k.lower(), TAGS[k], k)


def tx(s):
    """Marcação dos textos do spec: {E} {C} {I} {A} = selos de origem; {!C02} = ⚠ C02 em destaque."""
    if s is None:
        return ''
    s = str(s)
    s = re.sub(r'\{([ECIA])\}', lambda m: tg(m.group(1)), s)
    s = re.sub(r'\{!([^}]*)\}', lambda m: '<span class="warn">⚠ %s</span>' % m.group(1), s)
    return s


def sev(s):
    return '<span class="sev s%s">%s</span>' % ({'ALTA': 'a', 'MÉDIA': 'm', 'BAIXA': 'b'}.get(s, 'b'), s)


def h1(num, title, sub=None):
    return '<div class="h1"><span class="num">%s</span><div><h1>%s</h1>%s</div></div>' % (num, title, '<p class="sub">%s</p>' % tx(sub) if sub else '')


def font_css():
    css = []
    for fam, dirn, ws in [('Barlow', 'barlow', [400, 500, 600, 700]), ('Barlow Condensed', 'barlow-condensed', [500, 600, 700]), ('IBM Plex Mono', 'ibm-plex-mono', [400, 500, 600])]:
        for w in ws:
            p = os.path.join(ASSETS, 'fonts', '%s-latin-%d-normal.woff2' % (dirn, w))
            b = base64.b64encode(open(p, 'rb').read()).decode()
            css.append("@font-face{font-family:'%s';font-style:normal;font-weight:%d;font-display:block;src:url(data:font/woff2;base64,%s) format('woff2')}" % (fam, w, b))
    return '\n'.join(css)


class Manual:
    def __init__(self, pj):
        self.pj = pj
        self.S = pj.spec
        self.PJ = self.S['projeto']
        self.pages = []
        self.fer = {f['code']: f for f in self.S.get('ferragens', [])}
        self.marca = self._marca()

    def _marca(self):
        """Logo e cor da marca. Padrão do template: Luciano Lâminas. "marca": null desliga."""
        if 'marca' in self.S and self.S['marca'] is None:
            return None
        mk = dict(MARCA_PADRAO)
        mk.update(self.S.get('marca') or {})
        logo = mk.get('logo')
        path = None
        if logo:
            for cand in (os.path.join(self.pj.dir, logo), os.path.join(ASSETS, 'marca', logo)):
                if os.path.exists(cand):
                    path = cand
                    break
        mk['logo_path'] = path
        return mk

    def logo(self, cls=''):
        return '<i class="logo %s"></i>' % cls if self.marca and self.marca.get('logo_path') else ''

    def page(self, section, html, mod='', cls=''):
        self.pages.append((section, mod, html, cls))

    def modlabel(self, mid):
        m = self.pj.mods[mid]
        return m.get('rotulo') or ('MÓDULO %s — %s' % (mid[1:], m['nome'].upper()))

    # ------------------------------------------------------------ capa
    def cover(self):
        pj, P = self.pj, self.PJ
        caps = ''
        mods = ''
        for mid in pj.mod_ids():
            m = pj.mods[mid]
            lo, hi = pj.caixa_bbox(mid)
            caps += '<span class="cv-cap">%s · %s · %s × %s × %s</span>' % (mid, m['nome'], F(hi[0] - lo[0]), F(hi[1] - lo[1]), F(hi[2] - lo[2]))
            mods += '%s — %s<br>' % (mid, m['nome'])
        n_alta = sum(1 for c in self.S.get('conflitos', []) if c['prioridade'] == 'ALTA')
        aviso = self.S.get('aviso_capa') or ('<b>Antes de montar:</b> leia a seção 2.3 — Conflitos e pendências.' + ((' Há 1 ponto de prioridade ALTA a confirmar com a produção.' if n_alta == 1 else ' Há %d pontos de prioridade ALTA a confirmar com a produção.' % n_alta) if n_alta else ''))
        html = '''<div class="cover"><div class="cv-left">
<div class="cv-kicker">Documentação técnica de fabricação + montagem</div>
<div class="cv-title">Manual de<br>Montagem</div>
<div class="cv-proj">Pedido <b>%s</b> · %s</div>
<table class="cv-meta"><tr><th>Cliente</th><td>%s</td></tr><tr><th>Código</th><td class="mono">%s</td></tr>
<tr><th>Pedido (lista de corte)</th><td class="mono">%s</td></tr><tr><th>Data da venda</th><td class="mono">%s</td></tr>
<tr><th>Módulos</th><td>%s</td></tr></table>
<div class="cv-warn">%s</div></div>
<div class="cv-right">%s<div class="cv-fig">%s<div class="cv-caps">%s</div><div class="cv-src">Desenhos gerados a partir do arquivo SketchUp do projeto, na mesma escala.</div></div></div></div>''' % (
            esc(P['codigo']), esc(P['cliente']), esc(P['cliente']), esc(P['codigo']), esc(P.get('pedido', '—')), esc(P.get('data_venda', '—')), mods, tx(aviso), self.logo('cv-brand'), cover_scene(pj, 160, 138), caps)
        self.page('Capa', html, cls='p-cover')

    # ------------------------------------------------------------ 1
    def identificacao(self):
        pj, P = self.pj, self.PJ
        rows = [('Cliente', esc(P['cliente']) + ' ' + tg('E')),
                ('Código do projeto', '<span class="mono">%s</span> %s' % (esc(P['codigo']), tg('E'))),
                ('Pedido / lista de corte', '<span class="mono">%s</span> %s' % (esc(P.get('pedido', '—')), tg('E'))),
                ('Data da venda', '<span class="mono">%s</span> %s' % (esc(P.get('data_venda', '—')), tg('E'))),
                ('Fabricante / montadora', tx(P.get('fabricante') or 'Não informado nos arquivos {A}')),
                ('Endereço de instalação', tx(P.get('endereco') or 'Não informado nos arquivos {A}'))]
        arq = ''.join('<tr><th>%s</th><td>%s</td></tr>' % (k, tx(v)) for k, v in P.get('arquivos_desc', {}).items())
        mods = ''
        for mid in pj.mod_ids():
            m = pj.mods[mid]
            lo, hi = pj.caixa_bbox(mid)
            flo, _ = pj.mod_bbox(mid)
            tall = (hi[2] - lo[2]) > 1.6 * (hi[0] - lo[0])
            mods += '''<div class="modcard"><div class="mc-head"><span class="mono">%s</span> %s</div><div class="mc-body"><div class="mc-fig">%s</div><div class="mc-txt">
<p class="mc-sub">%s</p><table class="kv">
<tr><th>Largura × prof. × altura (caixa)</th><td class="mono">%s × %s × %s mm %s</td></tr>
<tr><th>Profundidade com frentes</th><td class="mono">%s mm %s</td></tr>
<tr><th>Componente no modelo</th><td>%s</td></tr>
<tr><th>Especificação (PDF)</th><td>%s</td></tr></table></div></div></div>''' % (
                mid, esc(m['nome'].upper()), assembled(pj, mid, 46, 70 if tall else 62, dims=False), tx(m.get('sub', '')),
                F(hi[0] - lo[0]), F(hi[1] - lo[1]), F(hi[2] - lo[2]), tg('E'), F(hi[1] - flo[1]), tg('C'),
                tx(m.get('gabster', '—')), '<br>'.join(tx(x) for x in m.get('pdf_spec', [])) or tx('Não informado {A}'))
        html = h1('01', 'Identificação do projeto') + '''<div class="cols2"><div><h3>Projeto</h3><table class="kv big">%s</table>
<h3>Arquivos de origem</h3><table class="kv">%s</table></div><div><h3>Módulos do projeto</h3>%s</div></div>''' % (
            ''.join('<tr><th>%s</th><td>%s</td></tr>' % r for r in rows), arq, mods)
        self.page('1 · Identificação', html)

    # ------------------------------------------------------------ 2
    def info_gerais(self):
        ig = self.S.get('info_gerais', {})
        right = ''
        for blk in ig.get('blocos', []):
            right += '<h3>%s</h3><p>%s</p>' % (esc(blk['titulo']), tx(blk['texto']))
        html = h1('02', 'Informações gerais') + '''<div class="cols2"><div>
<h3>2.1 Como as informações foram obtidas</h3><ul class="tight">
<li>O arquivo SketchUp foi lido diretamente: geometria de cada peça, posição no espaço, camadas (tags) visíveis e ocultas e parâmetros dos componentes Gábster.</li>
<li>Foram consideradas somente as peças <b>visíveis</b> no modelo. Variantes ocultas (outros puxadores, outras dobradiças, peças desativadas) foram descartadas.</li>
<li>A lista de corte (CSV) foi cruzada linha a linha com o modelo: as %d linhas foram associadas a um código de peça (Anexo A).</li>
<li>O PDF de venda foi usado para materiais especificados e medidas gerais.</li>
<li>Medidas em milímetros. As cotas de posição usam o piso como referência (base do rodapé = 0).</li></ul>
<h3>2.2 Legenda de origem da informação</h3><table class="legend">
<tr><td>%s</td><td><b>Encontrado</b> — lido no modelo 3D, na lista de corte ou no PDF.</td></tr>
<tr><td>%s</td><td><b>Calculado</b> — medido a partir da geometria do modelo (posições, folgas, distâncias).</td></tr>
<tr><td>%s</td><td><b>Inferido</b> — dedução técnica sem confirmação no projeto. Confirmar.</td></tr>
<tr><td>%s</td><td><b>Ausente</b> — não identificado no projeto. Nada foi inventado no lugar.</td></tr></table>
<h3>2.4 Convenções</h3><ul class="tight">
<li><b>Frente do móvel</b>: lado das gavetas e das portas. <b>Esquerda / direita</b>: vistas de frente para o móvel.</li>
<li><b>Comp. × Larg.</b>: na ordem em que aparecem na lista de corte.</li>
<li><b>ID</b>: número único de cada linha da lista de corte (8ª coluna do CSV). Não confundir com o código “Etiq.” da descrição.</li>
<li><span class="hl">Peça em laranja</span> nos desenhos = peça instalada naquela etapa. Peças em cinza claro = já instaladas.</li></ul>
</div><div>%s</div></div>''' % (len(self.pj.csv), tg('E'), tg('C'), tg('I'), tg('A'), right)
        self.page('2 · Informações gerais', html)
        rows = ''
        for c in self.S.get('conflitos', []):
            rows += '<tr><td class="mono b">%s</td><td>%s</td><td><b>%s</b></td><td>%s</td><td>%s</td></tr>' % (
                c['id'], sev(c['prioridade']), esc(c['titulo']), ''.join('<div class="src"><span class="srcn">%s</span> %s</div>' % (esc(a), tx(b)) for a, b in c['fontes']), tx(c['tratamento']))
        if not rows:
            rows = '<tr><td colspan="5">Nenhum conflito identificado entre o modelo 3D, a lista de corte e o PDF.</td></tr>'
        html = h1('02', 'Conflitos e pendências', '2.3 · Ler antes de iniciar a montagem. Nenhum valor foi escolhido arbitrariamente.') + \
            '<table class="grid conf"><thead><tr><th style="width:9mm">ID</th><th style="width:15mm">Prioridade</th><th style="width:38mm">Assunto</th><th>O que cada fonte informa</th><th style="width:72mm">Como este manual trata</th></tr></thead><tbody>%s</tbody></table>' % rows
        self.page('2 · Conflitos', html)

    # ------------------------------------------------------------ 3
    def vista_montado(self):
        pj = self.pj
        for mid in pj.mod_ids():
            m = pj.mods[mid]
            lo, hi = pj.caixa_bbox(mid)
            flo, _ = pj.mod_bbox(mid)
            hlo, _ = pj.mod_bbox(mid, hw=True)
            tall = (hi[2] - lo[2]) > 1.6 * (hi[0] - lo[0])
            svg = assembled(pj, mid, 150 if tall else 190, 158)
            txt = '''<h3>%s</h3><p class="muted">%s</p><table class="kv">
<tr><th>Largura</th><td class="mono">%s mm %s</td></tr><tr><th>Altura</th><td class="mono">%s mm %s</td></tr>
<tr><th>Profundidade da caixa</th><td class="mono">%s mm %s</td></tr><tr><th>Profundidade com frente</th><td class="mono">%s mm %s</td></tr>
<tr><th>Profundidade com ferragens</th><td class="mono">%s mm %s</td></tr></table>
<h3>Componentes visíveis</h3><ul class="tight">%s</ul>
<p class="note">Desenho gerado a partir da geometria do arquivo SketchUp.%s</p>''' % (
                esc(m['nome']), tx(m.get('sub', '')), F(hi[0] - lo[0]), tg('E'), F(hi[2] - lo[2]), tg('E'), F(hi[1] - lo[1]), tg('E'),
                F(hi[1] - flo[1]), tg('C'), F(hi[1] - hlo[1]), tg('C'), ''.join('<li>%s</li>' % tx(c) for c in m.get('componentes', [])), tx(' ' + m['nota_montado']) if m.get('nota_montado') else '')
            self.page('3 · Móvel montado', h1('03', 'Vista do móvel montado', self.modlabel(mid)) + '<div class="fig-side"><div class="fig">%s</div><div class="side">%s</div></div>' % (svg, txt), mid)

    # ------------------------------------------------------------ 4
    def medidas(self):
        pj = self.pj
        for mid in pj.mod_ids():
            m = pj.mods[mid]
            lo, hi = pj.caixa_bbox(mid)
            tall = (hi[2] - lo[2]) > 1.6 * (hi[0] - lo[0])
            if tall:
                (f, r), s = ortho_set(pj, mid, [('front', 78, 160), ('right', 100, 160)])
                t = ortho(pj, mid, 'top', 60, 92, scale=s * 1.3)
            else:
                (f, r), s = ortho_set(pj, mid, [('front', 112, 148), ('right', 92, 148)])
                t = ortho(pj, mid, 'top', 70, 82, scale=s * 0.62)
            nota = m.get('nota_medidas', 'Cotas em mm, calculadas da geometria do modelo {C}.')
            body = '''<div class="views3"><figure>%s<figcaption>Vista frontal</figcaption></figure><figure>%s<figcaption>Vista lateral direita</figcaption></figure>
<div class="vcol"><figure>%s<figcaption>Vista superior <span class="muted">(frente para baixo)</span></figcaption></figure><div class="vnote">%s</div></div></div>''' % (f, r, t, tx(nota))
            self.page('4 · Medidas gerais', h1('04', 'Medidas gerais', self.modlabel(mid)) + body, mid)

    # ------------------------------------------------------------ 5
    def chapa(self, p):
        mats = ' / '.join(sorted(set(x['mat'] for x in p['csv']))) or '—'
        return mats + (' · MDF (PDF)' if p.get('mdf_pdf') else ' · tipo não especificado')

    def lista_pecas(self):
        pj = self.pj
        for mid in pj.mod_ids():
            rows = ''
            for p in pj.mod_parts(mid):
                c = p['csv'][0] if p['csv'] else dict(c=0, l=0, lam='')
                hc, vc, hm, vm, names = match_csv(pj, p['code'])
                dmis = abs(hc - hm) > 1.5 or abs(vc - vm) > 1.5
                qm, qc = p['qtd_modelo'], p['qtd_csv']
                cref = ' (%s)' % ', '.join(p['conflitos']) if p.get('conflitos') else ''
                obs = []
                if dmis:
                    obs.append('<span class="warn">⚠ Modelo: %s × %s</span>%s' % (F(hm if names[0] == 'C' else vm), F(vm if names[0] == 'C' else hm), cref))
                if len(p['esp_csv']) > 1 or p.get('alerta_espessura'):
                    obs.append('<span class="warn">⚠ Espessura</span>%s' % cref)
                if qm != qc:
                    obs.append('<span class="warn">⚠ Qtd.</span>%s' % cref)
                obs += [tx(o) for o in p.get('obs', [])]
                esp_txt = '/'.join(str(e) for e in p['esp_csv']) or '—'
                rows += '<tr><td class="mono b">%s</td><td>%s</td><td class="num %s">%d</td><td class="num %s">%d</td><td class="num">%s</td><td class="num">%s</td><td class="num">%s<span class="muted"> (%s)</span></td><td class="small">%s</td><td>%s</td><td class="small">%s</td><td class="mono small">%s</td><td class="small">%s</td></tr>' % (
                    p['code'], esc(p['nome']), 'warnc' if qm != qc else '', qm, 'warnc' if qm != qc else '', qc, c['c'] or '—', c['l'] or '—', esp_txt, F(p['dim_modelo'][2]),
                    esc(self.chapa(p)), esc(p['cor']), esc(c['lam'] or '—'), ' '.join(x['id'] for x in p['csv']), '<br>'.join(obs) or '—')
            html = h1('05', 'Lista de peças', self.modlabel(mid)) + '''<table class="grid parts"><thead><tr><th>Código</th><th>Peça</th><th>Qtd.<br>modelo</th><th>Qtd.<br>lista</th><th>Comp.</th><th>Larg.</th><th>Esp.<br><span class="muted">(modelo)</span></th><th>Chapa (lista)</th><th>Cor / padrão</th><th>Fita (lista)</th><th>ID (lista)</th><th>Observações</th></tr></thead><tbody>%s</tbody></table>
<p class="foot-note">Comp., Larg., Esp., chapa, cor, fita e ID: lista de corte %s. “MDF”: somente onde o PDF especifica %s. Qtd. modelo e espessura entre parênteses: modelo 3D %s. Fita: “1C” = 1 comprimento, “2L” = 2 larguras, “4L” = 4 lados (nomenclatura Gábster) %s. “c/ furos” = peça com furação de fábrica %s; posição não identificada no modelo %s.</p>''' % (rows, tg('E'), tg('E'), tg('E'), tg('I'), tg('I'), tg('A'))
            self.page('5 · Lista de peças', html, mid)

    # ------------------------------------------------------------ 6
    def ferragens(self):
        rows = ''
        for f in self.S.get('ferragens', []):
            warn = 'CONFLITO' in f.get('obs', '') or 'não especificada' in f.get('obs', '')
            rows += '<tr><td class="mono b">%s</td><td><b>%s</b></td><td class="num">%s %s</td><td>%s</td><td class="small">%s</td><td class="small %s">%s</td></tr>' % (
                f['code'], esc(f['nome']), esc(f['qtd']), tg(f.get('origem_qtd', 'E')), tx(f['aplicacao']), tx(f['origem']), 'warn' if warn else '', tx(f.get('obs', '')))
        html = h1('06', 'Lista de ferragens') + '''<table class="grid hw"><thead><tr><th>Código</th><th>Ferragem</th><th>Quantidade</th><th>Aplicação</th><th>Origem da informação</th><th>Observação</th></tr></thead><tbody>%s</tbody></table>
<p class="foot-note">Quantidades contadas no modelo 3D (peças visíveis). Nenhuma quantidade foi estimada: onde a ferragem não aparece no projeto, a quantidade fica em branco (—).</p>''' % rows
        self.page('6 · Ferragens', html)

    # ------------------------------------------------------------ 7
    def legend_codes(self, codes, hw):
        s = '<table class="leg">'
        for c in codes:
            p = self.pj.P[c]
            s += '<tr><td class="mono b">%s</td><td>%s</td><td class="num">×%d</td></tr>' % (c, esc(p['nome']), p['qtd_modelo'])
        for h in hw:
            f = self.fer.get(h, {'nome': h})
            s += '<tr><td class="mono b">%s</td><td>%s</td><td class="num"></td></tr>' % (h, esc(f['nome']))
        return s + '</table>'

    def explodidas(self):
        for ex in self.S.get('explodidas', []):
            sc = exploded(self.pj, ex)
            W, H = ex.get('tamanho', [200, 160])
            leg = ex.get('legenda') or {'pecas': list(ex['pecas']), 'ferragens': sorted(set(h['key'].split('_')[0] for h in ex.get('hw', [])))}
            side = self.legend_codes(leg['pecas'], leg.get('ferragens', [])) + ('<p class="note">%s</p>' % tx(ex['nota']) if ex.get('nota') else '')
            sub = self.modlabel(ex['mod']) + (' · ' + ex['sub'] if ex.get('sub') else '')
            self.page('7 · Vista explodida', h1('07', 'Vista explodida', sub) + '<div class="fig-side"><div class="fig">%s</div><div class="side">%s</div></div>' % (sc.render(W, H), side), ex['mod'])

    # ------------------------------------------------------------ 8
    def pecas(self):
        codes = [p['code'] for p in self.pj.parts]
        for i in range(0, len(codes), 4):
            cards = ''.join(self.part_card(c) for c in codes[i:i + 4])
            self.page('8 · Peças identificadas', h1('08', 'Peças identificadas', 'Medidas de corte (lista) · desenho na posição de montagem') + '<div class="cards">%s</div>' % cards, self.pj.P[codes[i]]['mod'])

    def part_card(self, c):
        pj = self.pj
        p = pj.P[c]
        svg, view, warn, info = part_svg(pj, c, 58, 56)
        lo, hi = pj.caixa_bbox(p['mod'])
        tall = (hi[2] - lo[2]) > 1.6 * (hi[0] - lo[0])
        loc = locator(pj, p['mod'], c, 22, 46 if tall else 28)
        lam = p['csv'][0]['lam'] if p['csv'] else ''
        furos = 'c/ furos' in lam
        esp = '/'.join(map(str, p['esp_csv'])) + ' mm' if p['esp_csv'] else '—'
        viewname = {'lateral': 'vista lateral', 'frontal': 'vista frontal', 'superior': 'vista superior'}[view]
        qm, qc = p['qtd_modelo'], p['qtd_csv']
        cref = ', '.join(p.get('conflitos', []))
        lam_code = re.sub(r'\s*(c/ furos|Dir|Esq)\b', '', lam.replace('Lam.', 'Lam')).strip() or '—'
        rows = [
            ('Corte (lista)', '<span class="mono">%s × %s × %s</span> %s' % (p['csv'][0]['c'] if p['csv'] else '—', p['csv'][0]['l'] if p['csv'] else '—', esp, tg('E'))),
            ('Modelo 3D', '<span class="mono">%s × %s × %s</span> %s%s' % (F(p['dim_modelo'][0]), F(p['dim_modelo'][1]), F(p['dim_modelo'][2]), tg('E'), (' <span class="warn">⚠ %s</span>' % (cref or 'diverge')) if warn else '')),
            ('Quantidade', 'modelo <b>%d</b> · lista <b>%d</b>%s' % (qm, qc, (' <span class="warn">⚠ %s</span>' % (cref or 'diverge')) if qm != qc else '')),
            ('Chapa', esc(self.chapa(p)) + ((' <span class="warn">⚠ %s</span>' % cref) if (len(p['esp_csv']) > 1 or p.get('alerta_espessura')) else '')),
            ('Fita', '%s %s · %s %s' % (esc(lam_code), tg('E'), lam_expand(lam), tg('I'))),
            ('ID lista', '<span class="mono">%s</span>' % ' · '.join(x['id'] for x in p['csv'])),
            ('Furação', tx(p.get('furacao') or ('“c/ furos” na lista {E} · furação de fábrica {I} · posição não identificada no modelo {A}' if furos else 'Sem indicação na lista {E} · não identificada no modelo {A}'))),
            ('Recortes', tx(p.get('recortes') or 'Não identificados no modelo {A}')),
            ('Veio', tx(p.get('veio') or 'Não especificado no projeto {A}')),
        ]
        tbl = ''.join('<tr><th>%s</th><td>%s</td></tr>' % r for r in rows)
        return '''<div class="card"><div class="card-h"><span class="code">%s</span><span class="cname">%s</span><span class="cmod">%s</span></div>
<div class="card-b"><div class="card-fig">%s<div class="vcap">%s · medidas da lista</div></div><div class="card-loc">%s<div class="vcap">posição</div></div>
<table class="kv small">%s</table></div></div>''' % (c, esc(p['nome']), p['mod'], svg, viewname, loc, tbl)

    # ------------------------------------------------------------ 9
    def sequencia(self):
        steps = self.S.get('etapas', [])
        for i in range(0, len(steps), 2):
            pr = steps[i:i + 2]
            cells = ''
            for st in pr:
                sc = ghost_scene(self.pj, st['mod'], show=set(st.get('mostrar', [])), new=set(st.get('novas', [])), offsets=st.get('offsets'),
                                 hw_show=st.get('hw_mostrar', []), hw_new=st.get('hw_novas', []), label_sub=st.get('rotulos'),
                                 arrow_codes=st.get('setas'), inst={k: v for k, v in st.get('inst', {}).items()})
                if st.get('so_rotulos'):
                    sc.labels = [l for l in sc.labels if l[0] in st['so_rotulos']]
                svg = sc.render(132, 116)
                chips = ''.join('<span class="chip">%s <i>%s</i></span>' % (c, esc(self.pj.P[c]['nome'])) for c in st.get('novas', []))
                for h in st.get('hw_novas', []):
                    code = h['key'].split('_')[0]
                    chips += '<span class="chip hwc">%s <i>%s</i></span>' % (code, esc(self.fer.get(code, {'nome': code})['nome'].split(' — ')[0]))
                cells += '''<div class="step"><div class="st-h"><span class="st-id">%s</span><span class="st-t">%s</span><span class="st-m">%s</span></div>
<div class="st-fig">%s</div><div class="st-parts">%s</div><p class="st-d">%s</p><p class="st-o"><b>Obs.</b> %s</p></div>''' % (
                    st['id'], esc(st['titulo']), st['mod'], svg, chips, tx(st['desc']), tx(st.get('obs', '—')))
            mods = '/'.join(sorted(set(st['mod'] for st in pr)))
            self.page('9 · Sequência de montagem', h1('09', 'Sequência de montagem', self.S.get('sequencia_sub', 'Sequência sugerida {I} — a ordem de montagem não está definida no projeto. Posições e medidas: modelo 3D.')) + '<div class="steps">%s</div>' % cells, mods)

    # ------------------------------------------------------------ 10-12
    def na(self, num, title, section):
        self.page(section, h1(num, title) + '<p>Não se aplica a este projeto: nenhum item deste tipo foi identificado no modelo.</p>')

    def portas(self):
        dets = self.S.get('detalhes', {}).get('portas', [])
        if not dets:
            return self.na('10', 'Instalação das portas', '10 · Portas')
        for det in dets:
            p = self.pj.P[det['porta']]
            svg = door_detail(self.pj, det, 150, 158)
            lo, hi = self.pj.caixa_bbox(p['mod'])
            tall = (hi[2] - lo[2]) > 1.6 * (hi[0] - lo[0])
            loc = locator(self.pj, p['mod'], det['porta'], 28, 62 if tall else 34)
            txt = '<table class="kv">%s</table>%s' % (''.join('<tr><th>%s</th><td>%s</td></tr>' % (esc(a), tx(b)) for a, b in det.get('linhas', [])),
                                                   '<p class="note">%s</p>' % tx(det.get('nota', 'Linhas tracejadas laranja: eixos das dobradiças. Peças em tracejado cinza: caixa ao redor da porta.')))
            self.page('10 · Portas', h1('10', 'Instalação das portas', det.get('sub', self.modlabel(p['mod']))) + '<div class="fig-side"><div class="fig">%s</div><div class="side"><div class="locside">%s</div>%s</div></div>' % (svg, loc, txt), p['mod'])

    def gavetas(self):
        dets = self.S.get('detalhes', {}).get('gavetas', [])
        if not dets:
            return self.na('11', 'Instalação das gavetas', '11 · Gavetas')
        for det in dets:
            svg = ortho(self.pj, det['mod'], 'front', 120, 150)
            txt = '<table class="kv">%s</table>' % ''.join('<tr><th>%s</th><td>%s</td></tr>' % (esc(a), tx(b)) for a, b in det.get('linhas', []))
            if det.get('ordem'):
                txt += '<h3>Ordem sugerida %s</h3><ol class="tight">%s</ol>' % (tg('I'), ''.join('<li>%s</li>' % tx(x) for x in det['ordem']))
            self.page('11 · Gavetas', h1('11', 'Instalação das gavetas', det.get('sub', self.modlabel(det['mod']))) + '<div class="fig-side"><div class="fig">%s</div><div class="side">%s</div></div>' % (svg, txt), det['mod'])

    def puxadores(self):
        det = self.S.get('detalhes', {}).get('puxadores')
        if not det or not det.get('itens'):
            return self.na('12', 'Instalação dos puxadores', '12 · Puxadores')
        figs = ''
        n = len(det['itens'])
        for it in det['itens']:
            v = handle_values(self.pj, it)
            big = v['fw'] / max(v['fh'], 1) > 2.2
            W, H = (150, 66) if big else (100, 90)
            if n > 2:
                W, H = W * 0.7, H * 0.7
            cor = pfill(self.pj, it['painel'])
            figs += '<figure>%s<figcaption>%s</figcaption></figure>' % (handle_detail(W, H, v['fw'], v['fh'], v['hx'], v['hz'], v['hlen'], v['vertical'], cor), tx(it.get('legenda', it['painel'])))
        tb = det.get('tabela', {})
        tbl = ''
        if tb:
            tbl = '<table class="grid hwt"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (
                ''.join('<th>%s</th>' % esc(h) for h in tb.get('cabecalho', [])),
                ''.join('<tr><th>%s</th>%s</tr>' % (esc(r[0]), ''.join(('<td colspan="%d">%s</td>' % (len(tb['cabecalho']) - 1, tx(c))) if len(r) == 2 and len(tb['cabecalho']) > 2 else '<td>%s</td>' % tx(c) for c in r[1:])) for r in tb.get('linhas', [])))
        self.page('12 · Puxadores', h1('12', 'Instalação dos puxadores', det.get('sub', 'Posição do centro do puxador')) + '<div class="hd-figs">%s</div>%s' % (figs, tbl))

    # ------------------------------------------------------------ 13-15
    def regulagem(self):
        rg = self.S.get('regulagem', {})
        tr = ''.join('<tr><td><b>%s</b></td><td>%s %s</td><td class="small">%s</td><td class="cb"></td></tr>' % (esc(a), tx(b), tg(c) if c else '', tx(d) or '—') for a, b, c, d in rg.get('linhas', []))
        html = h1('13', 'Regulagem') + '<p>%s</p><table class="grid chk"><thead><tr><th style="width:34mm">Item</th><th>Referência</th><th style="width:70mm">Observação</th><th style="width:12mm">OK</th></tr></thead><tbody>%s</tbody></table>' % (
            tx(rg.get('intro', 'Valores de referência calculados do modelo {C}.')), tr)
        self.page('13 · Regulagem', html)

    def conferencia(self):
        tr = ''.join('<tr><td class="mono b">%s</td><td>%s</td><td class="mono">%s %s</td><td class="cb"></td><td class="cb"></td></tr>' % (esc(a), tx(b), tx(c), tg(d) if d else '') for a, b, c, d in self.S.get('conferencia', []))
        self.page('14 · Conferência final', h1('14', 'Conferência final') + '<table class="grid chk"><thead><tr><th style="width:14mm">Módulo</th><th>Verificação</th><th style="width:70mm">Valor esperado</th><th style="width:16mm">Medido</th><th style="width:12mm">OK</th></tr></thead><tbody>%s</tbody></table>' % tr)

    def cuidados(self):
        cu = self.S.get('cuidados', {})
        cols = ''
        for col in cu.get('colunas', []):
            cols += '<div>%s</div>' % ''.join('<h3>%s</h3><ul class="tight">%s</ul>' % (esc(b['titulo']), ''.join('<li>%s</li>' % tx(i) for i in b['itens'])) for b in col)
        self.page('15 · Cuidados', h1('15', 'Cuidados e recomendações', cu.get('sub', 'Recomendações gerais de montagem e uso — não são especificações do projeto')) + '<div class="cols2">%s</div>' % cols)

    # ------------------------------------------------------------ 16
    def desenho_final(self):
        pj = self.pj
        mids = pj.mod_ids()
        groups = ''
        ext = []
        for mid in mids:
            lo, hi = pj.caixa_bbox(mid)
            flo, _ = pj.mod_bbox(mid)
            ext.append((hi[0] - lo[0]) + (hi[1] - flo[1]) + 400)
        tot = sum(ext)
        avail = 262 - 12 * len(mids)
        Hh = 122 if len(mids) <= 2 else 100
        for mid, e in zip(mids, ext):
            lo, hi = pj.caixa_bbox(mid)
            flo, _ = pj.mod_bbox(mid)
            w = avail * e / tot
            wf = w * ((hi[0] - lo[0]) + 200) / e
            wr = w - wf
            (a, b), s = ortho_set(pj, mid, [('front', wf, Hh), ('right', wr, Hh)], detail=False)
            groups += '<div class="fgroup"><div class="fg-t">%s — %s</div><div class="fg-v"><figure>%s<figcaption>Frontal</figcaption></figure><figure>%s<figcaption>Lateral direita</figcaption></figure></div></div>' % (mid, esc(pj.mods[mid]['nome']), a, b)
        P = self.PJ
        tb = '''<table class="titleblock"><tr>%s<th>Cliente</th><td>%s</td><th>Código</th><td class="mono">%s</td><th>Pedido</th><td class="mono">%s</td><th>Data venda</th><td class="mono">%s</td></tr>
<tr><th>Conteúdo</th><td colspan="3">%s — vistas frontal e lateral direita</td><th>Unidade</th><td>mm</td><th>Escala</th><td>sem escala — usar as cotas</td></tr>
<tr><th>Fonte</th><td colspan="7">Geometria do modelo SketchUp (%s). Cotas %s. Vistas de cada módulo na mesma escala entre si.</td></tr></table>''' % (
            ('<td rowspan="3" class="tb-logo">%s</td>' % self.logo()) if self.logo() else '', esc(P['cliente']), esc(P['codigo']), esc(P.get('pedido', '—')), esc(P.get('data_venda', '—')), ' · '.join('%s %s' % (m, esc(pj.mods[m]['nome'])) for m in mids), esc(P['arquivos']['skp']), tg('E'))
        self.page('16 · Desenho técnico final', h1('16', 'Desenho técnico final') + '<div class="final2"><div class="frow">%s</div>%s</div>' % (groups, tb))

    # ------------------------------------------------------------ anexos
    def anexo_a(self):
        code_of = {x['id']: p['code'] for p in self.pj.parts for x in p['csv']}
        rows = self.pj.csv
        half = (len(rows) + 1) // 2

        def tbl(rs):
            return '<table class="grid csvt"><thead><tr><th>Seq.</th><th>ID</th><th>Descrição (lista de corte)</th><th>C</th><th>L</th><th>Material</th><th>Qtd.</th><th>Código</th></tr></thead><tbody>%s</tbody></table>' % ''.join(
                '<tr><td class="num">%d</td><td class="mono">%s</td><td class="small">%s</td><td class="num">%d</td><td class="num">%d</td><td class="small">%s</td><td class="num">%d</td><td class="mono b">%s</td></tr>' % (
                    r['seq'], r['id'], esc(r['desc'].replace('Etiq.', '')), r['c'], r['l'], esc(r['mat']), r['qtd'], code_of.get(r['id'], '<span class="warn">—</span>')) for r in rs)
        per = 46
        for k in range(0, len(rows), per * 2):
            chunk = rows[k:k + per * 2]
            h = (len(chunk) + 1) // 2
            self.page('Anexo A', h1('A', 'Anexo A — Rastreabilidade da lista de corte', 'As %d linhas do CSV associadas aos códigos deste manual {E} · caracteres corrompidos no arquivo original exibidos como “·”' % len(rows)) + '<div class="cols2 tight">%s%s</div>' % (tbl(chunk[:h]), tbl(chunk[h:])))

    def anexo_b(self):
        tr = ''.join('<tr><td class="cbx">✓</td><td><b>%s</b></td><td>%s</td></tr>' % (esc(a), tx(b)) for a, b in self.S.get('auditoria', []))
        self.page('Anexo B', h1('B', 'Anexo B — Controle de qualidade do manual') + '<table class="grid audit"><tbody>%s</tbody></table>' % tr)

    # ------------------------------------------------------------ render
    SECTIONS = [('01', 'Identificação do projeto', '1 · Identificação'), ('02', 'Informações gerais · conflitos', '2 · Informações gerais'),
                ('03', 'Vista do móvel montado', '3 · Móvel montado'), ('04', 'Medidas gerais', '4 · Medidas gerais'), ('05', 'Lista de peças', '5 · Lista de peças'),
                ('06', 'Lista de ferragens', '6 · Ferragens'), ('07', 'Vista explodida', '7 · Vista explodida'), ('08', 'Peças identificadas', '8 · Peças identificadas'),
                ('09', 'Sequência de montagem', '9 · Sequência de montagem'), ('10', 'Instalação das portas', '10 · Portas'), ('11', 'Instalação das gavetas', '11 · Gavetas'),
                ('12', 'Instalação dos puxadores', '12 · Puxadores'), ('13', 'Regulagem', '13 · Regulagem'), ('14', 'Conferência final', '14 · Conferência final'),
                ('15', 'Cuidados e recomendações', '15 · Cuidados'), ('16', 'Desenho técnico final', '16 · Desenho técnico final'),
                ('A', 'Anexo A — Rastreabilidade da lista de corte', 'Anexo A'), ('B', 'Anexo B — Controle de qualidade', 'Anexo B')]

    def toc_html(self):
        first = {}
        for i, (sec, mod, html, cls) in enumerate(self.pages):
            first.setdefault(sec, i + 1)
        items = ''
        for num, title, key in self.SECTIONS:
            pg = first.get(key)
            if pg:
                items += '<li><span class="tn">%s</span><span class="tt">%s</span><span class="dots"></span><span class="tp mono">%02d</span></li>' % (num, title, pg)
        leg = '<div class="toc-leg"><h3>Origem da informação</h3>%s Encontrado &nbsp; %s Calculado &nbsp; %s Inferido &nbsp; %s Ausente</div>' % (tg('E'), tg('C'), tg('I'), tg('A'))
        return h1('', 'Sumário') + '<div class="toc-wrap"><ol class="toc">%s</ol>%s</div>' % (items, leg)

    def build(self):
        self.cover()
        self.page('Sumário', '__TOC__')
        for f in (self.identificacao, self.info_gerais, self.vista_montado, self.medidas, self.lista_pecas, self.ferragens, self.explodidas,
                  self.pecas, self.sequencia, self.portas, self.gavetas, self.puxadores, self.regulagem, self.conferencia, self.cuidados,
                  self.desenho_final, self.anexo_a, self.anexo_b):
            f()
        return self

    def render(self, full_doc=True):
        P = self.PJ
        total = len(self.pages)
        sheets = []
        for i, (sec, mod, html, cls) in enumerate(self.pages):
            if html == '__TOC__':
                html = self.toc_html()
            if cls == 'p-cover':
                inner = html
            else:
                inner = '''<header class="pg-h"><span class="ph-l">%s<span>MANUAL DE MONTAGEM · <b>%s</b></span></span><span class="ph-c">%s</span><span class="ph-r">%s</span></header>
<main class="pg-m">%s</main>
<footer class="pg-f"><table><tr><th>Cliente</th><td>%s</td><th>Código</th><td class="mono">%s</td><th>Pedido</th><td class="mono">%s</td><th>Seção</th><td>%s</td><th>Folha</th><td class="mono b">%02d / %02d</td></tr></table></footer>''' % (
                    self.logo(), esc(P['codigo']), sec, mod, html, esc(P['cliente']), esc(P['codigo']), esc(P.get('pedido', '—')), sec, i + 1, total)
            sheets.append('<div class="sheet-wrap"><section class="sheet %s" id="folha-%02d">%s</section></div>' % (cls, i + 1, inner))
        js = '''<script>(function(){var MM=96/25.4;function fit(){var w=document.documentElement.clientWidth;var s=Math.min(1,(w-24)/(297*MM));document.querySelectorAll('.sheet-wrap').forEach(function(x){var sh=x.firstElementChild;sh.style.transform='scale('+s+')';x.style.width=(297*MM*s)+'px';x.style.height=(210*MM*s)+'px';});}
if(!(window.matchMedia&&window.matchMedia('print').matches)){fit();window.addEventListener('resize',fit);}})();</script>'''
        css = open(os.path.join(ASSETS, 'manual.css'), encoding='utf-8').read()
        title = 'Manual de Montagem %s' % P['codigo']
        brand_css = ''
        if self.marca:
            brand_css = ':root{--brand:%s}' % self.marca.get('cor', '#1d1f21')
            if self.marca.get('logo_path'):
                b64 = base64.b64encode(open(self.marca['logo_path'], 'rb').read()).decode()
                mime = 'image/svg+xml' if self.marca['logo_path'].endswith('.svg') else 'image/png'
                brand_css += '.logo{background-image:url(data:%s;base64,%s)}' % (mime, b64)
        head = '<title>%s</title><style>%s\n%s\n%s</style>' % (esc(title), font_css(), css, brand_css)
        intro = '<div class="screen-intro"><b>Manual de Montagem · Pedido %s</b> · %s · %d folhas A4 paisagem</div>' % (esc(P['codigo']), esc(P['cliente']), total)
        body = '%s<div class="doc">%s</div>%s' % (intro, '\n'.join(sheets), js)
        if full_doc:
            return '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">%s</head><body>%s</body></html>' % (head, body)
        return '<meta charset="utf-8">%s%s' % (head, body)

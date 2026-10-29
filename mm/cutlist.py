"""Lista de corte (CSV exportado pela produção, separado por ';').

Colunas observadas (pedidos 74391 e 74271):
 0 seq | 1 quantidade | 2 comprimento | 3 largura | 4 material (ex.: "Manhattan Sudati15") |
 5 descrição ("Etiq.30407 - Lat. Esq (...)") | 6 laminação/fita ("Lam 1C e 2L c/ furos") |
 7 ID da linha (ex.: 57546) | 8 item = nº do componente Gábster na raiz do modelo |
 9 pedido | 10 ?
A coluna 8 NÃO é quantidade: é o número do item do pedido, na ordem dos componentes Gábster
na raiz do .skp (componentes que não são Gábster, como a figura "Teddy", não contam).
Conferido nos pedidos 74391 (itens 1–4) e 74271 (itens 1–10). Ver model.item_map().
Caracteres corrompidos no arquivo original (ex.: "Rodap�") são mantidos como '·'.
"""
import csv
import io
import re

BRANDS = r'(Sudati|Duratex|Guararapes|Arauco|Berneck|Eucatex|Masisa|Fibraplac|Placas do Brasil)'


def _int(v):
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def read_csv(path):
    raw = open(path, 'rb').read()
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    txt = txt.replace('�', '·')
    rows = []
    for r in csv.reader(io.StringIO(txt), delimiter=';'):
        if not r or not r[0].strip():
            continue
        try:
            rows.append(dict(seq=int(r[0]), c=int(float(r[2])), l=int(float(r[3])), mat=r[4].strip(), desc=r[5].strip(),
                             lam=r[6].strip(), id=r[7].strip(), qtd=int(float(r[1])), item=_int(r[8]),
                             pedido=r[9].strip() if len(r) > 9 else ''))
        except (ValueError, IndexError):
            continue
    return rows


def material_info(mat):
    """'Manhattan Sudati15' -> ('Manhattan', 'Sudati', 15); 'Branco6' -> ('Branco', '', 6)"""
    m = re.match(r'^(.*?)\s*' + BRANDS + r'?\s*(\d+(?:[.,]\d+)?)$', mat)
    if not m:
        return mat, '', None
    cor = m.group(1).strip()
    marca = m.group(2) or ''
    esp = float(m.group(3).replace(',', '.'))
    return cor, marca, int(esp) if esp == int(esp) else esp


def lam_expand(lam):
    l = lam.replace('Lam.', 'Lam').replace(' c/ furos', '').replace(' Dir', '').replace(' Esq', '').strip()
    m = {'Lam 1C': '1 lado do comprimento', 'Lam 2C': '2 lados do comprimento', 'Lam 1C e 2L': '1 comprimento + 2 larguras',
         'Lam 1C e 1L': '1 comprimento + 1 largura', 'Lam 2C e 1L': '2 comprimentos + 1 largura', 'Lam 2C e 2L': '4 lados',
         'Lam 4L': '4 lados', 'Lam 1L': '1 lado da largura', 'Lam 2L': '2 lados da largura', '': 'sem fita'}
    return m.get(l, l)

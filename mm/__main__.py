"""Linha de comando.

  python -m mm inventario MODELO.skp [--csv LISTA.csv] [-o inventario.txt]
  python -m mm checar  spec.json
  python -m mm medidas spec.json
  python -m mm gerar   spec.json [--saida pasta] [--sem-pdf] [--sem-png]
"""
import argparse
import os
import shutil
import subprocess
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog='mm', description='Gerador de manual de montagem a partir de SketchUp (Gábster) + lista de corte')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('inventario')
    a.add_argument('skp')
    a.add_argument('--csv')
    a.add_argument('-o', '--saida')
    for name in ('checar', 'medidas'):
        b = sub.add_parser(name)
        b.add_argument('spec')
    g = sub.add_parser('gerar')
    g.add_argument('spec')
    g.add_argument('--saida')
    g.add_argument('--sem-pdf', action='store_true')
    g.add_argument('--sem-png', action='store_true')
    args = ap.parse_args(argv)

    if args.cmd == 'inventario':
        from .model import inventory
        txt = inventory(args.skp, args.csv)
        if args.saida:
            open(args.saida, 'w', encoding='utf-8').write(txt)
            print('inventário salvo em', args.saida, '(%d linhas)' % len(txt.splitlines()))
        else:
            print(txt)
        return 0

    from .model import Project
    pj = Project(args.spec)
    if args.cmd == 'checar':
        res = pj.checks()
        for lvl, t in res:
            print('%-8s %s' % (lvl, t))
        n_err = sum(1 for l, _ in res if l == 'ERRO')
        print('\n%d erro(s), %d divergência(s), %d aviso(s)' % (n_err, sum(1 for l, _ in res if l == 'DIVERGE'), sum(1 for l, _ in res if l == 'AVISO')))
        return 1 if n_err else 0
    if args.cmd == 'medidas':
        print(pj.medidas())
        return 0
    if args.cmd == 'gerar':
        from .manual import Manual
        out = args.saida or os.path.join(pj.dir, 'saida')
        os.makedirs(out, exist_ok=True)
        man = Manual(pj).build()
        P = pj.spec['projeto']
        base = 'Manual de Montagem %s' % P['codigo']
        p_print = os.path.join(out, 'manual_print.html')
        p_art = os.path.join(out, base + '.html')
        open(p_print, 'w', encoding='utf-8').write(man.render(True))
        open(p_art, 'w', encoding='utf-8').write(man.render(False))
        print('folhas:', len(man.pages))
        print('html (artifact):', p_art)
        if not args.sem_pdf:
            pdf = os.path.join(out, '%s - %s.pdf' % (base, P['cliente']))
            from .export import to_pdf
            n = to_pdf(p_print, pdf)
            print('pdf:', pdf, '(%s páginas)' % n)
            if n is not None and n != len(man.pages):
                print('ATENÇÃO: o PDF tem %s páginas, mas o manual tem %d folhas — algum conteúdo transbordou.' % (n, len(man.pages)))
            if not args.sem_png and shutil.which('pdftoppm'):
                pd = os.path.join(out, 'png')
                os.makedirs(pd, exist_ok=True)
                for f in os.listdir(pd):
                    os.remove(os.path.join(pd, f))
                subprocess.run(['pdftoppm', '-r', '60', '-png', pdf, os.path.join(pd, 'folha')], check=False)
                from .export import contact_sheets
                sheets = contact_sheets(pd)
                print('miniaturas para revisão:', ', '.join(sheets))
        for lvl, t in pj.checks():
            if lvl in ('ERRO', 'AVISO'):
                print('%-8s %s' % (lvl, t))
        return 0


if __name__ == '__main__':
    sys.exit(main())

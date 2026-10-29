"""Exportação para PDF (Chromium via Playwright) e folhas de miniaturas para revisão visual."""
import glob
import os
import subprocess


# Conteúdo que não cabe: (a) o miolo .pg-m passa do limite; (b) um bloco com overflow escondido
# (ex.: cartão de peça) corta o próprio conteúdo — no PDF ele cresce e invade o rodapé.
OVERFLOW_JS = """() => Array.from(document.querySelectorAll('section.sheet')).map(s => {
  const m = s.querySelector('.pg-m'); if (!m) return null;
  let worst = m.scrollHeight - m.clientHeight;
  m.querySelectorAll('*').forEach(e => {
    if (e.closest('svg')) return;
    const ov = getComputedStyle(e).overflowY;
    if (ov !== 'visible' && e.clientHeight > 0) worst = Math.max(worst, e.scrollHeight - e.clientHeight);
  });
  return worst > 6 ? [s.id, worst] : null; }).filter(x => x)"""


def to_pdf(html_path, pdf_path):
    """Gera o PDF e devolve o nº de páginas. to_pdf.overflow = [(id da folha, px além do limite)]."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto('file://' + os.path.abspath(html_path))
        pg.wait_for_timeout(800)
        pg.emulate_media(media='print')
        pg.wait_for_timeout(200)
        # conteúdo que passa do miolo da folha (invade o rodapé ou é cortado)
        to_pdf.overflow = pg.evaluate(OVERFLOW_JS)
        pg.pdf(path=pdf_path, prefer_css_page_size=True, print_background=True)
        b.close()
    try:
        out = subprocess.run(['pdfinfo', pdf_path], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.startswith('Pages:'):
                return int(line.split()[1])
    except FileNotFoundError:
        pass
    return None


to_pdf.overflow = []


def contact_sheets(png_dir, per=4):
    from PIL import Image
    fs = sorted(glob.glob(os.path.join(png_dir, 'folha-*.png')))
    out = []
    for k in range(0, len(fs), per):
        ims = [Image.open(f) for f in fs[k:k + per]]
        w, h = ims[0].size
        sheet = Image.new('RGB', (w * 2 + 10, h * 2 + 10), '#888888')
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % 2) * (w + 10), (i // 2) * (h + 10)))
        p = os.path.join(png_dir, 'revisao_%02d.png' % (k // per + 1))
        sheet.save(p)
        out.append(p)
    return out

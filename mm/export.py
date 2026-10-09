"""Exportação para PDF (Chromium via Playwright) e folhas de miniaturas para revisão visual."""
import glob
import os
import subprocess


def to_pdf(html_path, pdf_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto('file://' + os.path.abspath(html_path))
        pg.wait_for_timeout(800)
        pg.emulate_media(media='print')
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

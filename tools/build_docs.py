# -*- coding: utf-8 -*-
"""
tools/build_docs.py
Split-Screen Space Shooter projesi icin cift dilli (EN + TR) detayli PDF
dokumantasyonu uretir -> DOCUMENTATION.pdf (proje koku).

Calistir:  python tools/build_docs.py
Bagimlilik: reportlab  (pip install reportlab)

Stil, RTEU "DOCUMENTATION_FINAL.pdf" sablonunu temel alir: mavi bolum
basliklari, tablolar, kod kutulari, sayfa ust/alt bilgisi, kapak ve hizli
referans karti. Yazilar ASCII-foldlu (Helvetica uyumu icin).
"""

import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                Paragraph, Spacer, Table, TableStyle,
                                Preformatted, PageBreak, NextPageTemplate,
                                Image as RLImage, KeepTogether)
from reportlab.lib.utils import ImageReader

# ---------------------------------------------------------------------------
# Renkler / olculer
# ---------------------------------------------------------------------------
BLUE   = HexColor('#13509E')   # bolum basligi + ust bant
BLUE_D = HexColor('#0E4488')   # koyu mavi (kapak ust bant)
BLUE_L = HexColor('#2E6FBF')   # alt-bolum basligi
RED    = HexColor('#C1272D')   # sol kenar serit (kapak/kart)
TBL_ALT = HexColor('#EAF1FB')  # tablo zebra satiri
CODE_BG = HexColor('#F2F2F2')  # kod kutusu arka plan
GRID    = HexColor('#C9D6E8')  # tablo cizgi
GREY    = HexColor('#808080')
INFO_BG = HexColor('#E8F0FB')  # kapak bilgi kutusu

PAGE_W, PAGE_H = A4
LM = RM = 42
TM = 52
BM = 48
FRAME_W = PAGE_W - LM - RM

AUTHOR = 'Yakup Eroglu | 221401045'
HDR_EN = 'Embedded Systems Project -- Recep Tayyip Erdogan University'
HDR_TR = 'Gomulu Sistemler Projesi -- Recep Tayyip Erdogan Universitesi'

# ---------------------------------------------------------------------------
# Paragraf stilleri
# ---------------------------------------------------------------------------
ST_BODY = ParagraphStyle('body', fontName='Helvetica', fontSize=9.5,
                         leading=14, alignment=4, spaceAfter=6,
                         textColor=HexColor('#1A1A1A'))
ST_BUL = ParagraphStyle('bul', parent=ST_BODY, leftIndent=16,
                        bulletIndent=4, spaceAfter=3, alignment=0)
ST_H1W = ParagraphStyle('h1w', fontName='Helvetica-Bold', fontSize=13,
                        textColor=white, leading=16)
ST_H2W = ParagraphStyle('h2w', fontName='Helvetica-Bold', fontSize=10.5,
                        textColor=white, leading=13)
ST_TH = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8.8,
                       textColor=white, leading=11)
ST_TD = ParagraphStyle('td', fontName='Helvetica', fontSize=8.8,
                       textColor=HexColor('#222222'), leading=11)
ST_CODE = ParagraphStyle('code', fontName='Courier', fontSize=7.6,
                         leading=10.2, textColor=HexColor('#222222'))
ST_TOC1 = ParagraphStyle('toc1', fontName='Helvetica-Bold', fontSize=10.5,
                         textColor=BLUE, leading=18)
ST_TOC2 = ParagraphStyle('toc2', fontName='Helvetica', fontSize=9.5,
                         textColor=HexColor('#333333'), leading=15, leftIndent=16)
ST_FREF = ParagraphStyle('fref', fontName='Courier-Bold', fontSize=9,
                         textColor=BLUE, leading=12, spaceBefore=4)
ST_FREFD = ParagraphStyle('frefd', parent=ST_BODY, leftIndent=14, spaceAfter=2)
ST_CAP = ParagraphStyle('cap', fontName='Helvetica-Oblique', fontSize=8.5,
                        leading=11, alignment=1, textColor=GREY, spaceAfter=2)


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ---------------------------------------------------------------------------
# Flowable yardimcilari
# ---------------------------------------------------------------------------
def h1(text):
    t = Table([[Paragraph(esc(text), ST_H1W)]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BLUE),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    t.spaceBefore = 14
    t.spaceAfter = 8
    return t


def h2(text):
    t = Table([[Paragraph(esc(text), ST_H2W)]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BLUE_L),
        ('LEFTPADDING', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    t.spaceBefore = 9
    t.spaceAfter = 6
    return t


def para(text):
    return Paragraph(esc(text), ST_BODY)


def bullets(items):
    return [Paragraph(esc(i), ST_BUL, bulletText=u'•') for i in items]


def code(text):
    # Preformatted metni LITERAL isler (XML entity cozmez) -> escape ETME.
    txt = '\n'.join(line.rstrip() for line in text.strip('\n').split('\n'))
    inner = Preformatted(txt, ST_CODE)
    t = Table([[inner]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
        ('LINEBEFORE', (0, 0), (0, -1), 3, BLUE),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    t.spaceBefore = 4
    t.spaceAfter = 8
    return t


def table(headers, rows, widths=None):
    if widths is None:
        widths = [FRAME_W / len(headers)] * len(headers)
    data = [[Paragraph(esc(h), ST_TH) for h in headers]]
    for r in rows:
        data.append([Paragraph(esc(str(c)), ST_TD) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, TBL_ALT]),
        ('GRID', (0, 0), (-1, -1), 0.5, GRID),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, BLUE),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    t.setStyle(TableStyle(style))
    t.spaceBefore = 4
    t.spaceAfter = 8
    return t


def fref(name, desc):
    return [Paragraph(esc(name), ST_FREF), Paragraph(esc(desc), ST_FREFD)]


def figure(path, caption, max_h=360):
    """Ortali bir gorsel + altinda kursiv basligi. Sayfa icinde bolunmez."""
    iw, ih = ImageReader(path).getSize()
    w = FRAME_W * 0.52
    h = w * ih / iw
    if h > max_h:                  # portre gorsel cok uzunsa yukseklikten sinirla
        h = max_h
        w = h * iw / ih
    img = RLImage(path, width=w, height=h)
    img.hAlign = 'CENTER'
    return KeepTogether([Spacer(1, 5), img, Spacer(1, 3),
                         Paragraph(esc(caption), ST_CAP), Spacer(1, 8)])


# ---------------------------------------------------------------------------
# Sayfa cizimleri (canvas)
# ---------------------------------------------------------------------------
def draw_header_footer(canvas, doc, left_text):
    canvas.saveState()
    canvas.setFillColor(BLUE)
    canvas.rect(0, PAGE_H - 30, PAGE_W, 30, fill=1, stroke=0)
    canvas.setFillColor(BLUE_D)
    canvas.rect(PAGE_W - 10, PAGE_H - 30, 10, 30, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(LM, PAGE_H - 19, left_text)
    canvas.drawRightString(PAGE_W - LM, PAGE_H - 19, AUTHOR)
    canvas.setStrokeColor(HexColor('#CCCCCC'))
    canvas.setLineWidth(0.5)
    canvas.line(LM, 34, PAGE_W - LM, 34)
    canvas.setFillColor(GREY)
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(PAGE_W / 2.0, 24, 'Page %d' % doc.page)
    canvas.restoreState()


def _bg(canvas, color):
    canvas.setFillColor(color)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def draw_cover(canvas, doc, uni_lines, dept, branch, title, subtitle, info):
    canvas.saveState()
    _bg(canvas, white)
    canvas.setFillColor(RED)
    canvas.rect(0, 0, 22, PAGE_H, fill=1, stroke=0)
    # ust mavi bant
    band_h = 232
    canvas.setFillColor(BLUE)
    canvas.rect(22, PAGE_H - band_h, PAGE_W - 22, band_h, fill=1, stroke=0)
    cx = (PAGE_W + 22) / 2.0
    canvas.setFillColor(white)
    canvas.setFont('Helvetica-Bold', 21)
    canvas.drawCentredString(cx, PAGE_H - 78, uni_lines)
    canvas.setFont('Helvetica', 10.5)
    canvas.drawCentredString(cx, PAGE_H - 108, dept[0])
    canvas.drawCentredString(cx, PAGE_H - 125, dept[1])
    canvas.setLineWidth(1.2)
    canvas.setStrokeColor(white)
    canvas.line(cx - 175, PAGE_H - 142, cx + 175, PAGE_H - 142)
    canvas.setFont('Helvetica-Bold', 12)
    canvas.drawCentredString(cx, PAGE_H - 162, branch)
    # baslik alani (acik kutu)
    canvas.setFillColor(INFO_BG)
    canvas.rect(95, PAGE_H - 470, PAGE_W - 95 - 70, 130, fill=1, stroke=0)
    canvas.setFillColor(BLUE)
    canvas.setFont('Helvetica-Bold', 25)
    canvas.drawString(110, PAGE_H - 405, title)
    canvas.setFillColor(HexColor('#555555'))
    canvas.setFont('Helvetica', 11)
    canvas.drawCentredString(cx, PAGE_H - 455, subtitle[0])
    canvas.drawCentredString(cx, PAGE_H - 472, subtitle[1])
    # ogrenci bilgi kutusu
    bx, by, bw, bh = 120, 195, PAGE_W - 120 - 75, 220
    canvas.setFillColor(INFO_BG)
    canvas.rect(bx, by, bw, bh, fill=1, stroke=0)
    canvas.setStrokeColor(BLUE)
    canvas.setLineWidth(1.4)
    canvas.rect(bx, by, bw, bh, fill=0, stroke=1)
    canvas.setLineWidth(3)
    canvas.line(bx, by + bh, bx + bw, by + bh)
    yy = by + bh - 38
    for label, value in info:
        canvas.setFillColor(BLUE)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(bx + 38, yy, label)
        canvas.setFillColor(HexColor('#333333'))
        canvas.setFont('Helvetica', 10)
        canvas.drawString(bx + 190, yy, value)
        yy -= 33
    # alt mavi bant
    canvas.setFillColor(BLUE)
    canvas.rect(22, 0, PAGE_W - 22, 60, fill=1, stroke=0)
    canvas.restoreState()


def draw_divider(canvas, doc, title, subtitle):
    canvas.saveState()
    _bg(canvas, BLUE)
    canvas.setFillColor(RED)
    canvas.rect(0, 0, 26, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont('Helvetica-Bold', 34)
    canvas.drawCentredString(PAGE_W / 2.0 + 12, PAGE_H / 2.0 + 30, title)
    canvas.setFillColor(HexColor('#BFD3F0'))
    canvas.setFont('Helvetica', 13)
    canvas.drawCentredString(PAGE_W / 2.0 + 12, PAGE_H / 2.0 - 8, subtitle)
    canvas.setStrokeColor(white)
    canvas.setLineWidth(1)
    canvas.line(80, 60, PAGE_W - 40, 60)
    canvas.restoreState()


def draw_quickref(canvas, doc, title, subtitle, boxes):
    canvas.saveState()
    _bg(canvas, BLUE)
    canvas.setFillColor(RED)
    canvas.rect(0, 0, 26, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont('Helvetica-Bold', 26)
    canvas.drawCentredString(PAGE_W / 2.0 + 13, PAGE_H - 130, title)
    canvas.setFillColor(HexColor('#BFD3F0'))
    canvas.setFont('Helvetica', 11)
    canvas.drawCentredString(PAGE_W / 2.0 + 13, PAGE_H - 158, subtitle)
    top = PAGE_H - 205
    for box_title, rows in boxes:
        bx, bw = 70, PAGE_W - 70 - 55
        rh = 30
        bh = 52 + rh * len(rows)
        top_box = top
        canvas.setFillColor(HexColor('#1C5DB0'))
        canvas.rect(bx, top_box - bh, bw, bh, fill=1, stroke=0)
        canvas.setFillColor(white)
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawString(bx + 22, top_box - 30, box_title)
        yy = top_box - 64
        for cols in rows:
            canvas.setFillColor(white)
            canvas.setFont('Helvetica-Bold', 9.5)
            canvas.drawString(bx + 30, yy, cols[0])
            canvas.setFont('Helvetica', 9.5)
            canvas.drawString(bx + 185, yy, cols[1])
            canvas.setFillColor(HexColor('#BFD3F0'))
            canvas.setFont('Helvetica', 9)
            if len(cols) > 2:
                canvas.drawString(bx + 300, yy, cols[2])
            yy -= rh
        top = top_box - bh - 26
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Icerik: ortak bolum yazici (EN/TR sozlugu ile)
# ---------------------------------------------------------------------------
def build_sections(story, T):
    for sec in T['sections']:
        kind = sec[0]
        if kind == 'h1':
            story.append(h1(sec[1]))
        elif kind == 'h2':
            story.append(h2(sec[1]))
        elif kind == 'p':
            story.append(para(sec[1]))
        elif kind == 'bul':
            story.extend(bullets(sec[1]))
        elif kind == 'code':
            story.append(code(sec[1]))
        elif kind == 'table':
            story.append(table(sec[1], sec[2], sec[3] if len(sec) > 3 else None))
        elif kind == 'fref':
            for nm, dsc in sec[1]:
                story.extend(fref(nm, dsc))
        elif kind == 'fig':
            story.append(figure(sec[1], sec[2]))
        elif kind == 'sp':
            story.append(Spacer(1, sec[1]))


def build_toc(story, T):
    story.append(Paragraph(esc(T['toc_title']),
                           ParagraphStyle('toch', fontName='Helvetica-Bold',
                                          fontSize=17, textColor=BLUE,
                                          leading=22, spaceAfter=10)))
    story.append(Table([['']], colWidths=[FRAME_W],
                       style=[('LINEBELOW', (0, 0), (-1, -1), 1.2, BLUE)]))
    story.append(Spacer(1, 8))
    for entry in T['toc']:
        if entry[0] == 1:
            story.append(Paragraph(esc(entry[1]), ST_TOC1))
        else:
            story.append(Paragraph(esc(entry[1]), ST_TOC2))


# ---------------------------------------------------------------------------
# DOC
# ---------------------------------------------------------------------------
def build(en, tr, out_path):
    doc = BaseDocTemplate(out_path, pagesize=A4,
                          leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM,
                          title='Split-Screen Space Shooter -- Documentation',
                          author='Yakup Eroglu')
    frame = Frame(LM, BM, FRAME_W, PAGE_H - TM - BM, id='f')
    blank = Frame(0, 0, PAGE_W, PAGE_H, id='blank',
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def cover_en(c, d):
        draw_cover(c, d, en['uni'], en['dept'], en['branch'], en['title'],
                   en['subtitle'], en['info'])

    def cover_tr(c, d):
        draw_cover(c, d, tr['uni'], tr['dept'], tr['branch'], tr['title'],
                   tr['subtitle'], tr['info'])

    templates = [
        PageTemplate(id='cover_en', frames=[blank], onPage=cover_en),
        PageTemplate(id='body_en', frames=[frame],
                     onPage=lambda c, d: draw_header_footer(c, d, HDR_EN)),
        PageTemplate(id='qr_en', frames=[blank],
                     onPage=lambda c, d: draw_quickref(c, d, en['qr_title'],
                                                       en['qr_sub'], en['qr'])),
        PageTemplate(id='divider', frames=[blank],
                     onPage=lambda c, d: draw_divider(c, d, tr['div_title'],
                                                      tr['div_sub'])),
        PageTemplate(id='cover_tr', frames=[blank], onPage=cover_tr),
        PageTemplate(id='body_tr', frames=[frame],
                     onPage=lambda c, d: draw_header_footer(c, d, HDR_TR)),
        PageTemplate(id='qr_tr', frames=[blank],
                     onPage=lambda c, d: draw_quickref(c, d, tr['qr_title'],
                                                       tr['qr_sub'], tr['qr'])),
    ]
    doc.addPageTemplates(templates)

    story = []
    # ----- ENGLISH -----
    # Page 1 = cover_en (cizimi onPage'de). Sonra body'ye gec.
    story.append(Spacer(1, 2))
    story.append(NextPageTemplate('body_en'))
    story.append(PageBreak())                  # -> sayfa 2 (body_en): TOC
    build_toc(story, en)
    story.append(PageBreak())                  # TOC biter; bolumler body_en'de akar
    build_sections(story, en)
    story.append(NextPageTemplate('qr_en'))    # bolumlerden SONRA quick ref'e gec
    story.append(PageBreak())
    story.append(Spacer(1, 2))                 # quick ref karti (onPage cizer)
    story.append(NextPageTemplate('divider'))
    story.append(PageBreak())
    story.append(Spacer(1, 2))                 # TURKCE ayrac sayfasi
    # ----- TURKISH -----
    story.append(NextPageTemplate('cover_tr'))
    story.append(PageBreak())
    story.append(Spacer(1, 2))                 # TR kapak
    story.append(NextPageTemplate('body_tr'))
    story.append(PageBreak())                  # TR body: TOC
    build_toc(story, tr)
    story.append(PageBreak())
    build_sections(story, tr)
    story.append(NextPageTemplate('qr_tr'))    # bolumlerden SONRA quick ref'e gec
    story.append(PageBreak())
    story.append(Spacer(1, 2))                 # TR quick ref karti

    doc.build(story)
    print('PDF olusturuldu:', out_path)


if __name__ == '__main__':
    from docs_content import EN, TR  # noqa: E402
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build(EN, TR, os.path.join(root, 'DOCUMENTATION.pdf'))

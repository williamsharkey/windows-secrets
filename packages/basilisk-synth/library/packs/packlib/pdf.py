"""The pack's printed manual as a period PDF (PDF 1.3, standard Type 1 fonts, A5 or US letter), with a cover that uses
the pack art. Six house styles: zine, corporate_ja, swiss, typewriter, report, corporate."""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A5, letter
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
                                NextPageTemplate, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

STYLES = {
    #            body,          head,                 mono,            size,  ink,       accent,    paper
    'zine':        ('Courier', 'Helvetica-Bold', 'Courier', 'A5', '#111111', '#ff2a9d', '#f4f1f4'),
    'corporate_ja': ('Helvetica', 'Helvetica-Bold', 'Courier', 'A5', '#00264d', '#2a8fd6', '#ffffff'),
    'swiss':       ('Helvetica', 'Helvetica-Bold', 'Courier', 'A5', '#1a1a1a', '#ff6a00', '#ffffff'),
    'typewriter':  ('Courier', 'Courier-Bold', 'Courier', 'letter', '#111111', '#111111', '#ffffff'),
    'report':      ('Times-Roman', 'Times-Bold', 'Courier', 'letter', '#111111', '#111111', '#ffffff'),
    'corporate':   ('Helvetica', 'Helvetica-Bold', 'Courier', 'letter', '#1a1a1a', '#000080', '#ffffff'),
}


def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _cover_crop(png, W, H):
    """The cover art cropped (not stretched) to the page's shape."""
    from PIL import Image
    im = Image.open(png).convert('RGB')
    r = W / H
    if im.width / im.height > r:
        nw = int(im.height * r)
        im = im.crop(((im.width - nw) // 2, 0, (im.width - nw) // 2 + nw, im.height))
    else:
        nh = int(im.width / r)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height - nh) // 2 + nh))
    out = png[:-4] + '_page.png'
    im.save(out)
    return out


def build(p, data, cover_png, credits, out_path):
    st = p['files'].get('pdf_style', 'corporate')
    body, head, mono, size, ink, accent, paper = STYLES[st]
    PD = p.get('pdf', {})
    ink, accent, paper = PD.get('ink', ink), PD.get('accent', accent), PD.get('paper', paper)
    size = p['files'].get('pdf_size', size)
    band, band2 = colors.HexColor(PD.get('band', '#000060')), colors.HexColor(PD.get('band2', '#ffcc00'))
    line1 = PD.get('line1')
    foot = PD.get('foot')
    ink, accent, paper = colors.HexColor(ink), colors.HexColor(accent), colors.HexColor(paper)
    pagesize = A5 if size == 'A5' else letter
    W, H = pagesize
    T, M, pk = p['text'], p['maker'], p['pack']
    ja = st == 'corporate_ja'
    if ja:
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
    m = 14 * mm if size == 'A5' else 1 * 72
    fs = 8.6 if size == 'A5' else 10.5
    if st == 'typewriter':
        fs = 10
    S = {
        'body': ParagraphStyle('b', fontName=body, fontSize=fs, leading=fs * 1.35, textColor=ink, spaceAfter=fs * .6),
        'h1': ParagraphStyle('h1', fontName=head, fontSize=fs * 1.9, leading=fs * 2.3, textColor=accent, spaceAfter=fs, spaceBefore=0),
        'h2': ParagraphStyle('h2', fontName=head, fontSize=fs * 1.2, leading=fs * 1.6, textColor=accent if st != 'zine' else ink,
                             spaceBefore=fs * .8, spaceAfter=fs * .4),
        'mono': ParagraphStyle('m', fontName=mono, fontSize=fs * .8, leading=fs * 1.0, textColor=ink),
        'small': ParagraphStyle('s', fontName=body, fontSize=fs * .78, leading=fs * 1.0, textColor=ink),
        'ja': ParagraphStyle('j', fontName='HeiseiKakuGo-W5' if ja else body, fontSize=fs, leading=fs * 1.6, textColor=ink, spaceAfter=fs * .6),
    }
    if st == 'report':
        S['h2'].textColor = ink
        S['body'].alignment = 4  # justified
    if st == 'zine':
        S['body'].fontSize = fs * .95

    def cover(c, doc):
        c.saveState()
        c.setFillColor(paper)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        if st == 'report':
            # a tech-report cover: text block, rules, the figure small
            c.setFillColor(ink)
            c.setFont('Times-Roman', 11)
            c.drawCentredString(W / 2, H - 1.2 * 72, M['name'].upper())
            c.drawCentredString(W / 2, H - 1.2 * 72 - 14, M['contact'][2])
            c.setLineWidth(.6)
            c.line(72, H - 1.6 * 72, W - 72, H - 1.6 * 72)
            c.setFont('Times-Bold', 22)
            c.drawCentredString(W / 2, H - 2.6 * 72, pk['title'])
            c.setFont('Times-Roman', 15)
            c.drawCentredString(W / 2, H - 2.6 * 72 - 22, pk['subtitle'])
            c.setFont('Times-Italic', 11)
            c.drawCentredString(W / 2, H - 3.3 * 72, ', '.join(a for a, _ in M['people'][:2]))
            c.setFont('Times-Roman', 11)
            c.drawCentredString(W / 2, H - 3.3 * 72 - 16, pk['edition'])
            c.drawCentredString(W / 2, H - 3.3 * 72 - 30, '%s' % __import__('datetime').date.fromisoformat(pk['date']).strftime('%B %Y'))
            s = 3.4 * 72
            c.drawImage(cover_png, (W - s) / 2, 1.6 * 72, s, s, preserveAspectRatio=True, anchor='c')
            c.line(72, 1.3 * 72, W - 72, 1.3 * 72)
            c.setFont('Times-Roman', 9)
            c.drawCentredString(W / 2, 1.0 * 72, foot or 'Distribution unlimited for teaching and research.')
        elif st == 'typewriter':
            c.setFillColor(ink)
            c.setFont('Courier-Bold', 20)
            c.drawCentredString(W / 2, H - 1.5 * 72, pk['title'].upper())
            c.setFont('Courier', 12)
            c.drawCentredString(W / 2, H - 1.5 * 72 - 20, pk['subtitle'])
            c.drawCentredString(W / 2, H - 1.5 * 72 - 36, line1 or (pk.get('edition', '') + ' - User\'s Manual'))
            s = 4.6 * 72
            c.drawImage(cover_png, (W - s) / 2, 3.0 * 72, s, s * 1.25, preserveAspectRatio=True, anchor='c')
            c.setFont('Courier', 10)
            for i, ln in enumerate(M['contact'][:4]):
                c.drawCentredString(W / 2, 2.2 * 72 - i * 13, ln)
            c.setFont('Courier-Bold', 11)
            c.drawCentredString(W / 2, .9 * 72, foot or '*** THANK YOU FOR SUPPORTING SHAREWARE! ***')
        else:
            # full-bleed picture cover with a title band
            from PIL import Image as _I
            iw, ih = _I.open(cover_png).size
            if abs((iw / ih) / (W / H) - 1) < .15:
                c.drawImage(_cover_crop(cover_png, W, H), 0, 0, W, H, preserveAspectRatio=False)
            else:   # a square or landscape front: the whole front, letterboxed on the maker's colour
                c.setFillColor(colors.HexColor(p['look'].get('spine_bg', '#000000')))
                c.rect(0, 0, W, H, stroke=0, fill=1)
                dh = W * ih / iw
                c.drawImage(cover_png, 0, (H - dh) / 2, W, dh)
            if st == 'swiss':
                c.setFillColor(accent)
                c.rect(0, H - 34 * mm, W, 34 * mm, stroke=0, fill=1)
                c.setFillColor(colors.white)
                c.setFont('Helvetica-Bold', 22)
                c.drawString(10 * mm, H - 16 * mm, pk['title'])
                c.setFont('Helvetica', 10)
                c.drawString(10 * mm, H - 23 * mm, line1 or ('Manual  -  ' + pk['subtitle'] + '  -  ' + pk.get('edition', '')))
                c.setFillColor(colors.HexColor('#1a1a1a'))
                c.rect(0, 0, W, 14 * mm, stroke=0, fill=1)
                c.setFillColor(colors.white)
                c.setFont('Helvetica-Bold', 8)
                c.drawString(10 * mm, 5.5 * mm, foot or M['name'].upper())
            elif st == 'zine':
                c.setFillColor(colors.HexColor('#111111'))
                c.rect(0, H - 30 * mm, W, 30 * mm, stroke=0, fill=1)
                c.setFillColor(accent)
                c.setFont('Helvetica-Bold', 30)
                c.setFont('Helvetica-Bold', 30 if len(pk['title']) < 12 else 20)
                c.drawString(8 * mm, H - 20 * mm, PD.get('cover_title', pk['title'].lower()))
                c.setFillColor(colors.white)
                c.setFont('Courier-Bold', 9)
                c.drawString(8 * mm, H - 26 * mm, line1 or M['name'].lower())
                c.setFont('Courier', 8)
                c.setFillColor(colors.HexColor('#111111'))
                c.rect(0, 0, W, 10 * mm, stroke=0, fill=1)
                c.setFillColor(colors.white)
                c.drawString(8 * mm, 3.5 * mm, M['contact'][0])
            else:  # corporate / corporate_ja
                c.setFillColor(colors.white if st == 'corporate_ja' else band)
                c.rect(0, 0, W, H * .26, stroke=0, fill=1)
                c.setFillColor(accent if st == 'corporate_ja' else band2)
                c.rect(0, H * .26, W, 2.2 * mm, stroke=0, fill=1)
                c.setFillColor(ink if st == 'corporate_ja' else colors.white)
                c.setFont('Helvetica-Bold', 20 if size == 'A5' else 30)
                c.drawString(m, H * .26 - 12 * mm, pk['title'])
                c.setFont('Helvetica', 10 if size == 'A5' else 14)
                c.drawString(m, H * .26 - 19 * mm, '%s  -  %s' % (pk['subtitle'], pk.get('edition', '')))
                c.setFont('Helvetica', 8 if size == 'A5' else 10)
                c.drawString(m, H * .26 - 27 * mm, line1 or ("User's Guide" if not ja else "User's Guide  /"))
                if ja:
                    c.setFont('HeiseiKakuGo-W5', 8)
                    c.drawString(m + 25 * mm, H * .26 - 27 * mm, PD.get('line1_ja', 'ユーザーズガイド'))
                    c.drawString(m, 8 * mm, M['name_ja'])
                else:
                    c.drawString(m, 10 * mm, M['name'])
        c.restoreState()

    def later(c, doc):
        c.saveState()
        n = doc.page
        c.setFont(body, 7 if size == 'A5' else 8.5)
        c.setFillColor(ink)
        if st == 'report':
            c.drawCentredString(W / 2, .6 * 72, '- %d -' % n)
            c.drawString(72, H - .6 * 72, pk['edition'])
        elif st == 'typewriter':
            c.drawCentredString(W / 2, .6 * 72, '%s %s  -  Page %d' % (pk['title'], pk['version'], n))
        elif st == 'swiss':
            c.setFillColor(accent)
            c.rect(0, H - 6 * mm, W, 6 * mm, stroke=0, fill=1)
            c.setFillColor(ink)
            c.drawString(m, 6 * mm, '%s  %s' % (pk['title'], pk['edition']))
            c.drawRightString(W - m, 6 * mm, str(n))
        elif st == 'zine':
            c.setFont('Courier-Bold', 8)
            c.drawString(m, 6 * mm, 'p.%d   %s' % (n, M['name'].lower()))
            c.setStrokeColor(accent)
            c.setLineWidth(2)
            c.line(m, H - 8 * mm, W - m, H - 8 * mm)
        else:
            c.setFillColor(accent)
            c.rect(0, H - 5 * mm, W, 5 * mm, stroke=0, fill=1)
            c.setFillColor(ink)
            c.drawString(m, 7 * mm, '%s %s' % (pk['title'], pk.get('subtitle', '')))
            c.drawRightString(W - m, 7 * mm, str(n))
        c.restoreState()

    doc = BaseDocTemplate(out_path, pagesize=pagesize, leftMargin=m, rightMargin=m, topMargin=m, bottomMargin=m,
                          title='%s - %s' % (pk['title'], 'Manual'), author=M['name'], subject=p['text']['tagline'],
                          creator='%s document desk' % M['short'], producer='BASILISK pack generator')
    fr = Frame(m, m, W - 2 * m, H - 2 * m, id='f')
    doc.addPageTemplates([PageTemplate('cover', [Frame(0, 0, W, H)], onPage=cover), PageTemplate('body', [fr], onPage=later)])
    SW = 'swiss' if T.get('intro_de') else '-'
    HD = PD.get('heads', {})
    F = [NextPageTemplate('body'), PageBreak()]
    P = lambda s, k='body': F.append(Paragraph(_esc(s), S[k]))
    if st == 'report' and T.get('sections'):
        P(HD.get('Abstract', 'Abstract'), 'h2')
        P(T['abstract'])
        for i, (h, b) in enumerate(T['sections']):
            P('%d. %s' % (i + 1, h), 'h2')
            P(b)
        P('%d. The presets' % (len(T['sections']) + 1), 'h2')
    else:
        P((HD.get('Introduction') or {SW: 'Einleitung / Introduction', 'zine': 'hi.'}.get(st, 'Introduction')), 'h1')
        for x in T.get('intro_de', []):
            P(x)
        for x in T['intro']:
            P(x)
        for x in T.get('intro_ja', []) if ja else []:
            F.append(Paragraph(_esc(x), S['ja']))
        P((HD.get('Getting Started') or {SW: 'Bedienung / Operation', 'zine': 'how to'}.get(st, 'Getting Started')), 'h2')
        for i, x in enumerate(T['install']):
            P('%d. %s' % (i + 1, x))
        F.append(PageBreak())
        P((HD.get('The Presets') or {SW: 'Klangprogramme / Programs', 'zine': 'the tapes'}.get(st, 'The Presets')), 'h1')
    rows = [['File', 'Name', 'DNA']]
    for x in data['presets']:
        rows.append([Paragraph(_esc('\\' + x['disp']), S['mono']), Paragraph(_esc(x['name']) + ('' if 'XP' in x.get('ships', ['XP']) else ' <font size="6">(16 only)</font>'), S['small']),
                     Paragraph(_esc(x['dna']), S['mono'])])
    cw = W - 2 * m
    t = Table(rows, colWidths=[cw * .27, cw * .25, cw * .48], repeatRows=1)
    t.setStyle(TableStyle([('FONT', (0, 0), (-1, 0), head, fs * .85), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white if st not in ('report', 'typewriter') else ink),
                           ('BACKGROUND', (0, 0), (-1, 0), accent if st not in ('report', 'typewriter') else colors.white),
                           ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#999999')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2)]))
    F.append(t)
    if any('XP' not in x.get('ships', ['XP']) for x in data['presets']):
        P('(16 only): plays on BASILISK 16; BASILISK SYNTH lists the others.', 'small')
    if data['placeholder']:
        P('Preview disc: these presets are placeholders until the library lane builds this pack.', 'small')
    F.append(PageBreak())
    P((HD.get('note') or {SW: 'Anmerkung / Note', 'zine': 'word from the group', 'report': 'Acknowledgements'}.get(st, 'A Note from ' + M['short'])), 'h1' if st != 'report' else 'h2')
    for x in T['maker_note']:
        P(x)
    if T.get('references'):
        P('References', 'h2')
        for r in T['references']:
            P(r, 'small')
    if p.get('register'):
        R = p['register']
        P('Registration', 'h2')
        P(pk['title'] + ' is shareware. Registration is $%.2f plus $%.2f shipping. Registered users get %s.'
          % (R['price'], R['shipping'], R['bonus']))
        for c in M['contact'][:4]:
            P(c, 'mono')
    lic = T.get('license') or []
    if lic:
        P((HD.get('License') or {SW: 'Lizenz / Licence', 'zine': 'the rules'}.get(st, 'License')), 'h2')
        for x in lic:
            P(x, 'small')
    P('Contact', 'h2')
    for c in M['contact']:
        P(c, 'mono')
    P('Picture credits', 'h2')
    for cr in credits:
        P(cr, 'small')
    P('All names of people, companies and products in this pack are fictional.', 'small')
    doc.build(F)
    # PDF 1.3 header (nothing in the file needs 1.4)
    with open(out_path, 'r+b') as f:
        head_ = f.read(9)
        if head_.startswith(b'%PDF-1.'):
            f.seek(0)
            f.write(b'%PDF-1.3')

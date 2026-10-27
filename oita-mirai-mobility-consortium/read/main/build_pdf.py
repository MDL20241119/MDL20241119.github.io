#!/usr/bin/env python3
"""Build the seven-page PDF from the canonical reader HTML (no duplicate copy).

Run: python3 oita-mirai-mobility-consortium/read/main/build_pdf.py
Requires lxml, fontTools[woff], reportlab. Uses the bundled Noto Sans JP subsets.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from html import escape
import re

from lxml import html
from fontTools.ttLib import TTFont as Font
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent.parent / 'documents/main.pdf'
PINK, INK, ACCENT, SOFT = map(HexColor, ['#f7ecee', '#111111', '#bd3c39', '#fff8fa'])
PAGE_W, PAGE_H, PAD = 720, 960, 44
WIDTH = PAGE_W - 2 * PAD


def inline(el):
    out = escape(el.text or '')
    for child in el:
        content = inline(child)
        if child.tag == 'br':
            content = '<br/>'
        elif child.tag in ('strong', 'b'):
            content = f'<b>{content}</b>'
        elif child.tag == 'a':
            href = child.get('href', '')
            if href.startswith('/'):
                href = 'https://mobilitydlab.com' + href
            content = f'<a href="{escape(href, quote=True)}" color="#bd3c39"><u>{content}</u></a>'
        out += content + escape(child.tail or '')
    return out.strip()


def styles(scale):
    def make(name, size, leading=None, **kw):
        font = kw.pop('fontName', 'JP')
        color = kw.pop('textColor', INK)
        return ParagraphStyle(name, fontName=font, fontSize=size * scale,
                              leading=(leading or size * 1.7) * scale,
                              textColor=color, wordWrap='CJK', spaceAfter=7 * scale, **kw)
    return {
        'body': make('body', 14, 23),
        'note': make('note', 11.5, 18.5, textColor=HexColor('#51484a')),
        'h3': make('h3', 19, 27, fontName='JP-Bold', spaceBefore=8 * scale),
        'label': make('label', 10.5, 17, fontName='JP-Bold'),
        'large': make('large', 23, 32, fontName='JP-Bold'),
        'number': make('number', 32, 36, fontName='JP-Bold', textColor=ACCENT),
    }


def paragraph(el, st, key='body'):
    content = inline(el)
    if el.tag in ('strong', 'b'):
        content = f'<b>{content}</b>'
    if el.tag == 'a':
        href = el.get('href', '')
        if href.startswith('/'):
            href = 'https://mobilitydlab.com' + href
        content = f'<a href="{escape(href, quote=True)}" color="#bd3c39"><u>{content}</u></a>'
    return Paragraph(content, st[key])


def boxed(columns, width, st, gap=12):
    cols = []
    sizes = []
    colw = (width - gap * (len(columns) - 1)) / len(columns)
    for i, col in enumerate(columns):
        if i:
            cols.append('')
            sizes.append(gap)
        cols.append(col or [Spacer(1, 1)])
        sizes.append(colw)
    t = Table([cols], colWidths=sizes)
    commands = [('VALIGN', (0, 0), (-1, -1), 'TOP')]
    for i in range(0, len(cols), 2):
        commands += [('BOX', (i, 0), (i, 0), .6, INK),
                     ('BACKGROUND', (i, 0), (i, 0), SOFT),
                     ('LEFTPADDING', (i, 0), (i, 0), 14),
                     ('RIGHTPADDING', (i, 0), (i, 0), 14),
                     ('TOPPADDING', (i, 0), (i, 0), 8),
                     ('BOTTOMPADDING', (i, 0), (i, 0), 4)]
    t.setStyle(TableStyle(commands))
    return [t, Spacer(1, 9)]


def render(el, width, st):
    cls = set(el.get('class', '').split())
    if el.tag in ('p', 'h3', 'h4', 'strong', 'a', 'span'):
        if 'flow-arrow' in cls:
            return []
        key = 'h3' if el.tag in ('h3', 'h4') else 'body'
        if 'note' in cls or 'source-link' in cls:
            key = 'note'
        if 'eyebrow' in cls:
            key = 'label'
        if 'key-message' in cls:
            key = 'h3'
        if el.tag == 'p' and 'fee' in cls:
            num, unit = el.find('b').text_content(), el.find('strong').text_content()
            return [Paragraph(f'<font size="{58 * st["body"].fontSize / 14}"><b>{num}</b></font> <b>{unit}</b>',
                              ParagraphStyle('fee', parent=st['body'], leading=66 * st['body'].fontSize / 14, spaceBefore=10))]
        return [paragraph(el, st, key)]
    if el.tag in ('ol', 'ul'):
        if 'training-flow' in cls:
            items = [Paragraph(f'<b>{n:02}</b><br/>{inline(li)}', st['body']) for n, li in enumerate(el, 1)]
            t = Table([items[:3], items[3:]], colWidths=[width / 3] * 3)
            t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .5, INK),
                                  ('BACKGROUND', (0, 0), (-1, -1), SOFT),
                                  ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                  ('TOPPADDING', (0, 0), (-1, -1), 8),
                                  ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
            return [t, Spacer(1, 10)]
        result = []
        for n, li in enumerate(el, 1):
            if li.tag != 'li':
                continue
            numbered_steps = 'decision-flow' in cls or 'consultation-list' in cls
            if numbered_steps:
                content = []
                div = li.find('div')
                for child in div:
                    content += ([paragraph(child, st, 'h3')] if 'consultation-list' in cls
                                else render(child, width - 58, st))
                num = li.find('b').text_content()
                row = [Paragraph(num, st['number']), content]
            else:
                row = [Paragraph(f'{n:02}' if el.tag == 'ol' else '-', st['label']), paragraph(li, st)]
            number_width = 58 if numbered_steps else 42
            t = Table([row], colWidths=[number_width, width - number_width])
            t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                  ('LINEABOVE', (0, 0), (-1, -1), .5, INK),
                                  ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                  ('RIGHTPADDING', (0, 0), (0, -1), 8),
                                  ('TOPPADDING', (0, 0), (-1, -1), 7),
                                  ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
            result.append(t)
        return result + [Spacer(1, 9)]
    if el.tag == 'table':
        rows = [[paragraph(c, st) for c in tr] for tr in el.xpath('.//tr')]
        table = Table(rows, colWidths=[width * .42, width * .58])
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .5, INK),
                                   ('BACKGROUND', (0, 0), (-1, 0), HexColor('#eddee2')),
                                   ('BACKGROUND', (0, 1), (-1, -1), SOFT),
                                   ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                   ('LEFTPADDING', (0, 0), (-1, -1), 12),
                                   ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                                   ('TOPPADDING', (0, 0), (-1, -1), 9),
                                   ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        return [table, Spacer(1, 12)]
    if el.tag == 'dl':
        return [paragraph(c, st, 'label' if c.tag == 'dt' else 'body') for c in el]
    if cls & {'split-row', 'fee-options', 'milestones', 'meeting-topics', 'accounts', 'purpose-flow'}:
        children = [c for c in el if 'flow-arrow' not in c.get('class', '')]
        cw = (width - 12 * (len(children) - 1)) / len(children) - 28
        return boxed([render(c, cw, st) for c in children], width, st)
    if 'permission-line' in cls:
        return [paragraph(el, st, 'h3')]
    if 'joint-leaders' in cls or 'secretariat-lead' in cls or 'working-team' in cls:
        result = []
        for c in el:
            if c.tag == 'div':
                result += [paragraph(x, st, 'large') for x in c]
            else:
                result += render(c, width - 28, st)
        return boxed([result], width, st)
    result = []
    if el.text and el.text.strip():
        result.append(Paragraph(escape(el.text), st['body']))
    for child in el:
        result += render(child, width, st)
    return result


def height(flows, width):
    return sum(f.wrap(width, PAGE_H)[1] + (f.getSpaceBefore() + f.getSpaceAfter() if isinstance(f, Paragraph) else 0) for f in flows)


def main():
    root = html.fromstring((HERE / 'index.html').read_text())
    sections = root.xpath('//section[contains(@class,"reader-section")]')
    assert len(sections) == 7
    with TemporaryDirectory() as tmp:
        for label, file in [('JP', 'regular'), ('JP-Bold', 'black')]:
            f = Font(HERE / f'assets/proposal-jp-{file}.woff')
            f.flavor = None
            # Give static instances distinct internal names so ReportLab keeps
            # the regular and black faces separate when embedding the subsets.
            for name_id, value in [(1, 'Noto Sans JP Proposal'),
                                   (2, 'Black' if file == 'black' else 'Regular'),
                                   (4, 'Noto Sans JP Proposal ' + file.title()),
                                   (6, 'NotoSansJPProposal-' + file.title())]:
                f['name'].setName(value, name_id, 3, 1, 0x409)
                f['name'].setName(value, name_id, 1, 0, 0)
            fontpath = Path(tmp) / f'{file}.ttf'
            f.save(fontpath)
            pdfmetrics.registerFont(TTFont(label, str(fontpath)))
        pdfmetrics.registerFontFamily('JP', normal='JP', bold='JP-Bold', italic='JP', boldItalic='JP-Bold')
        c = canvas.Canvas(str(OUTPUT), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
        c.setTitle('構想説明書｜大分未来モビリティ・コンソーシアム｜2026.10.28')
        c.setAuthor('トヨタカローラ大分・モビリティデザインラボ')
        for n, sec in enumerate(sections, 1):
            c.setFillColor(PINK)
            c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont('JP-Bold', 11)
            c.drawString(PAD, PAGE_H - 34, '構想説明書｜大分未来モビリティ・コンソーシアム')
            c.setFont('JP', 10)
            c.drawRightString(PAGE_W - PAD, PAGE_H - 34, '関係者向け / 2026.10.28')
            c.setStrokeColor(INK)
            c.line(PAD, PAGE_H - 48, PAGE_W - PAD, PAGE_H - 48)
            c.setFont('JP-Bold', 66)
            c.setFillColor(ACCENT)
            c.drawString(PAD - 2, PAGE_H - 127, f'{n:02}')
            label = sec.xpath('.//span[@class="chapter-label"]')[0].text_content()
            lp = Paragraph(escape(label), ParagraphStyle('chapterlabel', fontName='JP-Bold', fontSize=13, leading=20, alignment=2, wordWrap='CJK'))
            _, lh = lp.wrap(WIDTH - 120, 100)
            lp.drawOn(c, PAD + 120, PAGE_H - 115 - lh / 2)
            c.line(PAD, PAGE_H - 147, PAGE_W - PAD, PAGE_H - 147)
            title = sec.xpath('.//header/h2')[0]
            tp = Paragraph(inline(title), ParagraphStyle('title', fontName='JP-Bold', fontSize=36, leading=50, wordWrap='CJK'))
            _, th = tp.wrap(WIDTH, 200)
            y = PAGE_H - 169 - th
            tp.drawOn(c, PAD, y)
            y -= 18
            lp = Paragraph(inline(sec.xpath('.//header/p')[0]), styles(1)['body'])
            _, lh = lp.wrap(WIDTH, 200)
            y -= lh
            lp.drawOn(c, PAD, y)
            y -= 19
            body = sec.xpath('.//div[@class="chapter-body"]')[0]
            available = y - 53
            for scale in [1, .95, .90, .85, .80]:
                flows = []
                st = styles(scale)
                if n == 1:
                    flows.append(Paragraph('<b>協議用の提案</b>｜体制・会員制度・費用負担・実施内容は、関係者との協議・合意を経て決めます。', st['note']))
                for child in body:
                    flows += render(child, WIDTH, st)
                needed = height(flows, WIDTH)
                if needed <= available:
                    break
            if needed > available:
                raise ValueError(f'Chapter {n} overflows: {needed:.1f} > {available:.1f}')
            for f in flows:
                before = f.getSpaceBefore() if isinstance(f, Paragraph) else 0
                after = f.getSpaceAfter() if isinstance(f, Paragraph) else 0
                _, h = f.wrap(WIDTH, PAGE_H)
                y -= before + h
                f.drawOn(c, PAD, y)
                y -= after
            assert y >= 52, (n, y)
            c.line(PAD, 43, PAGE_W - PAD, 43)
            c.setFillColor(INK)
            c.setFont('JP', 9)
            c.drawString(PAD, 26, 'トヨタカローラ大分 / モビリティデザインラボ')
            c.setFont('JP-Bold', 11)
            c.drawRightString(PAGE_W - PAD, 25, f'{n:02} / 07')
            c.showPage()
            print(f'Chapter {n}: scale={scale}, bottom={y:.1f}')
        c.save()
    print(OUTPUT)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build PDFs from the canonical reader HTML (no duplicate copy).

Run: python3 oita-mirai-mobility-consortium/read/main/build_pdf.py
Requires lxml, fontTools[woff], reportlab. Uses the bundled Noto Sans JP subsets.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from html import escape
import re
import argparse
import json

from lxml import html
from fontTools.ttLib import TTFont as Font
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate, PageBreak, HRFlowable

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
        elif child.get('class') == 'approval-tag':
            content = f' <font color="#822f31">[{content}]</font>'
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
        'h3': make('h3', 19, 27, fontName='JP-Bold', spaceBefore=8 * scale, keepWithNext=True),
        'label': make('label', 10.5, 17, fontName='JP-Bold'),
        'large': make('large', 23, 32, fontName='JP-Bold'),
        'number': make('number', 32, 36, fontName='JP-Bold', textColor=ACCENT),
    }


def paragraph(el, st, key='body'):
    content = inline(el)
    if el.tag in ('strong', 'b', 'th'):
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
    if 'document-links' in cls:
        links = []
        for a in el.xpath('.//a'):
            href = a.get('href', '')
            if href.startswith('/'):
                href = 'https://mobilitydlab.com' + href
            links.append(f'<a href="{escape(href, quote=True)}" color="#bd3c39"><u>{inline(a)}</u></a>')
        text = '<b>関連する文書</b><br/>' + ' / '.join(links)
        return [Paragraph(text, ParagraphStyle('related-documents', parent=st['note'],
                                               spaceBefore=12, leading=18))]
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
        if 'pvmv-statement' in cls:
            key = 'large'
        if el.tag == 'p' and 'fee' in cls:
            num, unit = el.find('b').text_content(), el.find('strong').text_content()
            return [Paragraph(f'<font size="{58 * st["body"].fontSize / 14}"><b>{num}</b></font> <b>{unit}</b>',
                              ParagraphStyle('fee', parent=st['body'], leading=66 * st['body'].fontSize / 14, spaceBefore=10))]
        return [paragraph(el, st, key)]
    if el.tag in ('ol', 'ul'):
        if 'pvmv-values' in cls:
            text = ' / '.join(f'<b>{inline(li)}</b>' for li in el if li.tag == 'li')
            return [Paragraph(text, st['h3']), Spacer(1, 8)]
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
        count = max(len(row) for row in rows)
        weights = [float(x) for x in el.get('data-pdf-widths', '').split(',') if x]
        if len(weights) != count:
            weights = [.42, .58] if count == 2 else [1 / count] * count
        table = Table(rows, colWidths=[width * w / sum(weights) for w in weights], repeatRows=1)
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


class NumberedCanvas(canvas.Canvas):
    """Draw final totals after layout so long chapters may continue naturally."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_pages = []

    def showPage(self):
        self.saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self.saved_pages)
        for state in self.saved_pages:
            self.__dict__.update(state)
            self.setStrokeColor(INK)
            self.line(PAD, 43, PAGE_W - PAD, 43)
            self.setFillColor(INK)
            self.setFont('JP', 9)
            self.drawString(PAD, 26, 'トヨタカローラ大分 / モビリティデザインラボ')
            self.setFont('JP-Bold', 11)
            self.drawRightString(PAGE_W - PAD, 25, f'{self._pageNumber:02} / {total:02}')
            super().showPage()
        super().save()


class ReaderDocTemplate(SimpleDocTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chapter_pages = {}

    def afterFlowable(self, flow):
        if hasattr(flow, 'chapter_id'):
            self.chapter_pages[flow.chapter_id] = self.canv.getPageNumber()


def chapter_header(sec, n):
    label = sec.xpath('.//span[@class="chapter-label"]')[0].text_content()
    num = Paragraph(f'{n:02}', ParagraphStyle('chapter-number', fontName='JP-Bold', fontSize=62,
                                              leading=70, textColor=ACCENT))
    num.chapter_id = sec.get('id')
    label_p = Paragraph(escape(label), ParagraphStyle('chapter-label', fontName='JP-Bold',
                                                       fontSize=13, leading=20, alignment=2, wordWrap='CJK'))
    top = Table([[num, label_p]], colWidths=[110, WIDTH - 110])
    top.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 12)]))
    top.chapter_id = sec.get('id')
    title = Paragraph(inline(sec.xpath('.//header/h2')[0]), ParagraphStyle(
        'chapter-title', fontName='JP-Bold', fontSize=34, leading=47,
        textColor=INK, wordWrap='CJK', spaceAfter=16, keepWithNext=True))
    lead = Paragraph(inline(sec.xpath('.//header/p')[0]), styles(1)['body'])
    return [top, HRFlowable(width=WIDTH, thickness=.8, color=INK), Spacer(1, 20), title, lead, Spacer(1, 13)]


def register_fonts(tmp):
    for label, file in [('JP', 'regular'), ('JP-Bold', 'black')]:
        f = Font(HERE / f'assets/proposal-jp-{file}.woff')
        f.flavor = None
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


def build_pdf(source, output, title):
    source, output = Path(source), Path(output)
    root = html.fromstring(source.read_text())
    sections = root.xpath('//section[contains(@class,"reader-section")]')
    target_nodes = root.xpath('//div[@class="book-top"]/p[@class="publication-update"][contains(.,"設立目標")]')
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as tmp:
        register_fonts(tmp)
        doc = ReaderDocTemplate(str(output), pagesize=(PAGE_W, PAGE_H),
                                leftMargin=PAD - 6, rightMargin=PAD - 6, topMargin=62,
                                bottomMargin=54, title=title,
                                author='トヨタカローラ大分・モビリティデザインラボ')
        story = []
        for n, sec in enumerate(sections, 1):
            if n > 1:
                story.append(PageBreak())
            header = chapter_header(sec, n)
            available = PAGE_H - 68 - 60 - height(header, WIDTH)
            for scale in [1, .95, .90, .85, .80]:
                flows = []
                st = styles(scale)
                if n == 1:
                    notices = root.xpath('//div[@class="book-top"]/p[@class="notice"]')
                    if notices:
                        flows.append(paragraph(notices[0], st, 'note'))
                    if target_nodes:
                        flows.append(paragraph(target_nodes[0], st, 'body'))
                for child in sec.xpath('.//div[@class="chapter-body"]')[0]:
                    flows += render(child, WIDTH, st)
                if height(flows, WIDTH) <= available - 12:
                    break
            else:
                # Preserve readable type; the layout engine carries the chapter
                # onto another page instead of clipping or shrinking it further.
                scale = .95
                st = styles(scale)
                flows = []
                if n == 1 and notices:
                    flows.append(paragraph(notices[0], st, 'note'))
                if n == 1 and target_nodes:
                    flows.append(paragraph(target_nodes[0], st, 'body'))
                for child in sec.xpath('.//div[@class="chapter-body"]')[0]:
                    flows += render(child, WIDTH, st)
                # Make the two longer introductory chapters read as intentional
                # two-page spreads instead of leaving a small tail on page two.
                if sec.get('id') in ('main_ch01', 'main_ch03'):
                    flows = []
                    if n == 1 and notices:
                        flows.append(paragraph(notices[0], st, 'note'))
                    if n == 1 and target_nodes:
                        flows.append(paragraph(target_nodes[0], st, 'body'))
                    for child in sec.xpath('.//div[@class="chapter-body"]')[0]:
                        if sec.get('id') == 'main_ch03' and 'organization-chart' in child.get('class', ''):
                            flows += [PageBreak(), Paragraph('役職候補と実務', st['h3'])]
                        flows += render(child, WIDTH, st)
                        if sec.get('id') == 'main_ch01' and 'pvmv-block' in child.get('class', ''):
                            flows += [PageBreak(), Paragraph('地域で生み出す価値', st['h3'])]
            story.extend(header + flows)
            print(f'{output.name} chapter {n}: type scale={scale}')

        def page_background(c, d):
            c.saveState()
            c.setFillColor(PINK)
            c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont('JP-Bold', 10)
            short = title.replace('大分未来モビリティ・コンソーシアム', '大分未来モビリティ')
            c.drawString(PAD, PAGE_H - 34, short)
            c.setFont('JP', 9)
            c.drawRightString(PAGE_W - PAD, PAGE_H - 34, '関係者向け / 2026.10.28')
            c.setStrokeColor(INK)
            c.line(PAD, PAGE_H - 48, PAGE_W - PAD, PAGE_H - 48)
            c.restoreState()

        doc.build(story, onFirstPage=page_background, onLaterPages=page_background,
                  canvasmaker=NumberedCanvas)
    from pypdf import PdfReader
    page_count = len(PdfReader(output).pages)
    return {'pages': page_count, 'chapter_pages': doc.chapter_pages}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help='Build all four founding PDFs and sync their labels')
    args = parser.parse_args()
    base = HERE.parent.parent
    if args.all:
        config = json.loads((base / 'documents/founding.json').read_text())
        results = []
        for item in config['documents']:
            source = base / item['path'] / 'index.html'
            output = base / item['pdf']
            result = build_pdf(source, output, item['title'] + '｜大分未来モビリティ・コンソーシアム')
            r = html.fromstring(source.read_text())
            for a in r.xpath('//div[@class="book-actions"]/a[contains(@href,".pdf")]'):
                a.text = f'同じ内容のPDF（{result["pages"]}ページ）'
            for sec in r.xpath('//section[contains(@class,"reader-section")]'):
                sec.set('data-pdf-page', str(result['chapter_pages'][sec.get('id')]))
            source.write_text('<!DOCTYPE html>\n' + html.tostring(r, encoding='unicode', method='html') + '\n')
            results.append({**item, **result})
        guide = base / 'guide/index.html'
        r = html.fromstring(guide.read_text())
        for item in results:
            meta = r.xpath(f'//*[@data-pdf-key="{item["key"]}"]')[0]
            meta.text = f'PDF {item["pages"]}ページ｜Web版と同じ内容'
        guide.write_text('<!DOCTYPE html>\n' + html.tostring(r, encoding='unicode', method='html') + '\n')
        manifest = {'version': config['version'], 'target_date': config['target_date'], 'documents': results}
        (base / 'documents/document-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(manifest, ensure_ascii=False))
    else:
        print(build_pdf(HERE / 'index.html', OUTPUT, '構想説明書・設立趣意書｜大分未来モビリティ・コンソーシアム'))


if __name__ == '__main__':
    main()

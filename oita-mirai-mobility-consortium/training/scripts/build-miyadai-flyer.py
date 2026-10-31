#!/usr/bin/env python3
"""Build the public December 2 announcement and its matching A4 print image.

Inputs are the confirmed event record, existing public photos and a local Noto
Sans JP font. Never reads or embeds the speaker's protected reference material.
Never writes participation-flyer.pdf, the approved November handout.

python scripts/build-miyadai-flyer.py --font-variable /path/to/NotoSansJP.ttf
Dependencies: reportlab, fonttools, Pillow and Poppler (pdftoppm).
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import subprocess
import tempfile
from datetime import datetime
from html import escape

from fontTools.ttLib import TTFont as FontToolsFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageOps
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

BASE = Path(__file__).resolve().parent.parent
WEB = "https://mobilitydlab.com/oita-mirai-mobility-consortium/training/"
LECTURE = WEB + "lecture-20261202.html"
W, H = landscape(A4)
INK = "#111315"
MUTED = "#555b62"
PINK = "#f840b3"
YELLOW = "#eeff2d"
CYAN = "#51d9f1"
LINE = "#c9cfd5"


def register_fonts(source, cache):
    key = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    for name, weight in [("JP", 400), ("JPB", 900)]:
        dest = cache / f"NotoSansJP-flyer-{key}-{weight}.ttf"
        if not dest.exists():
            font = FontToolsFont(source)
            if "fvar" in font:
                instantiateVariableFont(font, {"wght": weight}, inplace=True)
            font.flavor = None
            for record in font["name"].names:
                if record.nameID in (1, 2, 3, 4, 6):
                    record.string = f"NotoSansJP-Flyer-{weight}".encode(record.getEncoding(), errors="replace")
            font.save(dest)
        pdfmetrics.registerFont(TTFont(name, str(dest)))
    pdfmetrics.registerFontFamily("JP", normal="JP", bold="JPB", italic="JP", boldItalic="JPB")


class Flyer:
    def __init__(self, path):
        self.c = canvas.Canvas(str(path), pagesize=(W, H), pageCompression=1)
        self.c.setTitle("大分未来モビリティ人材育成プログラム｜12月2日 宮代陽之氏講演・参加案内")
        self.c.setAuthor("トヨタカローラ大分株式会社／株式会社モビリティデザインラボ")
        self.c.setSubject("宮代陽之氏講演・参加費無料・会場Garraway0・配信なし・コンソーシアム参画案内")
        self.boxes = []

    def rect(self, x, y, w, h, fill, stroke=None):
        self.c.setFillColor(HexColor(fill))
        if stroke:
            self.c.setStrokeColor(HexColor(stroke))
            self.c.setLineWidth(.55)
        self.c.rect(x, H-y-h, w, h, fill=1, stroke=bool(stroke))

    def text(self, text, x, y, w, h, size=10, leading=None, bold=False, color=INK, link=None):
        leading = leading or size * 1.45
        style = ParagraphStyle(
            "copy", fontName="JPB" if bold else "JP", fontSize=size,
            leading=leading, textColor=HexColor(color), wordWrap="CJK",
            splitLongWords=True, allowWidows=0, allowOrphans=0,
        )
        paragraph = Paragraph(text, style)
        _, used = paragraph.wrap(w, h)
        if used > h + .01 or x < 0 or y < 0 or x+w > W+.01 or y+used > H:
            raise ValueError(f"Text outside box: {text[:50]} ({used:.2f}>{h})")
        paragraph.drawOn(self.c, x, H-y-used)
        if link:
            self.c.linkURL(link, (x, H-y-used, x+w, H-y), relative=0, thickness=0)
        self.boxes.append(dict(text=text, x=x, y=y, w=w, h=used, size=size))

    def photo(self, path, x, y, w, h, contain=False, link=None):
        image = Image.open(path).convert("RGB")
        if contain:
            image.thumbnail((1200, 900))
            scale = min(w/image.width, h/image.height)
            iw, ih = image.width*scale, image.height*scale
            x += (w-iw)/2
            y += (h-ih)/2
            w, h = iw, ih
        else:
            image = ImageOps.fit(image, (round(w*4), round(h*4)), centering=(.5, .15))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=93)
        self.c.drawImage(ImageReader(io.BytesIO(buffer.getvalue())), x, H-y-h, w, h)
        if link:
            self.c.linkURL(link, (x, H-y-h, x+w, H-y), relative=0, thickness=0)

    def qr(self, url, x, y, size):
        qr = QrCodeWidget(url, barLevel="M", barBorder=4)
        a, b, c, d = qr.getBounds()
        drawing = Drawing(size, size, transform=[size/(c-a), 0, 0, size/(d-b), 0, 0])
        drawing.add(qr)
        self.rect(x, y, size, size, "#ffffff")
        renderPDF.draw(drawing, self.c, x, H-y-size)
        self.c.linkURL(url, (x, H-y-size, x+size, H-y), relative=0, thickness=0)


def build(path, event):
    if event["appearance_status"] != "confirmed" or event["venue"] != "Garraway0":
        raise ValueError("Expected the confirmed December 2 event")
    if event["fee"] != 0 or event["online_delivery"] is not False:
        raise ValueError("Confirm fee and streaming before building")
    start, end = datetime.fromisoformat(event["starts_at"]), datetime.fromisoformat(event["ends_at"])
    weekday = "月火水木金土日"[start.weekday()]
    date = f"{start.year}年{start.month}月{start.day}日（{weekday}）"
    hours = f"{start:%H:%M}-{end:%H:%M}"
    form = event["registration"]["url"].split("?", 1)[0]
    p = Flyer(path)
    p.rect(0, 0, W, H, "#ffffff")
    p.rect(0, 0, W, 7, INK)
    p.text("O I T A  M I R A I  M O B I L I T Y / P R O G R A M  2 0 2 6", 25, 20, 590, 13, 7.5, 11, True)
    p.rect(631, 16, 186, 24, YELLOW)
    p.text("2026年度 国土交通省採択事業", 640, 20, 172, 17, 10.5, 15, True,
           link="https://www.mlit.go.jp/report/press/content/002012284.pdf#page=6")
    p.text("大分未来モビリティ人材育成プログラム", 25, 47, 600, 45, 27.5, 39, True, link=WEB)
    p.text("地域の課題から、来年度の実証を一緒につくる。", 25, 91, 596, 29, 18.5, 27, True)
    p.rect(25, 125, 4, 18, PINK)
    p.text("2026年11月-2027年2月", 38, 123, 215, 23, 13, 19, True)
    p.text("4か月弱の実践型プログラム", 252, 126, 300, 20, 10.5, 15.5, True)
    p.text("現地調査・サービス企画・アプリ開発・データ分析を通じ、2027年度以降の実証につなげます。", 25, 151, 588, 17, 9.7, 14)
    p.rect(631, 47, 186, 111, "#f3f4f4", LINE)
    p.photo(BASE.parent/"assets/mobility-epalette.webp", 635, 48, 178, 109, contain=True,
            link="https://commons.wikimedia.org/wiki/File:Toyota_e-Palette_02.jpg")
    p.text("e-Palette　参考写真 / TTTNIS・CC0", 631, 160, 186, 11, 6.5, 9)

    cards = [
        ("01 / PLAN", "課題を、動く企画へ。", "地域の仲間・専門家と一緒に、現地調査からサービス案・実証計画まで具体化。企画・データ活用の力を実践で身につけます。", PINK),
        ("02 / SUPPORT", "開発・分析を無料で。", "プログラム内のサービス開発・アプリ開発・データ分析を無料で支援。自治体の参加・コンソーシアム参画も無料です。", YELLOW),
        ("03 / NEXT YEAR", "来年度の実証を、一緒に。", "e-Paletteを活用したサービスや自動運転実証の内容・候補地を、参加自治体の課題・提案から優先的に検討します。", CYAN),
    ]
    cw = (W-50-24)/3
    for i, (label, title, body, color) in enumerate(cards):
        x = 25+i*(cw+12)
        p.rect(x, 176, cw, 109, "#ffffff", LINE)
        p.rect(x, 176, 4, 109, color)
        p.text(label, x+14, 185, cw-27, 13, 7.4, 11, True)
        p.text(title, x+14, 202, cw-27, 25, 14.9, 22, True)
        p.text(body, x+14, 231, cw-27, 49, 9.1, 13.1)

    p.text("プログラムの一環", 25, 292, 115, 17, 9.2, 13.5, True)
    p.rect(145, 291, 4, 18, PINK)
    p.text("12月2日｜宮代陽之氏 講演・トークセッション", 158, 291, 658, 21, 11.7, 17, True, link=LECTURE)
    p.rect(25, 311, W-50, .85, INK)
    p.photo(BASE/"assets/miyadai-haruyuki.webp", 25, 323, 111, 126,
            link="https://garrawayf.com/#lnk03")
    p.text("宮代 陽之 氏", 150, 321, 244, 35, 24.5, 34, True)
    p.text("株式会社国際経済研究所<br/>非常勤フェロー（トヨタのシンクタンク）", 150, 358, 239, 32, 9.9, 14.4)
    heading = escape(event["editorial_heading"]).replace("場所に", "場所に<br/>", 1)
    p.text(heading, 150, 396, 239, 36, 12, 17, True)
    p.text("講演内容と最新情報は告知HPへ →", 150, 437, 239, 12, 7.4, 10.5, link=LECTURE)
    p.text(date, 405, 324, 198, 22, 12.9, 19, True)
    p.text(hours, 405, 349, 198, 32, 22.5, 30, True)
    p.rect(405, 384, 197, 27, YELLOW)
    p.text("会場 Garraway0", 414, 388, 180, 22, 13.8, 20, True)
    p.text(event["venue_address"], 405, 416, 198, 16, 8.4, 12)
    p.text("参加費無料 / 配信なし", 405, 435, 198, 16, 9.9, 14, True)
    p.photo(BASE.parent/"assets/garraway0-space.webp", 625, 323, 192, 107,
            link="https://garraway0.com/")
    p.text("会場写真：Garraway0公式サイト", 625, 436, 192, 12, 6.8, 10)

    p.rect(25, 458, W-50, 85, INK)
    p.text("地域の課題と、やってみたいことを教えてください。", 40, 467, 619, 27, 15, 22, True, "#ffffff", form)
    p.text("企画書不要・全活動への出席不要。関心のあるテーマから参加できます。", 41, 496, 605, 16, 8.8, 13, color="#ffffff")
    p.text("自治体・企業・交通事業者・大学・学生・地域住民など、どなたでも参加できます。", 41, 512, 605, 16, 8.8, 13, color="#ffffff")
    p.text("講演への参加予定と、人材育成プログラムへの参加登録は、同じフォームから。", 41, 528, 614, 14, 7.6, 11, color="#ffffff", link=form)
    p.text("参加申込", 665, 485, 60, 16, 10, 14, True, "#ffffff", form)
    p.text("QRから登録 →", 661, 507, 66, 14, 7.7, 11, color="#ffffff", link=form)
    p.qr(form, 738, 465, 70)
    p.text("事業主体：トヨタカローラ大分株式会社　｜　企画・運営：株式会社モビリティデザインラボ", 25, 551, 792, 13, 6.8, 10, True, MUTED)
    p.text("国土交通省 令和8年度「『交通空白』解消等リ・デザイン全面展開プロジェクト」モビリティ人材・組織育成タイプ", 25, 563, 792, 11, 6.2, 9, color=MUTED,
           link="https://www.mlit.go.jp/report/press/content/002012284.pdf#page=6")
    p.text("実証の実施条件・役割・費用は個別協議。写真：Garraway F / Garraway0公式（既存掲載素材） / e-Palette：TTTNIS・CC0", 25, 575, 792, 11, 6.1, 9, color=MUTED)
    p.c.showPage()
    p.c.save()
    return p.boxes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-variable", type=Path, required=True)
    parser.add_argument("--font-cache", type=Path)
    parser.add_argument("--output", type=Path, default=BASE/"participation-flyer-20261202.pdf")
    parser.add_argument("--print-image", type=Path, default=BASE/"assets/lecture-20261202-print.png")
    parser.add_argument("--qa-json", type=Path)
    args = parser.parse_args()
    if args.output.resolve() == (BASE/"participation-flyer.pdf").resolve():
        raise ValueError("The approved November handout must remain unchanged")
    event = next(e for e in json.loads((BASE/"lectures.json").read_text())["lectures"] if e["id"] == "lecture-20261202")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.print_image.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        cache = args.font_cache or Path(temp)
        cache.mkdir(parents=True, exist_ok=True)
        register_fonts(args.font_variable, cache)
        boxes = build(args.output, event)
    subprocess.run(["pdftoppm", "-r", "200", "-singlefile", "-png", str(args.output), str(args.print_image.with_suffix(""))], check=True)
    if args.qa_json:
        args.qa_json.write_text(json.dumps(boxes, ensure_ascii=False, indent=2))
    print(json.dumps({"pdf": str(args.output), "print_image": str(args.print_image), "pages": 1, "text_boxes": len(boxes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Rebuild the local Yomogi webfont from the licensed original TTF.

Usage: python scripts/subset-font.py /path/to/Yomogi-Regular.ttf
Requires fontTools. The original release and OFL are cited in README.md.
"""
from pathlib import Path
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2:
    raise SystemExit("Supply the original Yomogi-Regular.ttf path.")

source = Path(sys.argv[1])
text = "".join((ROOT / name).read_text() for name in (
    "index.html", "app.js", "maps.css", "zine.css", "illustrations.css", "global-loop.css"
)) + "".join(chr(code) for code in range(32, 127))

font = TTFont(source)
options = subset.Options()
options.flavor = "woff"
subsetter = subset.Subsetter(options=options)
subsetter.populate(text=text)
subsetter.subset(font)
font.flavor = "woff"
target = ROOT / "assets/yomogi-zine.woff"
font.save(target)
print(f"Wrote {target.name}: {target.stat().st_size:,} bytes")

"""Official photo-source cards; unlicensed photographs are not embedded or copied."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'data/photo-sources.json').read_text())

def render(case_id):
    cards = DATA.get(case_id, [])
    if not cards:
        return ''
    e = lambda value: html.escape(value, quote=True)
    out = ['<section class="photo-sources" id="official-photo-sources" aria-labelledby="photo-sources-title"><p class="eyebrow">OFFICIAL PHOTO SOURCES</p><h2 id="photo-sources-title">もっと見る：公式写真で、活動の細部へ。</h2><p class="photo-sources-intro">以下は写真の転載ではなく、公式の掲載ページへの案内です。リンク先で見られる場面を整理しました。写真だけから、協働の効果や事業化の成果は判断できません。</p><div class="photo-source-grid">']
    for i, card in enumerate(cards, 1):
        if not card['url'].startswith('https://'):
            raise ValueError('Official photo sources must use HTTPS')
        out.append(f'<article class="photo-source-card"><p class="eyebrow">SOURCE {i:02d} / 公式掲載元</p><h3>{e(card["title"])}</h3><p class="photo-source-label">写真で確認できる場面</p><ul>' + ''.join(f'<li>{e(scene)}</li>' for scene in card['scenes']) + f'</ul><p class="photo-source-context">{e(card["context"])}</p><a href="{e(card["url"])}" target="_blank" rel="noopener noreferrer">公式ページで写真を見る <span aria-hidden="true">↗</span><span class="sr-only">（新しいタブ）</span></a></article>')
    out.append('</div><p class="photo-sources-note">追加候補の転載条件は確認中のため、この欄では画像を複製・埋め込みしていません。公式サイトでの公開は、第三者による自由な転載を意味しません。写真案内の確認日：2026-10-27。</p></section>')
    return ''.join(out)

def stylesheet(prefix=''):
    return f'<link rel="stylesheet" href="{prefix}photo-sources.css?v=20261027.1">'

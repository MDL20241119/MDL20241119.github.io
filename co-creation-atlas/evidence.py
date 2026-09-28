"""Make verification scope and sources visible without claiming independent proof."""
import html


def e(value):
    return html.escape(str(value), quote=True)


def notice(case):
    sources = case['sources']
    dates = sorted({s.get('verified', '') for s in sources if s.get('verified')})
    checked = dates[-1] if dates else '未記録'
    return (
        '<aside class="evidence-notice" aria-label="情報源と確認の範囲">'
        f'<a href="#evidence-sources">情報源 {len(sources)}件 ↓</a>'
        f'<span>確認：<time datetime="{e(checked)}">{e(checked)}</time></span>'
        '<a href="#evidence">確認できた成果を見る ↓</a></aside>'
    )

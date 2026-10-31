# 日本のモビリティ実証と政策の10年

2026年10月31日版、デザイン02（黒背景・ビビットな配色）の公開ソース。静的HTML・CSS・JavaScriptのみ。

公開URL：https://mobilitydlab.com/mobility-policy-history/

## ファイル

- `index.html`：ページ入口。公開URLのcanonical・共有用メタ情報を設定。
- `assets/history.css`：既存のレイアウト・基本部品。
- `assets/design-v2.css`：黒背景、蛍光イエロー・ピンク・シアン、特大の数字・年・キーワード。
- `assets/archive-display.woff2` と `OFL-archive-display.txt`：数字・英字用のローカルフォントとSIL OFLライセンス。
- `assets/history.js`：検索、年表、詳細、出典、10テーマの大きな入口、ハッシュURLと戻る操作。
- `data/mobility_history_data.json`：受領した正本をバイト単位で保持。
- `data/view-data.js`：正本から生成する表示データ。テーマ・検索分類・原URLの接続点検結果を追加。
- `downloads/mobility-history-report.pdf`：94ページの調査報告。
- `downloads/mobility-history-ledger.xlsx`：年表・事例・制度・出典の照合台帳。
- `maintenance/rebuild.py`：表示データと件数検査を再生成。Pythonのpypdf・openpyxlを使用（制作時のみ）。
- `verification/`：件数、正本ハッシュ、接続点検、受入検査。実行時の依存なし。

## 表示とURL

`index.html#case/meti_eiheiji` のように入口ページのハッシュで遷移します。GitHub PagesにSPA用の書き換え・404回避ファイル・外部APIは不要です。詳細への直接アクセス、再読み込み、共有URLで同じIDを開けます。絞り込みはURLに、閲覧位置はブラウザーの履歴状態に保持します。

`#cases?year=2024&pref=静岡県`、`#timeline?kind=policy&year=2026`、`#program/commmmons`、`#source/SRC-e3caafad86`。

検索用のテーマは名称・実施内容等の記載から付けた分類で、制度帰属や因果関係を増やすものではありません。状態フィルターも原記載を検索するための分類です。元の状態・根拠時点は常に併記します。

## 更新

1. 既存IDを維持して正本JSONへ新しい出来事と出典を追記する。過去の状態と統合前の元記録を消さない。
2. 正本の`counts`を更新する。事例、制度、イベント、出典は実データから再計算し照合する。
3. 照合用Excelも同じID・出典URLへ更新する。資料日付、事象日、確認日、年度の精度を維持する。
4. `python3 maintenance/rebuild.py`を実行し、`node verification/acceptance.cjs`で検査する。受入検査の111・66等は今回凍結版の期待値なので、改訂時は独立した照合結果で期待値を更新する。
5. PDFを差し替える場合は`maintenance/rebuild.py`の詳説章のページ範囲と`detailed_case_ids`を確認する。現在は15–41ページに主要25事例がある。
6. PC・スマホで表示、検索、戻る、出典リンクを確認する。原URLの接続点検結果は本文の真偽判定や消滅判定と別に管理する。

## 公開と配信

本人の公開指示に基づき、既存のGitHub Pages（mainのルート配信）へこのフォルダーを追加する。トップページのNEWSと公開リサーチに導線を追加。既存の`.nojekyll`・CNAME・公開範囲・認証・他ページは維持する。

トップページからの導線：

> 日本のモビリティ実証と政策の10年。111の取り組みを、開始から継続・変更・終了までたどる。

PDF・Excel・JSONは共有された原資料を収録しています。正本JSON・PDF・Excelは受領時のバイトを保持。第三者原資料の画像・本文を追加転載していません。原出典の権利・利用条件は各提供元に従います。

出典の接続点検では39件が再確認対象（404、403、503、応答なし）です。原URLとIDを保持し、個別に「接続再確認」を表示します。接続不可を資料消滅・記述の誤りとは扱いません。

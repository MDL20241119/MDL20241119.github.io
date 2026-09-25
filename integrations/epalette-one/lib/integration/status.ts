export const integrationStatus=[
 {name:'共通業務API',version:'e-Palette ONE v1',implementation:'実装済み',verification:'ローカル自動試験済み',connection:'外部未接続',scope:'検索・本人の乗車予約・車両状況・充電計算・確認後の確定'},
 {name:'MCP',version:'2026-07-28',implementation:'採用範囲を実装',verification:'ローカル呼出・原本スキーマ試験済み',connection:'対象AI未接続',scope:'発見・ツール一覧・呼出。旧版互換とOAuth接続は未検証'},
 {name:'A2A',version:'1.0 / JSONRPC',implementation:'採用範囲を実装',verification:'ローカルタスク試験済み',connection:'外部エージェント未接続',scope:'構造化依頼とポーリング。ストリーミング・通知は対象外'},
 {name:'COMmmmONS デマンドバス',version:'1.0.0',implementation:'4操作を実装・15操作未実装',verification:'採用した入出力の原本契約試験済み',connection:'交通事業者未接続',scope:'候補・予約確定・本人予約一覧・取消。指定乗降点・一般区分・配車済み便に限定'},
 {name:'GTFS-JP',version:'v4',implementation:'Schedule出力・限定検査・Flex変換を実装',verification:'合成フィードの検査',connection:'経路検索事業者未接続',scope:'Scheduleは同じ予定から生成。Flexは明示設定の変換試験のみ。Realtimeは取得データ未設定'},
 {name:'COMmmmONS QRチケット',version:'1.0.0 / MaaS通知',implementation:'単回乗車通知の変換を実装',verification:'合成権利の再送・二重使用試験済み',connection:'認証ハブ未接続',scope:'外部受付は無効。発券・QR生成・払戻などは未実装'},
];

"""Export the local Agent Card and application data envelope (not A2A fields)."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.a2a_adapter import card
from google.protobuf.json_format import MessageToDict


def contract():
    identifier={'type':'string','pattern':'^[A-Za-z0-9_-]{1,100}$'}
    def variant(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','title':'MDL local A2A Part.data application envelope',
        'description':'独自の業務データ契約。A2A 1.0自体の公式スキーマは同梱a2a.proto。実行は別途本人が承認した操作の参照のみ。',
        'oneOf':[variant({'action':{'const':'read_reservation'},'reservation_id':identifier}),variant({'action':{'const':'execute'}}),
            variant({'action':{'const':'execute'},'operation_id':identifier,'idempotency_key':identifier,
                'kind':{'enum':['request','book','change','cancel']},'operation_digest':{'type':'string','pattern':'^[0-9a-f]{64}$'}})]}


if __name__=='__main__':
    for name,value in [('a2a-agent-card.json',MessageToDict(card(8767))),('a2a-task-data.schema.json',contract())]:
        (ROOT/'api'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        print('api/'+name)

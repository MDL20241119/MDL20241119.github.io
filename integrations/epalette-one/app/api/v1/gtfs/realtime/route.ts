import {authenticate,json,errorResponse} from '@/lib/integration/service';
export async function GET(request:Request){try{await authenticate(request,'api');return json({error:'許可された実測位置・便との対応・鮮度が未設定です。GTFS Realtime の遅延ゼロや現在位置を生成しません。'},503);}catch(e){return errorResponse(e);}}

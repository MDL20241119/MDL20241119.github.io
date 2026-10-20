import {authenticate,jsonBody,errorResponse} from '@/lib/integration/service';
import {fail} from '@/lib/integration/core';
export async function POST(request:Request){try{await authenticate(request,'commmmons');await jsonBody(request);fail(503,'QR接続先・権利の対応表・認証契約が未設定です。使用済みとは記録しません。');}catch(e){return errorResponse(e);}}

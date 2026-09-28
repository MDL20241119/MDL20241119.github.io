import { env } from 'cloudflare:workers';
import { responseError } from '@/lib/store';
import { DomainError } from '@/lib/model';
// Fail closed until the transport, per-vehicle profile, and tenant mapping are approved.
// No VCI actuator or remote driving command is implemented.
export async function POST(){try{const config=env as unknown as Record<string,unknown>;if(!config.VEHICLE_CONNECTION_APPROVED)throw new DomainError(503,'実車連携は未接続です。正式な接続契約・認証・車両別プロファイルの設定が必要です。');throw new DomainError(501,'接続先固有の認証・イベント変換は未実装です。実車データは受理していません。');}catch(e){return responseError(e);}}

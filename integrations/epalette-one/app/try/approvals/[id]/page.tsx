import GuestApproval from './view';
export default async function Page({params}:{params:Promise<{id:string}>}){return <GuestApproval id={(await params).id}/>;}

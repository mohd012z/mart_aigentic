// Cloudflare Worker: authenticated Telegram ingress, D1-backed leasing, no deployment side effects.
const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{"content-type":"application/json"}});
const bytes=s=>new TextEncoder().encode(s);
function equal(a,b){const x=bytes(a),y=bytes(b);let diff=x.length^y.length;for(let i=0;i<Math.max(x.length,y.length);i++)diff|=(x[i]||0)^(y[i]||0);return diff===0}
export default {
 async fetch(request,env){
  if(new URL(request.url).pathname!=="/telegram/webhook")return json({error:"not_found"},404);
  if(request.method!=="POST")return json({error:"method_not_allowed"},405);
  if(!env.TELEGRAM_WEBHOOK_SECRET||!equal(request.headers.get("X-Telegram-Bot-Api-Secret-Token")||"",env.TELEGRAM_WEBHOOK_SECRET))return json({error:"forbidden"},403);
  if(Number(request.headers.get("content-length")||0)>65536)return json({error:"too_large"},413);
  let update;try{const body=await request.text();if(bytes(body).length>65536)return json({error:"too_large"},413);update=JSON.parse(body)}catch{return json({error:"invalid_json"},400)}
  if(!Number.isSafeInteger(update?.update_id)||update.update_id<0)return json({error:"invalid_update_id"},400);
  try{
   const result=await env.MART_DB.prepare("INSERT INTO telegram_updates (update_id,payload,status,attempts,next_attempt_at) VALUES (?1,?2,'pending',0,0) ON CONFLICT(update_id) DO NOTHING").bind(update.update_id,JSON.stringify(update)).run();
   if(!result || result.success!==true)throw new Error("D1 insert did not confirm success");
   return json({ok:true});
  }catch{return json({error:"storage_unavailable"},503)}
 }
};

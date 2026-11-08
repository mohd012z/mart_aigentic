// Staging-only Telegram webhook adapter. No campaign creation, publishing or registration.
export const COMMANDS = ["start","menu","campaign","campaignstatus","research","recommend","marketing","ads","social","video","affiliate","status","help"];
const actions = [
  ["campaign","🚀 Campaign"],["research","🔎 Research"],["recommend","📊 Recommendations"],
  ["marketing","📣 Marketing"],["ads","🎯 Ads Creator"],["social","📱 Social Posts"],
  ["video","🎬 Video Script"],["affiliate","🛍 Affiliate"]
];
export function keyboard() {
  const rows = [];
  for (let i=0;i<actions.length;i+=2)
    rows.push(actions.slice(i,i+2).map(([key,text])=>({text,callback_data:"action:"+key})));
  rows.push([{text:"⚙️ Status",callback_data:"status"},{text:"❓ Help",callback_data:"help"}]);
  rows.push([{text:"🏠 Main Menu",callback_data:"menu"}]);
  return {inline_keyboard:rows};
}
export function menuText() {
  return "🚀 MART | AI Research & Marketing Studio\n\nChoose a tool below or type a command.\n\n🔎 Research & recommendations\n📣 Marketing, ads, social and video drafts\n🛍 Affiliate research\n🚀 Campaign preparation and review\n\n🔒 Research mode: no automatic publishing or live campaign delivery.\nUse /help for examples.";
}
const help = "MART Research Bot\n/start — open menu\n/menu — show tools\n/research <topic> — research (requires Python service)\n/recommend <topic> — recommendations (requires Python service)\n/status — staging status\n/help — commands";
function response(body,status=200){return new Response(JSON.stringify(body),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}});}
function safeEqual(a,b) {
  if(typeof a!=="string"||typeof b!=="string"||!a||!b) return false;
  const x=new TextEncoder().encode(a),y=new TextEncoder().encode(b);
  let diff=x.length^y.length;
  for(let i=0;i<Math.max(x.length,y.length);i++) diff|=(x[i]??0)^(y[i]??0);
  return diff===0;
}
export function render(update) {
  const callback=update.callback_query;
  const message=callback?.message ?? update.message;
  const chat=message?.chat;
  const chatId=chat?.id;
  if(!Number.isSafeInteger(chatId)) return null;
  const data=callback?.data;
  if(callback) {
    if(typeof callback.id!=="string"||!callback.id) return null;
    if(data==="menu") return {chatId,text:menuText(),callbackId:callback.id};
    if(data==="help") return {chatId,text:help,callbackId:callback.id};
    if(data==="status") return {chatId,text:"MART staging adapter online. Research and campaign execution disabled.",callbackId:callback.id};
    if(typeof data==="string"&&data.startsWith("action:")) {
      const kind=data.slice(7);
      if(actions.some(([k])=>k===kind)) return {chatId,text:kind==="campaign"?"Campaign creation requires the Python service. No campaign was created.":`Selected: ${actions.find(([k])=>k===kind)[1]}\nEnter /${kind} followed by your topic in the Python service.`,callbackId:callback.id};
    }
    return {chatId,text:menuText(),callbackId:callback.id};
  }
  if(typeof message?.text!=="string") return null;
  const command=message.text.trim().split(/\s+/,1)[0].split("@",1)[0].toLowerCase();
  if(command==="/start"||command==="/menu") return {chatId,text:menuText()};
  if(command==="/help") return {chatId,text:help};
  if(command==="/status") return {chatId,text:"MART staging adapter online. Research and campaign execution disabled."};
  if(command==="/campaign"||command==="/campaignstatus"||command==="/research"||command==="/recommend"||command==="/marketing"||command==="/ads"||command==="/social"||command==="/video"||command==="/affiliate")
    return {chatId,text:"This staging adapter displays the menu only. The Python service is required for this command."};
  return {chatId,text:help};
}
async function telegram(token,method,payload) {
  const r=await fetch("https://api.telegram.org/bot"+token+"/"+method,{
    method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(payload)
  });
  if(!r.ok) throw new Error("Telegram "+method+" HTTP "+r.status);
  const json=await r.json();
  if(json.ok!==true) throw new Error("Telegram "+method+" rejected request");
}
export default {
  async fetch(request,env) {
    const url=new URL(request.url);
    if(url.pathname==="/health"&&request.method==="GET")
      return response({status:"ok",service:"mart-telegram-staging",delivery_enabled:env.STAGING_ENABLE_DELIVERY==="true"});
    if(url.pathname!=="/telegram/webhook") return response({error:"not_found"},404);
    if(request.method!=="POST") return response({error:"method_not_allowed"},405);
    if(!safeEqual(request.headers.get("X-Telegram-Bot-Api-Secret-Token"),env.TELEGRAM_WEBHOOK_SECRET))
      return response({error:"forbidden"},403);
    if(!request.headers.get("content-type")?.toLowerCase().startsWith("application/json"))
      return response({error:"unsupported_media_type"},415);
    let update;
    try {update=await request.json();} catch {return response({error:"invalid_json"},400);}
    if(!update||!Number.isSafeInteger(update.update_id)||update.update_id<0) return response({error:"invalid_update_id"},400);
    const reply=render(update);
    if(!reply) return response({ok:true,handled:false});
    // Default is preview-only: never send messages or acknowledge callbacks.
    if(env.STAGING_ENABLE_DELIVERY!=="true") return response({ok:true,preview:true,command:reply.text.slice(0,100)});
    if(!env.TELEGRAM_BOT_TOKEN) return response({error:"missing_token"},503);
    try {
      if(reply.callbackId) await telegram(env.TELEGRAM_BOT_TOKEN,"answerCallbackQuery",{callback_query_id:reply.callbackId});
      await telegram(env.TELEGRAM_BOT_TOKEN,"sendMessage",{chat_id:reply.chatId,text:reply.text,reply_markup:keyboard(),disable_web_page_preview:true});
    } catch {return response({error:"delivery_failed"},502);}
    return response({ok:true});
  }
};

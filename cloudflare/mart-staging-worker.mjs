// Staging-only Telegram webhook adapter. No campaign creation, publishing or registration.
export const COMMANDS = ["start","menu","campaign","campaignstatus","research","recommend","marketing","ads","social","video","affiliate","forexbonus","forexa","status","help"];
const actions = [
  ["campaign","🚀 Campaign"],["research","🔎 Research"],["recommend","📊 Recommendations"],
  ["marketing","📣 Marketing"],["ads","🎯 Ads Creator"],["social","📱 Social Posts"],
  ["video","🎬 Video Script"],["affiliate","🛍 Affiliate"],
  ["forexbonus","💵 Forex No-Deposit Bonus"],["forexa","🔗 Forex Affiliate Links"]
];
export function keyboard() {
  const rows = [];
  for (let i=0;i<actions.length;i+=2)
    rows.push(actions.slice(i,i+2).map(([key,text])=>({text,callback_data:"action:"+key})));
  rows.push([{text:"⚙️ Status",callback_data:"status"},{text:"❓ Help",callback_data:"help"}]);
  rows.push([{text:"🏠 Main Menu",callback_data:"menu"}]);
  return {inline_keyboard:rows};
}
// Examples describe inputs to the Python service. Staging serves these guides offline.
const guides = new Map([
  ["campaign", ["Campaign brief", "/campaign reusable bottles for campus clubs", "Specify the product, audience and goal. Keep the campaign ID from the Python service and check the draft before publishing."]],
  ["campaignstatus", ["Campaign status", "/campaignstatus 12", "Use the ID returned when you submitted a campaign. A queued job is waiting, a running job is processing, and a draft in review is ready to inspect."]],
  ["research", ["Source-backed research", "/research refill stations on Malaysian campuses", "Ask one verifiable question. For each claim, keep the source URL, date and supporting passage. Mark anything the source does not establish as unknown."]],
  ["recommend", ["Compare ideas", "/recommend campus bottle refill campaign", "Compare ideas for the same audience. Inspect the sources behind a score and record one assumption you would test before spending money."]],
  ["marketing", ["Marketing plan", "/marketing reusable bottles for campus clubs", "Name the audience, offer and channel. Choose one observable outcome, such as completed sign-ups, and a date to review it."]],
  ["ads", ["Ad copy", "/ads campus bottle refill launch", "Draft two headlines with the same offer. Change one element at a time and check every price or performance claim against the brief."]],
  ["social", ["Social post", "/social campus refill challenge", "Write a hook, one useful detail and one action. Example hook — Where can you refill between lectures? Add the station location before posting."]],
  ["video", ["Short video", "/video how to find the refill station", "Storyboard a 30-second clip. Open with the empty bottle, show the route and refill, then close with the station location."]],
  ["affiliate", ["Affiliate review", "/affiliate trading tools", "Check the merchant page for eligibility, commission and verification date. Keep the disclosure beside any link you share."]],
  ["forexbonus", ["Offer verification", "/forexbonus", "Record the offer date, eligible region, withdrawal conditions and official terms. An undated listing needs fresh confirmation."]],
  ["forexa", ["Saved affiliate links", "/forexa list", "In the Python service, use private chat to inspect your saved links. Check the destination and disclosure before using /forexa share."]],
  ["contentlab", ["Content Lab", "/contentlab campus refill challenge tiktok", "Prepare a script, caption, hashtags and stock-footage search terms around one topic. Check the footage licence before publishing."]],
  ["prompt", ["Prompt Lab", "/prompt campus refill campaign bm", "State the audience, source material and output format. Add bm for a Malay-language prompt or en for English."]],
  ["metrics", ["Usage ledger", "/metrics", "Review the Python service’s recorded activity. Compare operations over the same period and distinguish measured usage from estimates."]]
]);

const aliases = new Set(["usage", "quality", "agentstatus", "report"]);
const statusText = "MART staging menu is online. Tool guides are available offline. Campaign processing, web research and usage records are available in the Python service.";
function guideText(key) {
  const guide = guides.get(key);
  if (!guide) return null;
  const [title, example, instructions] = guide;
  return title + "\n\n" + instructions + "\n\nPython service example\n" + example;
}
export function menuText() {
  return "MART | Research & Marketing Studio\n\nChoose a tool for its guide and a worked example.\n\nResearch a claim → compare ideas → draft a campaign.\nFor creative work, try /contentlab or /prompt. For the usage guide, type /metrics.\n\nThis staging menu shows guidance. Use the Python service to run a command.";
}
const help = "MART staging command guide\n\n" + [...guides]
  .map(([key, [title]]) => "/" + key + " — " + title).join("\n")
  + "\n\n/menu — main menu\n/status — service scope\n/help — this list";
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
  let key;
  if (callback) {
    if (typeof callback.id !== "string" || !callback.id) return null;
    key = typeof callback.data === "string" ? callback.data.replace(/^action:/, "") : "";
  } else {
    if (typeof message?.text !== "string") return null;
    key = message.text.trim().split(/\s+/, 1)[0].split("@", 1)[0].toLowerCase();
    key = key.startsWith("/") ? key.slice(1) : "";
  }
  let text = guideText(aliases.has(key) ? "metrics" : key);
  if (key === "menu" || key === "start") text = menuText();
  if (key === "status") text = statusText;
  if (key === "help") text = help;
  return {chatId, text:text ?? (callback ? menuText() : help), ...(callback && {callbackId:callback.id})};
}
async function telegram(token,method,payload) {
  const r=await fetch("https://api.telegram.org/bot"+token+"/"+method,{
    method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(payload),
    signal:AbortSignal.timeout(method === "answerCallbackQuery" ? 3000 : 10000)
  });
  if (r.status === 429) {
    const error = new TelegramRateLimit();
    const body = await r.json().catch(() => ({}));
    const seconds = body?.parameters?.retry_after;
    error.retryAt = Number.isSafeInteger(seconds) && seconds > 0 ? Date.now() + seconds * 1000 : 0;
    throw error;
  }
  if(!r.ok) throw new Error("Telegram "+method+" HTTP "+r.status);
  const json=await r.json();
  if(json.ok!==true) throw new Error("Telegram "+method+" rejected request");
}
class TelegramRateLimit extends Error {}

// One object per bot and webhook update. The saved payload wins on replay.
export class StartJob {
  constructor(ctx, env) {
    this.storage = ctx.storage;
    this.env = env;
    this.storage.sql.exec(`CREATE TABLE IF NOT EXISTS job (
      id INTEGER PRIMARY KEY CHECK (id = 1), status TEXT NOT NULL, payload TEXT
    )`);
    this.storage.sql.exec("CREATE TABLE IF NOT EXISTS backoff (retry_at INTEGER NOT NULL)");
  }

  async fetch(request) {
    const payload = await request.text();
    if (!this.active) {
      this.active = this.deliver(payload).finally(() => { this.active = undefined; });
    }
    const status = await this.active;
    return response(status === 200 ? {ok:true} : {error:"delivery_unconfirmed"}, status);
  }

  async deliver(payload) {
    const sql = this.storage.sql;
    sql.exec("INSERT OR IGNORE INTO job VALUES (1, 'pending', ?)", payload);
    await this.storage.sync();
    const [job] = sql.exec("SELECT status, payload FROM job WHERE id=1").toArray();
    if (job.status === "done") return 200;
    // A previous process may have sent this message before losing the receipt.
    if (job.status === "sending") return 503;
    const [delay] = sql.exec("SELECT retry_at FROM backoff").toArray();
    if (delay && delay.retry_at > Date.now()) return 503;
    sql.exec("DELETE FROM backoff");
    sql.exec("UPDATE job SET status='sending' WHERE id=1");
    await this.storage.sync();
    try {
      const intent = JSON.parse(job.payload);
      if (intent.callbackId) {
        // An expired callback must not suppress the requested guide.
        await telegram(this.env.TELEGRAM_BOT_TOKEN, "answerCallbackQuery", {
          callback_query_id:intent.callbackId
        }).catch(() => {});
      }
      // Older /start jobs stored the Telegram payload directly.
      await telegram(this.env.TELEGRAM_BOT_TOKEN, "sendMessage", intent.message ?? intent);
    } catch (error) {
      if (error instanceof TelegramRateLimit) {
        if (error.retryAt) sql.exec("INSERT INTO backoff VALUES (?)", error.retryAt);
        sql.exec("UPDATE job SET status='pending' WHERE id=1");
        await this.storage.sync();
      }
      return 503;
    }
    sql.exec("UPDATE job SET status='done', payload=NULL WHERE id=1");
    await this.storage.sync();
    return 200;
  }
}

const MAX_BODY_BYTES=65536;
class InvalidUtf8Error extends Error {}
async function readBoundedBody(request){
  if(!request.body)return '';
  const reader=request.body.getReader();
  const chunks=[];
  let size=0;
  try{
    while(true){
      const {done,value}=await reader.read();
      if(done)break;
      size+=value.byteLength;
      if(size>MAX_BODY_BYTES){
        await reader.cancel().catch(()=>{});
        return null;
      }
      chunks.push(value);
    }
  }finally{reader.releaseLock()}
  const buffer=new Uint8Array(size);
  let offset=0;
  for(const chunk of chunks){buffer.set(chunk,offset);offset+=chunk.byteLength}
  try{return new TextDecoder('utf-8',{fatal:true}).decode(buffer)}catch{throw new InvalidUtf8Error()}
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
    if(request.headers.get("content-type")?.split(";",1)[0].trim().toLowerCase() !== "application/json")
      return response({error:"unsupported_media_type"},415);
  const declared=request.headers.get("content-length");
  if(declared!==null && (!/^\d+$/.test(declared) || !Number.isSafeInteger(Number(declared))))return response({error:"invalid_content_length"},400);
  if(declared!==null && Number(declared)>MAX_BODY_BYTES)return response({error:"too_large"},413);
  let body;
  try{body=await readBoundedBody(request)}catch(error){return error instanceof InvalidUtf8Error?response({error:"invalid_json"},400):response({error:"body_unavailable"},503)}
  if(body===null)return response({error:"too_large"},413);
  let update;
  try{update=JSON.parse(body)}catch{return response({error:"invalid_json"},400)}

    if(!update||!Number.isSafeInteger(update.update_id)||update.update_id<0) return response({error:"invalid_update_id"},400);
    const reply=render(update);
    if(!reply) return response({ok:true,handled:false});
    // Default is preview-only: never send messages or acknowledge callbacks.
    if(env.STAGING_ENABLE_DELIVERY!=="true") return response({ok:true,preview:true,command:reply.text.slice(0,100),text:reply.text,reply_markup:keyboard()});
    if(!env.TELEGRAM_BOT_TOKEN) return response({error:"missing_token"},503);
    try {
      if (!env.START_JOBS) return response({error:"missing_job_store"},503);
      const botId = env.TELEGRAM_BOT_TOKEN.split(":",1)[0];
      const id = env.START_JOBS.idFromName(botId + ":" + update.update_id);
      const message = {chat_id:reply.chatId,text:reply.text,reply_markup:keyboard(),disable_web_page_preview:true};
      return await env.START_JOBS.get(id).fetch("https://job/deliver", {
        method:"POST", body:JSON.stringify({message,callbackId:reply.callbackId})
      });
    } catch {return response({error:"delivery_failed"},502);}
  }
};

import test from "node:test";
import assert from "node:assert/strict";
import worker,{COMMANDS,keyboard,render} from "./mart-staging-worker.mjs";
const env={TELEGRAM_WEBHOOK_SECRET:"test-secret",STAGING_ENABLE_DELIVERY:"false"};
const req=(payload,secret="test-secret",path="/telegram/webhook")=>new Request("https://staging.example"+path,{method:"POST",headers:{"content-type":"application/json","X-Telegram-Bot-Api-Secret-Token":secret},body:JSON.stringify(payload)});
test("15 commands and 13 inline buttons",()=>{assert.equal(COMMANDS.length,15);assert.equal(new Set(COMMANDS).size,15);assert.equal(keyboard().inline_keyboard.flat().length,13);});
test("start preview never calls Telegram",async()=>{const r=await worker.fetch(req({update_id:1,message:{chat:{id:123},text:"/start"}}),env);assert.equal(r.status,200);assert.equal((await r.json()).preview,true);});
test("callback preview",async()=>{const r=await worker.fetch(req({update_id:2,callback_query:{id:"abc",data:"action:research",message:{chat:{id:123}}}}),env);assert.equal((await r.json()).preview,true);});
test("wrong secret",async()=>{assert.equal((await worker.fetch(req({update_id:3},"bad"),env)).status,403);});
test("missing secret configuration fails closed",async()=>{assert.equal((await worker.fetch(req({update_id:3}),{STAGING_ENABLE_DELIVERY:"false"})).status,403);});
test("missing update id",async()=>{assert.equal((await worker.fetch(req({message:{chat:{id:123},text:"/start"}}),env)).status,400);});
test("invalid payload",async()=>{assert.equal((await worker.fetch(req({update_id:"5"}),env)).status,400);});
test("unknown path",async()=>{assert.equal((await worker.fetch(req({update_id:1},undefined,"/unknown"),env)).status,404);});
test("non-text update ignored",async()=>{const r=await worker.fetch(req({update_id:4,message:{chat:{id:123}}}),env);assert.equal((await r.json()).handled,false);});
test("staging never creates campaigns",()=>{assert.match(render({message:{chat:{id:123},text:"/campaign x"}}).text,/Python service/);});
test("delivery requires token",async()=>{const r=await worker.fetch(req({update_id:5,message:{chat:{id:123},text:"/start"}}),{...env,STAGING_ENABLE_DELIVERY:"true"});assert.equal(r.status,503);});

test("every tool button and typed command give the same actionable guide", () => {
  for (const button of keyboard().inline_keyboard.flat().filter(b => b.callback_data.startsWith("action:"))) {
    const key = button.callback_data.slice(7);
    const typed = render({message:{chat:{id:42},text:"/" + key + "@mart_aigenticbot"}});
    const tapped = render({callback_query:{id:"cb",data:button.callback_data,message:{chat:{id:42}}}});
    assert.equal(tapped.text, typed.text);
    assert.ok(tapped.text.includes("/" + key));
    assert.equal(tapped.callbackId, "cb");
  }
  for (const key of ["contentlab","prompt","metrics","campaignstatus"]) {
    assert.ok(render({message:{chat:{id:42},text:"/"+key}}).text.includes("Python service example"));
  }
  assert.equal(render({message:{chat:{id:42},text:"/quality"}}).text, render({message:{chat:{id:42},text:"/metrics"}}).text);
});
test("rejects oversized bodies, invalid UTF-8 and lookalike media types", async () => {
  const send = (body, type) => worker.fetch(new Request("https://fixture/telegram/webhook", {
    method:"POST",headers:{"content-type":type,"X-Telegram-Bot-Api-Secret-Token":"test-secret"},body
  }),env);
  assert.equal((await send(" ".repeat(65537),"application/json")).status,413);
  assert.equal((await send(new Uint8Array([255]),"application/json")).status,400);
  assert.equal((await send("{}","application/json-extra")).status,415);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../mart-webhook.js';

function env() {
 const rows=new Map();
 return {TELEGRAM_WEBHOOK_SECRET:'secret',MART_DB:{
  prepare(sql){return {bind(id,payload){return {async run(){if(!rows.has(id))rows.set(id,payload);return {success:true}}}}}}
 },rows};
}
function req(update,secret='secret'){return new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':secret},body:JSON.stringify(update)})}
test('accepts valid update once, acknowledges duplicate',async()=>{
 const e=env();assert.equal((await worker.fetch(req({update_id:7}),e)).status,200);
 assert.equal((await worker.fetch(req({update_id:7}),e)).status,200);
 assert.equal(e.rows.size,1);
});
test('rejects bad secret without storing',async()=>{
 const e=env();assert.equal((await worker.fetch(req({update_id:8},'wrong'),e)).status,403);assert.equal(e.rows.size,0);
});
test('rejects invalid update id',async()=>{
 const e=env();assert.equal((await worker.fetch(req({update_id:'8'}),e)).status,400);
});
test('storage errors return retryable 503',async()=>{
 const e=env();e.MART_DB.prepare=()=>{throw Error('offline')};
 assert.equal((await worker.fetch(req({update_id:9}),e)).status,503);
});

test('oversized streamed body is rejected before reading additional chunks',async()=>{
 const e=env();let pulls=0,canceled=false;
 const stream=new ReadableStream({pull(controller){pulls++;if(pulls===1)controller.enqueue(new Uint8Array(65537));else throw Error('oversized body should not be drained')},cancel(){canceled=true}});
 const request=new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'secret'},body:stream,duplex:'half'});
 const response=await worker.fetch(request,e);
 assert.equal(response.status,413);assert.equal(pulls,1);assert.equal(canceled,true);assert.equal(e.rows.size,0);
});
test('stream read failures are retryable and do not store updates',async()=>{
 const e=env();
 const stream=new ReadableStream({pull(){throw Error('temporary stream failure')}});
 const request=new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'secret'},body:stream,duplex:'half'});
 const response=await worker.fetch(request,e);
 assert.equal(response.status,503);assert.equal(e.rows.size,0);
});
test('exact limit body is processed, invalid JSON remains non-retryable',async()=>{
 const e=env();const body=JSON.stringify({update_id:11,extra:'x'.repeat(65536-27)});
 assert.equal(new TextEncoder().encode(body).length,65536);
 const request=new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'secret'},body});
 const response=await worker.fetch(request,e);
 assert.equal(response.status,200);
 assert.equal((await worker.fetch(new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'secret'},body:'{'}),e)).status,400);
});
test('invalid UTF-8 is rejected without retry or D1 write',async()=>{
 const e=env();
 const stream=new ReadableStream({start(controller){controller.enqueue(new Uint8Array([0xc3,0x28]));controller.close()}});
 const request=new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'secret'},body:stream,duplex:'half'});
 assert.equal((await worker.fetch(request,e)).status,400);assert.equal(e.rows.size,0);
});

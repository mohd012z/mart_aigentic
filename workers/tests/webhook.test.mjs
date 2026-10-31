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

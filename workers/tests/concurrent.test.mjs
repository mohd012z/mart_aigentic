import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../mart-webhook.js';
test('parallel duplicate ingress produces one durable record',async()=>{
 const rows=new Map();
 const env={TELEGRAM_WEBHOOK_SECRET:'secret',MART_DB:{prepare(){return{bind(id,payload){return{async run(){if(!rows.has(id))rows.set(id,payload);return{success:true}}}}}}}};
 const request=()=>new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'secret'},body:JSON.stringify({update_id:902})});
 const responses=await Promise.all(Array.from({length:25},()=>worker.fetch(request(),env)));
 assert.ok(responses.every(r=>r.status===200));assert.equal(rows.size,1);
});
test('unauthorized concurrent requests cannot insert',async()=>{
 const rows=new Map();
 const env={TELEGRAM_WEBHOOK_SECRET:'secret',MART_DB:{prepare(){throw Error('must not touch DB')}}};
 const requests=Array.from({length:10},()=>worker.fetch(new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'wrong'},body:'{"update_id":12}'}),env));
 const responses=await Promise.all(requests);
 assert.ok(responses.every(r=>r.status===403));assert.equal(rows.size,0);
});

test('D1 unsuccessful result must return retryable 503',async()=>{
 const env={TELEGRAM_WEBHOOK_SECRET:'secret',MART_DB:{prepare(){return{bind(){return{async run(){return{success:false}}}}}}}};
 const response=await worker.fetch(new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'secret'},body:JSON.stringify({update_id:904})}),env);
 assert.equal(response.status,503);
});
test('oversized body rejected without D1 access',async()=>{
 const env={TELEGRAM_WEBHOOK_SECRET:'secret',MART_DB:{prepare(){throw Error('D1 accessed')}}};
 const response=await worker.fetch(new Request('https://example.test/telegram/webhook',{method:'POST',headers:{'X-Telegram-Bot-Api-Secret-Token':'secret'},body:'x'.repeat(65537)}),env);
 assert.equal(response.status,413);
});

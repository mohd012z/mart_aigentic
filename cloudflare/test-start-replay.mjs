import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as adapter from "./mart-staging-worker.mjs";

test("a saved /start survives restart and concurrent webhook replay", async t => {
  const dir = mkdtempSync(join(tmpdir(), "mart-start-"));
  let db, object, stopAfterCommit = true;
  const calls = [];
  const env = {
    TELEGRAM_WEBHOOK_SECRET: "fixture", TELEGRAM_BOT_TOKEN: "123:fixture",
    STAGING_ENABLE_DELIVERY: "true",
    START_JOBS: {
      idFromName: name => name,
      get(name) {
        assert.equal(name, "123:7001");
        if (!object) {
          db = new DatabaseSync(join(dir, "store.sqlite"));
          const storage = {
            sql: { exec: (sql, ...args) => {
              const rows = db.prepare(sql).all(...args);
              return { toArray: () => rows };
            } },
            async sync() {
              if (stopAfterCommit) {
                stopAfterCommit = false;
                throw new Error("simulated restart after intent commit");
              }
            }
          };
          object = new adapter.StartJob({storage}, env);
        }
        return {fetch: (url, init) => object.fetch(new Request(url, init))};
      }
    }
  };
  t.after(() => { db?.close(); rmSync(dir, {recursive:true, force:true}); });
  t.mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(new URL(url).pathname, "/bot123:fixture/sendMessage");
    calls.push(JSON.parse(init.body));
    return Response.json({ok:true});
  });
  const deliver = () => adapter.default.fetch(new Request("https://fixture/telegram/webhook", {
    method:"POST", headers:{"content-type":"application/json","X-Telegram-Bot-Api-Secret-Token":"fixture"},
    body: JSON.stringify({update_id:7001,message:{chat:{id:42},text:"/start"}})
  }), env);
  assert.ok((await deliver()).status >= 500);
  assert.equal(calls.length, 0);
  assert.equal(db.prepare("SELECT status FROM job").get().status, "pending");
  db.close(); db = undefined; object = undefined;
  const replies = await Promise.all([deliver(), deliver()]);
  assert.deepEqual(replies.map(r => r.status), [200, 200]);
  assert.equal((await deliver()).status, 200);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].chat_id, 42);
  assert.equal(calls[0].text, adapter.menuText());
  assert.deepEqual(calls[0].reply_markup, adapter.keyboard());
  assert.deepEqual(db.prepare("SELECT status FROM job").all().map(row => row.status), ["done"]);
});

test("expired callback, rate limit and uncertain receipt survive job recreation", async t => {
  const db = new DatabaseSync(":memory:");
  t.after(() => db.close());
  const storage = {sql:{exec(query,...args) {
    const rows = db.prepare(query).all(...args);
    return {toArray:() => rows};
  }},async sync() {}};
  const methods = [];
  let now = 100000;
  t.mock.method(Date, "now", () => now);
  let sends = 0;
  t.mock.method(globalThis, "fetch", async url => {
    const method = new URL(url).pathname.split("/").pop();
    methods.push(method);
    if (method === "answerCallbackQuery") return Response.json({ok:false},{status:400});
    if (++sends === 1) return Response.json({parameters:{retry_after:10}},{status:429});
    throw new Error("lost receipt");
  });
  const env = {TELEGRAM_BOT_TOKEN:"123:fixture",TELEGRAM_WEBHOOK_SECRET:"test",STAGING_ENABLE_DELIVERY:"true",
    START_JOBS:{idFromName:name=>name,get(name) {
      assert.equal(name,"123:7");
      const job = new adapter.StartJob({storage},env);
      return {fetch:(url,init)=>job.fetch(new Request(url,init))};
    }}};
  const replay = () => adapter.default.fetch(new Request("https://fixture/telegram/webhook", {
    method:"POST", headers:{"content-type":"application/json","X-Telegram-Bot-Api-Secret-Token":"test"},
    body:JSON.stringify({update_id:7,callback_query:{id:"cb",data:"action:research",message:{chat:{id:42}}}})
  }),env);
  assert.equal((await replay()).status,503);
  now += 9999;
  assert.equal((await replay()).status,503);
  assert.equal(sends,1);
  now += 1;
  assert.equal((await replay()).status,503);
  assert.equal((await replay()).status,503);
  assert.deepEqual(methods,["answerCallbackQuery","sendMessage","answerCallbackQuery","sendMessage"]);
});

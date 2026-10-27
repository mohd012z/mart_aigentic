"""Durable, provider-neutral agent execution receipts. No secrets or prompt bodies stored."""
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager

DB_PATH = os.getenv("MART_METRICS_DB", "mart_metrics.sqlite3")

@contextmanager
def connect(path=None):
    db = sqlite3.connect(path or DB_PATH, timeout=10)
    try:
        db.execute("PRAGMA busy_timeout=10000")
        yield db
        db.commit()
    finally:
        db.close()

def initialize(path=None):
    with connect(path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS receipts(
            id TEXT PRIMARY KEY, created_at INTEGER NOT NULL,
            agent TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
            status TEXT NOT NULL, latency_ms INTEGER NOT NULL,
            input_tokens INTEGER, output_tokens INTEGER,
            cost_usd REAL, pricing_state TEXT NOT NULL,
            source_count INTEGER NOT NULL, error_type TEXT NOT NULL)""")

def record(agent, provider="none", model="none", status="ok", latency_ms=0,
           input_tokens=None, output_tokens=None, cost_usd=None,
           source_count=0, error_type="", path=None):
    if status not in ("ok", "failed", "timeout", "empty"):
        raise ValueError("invalid status")
    if cost_usd is not None and cost_usd < 0:
        raise ValueError("negative cost")
    initialize(path)
    receipt_id = str(uuid.uuid4())
    pricing_state = "unknown" if cost_usd is None else "reported_or_estimated"
    with connect(path) as db:
        db.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (receipt_id,int(time.time()),agent,provider,model,status,
             max(0,int(latency_ms)),input_tokens,output_tokens,cost_usd,
             pricing_state,max(0,int(source_count)),error_type[:100]))
    return receipt_id

def summary(path=None):
    initialize(path)
    with connect(path) as db:
        row=db.execute("""SELECT COUNT(*), SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status!='ok' THEN 1 ELSE 0 END),
            AVG(latency_ms), SUM(COALESCE(cost_usd,0)),
            SUM(CASE WHEN cost_usd IS NULL THEN 1 ELSE 0 END)
            FROM receipts""").fetchone()
    return {"calls":row[0],"success":row[1] or 0,"failures":row[2] or 0,
            "avg_latency_ms":round(row[3] or 0),"known_cost_usd":round(row[4] or 0,6),
            "unknown_cost_calls":row[5] or 0}

def report(path=None):
    s=summary(path)
    return (f"MART Agent Metrics\nCalls: {s['calls']}\nSuccess: {s['success']}\n"
            f"Failures: {s['failures']}\nMean latency: {s['avg_latency_ms']} ms\n"
            f"Known recorded cost: USD {s['known_cost_usd']:.6f}\n"
            f"Unknown-cost calls: {s['unknown_cost_calls']}\n"
            "Unknown cost is not treated as free. Figures cover MART-instrumented calls only.")

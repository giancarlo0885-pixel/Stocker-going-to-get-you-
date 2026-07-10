from __future__ import annotations
import math, os, sqlite3, threading, time
from contextlib import contextmanager
from datetime import datetime, time as dtime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from market_data import load_history
from news_intelligence import combined_regime

APP_VERSION = "2.0.0"
DB_PATH = Path(os.getenv("PAPER_DB_PATH","paper_trading.db"))
STARTING_CASH = float(os.getenv("PAPER_STARTING_CASH","10"))
SCAN_SECONDS = max(60, int(os.getenv("BOT_SCAN_SECONDS","300")))
MIN_TRADE_USD = max(0.10, float(os.getenv("MIN_TRADE_USD","0.50")))
MAX_POSITION_PCT = min(0.50, max(0.05, float(os.getenv("MAX_POSITION_PCT","0.30"))))
MAX_OPEN_POSITIONS = max(1, int(os.getenv("MAX_OPEN_POSITIONS","4")))
STOP_LOSS_PCT = min(0.25, max(0.01, float(os.getenv("STOP_LOSS_PCT","0.05"))))
TAKE_PROFIT_PCT = min(1.0, max(0.01, float(os.getenv("TAKE_PROFIT_PCT","0.10"))))
TRAILING_STOP_PCT = min(0.25, max(0.01, float(os.getenv("TRAILING_STOP_PCT","0.04"))))
SLIPPAGE_BPS = max(0.0, float(os.getenv("SLIPPAGE_BPS","5")))
CASH_SYMBOLS = tuple(s.strip().upper() for s in os.getenv("CASH_SYMBOLS","AAPL,NVDA,TSLA,RKLB,GLW,PLTR,SOFI,SPY,QQQ,UUP,GLD,TLT,EURUSD=X,JPY=X").split(",") if s.strip())
CRYPTO_SYMBOLS = tuple(s.strip().upper() for s in os.getenv("CRYPTO_SYMBOLS","BTC-USD,ETH-USD,SOL-USD,XRP-USD,DOGE-USD").split(",") if s.strip())
_LOCK = threading.RLock()
_BOT_THREAD = None

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        try:
            yield c
            c.commit()
        finally:
            c.close()

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS accounts(board TEXT PRIMARY KEY,starting_cash REAL NOT NULL,cash REAL NOT NULL,peak_equity REAL NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS positions(board TEXT NOT NULL,symbol TEXT NOT NULL,quantity REAL NOT NULL,avg_price REAL NOT NULL,last_price REAL NOT NULL,high_water REAL NOT NULL,opened_at TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(board,symbol));
        CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL,board TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,quantity REAL NOT NULL,price REAL NOT NULL,gross_value REAL NOT NULL,confidence REAL NOT NULL,reason TEXT NOT NULL,data_source TEXT,regime TEXT);
        CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL,board TEXT NOT NULL,symbol TEXT NOT NULL,price REAL,score REAL NOT NULL,confidence REAL NOT NULL,action TEXT NOT NULL,reason TEXT NOT NULL,data_source TEXT,regime TEXT);
        CREATE TABLE IF NOT EXISTS equity_history(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL,board TEXT NOT NULL,equity REAL NOT NULL,cash REAL NOT NULL,positions_value REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS bot_status(board TEXT PRIMARY KEY,enabled INTEGER NOT NULL DEFAULT 1,last_scan TEXT,last_error TEXT,updated_at TEXT NOT NULL);
        """)
        n = now_iso()
        for b in ("cash","crypto"):
            c.execute("INSERT OR IGNORE INTO accounts VALUES(?,?,?,?,?,?)",(b,STARTING_CASH,STARTING_CASH,STARTING_CASH,n,n))
            c.execute("INSERT OR IGNORE INTO bot_status(board,enabled,updated_at) VALUES(?,1,?)",(b,n))

def market_open_cash():
    e = datetime.now(timezone.utc).astimezone(ZoneInfo("America/New_York"))
    return e.weekday() < 5 and dtime(9,30) <= e.time().replace(tzinfo=None) <= dtime(16,0)

def compute_signal(f, reg):
    cl = f["Close"].dropna()
    if len(cl) < 35:
        return {"price":math.nan,"score":0.0,"confidence":0.0,"action":"HOLD","reason":"Insufficient history."}
    p=float(cl.iloc[-1]); e8=float(cl.ewm(span=8,adjust=False).mean().iloc[-1]); e21=float(cl.ewm(span=21,adjust=False).mean().iloc[-1]); e55=float(cl.ewm(span=55,adjust=False).mean().iloc[-1])
    d=cl.diff(); g=d.clip(lower=0).rolling(14).mean(); l=(-d.clip(upper=0)).rolling(14).mean(); rsi=float((100-100/(1+g/l.replace(0,np.nan))).iloc[-1]); rsi=50 if not np.isfinite(rsi) else rsi
    mom=float(cl.pct_change(8).iloc[-1]); vol=float(cl.pct_change().rolling(30).std().iloc[-1]); vol=0 if not np.isfinite(vol) else vol
    score=.38*np.clip((e8/e21-1)*100,-1,1)+.28*np.clip((e21/e55-1)*70,-1,1)+.24*np.clip(mom*24,-1,1)+.10*np.clip((55-rsi)/35,-1,1)+.14*reg
    risk=np.clip(vol*8,0,.45); score=float(np.clip(score-risk if score>0 else score+risk,-1,1)); conf=float(np.clip(abs(score)*100+min(15,abs(mom)*500),0,99))
    action="BUY" if score>=.27 and e8>e21 and rsi<74 else ("SELL" if score<=-.23 or (e8<e21 and rsi>58) else "HOLD")
    reason=f"EMA8 {e8:.4f} vs EMA21 {e21:.4f}; EMA55 {e55:.4f}; RSI {rsi:.1f}; momentum {mom:.2%}; volatility {vol:.2%}; news {reg:+.2f}."
    return {"price":p,"score":score,"confidence":conf,"action":action,"reason":reason}

def account_snapshot(b):
    with connect() as c:
        a=c.execute("SELECT * FROM accounts WHERE board=?",(b,)).fetchone(); ps=c.execute("SELECT * FROM positions WHERE board=?",(b,)).fetchall()
    cash=float(a["cash"]); pv=sum(float(p["quantity"])*float(p["last_price"]) for p in ps); eq=cash+pv; start=float(a["starting_cash"]); peak=max(float(a["peak_equity"]),eq)
    return {"starting_cash":start,"cash":cash,"positions_value":pv,"equity":eq,"pnl":eq-start,"return_pct":(eq/start-1)*100 if start else 0,"drawdown_pct":(eq/peak-1)*100 if peak else 0}

def update_equity(b):
    s=account_snapshot(b)
    with connect() as c:
        c.execute("UPDATE accounts SET peak_equity=?,updated_at=? WHERE board=?",(max(s["equity"],s["starting_cash"]),now_iso(),b))
        c.execute("INSERT INTO equity_history(timestamp,board,equity,cash,positions_value) VALUES(?,?,?,?,?)",(now_iso(),b,s["equity"],s["cash"],s["positions_value"]))

def execute_trade(b,sym,side,price,conf,reason,source,regime):
    if not np.isfinite(price) or price<=0: return False
    fill=price*(1+SLIPPAGE_BPS/10000 if side=="BUY" else 1-SLIPPAGE_BPS/10000); n=now_iso()
    with connect() as c:
        a=c.execute("SELECT * FROM accounts WHERE board=?",(b,)).fetchone(); p=c.execute("SELECT * FROM positions WHERE board=? AND symbol=?",(b,sym)).fetchone(); cash=float(a["cash"]); allp=c.execute("SELECT quantity,last_price FROM positions WHERE board=?",(b,)).fetchall(); eq=cash+sum(float(x["quantity"])*float(x["last_price"]) for x in allp)
        if side=="BUY":
            if p is None and len(allp)>=MAX_OPEN_POSITIONS: return False
            cur=0 if p is None else float(p["quantity"])*fill; target=eq*MAX_POSITION_PCT*max(.35,min(1,conf/75)); budget=min(max(0,target-cur),cash*.95)
            if budget<MIN_TRADE_USD: return False
            qty=budget/fill; oq=0 if p is None else float(p["quantity"]); oa=0 if p is None else float(p["avg_price"]); nq=oq+qty; na=((oq*oa)+(qty*fill))/nq
            c.execute("INSERT INTO positions VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(board,symbol) DO UPDATE SET quantity=excluded.quantity,avg_price=excluded.avg_price,last_price=excluded.last_price,high_water=MAX(positions.high_water,excluded.high_water),updated_at=excluded.updated_at",(b,sym,nq,na,fill,fill,n,n)); c.execute("UPDATE accounts SET cash=?,updated_at=? WHERE board=?",(cash-budget,n,b)); gross=budget
        elif side=="SELL":
            if p is None: return False
            qty=float(p["quantity"]); gross=qty*fill; c.execute("DELETE FROM positions WHERE board=? AND symbol=?",(b,sym)); c.execute("UPDATE accounts SET cash=?,updated_at=? WHERE board=?",(cash+gross,n,b))
        else: return False
        c.execute("INSERT INTO trades(timestamp,board,symbol,side,quantity,price,gross_value,confidence,reason,data_source,regime) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(n,b,sym,side,qty,fill,gross,conf,reason,source,regime))
        return True

def scan_board(b):
    reg=combined_regime(b); syms=CASH_SYMBOLS if b=="cash" else CRYPTO_SYMBOLS
    if b=="cash" and not market_open_cash():
        with connect() as c: c.execute("UPDATE bot_status SET last_scan=?,last_error=?,updated_at=? WHERE board=?",(now_iso(),"Cash market closed; no simulated fills.",now_iso(),b))
        return
    errs=[]
    for sym in syms:
        try:
            f,src=load_history(sym,b)
            if f.empty: errs.append(sym+": no data"); continue
            r=compute_signal(f,reg.score); price=float(r["price"]); score=float(r["score"]); conf=float(r["confidence"]); action=str(r["action"]); reason=str(r["reason"])
            with connect() as c:
                c.execute("UPDATE positions SET last_price=?,high_water=MAX(high_water,?),updated_at=? WHERE board=? AND symbol=?",(price,price,now_iso(),b,sym)); p=c.execute("SELECT * FROM positions WHERE board=? AND symbol=?",(b,sym)).fetchone()
            if p is not None:
                avg=float(p["avg_price"]); high=max(float(p["high_water"]),price); chg=price/avg-1; trail=price/high-1
                if chg<=-STOP_LOSS_PCT: action="SELL"; conf=max(conf,90); reason=f"Stop loss {chg:.2%}. "+reason
                elif chg>=TAKE_PROFIT_PCT: action="SELL"; conf=max(conf,85); reason=f"Take profit {chg:.2%}. "+reason
                elif trail<=-TRAILING_STOP_PCT and chg>0: action="SELL"; conf=max(conf,82); reason=f"Trailing stop {trail:.2%}. "+reason
            with connect() as c: c.execute("INSERT INTO signals(timestamp,board,symbol,price,score,confidence,action,reason,data_source,regime) VALUES(?,?,?,?,?,?,?,?,?,?)",(now_iso(),b,sym,price,score,conf,action,reason,src,reg.label))
            if action in ("BUY","SELL"): execute_trade(b,sym,action,price,conf,reason,src,reg.label)
        except Exception as exc: errs.append(sym+": "+type(exc).__name__)
    update_equity(b)
    with connect() as c: c.execute("UPDATE bot_status SET last_scan=?,last_error=?,updated_at=? WHERE board=?",(now_iso()," | ".join(errs[:6]) if errs else None,now_iso(),b))

def enabled(b):
    with connect() as c:
        r=c.execute("SELECT enabled FROM bot_status WHERE board=?",(b,)).fetchone(); return bool(r and r["enabled"])
def set_enabled(b,v):
    with connect() as c: c.execute("UPDATE bot_status SET enabled=?,updated_at=? WHERE board=?",(1 if v else 0,now_iso(),b))
def reset_board(b):
    with connect() as c:
        n=now_iso(); c.execute("DELETE FROM positions WHERE board=?",(b,)); c.execute("DELETE FROM trades WHERE board=?",(b,)); c.execute("DELETE FROM signals WHERE board=?",(b,)); c.execute("DELETE FROM equity_history WHERE board=?",(b,)); c.execute("UPDATE accounts SET cash=?,starting_cash=?,peak_equity=?,updated_at=? WHERE board=?",(STARTING_CASH,STARTING_CASH,STARTING_CASH,n,b))
def read_df(q,p=()):
    with connect() as c: return pd.read_sql_query(q,c,params=p)
def positions_df(b): return read_df("SELECT symbol,quantity,avg_price,last_price,quantity*last_price AS market_value,quantity*(last_price-avg_price) AS unrealized_pnl,CASE WHEN avg_price>0 THEN (last_price/avg_price-1)*100 ELSE 0 END AS return_pct,updated_at FROM positions WHERE board=? ORDER BY market_value DESC",(b,))
def trades_df(b,limit=250): return read_df("SELECT timestamp,symbol,side,quantity,price,gross_value,confidence,regime,reason,data_source FROM trades WHERE board=? ORDER BY id DESC LIMIT ?",(b,limit))
def signals_df(b,limit=250): return read_df("SELECT timestamp,symbol,price,score,confidence,action,regime,reason,data_source FROM signals WHERE board=? ORDER BY id DESC LIMIT ?",(b,limit))
def equity_df(b,limit=1000): return read_df("SELECT timestamp,equity,cash,positions_value FROM equity_history WHERE board=? ORDER BY id ASC LIMIT ?",(b,limit))
def status_df(): return read_df("SELECT * FROM bot_status ORDER BY board")
def run_once():
    init_db()
    for b in ("crypto","cash"):
        if enabled(b): scan_board(b)
def bot_loop():
    init_db()
    while True:
        started=time.monotonic()
        for b in ("crypto","cash"):
            if enabled(b):
                try: scan_board(b)
                except Exception as exc:
                    with connect() as c: c.execute("UPDATE bot_status SET last_error=?,updated_at=? WHERE board=?",(type(exc).__name__+": "+str(exc)[:200],now_iso(),b))
        time.sleep(max(5,SCAN_SECONDS-(time.monotonic()-started)))
def start_background_bot():
    global _BOT_THREAD
    init_db()
    if _BOT_THREAD is None or not _BOT_THREAD.is_alive():
        _BOT_THREAD=threading.Thread(target=bot_loop,daemon=True,name="oracle-v2-bot"); _BOT_THREAD.start()
    return _BOT_THREAD

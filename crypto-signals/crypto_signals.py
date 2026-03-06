#!/usr/bin/env python3
"""MoltStreet Crypto Early-Detection Scanner v2.0
Runs daily via GitHub Actions. Zero external dependencies.
Data: CoinGecko API + DeFiLlama API
"""
import urllib.request, json, time, datetime, smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

WATCHLIST = [
    ("hyperliquid",             "HYPE",   "perp-dex",   "Dominant perp DEX, real revenue, bear-resilient"),
    ("bittensor",               "TAO",    "ai",         "AI compute marketplace, subnet growth, -75% ATH"),
    ("ondo-finance",            "ONDO",   "rwa",        "RWA leader, BlackRock ties, institutional push"),
    ("jupiter-exchange-solana", "JUP",    "dex",        "Solana #1 DEX aggregator, -91% ATH deep value"),
    ("ethena",                  "ENA",    "stablecoin", "USDe yield stablecoin, -93% ATH oversold"),
    ("pendle",                  "PENDLE", "yield",      "Yield tokenization pioneer, DeFi primitive"),
    ("berachain-bera",          "BERA",   "l1",         "Novel PoL consensus, strong DeFi ecosystem"),
    ("kaito",                   "KAITO",  "ai-social",  "AI info marketplace, small cap, early momentum"),
    ("starknet",                "STRK",   "l2",         "ZK rollup L2, Ethereum scaling, -99% ATH"),
    ("eigenlayer",              "EIGEN",  "restaking",  "Restaking pioneer, ETH security layer"),
    ("worldcoin-wld",           "WLD",    "identity",   "Global ID + UBI, Sam Altman, -97% ATH"),
    ("sonic-3",                 "S",      "l1",         "High-perf EVM L1, DeFi ecosystem rebuilding"),
]
EMAIL_FROM   = "italiamolt5@gmail.com"
EMAIL_TO     = "italiamolt5@gmail.com"
EMAIL_APP_PW = os.environ.get("MAIL_APPPASSWORD", "")

def fetch_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"MoltStreet/2.0","accept":"application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if i < retries - 1: time.sleep(2**i)
            else: print(f"  [WARN] {url[:60]}: {e}"); return None

def get_coin_data(ids_list):
    ids = ",".join(ids_list)
    url = (f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}"
           f"&order=market_cap_desc&per_page=50&page=1&sparkline=false"
           f"&price_change_percentage=7d,30d")
    data = fetch_json(url)
    return {c["id"]: c for c in data} if data else {}

def get_defi_tvl():
    data = fetch_json("https://api.llama.fi/protocols")
    if not data: return {}
    out = {}
    for p in data:
        sym = (p.get("symbol") or "").upper()
        if sym:
            out[sym] = {"tvl": p.get("tvl",0) or 0, "tvl_7d": p.get("change_7d",0) or 0}
    return out

def score_coin(cd, tvl_data):
    score = 50.0; signals = []
    p24  = cd.get("price_change_percentage_24h",0) or 0
    p7   = cd.get("price_change_percentage_7d_in_currency",0) or 0
    p30  = cd.get("price_change_percentage_30d_in_currency",0) or 0
    ath  = cd.get("ath_change_percentage",0) or 0
    vol  = cd.get("total_volume",1) or 1
    mc   = cd.get("market_cap",1) or 1
    sym  = (cd.get("symbol") or "").upper()
    if p24>10: score+=12; signals.append(f"24h+{p24:.0f}%")
    elif p24>5: score+=7; signals.append(f"24h+{p24:.0f}%")
    elif p24<-10: score-=12
    elif p24<-5: score-=7
    if p7>20: score+=22; signals.append(f"7d+{p7:.0f}%")
    elif p7>10: score+=14; signals.append(f"7d+{p7:.0f}%")
    elif p7>5: score+=7
    elif p7<-20: score-=20; signals.append(f"7d{p7:.0f}%")
    elif p7<-10: score-=12
    elif p7<-5: score-=6
    if p30>30: score+=14; signals.append(f"30d+{p30:.0f}%")
    elif p30>15: score+=8
    elif p30>5: score+=4
    elif p30<-30: score-=14
    elif p30<-15: score-=8
    if ath<-90: score+=18; signals.append(f"ATH-{abs(ath):.0f}%")
    elif ath<-75: score+=12; signals.append(f"ATH-{abs(ath):.0f}%")
    elif ath<-50: score+=6
    elif ath>-20: score-=5
    vr = vol/mc
    if vr>0.30: score+=20; signals.append(f"Vol/MC:{vr:.2f}")
    elif vr>0.15: score+=12; signals.append(f"Vol/MC:{vr:.2f}")
    elif vr>0.08: score+=6
    elif vr<0.01: score-=8
    ti = tvl_data.get(sym,{})
    if ti:
        tvl=ti.get("tvl",0); t7=ti.get("tvl_7d",0)
        if tvl>1e9: score+=8; signals.append(f"TVL\${tvl/1e9:.1f}B")
        elif tvl>1e8: score+=4; signals.append(f"TVL\${tvl/1e6:.0f}M")
        if t7>20: score+=10; signals.append(f"TVL+{t7:.0f}%/7d")
        elif t7>10: score+=5
        elif t7<-20: score-=8
    return min(100,max(0,round(score,1))), signals

def rating(s):
    if s>=78: return "STRONG BUY"
    if s>=65: return "BUY WATCH"
    if s>=50: return "MONITOR"
    if s>=35: return "CAUTION"
    return "AVOID"

def build_html(rows, date_str):
    buys = [r for r in rows if r["score"] >= 65]
    def rh(r):
        bg = "#0d2b0d" if r["score"]>=78 else "#2b2b0d" if r["score"]>=65 else "#0d0d1a"
        c7 = "#4f4" if r["p7"]>=0 else "#f44"
        c30= "#4f4" if r["p30"]>=0 else "#f44"
        sg = " | ".join(r["signals"][:4])
        return (f'<tr style="background:{bg};">'
                f'<td style="padding:8px;font-weight:bold;color:#fff;">{r["symbol"]}</td>'
                f'<td style="padding:8px;color:#aef;">${r["price"]:,.4f}</td>'
                f'<td style="padding:8px;color:{c7};">{r["p7"]:+.1f}%</td>'
                f'<td style="padding:8px;color:{c30};">{r["p30"]:+.1f}%</td>'
                f'<td style="padding:8px;color:#fa0;font-weight:bold;">{r["score"]}</td>'
                f'<td style="padding:8px;color:#0df;">{r["rating"]}</td>'
                f'<td style="padding:8px;color:#999;font-size:12px;">{sg}</td>'
                f'<td style="padding:8px;color:#888;font-size:11px;">{r["note"]}</td></tr>')
    rh_all = "".join(rh(r) for r in rows)
    bl = "".join(f'<li><b>{r["symbol"]}</b> ({r["score"]}) {r["note"]}</li>' for r in buys)
    bs = f'<h3 style="color:#4f4;">HIGH SIGNAL:</h3><ul style="color:#4f4;">{bl}</ul>' if buys else ""
    return (f'<!DOCTYPE html><html><body style="background:#0d0d0d;color:#eee;font-family:monospace;padding:20px;">'
            f'<h2 style="color:#0df;">MoltStreet Crypto Scanner — {date_str}</h2>{bs}'
            f'<table style="width:100%;border-collapse:collapse;margin-top:16px;">'
            f'<thead><tr style="background:#111;color:#888;text-align:left;">'
            f'<th style="padding:8px;">SYM</th><th>PRICE</th><th>7D%</th><th>30D%</th>'
            f'<th>SCORE</th><th>SIGNAL</th><th>WHY</th><th>THESIS</th></tr></thead>'
            f'<tbody>{rh_all}</tbody></table>'
            f'<p style="color:#555;margin-top:20px;font-size:11px;">'
            f'Not financial advice. Data: CoinGecko+DeFiLlama | {date_str}</p></body></html>')

def send_email(subject, html_body):
    if not EMAIL_APP_PW: print("  [INFO] No email creds"); return
    msg = MIMEMultipart("alternative")
    msg["Subject"]=subject; msg["From"]=EMAIL_FROM; msg["To"]=EMAIL_TO
    msg.attach(MIMEText(html_body,"html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com",465) as s:
            s.login(EMAIL_FROM,EMAIL_APP_PW)
            s.sendmail(EMAIL_FROM,EMAIL_TO,msg.as_string())
        print("  Email sent!")
    except Exception as e: print(f"  Email error: {e}")

def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"MOLTSTREET CRYPTO SCANNER | {now}")
    ids = [w[0] for w in WATCHLIST]
    print("[1/3] Fetching CoinGecko prices...")
    coin_data = get_coin_data(ids)
    print(f"  Got {len(coin_data)} coins")
    print("[2/3] Fetching DeFiLlama TVL...")
    tvl_data = get_defi_tvl()
    print(f"  Got {len(tvl_data)} protocols")
    print("[3/3] Scoring projects...")
    rows = []
    for cg_id, symbol, category, note in WATCHLIST:
        if cg_id not in coin_data: print(f"  [SKIP] {symbol}"); continue
        cd = coin_data[cg_id]
        score, signals = score_coin(cd, tvl_data)
        rows.append({"symbol":symbol,"category":category,"note":note,
            "price":cd.get("current_price",0) or 0,
            "p24":cd.get("price_change_percentage_24h",0) or 0,
            "p7":cd.get("price_change_percentage_7d_in_currency",0) or 0,
            "p30":cd.get("price_change_percentage_30d_in_currency",0) or 0,
            "ath_drop":cd.get("ath_change_percentage",0) or 0,
            "mcap":cd.get("market_cap",0) or 0,
            "volume":cd.get("total_volume",0) or 0,
            "score":score,"signals":signals,"rating":rating(score)})
    rows.sort(key=lambda x:x["score"],reverse=True)
    print(f"\n{'SYM':<10} {'PRICE':>12} {'24H':>7} {'7D':>7} {'30D':>7} {'SCORE':>6} {'SIGNAL':<14}")
    print("-"*75)
    for r in rows:
        print(f"{r['symbol']:<10} \${r['price']:>11,.4f}"
              f"  {r['p24']:>+6.1f}%  {r['p7']:>+6.1f}%  {r['p30']:>+6.1f}%"
              f"  {r['score']:>5}  {r['rating']}")
    hot = [r for r in rows if r["score"]>=65]
    print(f"\nHIGH SIGNAL: {len(hot)} project(s)")
    for r in hot: print(f"  {r['symbol']}: {', '.join(r['signals'][:3])}")
    if hot:
        html = build_html(rows, now)
        send_email(f"MoltStreet Scanner {len(hot)} signal(s) | {now[:10]}", html)
    return rows

if __name__=="__main__": main()

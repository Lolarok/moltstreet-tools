#!/usr/bin/env python3
"""MoltStreet Crypto Alpha Hunter v1.0
github.com/Lolarok/moltstreet-tools/crypto-signals
Usage: python3 crypto_alpha_hunter.py [--top N] [--sector perp|rwa|ai|l2|defi|infra] [--email] [--json]
"""
import os, json, time, argparse, smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.request import urlopen, Request

SECTORS={
 "perp":["hyperliquid","gmx","dydx","vertex","aevo","drift","jupiter","gains"],
 "rwa":["ondo","maple","centrifuge","superstate","backed","clearpool","goldfinch"],
 "ai":["bittensor","fetch-ai","singularitynet","allora","ritual","autonolas"],
 "l2":["arbitrum","optimism","base","starknet","zksync","scroll","blast","taiko"],
 "defi":["aave","uniswap","lido","eigenlayer","pendle","ethena","sky","morpho"],
 "infra":["chainlink","pyth","wormhole","layerzero","axelar","hyperlane"],
}
W={"tvl30":0.25,"vol7":0.20,"github":0.15,"mcap_tvl":0.15,"age":0.10,"trend":0.15}

def fetch(url,h=None,t=12):
    try:
        req=Request(url,headers=h or {"User-Agent":"MoltStreet/1.0"})
        with urlopen(req,timeout=t) as r: return json.loads(r.read().decode())
    except: return None

def spct(n,o):
    if not o or o==0: return 0.0
    return ((n-o)/abs(o))*100

def snorm(v,mn,mx):
    if mx==mn: return 50.0
    return max(0.0,min(100.0,(v-mn)/(mx-mn)*100))

def fusd(n):
    if n>=1e9: return f"${n/1e9:.2f}B"
    if n>=1e6: return f"${n/1e6:.1f}M"
    if n>=1e3: return f"${n/1e3:.0f}K"
    return f"${n:.0f}"

def cpct(p):
    s="🚀" if p>50 else ("📈" if p>20 else ("↗" if p>0 else ("↘" if p>-20 else "📉")))
    return f"{s}{'+' if p>0 else ''}{p:.1f}%"


def get_protocols():
    print("  ⟳ DeFiLlama protocols...")
    d=fetch("https://api.llama.fi/protocols")
    if not d: return []
    return sorted(d,key=lambda x:x.get("tvl",0) or 0,reverse=True)[:400]

def get_dex():
    print("  ⟳ DEX volumes...")
    d=fetch("https://api.llama.fi/overview/dexs?excludeTotalDataChartBreakdown=true&excludeTotalDataChart=true")
    if not d: return {}
    return {(p.get("name","")).lower():{"vol_24h":p.get("total24h",0) or 0,"chg_7d":p.get("change_7d",0) or 0} for p in d.get("protocols",[])}

def get_perp():
    print("  ⟳ Perp volumes...")
    d=fetch("https://api.llama.fi/overview/derivatives?excludeTotalDataChartBreakdown=true&excludeTotalDataChart=true")
    if not d: return {}
    return {(p.get("name","")).lower():{"vol_24h":p.get("total24h",0) or 0,"chg_7d":p.get("change_7d",0) or 0} for p in d.get("protocols",[])}

def get_trend():
    print("  ⟳ CoinGecko trending...")
    d=fetch("https://api.coingecko.com/api/v3/search/trending")
    if not d: return {}
    t={}
    for i,item in enumerate(d.get("coins",[])[:10]):
        c=item.get("item",{}); sc=10-i
        t[(c.get("symbol","")).lower()]=sc
        t[(c.get("name","")).lower()]=sc
    return t

def get_mkt():
    print("  ⟳ CoinGecko markets...")
    url="https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=50&page=1&sparkline=false&price_change_percentage=7d,30d"
    d=fetch(url)
    if not d: return {}
    m={}
    for c in (d or []):
        e={"mcap":c.get("market_cap",0) or 0,"chg_7d":c.get("price_change_percentage_7d_in_currency",0) or 0}
        m[(c.get("symbol","")).lower()]=e
        m[(c.get("id","")).lower()]=e
    return m

def score_p(p,dex,perp,trend,mkt):
    name=(p.get("name","")).lower()
    slug=(p.get("slug",name)).lower()
    tvl=p.get("tvl",0) or 0
    tvl30=p.get("tvlPrevMonth",tvl) or tvl
    tvl7=p.get("tvlPrevWeek",tvl) or tvl
    tvl1=p.get("tvlPrevDay",tvl) or tvl
    c30=spct(tvl,tvl30); c7=spct(tvl,tvl7); c1=spct(tvl,tvl1)
    vd=dex.get(name) or dex.get(slug) or perp.get(name) or perp.get(slug) or {}
    vol=vd.get("vol_24h",0); vchg=vd.get("chg_7d",0)
    md=mkt.get(name) or mkt.get(slug) or {}
    mcap=md.get("mcap",0) or 0
    mcap_tvl=(mcap/tvl) if tvl>0 and mcap>0 else 999
    ts=trend.get(name,0) or trend.get(slug,0) or 0
    inc=p.get("listedAt",0) or 0
    age=(time.time()-inc)/86400 if inc else 1000
    ab=max(0,100-(age/10))
    s_tvl=snorm(c30,-50,200); s_vol=snorm(vchg,-50,200)
    s_mc=snorm(-mcap_tvl,-50,0); s_tr=snorm(ts,0,10); s_ag=snorm(ab,0,100)
    a=(W["tvl30"]*s_tvl+W["vol7"]*s_vol+W["mcap_tvl"]*s_mc+W["trend"]*s_tr+W["age"]*s_ag+W["github"]*50.0)
    desc=(p.get("description","") or "").lower()
    if any(k in desc for k in ["exploit","hack","rug"]): a*=0.5
    if tvl<1e6: a*=0.6
    if tvl>10e9: a*=0.7
    return {"name":p.get("name","?"),"slug":slug,"cat":p.get("category",""),
            "chains":(p.get("chains",[]) or [])[:3],"tvl":tvl,
            "c1":c1,"c7":c7,"c30":c30,"vol":vol,"vchg":vchg,
            "mcap":mcap,"mcap_tvl":mcap_tvl,"trend":ts,"age":int(age),"alpha":round(a,1)}

def report(scored,top=20,sec=None):
    if sec:
        sl=SECTORS.get(sec,[])
        scored=[s for s in scored if any(x in s["slug"] or x in s["name"].lower() for x in sl)]
    ss=sorted(scored,key=lambda x:x["alpha"],reverse=True)[:top]
    ts=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    L=["="*70,f"  🔬 MOLTSTREET ALPHA HUNTER — {ts}",
       "  github.com/Lolarok/moltstreet-tools","="*70,
       f"  Protocols scanned: {len(scored)} | Top {len(ss)} shown"+(f" | Sector: {sec.upper()}" if sec else ""),""]
    L.append(f"  {'#':<3} {'NAME':<22} {'SCORE':>6} {'TVL':>9} {'TVL30d':>12} {'VOL24h':>9} {'VOL7d':>9}")
    L.append("─"*70)
    for i,p in enumerate(ss,1):
        fl="🔥" if p["alpha"]>=70 else ("⭐" if p["alpha"]>=55 else ("👀" if p["alpha"]>=40 else "  "))
        L.append(f"  {fl}{i:<2} {p['name']:<22} {p['alpha']:>5.1f} {fusd(p['tvl']):>9} {cpct(p['c30']):>16} {fusd(p['vol']):>9} {cpct(p['vchg']):>14}")
    L+=["","─"*70,"  DETAIL — TOP 5:","─"*70]
    for p in ss[:5]:
        mc=f" | MCap:{fusd(p['mcap'])} MCap/TVL:{p['mcap_tvl']:.2f}x" if p["mcap"]>0 else ""
        L.append(f"\n  [{p['alpha']}] {p['name']} | {p['cat']} | Age:{p['age']}d | Chains:{','.join(p['chains'])}")
        L.append(f"  TVL:{fusd(p['tvl'])} ({cpct(p['c30'])} 30d){mc}")
        L.append(f"  Vol24h:{fusd(p['vol'])} ({cpct(p['vchg'])} 7d)")
    L+=["","─"*70,"  ⚠️  DILUTION RISK (MCap/TVL < 0.3):","─"*70]
    fl=[p for p in scored if 0<p["mcap_tvl"]<0.3 and p["tvl"]>50e6]
    if fl:
        for p in fl[:5]: L.append(f"  • {p['name']}: MCap/TVL={p['mcap_tvl']:.2f}x TVL={fusd(p['tvl'])}")
    else: L.append("  None detected.")
    L+=["","="*70,"  DYOR. Not financial advice. | MoltStreet","="*70]
    return "\n".join(L)

def send_mail(txt):
    em=os.environ.get("SMTP_EMAIL","italiamolt5@gmail.com")
    pw=os.environ.get("SMTP_PASSWORD") or os.environ.get("Mail_apppassword","")
    to=os.environ.get("ALERT_EMAIL",em)
    if not pw: print("  Set SMTP_PASSWORD or Mail_apppassword env var"); return
    msg=MIMEMultipart("alternative")
    msg["Subject"]=f"🔬 MoltStreet Alpha — {datetime.utcnow().strftime('%Y-%m-%d')}"
    msg["From"]=em; msg["To"]=to
    msg.attach(MIMEText(txt,"plain"))
    html=f'<html><body style="font-family:monospace;background:#0d1117;color:#c9d1d9;padding:20px"><h2 style="color:#58a6ff">🔬 MoltStreet Alpha Hunter</h2><pre style="background:#161b22;padding:15px;border-radius:8px;font-size:12px">{txt}</pre><p style="color:#8b949e;font-size:11px">github.com/Lolarok/moltstreet-tools — DYOR</p></body></html>'
    msg.attach(MIMEText(html,"html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com",465) as s:
            s.login(em,pw); s.sendmail(em,to,msg.as_string())
        print(f"  ✅ Email sent → {to}")
    except Exception as e: print(f"  ❌ {e}")

def main():
    pa=argparse.ArgumentParser(description="MoltStreet Crypto Alpha Hunter")
    pa.add_argument("--top",type=int,default=20)
    pa.add_argument("--email",action="store_true",help="Send email digest")
    pa.add_argument("--sector",type=str,default=None,choices=list(SECTORS.keys()))
    pa.add_argument("--json",action="store_true",help="Raw JSON output")
    pa.add_argument("--min-tvl",type=float,default=1e6,help="Min TVL filter (default 1M)")
    args=pa.parse_args()
    print("\n🔬 MoltStreet Alpha Hunter — Scanning...\n")
    P=get_protocols(); D=get_dex(); PR=get_perp(); T=get_trend(); M=get_mkt()
    print(f"\n  📊 {len(P)} protocols | {len(D)} DEX | {len(PR)} perp | {len(T)} trending\n")
    scored=[]
    for p in P:
        if (p.get("tvl") or 0)<args.min_tvl: continue
        try: scored.append(score_p(p,D,PR,T,M))
        except: pass
    print(f"  ✅ Scored {len(scored)} protocols above ${args.min_tvl:.0f} TVL\n")
    if args.json:
        print(json.dumps(sorted(scored,key=lambda x:x["alpha"],reverse=True)[:args.top],indent=2))
        return
    rpt=report(scored,top=args.top,sec=args.sector)
    print(rpt)
    if args.email: send_mail(rpt)
    try:
        out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"latest_report.txt")
        open(out,"w").write(rpt); print(f"\n  💾 Saved → {out}")
    except: pass

if __name__=="__main__": main()

#!/usr/bin/env python3
"""MoltStreet Crypto Early-Detection Scanner v3.0 — Top 100 Dynamic
Runs daily via GitHub Actions. Zero external dependencies.
Data: CoinGecko API + DeFiLlama API

v3.0 changes:
  - Dynamic top 100 from CoinGecko (no more hardcoded watchlist)
  - Sector classification from CoinGecko categories
  - JSON output for downstream consumers (SignalHub, dashboards)
  - Market cap ranking + volume/mcap ratio scoring
  - ATH drawdown detection for "deep value" signals
"""
import urllib.request, json, time, datetime, smtplib, os, sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── Config ──────────────────────────────────────────────────────────
TOP_N          = int(os.environ.get("MOLTSTREET_TOP", "100"))
EMAIL_FROM     = "italiamolt5@gmail.com"
EMAIL_TO       = "italiamolt5@gmail.com"
EMAIL_APP_PW   = os.environ.get("MAIL_APPPASSWORD", "")
OUTPUT_JSON    = os.environ.get("MOLTSTREET_JSON", "1")  # set "0" to skip
OUTPUT_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")

# CoinGecko category mapping (fallback if API doesn't provide)
SECTOR_KEYWORDS = {
    "defi":       ["defi", "decentralized-finance", "lending", "dex", "yield", "amm"],
    "l1":         ["layer-1", "smart-contract-platform", "blockchain"],
    "l2":         ["layer-2", "scaling", "rollup", "zk"],
    "meme":       ["meme", "dog-themed", "animal-themed"],
    "ai":         ["artificial-intelligence", "ai", "machine-learning", "compute"],
    "rwa":        ["real-world-assets", "tokenized-assets", "rwa"],
    "gaming":     ["gaming", "play-to-earn", "gamefi", "metaverse"],
    "infra":      ["infrastructure", "oracle", "data-availability", "interoperability"],
    "stablecoin": ["stablecoins", "stablecoin"],
    "exchange":   ["exchange", "cefi", "centralized-exchange"],
}

# ─── HTTP helpers ────────────────────────────────────────────────────
def fetch_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "MoltStreet/3.0",
                "accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read())
        except Exception as e:
            if i < retries - 1:
                time.sleep(2 ** i)
            else:
                print(f"  [WARN] {url[:70]}: {e}")
                return None

# ─── Data fetching ───────────────────────────────────────────────────
def get_top_coins(n=100):
    """Fetch top N coins by market cap from CoinGecko. Handles pagination."""
    coins = {}
    per_page = min(n, 250)  # CoinGecko max per page
    pages = (n + per_page - 1) // per_page

    for page in range(1, pages + 1):
        url = (f"https://api.coingecko.com/api/v3/coins/markets"
               f"?vs_currency=usd&order=market_cap_desc"
               f"&per_page={per_page}&page={page}&sparkline=false"
               f"&price_change_percentage=1h,24h,7d,30d")
        data = fetch_json(url)
        if not data:
            print(f"  [WARN] Failed to fetch page {page}")
            continue
        for c in data:
            cid = c.get("id")
            if cid:
                coins[cid] = c
        # Respect rate limits
        if page < pages:
            time.sleep(1.5)

    return coins

def get_coin_categories():
    """Fetch category tags from CoinGecko for top coins."""
    url = "https://api.coingecko.com/api/v3/coins/categories/list"
    data = fetch_json(url)
    if not data:
        return {}
    return {c["category_id"]: c.get("name", "") for c in data}

def get_defi_tvl():
    """Fetch TVL data from DeFiLlama."""
    data = fetch_json("https://api.llama.fi/protocols")
    if not data:
        return {}
    out = {}
    for p in data:
        sym = (p.get("symbol") or "").upper()
        if sym:
            out[sym] = {
                "tvl": p.get("tvl", 0) or 0,
                "tvl_7d": p.get("change_7d", 0) or 0,
                "name": (p.get("name") or "").lower(),
                "slug": (p.get("slug") or "").lower(),
            }
    return out

def get_trending():
    """Fetch CoinGecko trending list for momentum signal."""
    data = fetch_json("https://api.coingecko.com/api/v3/search/trending")
    if not data:
        return set()
    trending = set()
    for item in data.get("coins", []):
        c = item.get("item", {})
        trending.add((c.get("id") or "").lower())
        trending.add((c.get("symbol") or "").lower())
    return trending

# ─── Sector classification ───────────────────────────────────────────
def classify_sector(coin):
    """Classify a coin into a sector based on available metadata."""
    # Try CoinGecko categories first
    cats = coin.get("categories") or []
    for cat in cats:
        cat_lower = cat.lower()
        for sector, keywords in SECTOR_KEYWORDS.items():
            if any(kw in cat_lower for kw in keywords):
                return sector

    # Fallback: symbol/name heuristics
    name = (coin.get("name") or "").lower()
    sym = (coin.get("symbol") or "").lower()

    if any(m in name for m in ["doge", "shib", "pepe", "floki", "bonk", "wif", "brett"]):
        return "meme"
    if any(a in name for a in ["bitcoin", "ethereum", "solana", "cardano", "avalanche",
                                "polkadot", "near", "aptos", "sui", "sei"]):
        return "l1"
    if any(d in name for d in ["aave", "uniswap", "curve", "maker", "compound", "lido",
                                "pendle", "eigenlayer", "jupiter"]):
        return "defi"
    if any(i in name for i in ["chainlink", "pyth", "wormhole", "layerzero"]):
        return "infra"

    return "other"

# ─── Scoring engine ─────────────────────────────────────────────────
def score_coin(coin, tvl_data, trending_set, rank):
    """Score a coin 0-100 based on technical + fundamental signals."""
    score = 50.0
    signals = []

    p1h  = coin.get("price_change_percentage_1h_in_currency") or 0
    p24  = coin.get("price_change_percentage_24h") or 0
    p7   = coin.get("price_change_percentage_7d_in_currency") or 0
    p30  = coin.get("price_change_percentage_30d_in_currency") or 0
    ath  = coin.get("ath_change_percentage") or 0
    vol  = coin.get("total_volume") or 1
    mc   = coin.get("market_cap") or 1
    sym  = (coin.get("symbol") or "").upper()
    cid  = (coin.get("id") or "").lower()

    # ── Momentum (24h) ──
    if p24 > 15:   score += 14; signals.append(f"24h+{p24:.0f}%")
    elif p24 > 8:  score += 9;  signals.append(f"24h+{p24:.0f}%")
    elif p24 > 3:  score += 4
    elif p24 < -15: score -= 14; signals.append(f"24h{p24:.0f}%")
    elif p24 < -8: score -= 9
    elif p24 < -3: score -= 4

    # ── Weekly trend ──
    if p7 > 25:    score += 24; signals.append(f"7d+{p7:.0f}%")
    elif p7 > 15:  score += 16; signals.append(f"7d+{p7:.0f}%")
    elif p7 > 5:   score += 8
    elif p7 < -25: score -= 22; signals.append(f"7d{p7:.0f}%")
    elif p7 < -15: score -= 14
    elif p7 < -5:  score -= 6

    # ── Monthly trend ──
    if p30 > 40:   score += 16; signals.append(f"30d+{p30:.0f}%")
    elif p30 > 20: score += 10
    elif p30 > 5:  score += 5
    elif p30 < -40: score -= 16
    elif p30 < -20: score -= 10
    elif p30 < -5: score -= 5

    # ── ATH drawdown (deep value) ──
    if ath < -95:  score += 20; signals.append(f"ATH-{abs(ath):.0f}%")
    elif ath < -85: score += 15; signals.append(f"ATH-{abs(ath):.0f}%")
    elif ath < -70: score += 10; signals.append(f"ATH-{abs(ath):.0f}%")
    elif ath < -50: score += 5
    elif ath > -15: score -= 6  # near ATH = less upside

    # ── Volume / Market Cap ratio ──
    vr = vol / mc if mc > 0 else 0
    if vr > 0.35:  score += 22; signals.append(f"Vol/MC:{vr:.2f}")
    elif vr > 0.20: score += 14; signals.append(f"Vol/MC:{vr:.2f}")
    elif vr > 0.10: score += 7
    elif vr < 0.015: score -= 10

    # ── DeFiLlama TVL ──
    ti = tvl_data.get(sym, {})
    if not ti:
        # try by id
        for k, v in tvl_data.items():
            if v.get("name") == cid or v.get("slug") == cid:
                ti = v
                break
    if ti:
        tvl = ti.get("tvl", 0)
        t7 = ti.get("tvl_7d", 0)
        if tvl > 5e9:  score += 10; signals.append(f"TVL${tvl/1e9:.1f}B")
        elif tvl > 1e9: score += 7;  signals.append(f"TVL${tvl/1e9:.1f}B")
        elif tvl > 100e6: score += 4; signals.append(f"TVL${tvl/1e6:.0f}M")
        elif tvl > 10e6: score += 2
        if t7 > 25:   score += 12; signals.append(f"TVL+{t7:.0f}%/7d")
        elif t7 > 12: score += 6
        elif t7 < -25: score -= 10

    # ── Market cap rank bonus ──
    if rank <= 10:  score += 5   # top 10 = blue chip stability
    elif rank <= 30: score += 3
    elif rank > 80: score -= 3   # micro cap risk

    # ── Trending bonus ──
    if cid in trending_set or sym.lower() in trending_set:
        score += 8; signals.append("🔥TRENDING")

    # ── Sector classification ──
    sector = classify_sector(coin)

    return min(100, max(0, round(score, 1))), signals, sector

def rating(s):
    if s >= 80:  return "🔥 STRONG BUY"
    if s >= 70:  return "⭐ BUY WATCH"
    if s >= 55:  return "👀 MONITOR"
    if s >= 40:  return "😐 CAUTION"
    return "⛔ AVOID"

# ─── Output formatters ──────────────────────────────────────────────
def build_html(rows, date_str):
    buys = [r for r in rows if r["score"] >= 70]

    def row_html(r):
        bg = "#0d2b0d" if r["score"] >= 78 else "#2b2b0d" if r["score"] >= 65 else "#0d0d1a"
        c7 = "#4f4" if r["p7"] >= 0 else "#f44"
        c30 = "#4f4" if r["p30"] >= 0 else "#f44"
        sg = " | ".join(r["signals"][:4])
        return (f'<tr style="background:{bg};">'
                f'<td style="padding:6px;font-weight:bold;color:#fff;">#{r["rank"]}</td>'
                f'<td style="padding:6px;font-weight:bold;color:#0df;">{r["symbol"]}</td>'
                f'<td style="padding:6px;color:#aef;">${r["price"]:,.4f}</td>'
                f'<td style="padding:6px;color:{c7};">{r["p7"]:+.1f}%</td>'
                f'<td style="padding:6px;color:{c30};">{r["p30"]:+.1f}%</td>'
                f'<td style="padding:6px;color:#fa0;font-weight:bold;">{r["score"]}</td>'
                f'<td style="padding:6px;color:#0df;">{r["rating"]}</td>'
                f'<td style="padding:6px;color:#888;">{r["sector"]}</td>'
                f'<td style="padding:6px;color:#999;font-size:11px;">{sg}</td></tr>')

    rh_all = "".join(row_html(r) for r in rows)
    bl = "".join(f'<li><b>{r["symbol"]}</b> #{r["rank"]} ({r["score"]}) — {", ".join(r["signals"][:3])}</li>' for r in buys[:10])
    bs = f'<h3 style="color:#4f4;">🔥 HIGH SIGNAL ({len(buys)} coins):</h3><ul style="color:#4f4;">{bl}</ul>' if buys else ""

    # Sector summary
    sectors = {}
    for r in rows:
        sectors.setdefault(r["sector"], []).append(r)
    sec_html = ""
    for sec, coins in sorted(sectors.items()):
        avg = sum(c["score"] for c in coins) / len(coins)
        sec_html += f'<span style="margin-right:12px;color:#{"4f4" if avg>=60 else "fa0" if avg>=45 else "f44"}">{sec.upper()}: {avg:.0f} ({len(coins)})</span> '

    return (f'<!DOCTYPE html><html><body style="background:#0d0d0d;color:#eee;font-family:monospace;padding:20px;">'
            f'<h2 style="color:#0df;">MoltStreet Crypto Scanner v3.0 — Top {len(rows)} — {date_str}</h2>'
            f'<p style="color:#888;">Sectors: {sec_html}</p>'
            f'{bs}'
            f'<table style="width:100%;border-collapse:collapse;margin-top:16px;">'
            f'<thead><tr style="background:#111;color:#888;text-align:left;">'
            f'<th style="padding:6px;">#</th><th>SYM</th><th>PRICE</th><th>7D%</th>'
            f'<th>30D%</th><th>SCORE</th><th>SIGNAL</th><th>SECTOR</th><th>WHY</th></tr></thead>'
            f'<tbody>{rh_all}</tbody></table>'
            f'<p style="color:#555;margin-top:20px;font-size:11px;">'
            f'Not financial advice. Data: CoinGecko+DeFiLlama | {date_str}</p></body></html>')

def build_json(rows, date_str):
    """Output JSON for downstream consumers (SignalHub, dashboards)."""
    return json.dumps({
        "version": "3.0",
        "generated": date_str,
        "count": len(rows),
        "coins": [{
            "rank": r["rank"],
            "symbol": r["symbol"],
            "name": r["name"],
            "sector": r["sector"],
            "price": r["price"],
            "mcap": r["mcap"],
            "volume": r["volume"],
            "p1h": r["p1h"],
            "p24": r["p24"],
            "p7": r["p7"],
            "p30": r["p30"],
            "ath_drop": r["ath_drop"],
            "score": r["score"],
            "rating": r["rating"],
            "signals": r["signals"],
        } for r in rows],
        "sectors": {
            sec: {
                "count": len(coins),
                "avg_score": round(sum(c["score"] for c in coins) / len(coins), 1),
                "top": coins[0]["symbol"] if coins else None,
            }
            for sec, coins in sorted(
                ((s, [r for r in rows if r["sector"] == s]) for s in set(r["sector"] for r in rows)),
                key=lambda x: x[1][0]["score"] if x[1] else 0, reverse=True
            )
        },
    }, indent=2)

def send_email(subject, html_body):
    if not EMAIL_APP_PW:
        print("  [INFO] No email creds, skipping email")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_FROM, EMAIL_APP_PW)
            s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print("  ✅ Email sent!")
    except Exception as e:
        print(f"  ❌ Email error: {e}")

# ─── Main ────────────────────────────────────────────────────────────
def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"MOLTSTREET CRYPTO SCANNER v3.0 | Top {TOP_N} | {now}")
    print("=" * 70)

    # Step 1: Fetch top coins
    print(f"\n[1/4] Fetching top {TOP_N} coins from CoinGecko...")
    coins = get_top_coins(TOP_N)
    print(f"  ✅ Got {len(coins)} coins")

    if not coins:
        print("  ❌ No data from CoinGecko, aborting")
        sys.exit(1)

    # Step 2: Fetch TVL data
    print("[2/4] Fetching DeFiLlama TVL...")
    tvl_data = get_defi_tvl()
    print(f"  ✅ Got {len(tvl_data)} protocols")

    # Step 3: Fetch trending
    print("[3/4] Fetching CoinGecko trending...")
    trending = get_trending()
    print(f"  ✅ {len(trending)} trending tokens")

    # Step 4: Score all coins
    print("[4/4] Scoring coins...")
    rows = []
    for rank, (cid, c) in enumerate(sorted(coins.items(), key=lambda x: x[1].get("market_cap_rank", 999)), 1):
        score, signals, sector = score_coin(c, tvl_data, trending, rank)
        rows.append({
            "rank": c.get("market_cap_rank", rank),
            "symbol": (c.get("symbol") or "").upper(),
            "name": c.get("name", ""),
            "sector": sector,
            "price": c.get("current_price") or 0,
            "mcap": c.get("market_cap") or 0,
            "volume": c.get("total_volume") or 0,
            "p1h": c.get("price_change_percentage_1h_in_currency") or 0,
            "p24": c.get("price_change_percentage_24h") or 0,
            "p7": c.get("price_change_percentage_7d_in_currency") or 0,
            "p30": c.get("price_change_percentage_30d_in_currency") or 0,
            "ath_drop": c.get("ath_change_percentage") or 0,
            "score": score,
            "rating": rating(score),
            "signals": signals,
        })

    rows.sort(key=lambda x: x["score"], reverse=True)

    # ── Console output ──
    print(f"\n{'RANK':<6} {'SYM':<10} {'PRICE':>12} {'24H':>8} {'7D':>8} {'30D':>8} {'SCORE':>6} {'SIGNAL':<16} {'SECTOR':<10}")
    print("-" * 100)
    for r in rows:
        print(f"#{r['rank']:<5} {r['symbol']:<10} ${r['price']:>11,.4f}"
              f"  {r['p24']:>+7.1f}%  {r['p7']:>+7.1f}%  {r['p30']:>+7.1f}%"
              f"  {r['score']:>5.0f}  {r['rating']:<16} {r['sector']}")

    # Summary
    hot = [r for r in rows if r["score"] >= 70]
    print(f"\n🔥 HIGH SIGNAL: {len(hot)} coins")
    for r in hot[:10]:
        print(f"  {r['symbol']}: {', '.join(r['signals'][:4])}")

    # Sector breakdown
    sectors = {}
    for r in rows:
        sectors.setdefault(r["sector"], []).append(r)
    print(f"\n📊 SECTOR BREAKDOWN:")
    for sec, coins_list in sorted(sectors.items(), key=lambda x: sum(c["score"] for c in x[1]), reverse=True):
        avg = sum(c["score"] for c in coins_list) / len(coins_list)
        top = coins_list[0] if coins_list else None
        print(f"  {sec.upper():<12} avg:{avg:.0f}  top:{top['symbol']} ({top['score']:.0f})  [{len(coins_list)} coins]")

    # ── Save outputs ──
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # JSON output
    if OUTPUT_JSON != "0":
        json_path = os.path.join(OUTPUT_DIR, "signals_top100.json")
        with open(json_path, "w") as f:
            f.write(build_json(rows, now))
        print(f"\n💾 JSON saved → {json_path}")

    # HTML report
    html = build_html(rows, now)
    html_path = os.path.join(OUTPUT_DIR, "report_top100.html")
    with open(html_path, "w") as f:
        f.write(html)
    print(f"💾 HTML saved → {html_path}")

    # Email
    if hot:
        send_email(f"MoltStreet v3.0: {len(hot)} signal(s) | Top {TOP_N} | {now[:10]}", html)

    print(f"\n✅ Done. {len(rows)} coins scored, {len(hot)} high signals.")
    return rows

if __name__ == "__main__":
    main()

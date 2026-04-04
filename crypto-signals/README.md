# 🔬 Crypto Alpha Hunter

Automated early-signal detection engine for crypto projects.
Modeled on patterns that identified **Hyperliquid**, **Pendle**, **EigenLayer** before mainstream.

## Signals & Weights

| Signal | Source | Weight |
|--------|--------|--------|
| TVL 30d growth | DeFiLlama | 25% |
| Volume 7d spike | DeFiLlama DEX/Perp | 20% |
| GitHub commit velocity | GitHub API | 15% |
| MCap/TVL ratio | CoinGecko + DeFiLlama | 15% |
| Protocol age bonus | DeFiLlama | 10% |
| Social trending | CoinGecko Trending | 15% |

## Usage

```bash
pip install -r ../../requirements.txt   # no extra deps needed (stdlib only)
python3 crypto_alpha_hunter.py                    # full scan, top 20
python3 crypto_alpha_hunter.py --top 10           # top 10
python3 crypto_alpha_hunter.py --sector perp      # perp DEX only
python3 crypto_alpha_hunter.py --sector rwa       # RWA protocols
python3 crypto_alpha_hunter.py --sector ai        # AI crypto
python3 crypto_alpha_hunter.py --email            # scan + email digest
python3 crypto_alpha_hunter.py --json             # raw JSON
python3 crypto_alpha_hunter.py --min-tvl 5000000  # TVL > $5M
```

## Daily Cron (8 AM)

```bash
0 8 * * * cd /path/to/crypto-signals && \
  Mail_apppassword="xxx" ALERT_EMAIL="you@mail.com" \
  python3 crypto_alpha_hunter.py --email >> /var/log/alpha.log 2>&1
```

## AlphaScore Guide

| Score | Meaning |
|-------|---------|
| 🔥 70–100 | Strong early signal — investigate now |
| ⭐ 55–69 | Promising — add to watchlist |
| 👀 40–54 | Moderate — monitor for confirmation |
| < 40 | Noise or already priced in |

## Red Flags (Auto-Filtered)

- MCap/TVL < 0.3 → over-dilution / upcoming unlock risk
- TVL < $1M → illiquid / too early
- TVL > $10B → already discovered (upside reduced)
- Description contains: exploit / hack / rug

## Sectors Tracked

`perp` · `rwa` · `ai` · `l2` · `defi` · `infra`

---
*Part of [MoltStreet Tools](https://github.com/Lolarok/moltstreet-tools) — DYOR*

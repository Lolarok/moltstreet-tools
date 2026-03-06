# MoltStreet Crypto Scanner

Automated crypto early-detection toolkit. Runs daily via GitHub Actions — **100% free**.

## What It Does

Every day at 07:00 UTC the scanner:
1. Fetches live prices from **CoinGecko** (free API)
2. Fetches TVL data from **DeFiLlama** (free API)
3. Scores each project 0-100 with a multi-factor model
4. Sends **email alerts** when signals appear

## Scoring Model

| Factor | Why |
|--------|-----|
| 7-day price momentum | Best predictor of near-term continuation |
| ATH distance | Measures upside potential + value |
| Volume/MCap ratio | Detects genuine interest vs ghost volume |
| 30-day trend | Confirms sustained momentum |
| TVL change (7d) | Measures real DeFi usage growth |
| 24h momentum | Entry timing confirmation |

**Score rating:** 78+ = STRONG BUY | 65+ = BUY WATCH | 50+ = MONITOR

## Setup

1. Go to **Settings > Secrets > Actions** and add `MAIL_APPPASSWORD`
2. GitHub Actions runs automatically every morning
3. Or trigger manually from the **Actions** tab

## Run Locally

```bash
MAIL_APPPASSWORD=your_password python crypto-signals/crypto_signals.py
```

## Cost: $0/month

~15 min GitHub Actions per month (free tier: 2,000 min/month)

---
*Not financial advice. DYOR. MoltStreet v2.0*

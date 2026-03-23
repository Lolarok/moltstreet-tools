# MoltStreet Tools

Crypto intelligence toolkit — automated scanners, signal engines, and content tools.

## 🚀 Come farlo partire (passo-passo)

### Prerequisiti
- **Python 3.10+**
- **Git**

### Passo 1: Clona
```bash
git clone https://github.com/Lolarok/moltstreet-tools.git
cd moltstreet-tools
```

### Passo 2: Esegui gli scanner

**Crypto Alpha Hunter** (DeFi screener con filtri per settore):
```bash
python3 crypto-signals/crypto_alpha_hunter.py --top 10
python3 crypto-signals/crypto_alpha_hunter.py --sector perp
python3 crypto-signals/crypto_alpha_hunter.py --json
```

**Crypto Signals v2** (watchlist-based scanner):
```bash
python3 crypto-signals/crypto_signals.py
```

**RSS Aggregator** (auto-post WordPress):
```bash
python3 rss-aggregator/rss_aggregator.py --site crypto --dry-run
python3 rss-aggregator/rss_aggregator.py --site all --max 3
```

### Passo 3: Email alerts (opzionale)
```bash
export MAIL_APPPASSWORD=your_gmail_app_password
python3 crypto-signals/crypto_alpha_hunter.py --top 10 --email
```

### Nessuna dipendenza da installare!
Tutto usa Python stdlib + API gratuite. Zero pip install.

---

## Tools

### 🔬 Crypto Alpha Hunter (`crypto-signals/crypto_alpha_hunter.py`)
Protocol scanner that scores DeFi projects by TVL growth, volume, GitHub activity, and market metrics. Supports sector filtering (perp, rwa, ai, l2, defi, infra).

```bash
python3 crypto-signals/crypto_alpha_hunter.py --top 10 --email
python3 crypto-signals/crypto_alpha_hunter.py --sector perp
python3 crypto-signals/crypto_alpha_hunter.py --json
```

### 📡 Crypto Signals v2 (`crypto-signals/crypto_signals.py`)
Watchlist-based daily scanner. Scores 12 hand-picked projects using CoinGecko + DeFiLlama data. Sends email alerts on strong signals.

```bash
python3 crypto-signals/crypto_signals.py
MAIL_APPPASSWORD=your_pw python3 crypto-signals/crypto_signals.py
```

### 📰 RSS Aggregator (`rss-aggregator/rss_aggregator.py`)
Fetches crypto news from RSS feeds, scores relevance, and auto-posts drafts to WordPress sites.

```bash
python3 rss-aggregator/rss_aggregator.py --site crypto --dry-run
python3 rss-aggregator/rss_aggregator.py --site all --max 3
```

## Setup

1. **No pip install needed** — all tools use Python stdlib only
2. For email alerts: set `MAIL_APPPASSWORD` (see [docs/EMAIL_SETUP.md](docs/EMAIL_SETUP.md))
3. For WordPress posting: configure `WP_SITES` in `rss-aggregator/rss_aggregator.py`
4. GitHub Actions runs scanners daily (see `.github/workflows/`)

## Architecture

```
moltstreet-tools/
├── crypto-signals/
│   ├── crypto_alpha_hunter.py   # DeFi protocol screener (sector-based)
│   ├── crypto_signals.py        # Watchlist daily scanner
│   └── README.md
├── rss-aggregator/
│   └── rss_aggregator.py        # RSS → WordPress auto-poster
├── docs/
│   ├── EMAIL_SETUP.md
│   └── SETUP_GUIDE.md
├── .github/workflows/
│   └── daily-scans.yml          # Daily cron for scanners
└── README.md
```

## Cost

$0/month — Python stdlib + free APIs (CoinGecko, DeFiLlama) + GitHub Actions free tier (2,000 min/month).

---
*Not financial advice. DYOR. MoltStreet*

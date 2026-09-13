# Survival Trading Bot

A trend-following crypto trading bot with a twist: its position sizing
is tied to its own account balance. As the balance falls, it trades
smaller and more cautiously; if the balance falls to (near) zero, it
stops trading entirely.

**Start in `DRY_RUN=true` + `SANDBOX_MODE=true`. Do not flip both to
false until you've watched it run correctly for at least a few days.**

---

## 1. Create an OKX account

1. Go to okx.com and sign up (email + password).
2. Complete identity verification (KYC) -- required before you can
   fund the account or trade, even small amounts. You'll need a
   government ID and a selfie step.
3. Fund the account. Options that work from Kenya typically include
   card purchase or P2P (buying USDT from another user via OKX's P2P
   marketplace, often the cheapest route). Start with the ~$20 (or
   whatever amount) you intend to risk -- send only that.

## 2. Create API keys (do this carefully)

1. In OKX, go to **Profile -> API** (sometimes under Account settings).
2. Click **Create API Key**.
3. **Permissions: enable "Trade" only. Do NOT enable "Withdraw."**
   This is the single most important safety step -- it means that
   even if your API key ever leaks, nobody can move funds out of the
   account, only place trades inside it.
4. If OKX offers **IP whitelisting**, add the outbound IP of wherever
   you'll run the bot. On Render this is trickier since free-tier
   outbound IPs aren't static/guaranteed, so you may need to leave
   this open or check Render's docs for a static IP add-on. Weigh
   convenience vs. this extra layer of protection.
5. OKX will generate three values: **API Key**, **Secret Key**, and
   **Passphrase** (you set the passphrase yourself when creating the
   key). Copy all three somewhere safe immediately -- the secret is
   only shown once.
6. For testing before risking real money, use **OKX's demo trading /
   sandbox environment** (found in the same API section, sometimes
   labeled "Demo Trading"). Generate a *separate* set of demo API
   keys for this -- keep demo and live keys clearly labeled and never
   mix them up.

## 3. Set up the GitHub repo

```bash
cd tradingbot
git init
git add .
git commit -m "Initial commit: survival trading bot"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

Your `.env` file is already excluded via `.gitignore` -- double check
it never gets committed. Real secrets only ever go into Render's
environment variable dashboard (next step), never into git.

## 4. Deploy to Render

1. Go to render.com, sign up, and connect your GitHub account.
2. **New -> Web Service**, select your repo. Render will detect
   `render.yaml` and pre-fill most settings.
3. Under **Environment**, add these as secret env vars (do NOT put
   them in render.yaml, which gets committed to git):
   - `API_KEY`
   - `API_SECRET`
   - `API_PASSPHRASE`
4. Leave `DRY_RUN=true` and `SANDBOX_MODE=true` for the first
   deploy -- this proves the whole pipeline works without risking
   anything.
5. Deploy. Check the logs tab -- you should see the bot's journal
   entries ("Balance holding steady...", etc.) appear every
   `POLL_INTERVAL_SECONDS`.
6. Visit `https://<your-app>.onrender.com/status` to see the bot's
   current simulated balance and trade count as JSON.

### Critical gotcha: Render's free tier sleeps

Free web services on Render spin down after ~15 minutes without
incoming HTTP requests, which pauses your bot's background thread
along with the whole process. To keep it running 24/7 for free:

- Sign up for a free account at **UptimeRobot** (or similar) and add
  an HTTP monitor that pings `https://<your-app>.onrender.com/health`
  every 5-10 minutes. This keeps Render from spinning the service
  down.
- Understand this is a workaround, not a guarantee -- Render can
  still restart the instance for deploys/maintenance, which is why
  `bot/state.py` persists balance/trade-count to disk. Note, though,
  that Render's free-tier disk is *not* guaranteed to survive a full
  redeploy or plan-level restart -- for anything you truly can't
  afford to lose, use a small external store (Render's free Postgres
  tier, or a hosted key-value store) instead of the local JSON file.

## 5. Going live (only after real testing)

When you've watched the bot behave correctly in dry-run/sandbox for
several days and are ready to trade your real $20 (or whatever amount
you choose):

1. In Render's dashboard, flip `SANDBOX_MODE` to `false` and
   `DRY_RUN` to `false`.
2. Make sure the `API_KEY` / `API_SECRET` / `API_PASSPHRASE` env vars
   are your **live** OKX keys, not demo ones.
3. Redeploy and watch the logs closely for the first few hours.

## Project structure

```
tradingbot/
  app.py                  # Flask entry point Render runs
  bot/
    config.py             # env-var driven configuration
    exchange_client.py     # ccxt wrapper (OKX by default)
    strategy.py            # MA crossover signal
    risk_manager.py         # survival-linked position sizing
    journal.py              # narrated logging
    state.py                 # simple JSON persistence
    main_loop.py              # the bot's heartbeat
  requirements.txt
  render.yaml
  .env.example
```

## Tuning knobs (all via env vars, see `.env.example`)

| Variable | What it does |
|---|---|
| `FAST_MA` / `SLOW_MA` | Moving average periods for the crossover signal |
| `MAX_RISK_PER_TRADE_PCT` | Max % of current balance risked per trade when "healthy" |
| `CRITICAL_BALANCE_PCT` | % of starting balance below which the bot goes into "critical" mode (smaller trades) |
| `DEATH_BALANCE_USD` | Balance floor -- at or below this, the bot stops trading permanently |
| `POLL_INTERVAL_SECONDS` | How often the bot checks the market |

## Safety checklist before going live

- [ ] API key has **trade-only** permission, withdrawal disabled
- [ ] Tested in `DRY_RUN` + `SANDBOX_MODE` for several days first
- [ ] Only funded with money you can fully afford to lose
- [ ] `.env` is not committed to git
- [ ] Uptime pinger set up so the bot doesn't silently sleep

# Ai-Tree
Visualized mobile ai app

---

# wfbot — automated Warframe market trading

An unattended trading assistant for [warframe.market](https://warframe.market):
it finds mispriced items, ranks them by expected platinum, and keeps your own
listings priced to win — automatically, on a loop, on your computer.

## What it automates, and what it can't

Read this part before anything else, because it decides what "automatic" can
mean here.

**Warframe has no API that moves items or platinum.** Every trade happens inside
the game client, in person, between two players standing at a trade post.
warframe.market only hosts *listings* — the advert, not the transaction. So no
tool can complete a trade for you without driving your game client with
synthetic mouse and keyboard input, and that is exactly what Digital Extremes'
EULA bans and bans accounts for. wfbot does not do it, and adding it would put
your account at risk for no advantage.

What is left is where the actual edge is, and all of it runs unattended:

| | |
|---|---|
| **Finds the money** | Scans the market for crossed books and underpriced listings, ranked by expected profit, filtered by your budget |
| **Prices your listings** | Undercuts the cheapest live seller / outbids the richest live buyer on every one of your orders, inside floors and ceilings derived from fair value |
| **Tracks the market** | Records price history locally so you can see what an item really costs before you buy |
| **Tells you when to act** | Desktop notification plus the exact `/w` whisper on your clipboard, ready to paste |
| **Knows when you're online** | Reads Warframe's own log file (read-only) to see when you're in-game, and can hide your listings when you're not |

You do one thing by hand: paste the whisper, meet the player, click trade. The
bot does the other 95%, which is the part that takes hours.

## Install

```bash
git clone https://github.com/kingspartin/ai-tree
cd ai-tree
pip install -e .
# optional, better clipboard support on Windows/Linux:
pip install pyperclip
```

Python 3.11+. The only hard dependency is `requests`.

```bash
cp wfbot.example.toml wfbot.toml   # then edit it
wfbot config                       # check what got picked up
```

## Quick start

```bash
# What is worth buying right now, with 500 platinum to spend?
wfbot scan --budget 500

# Everything about one item: both sides of the book, fair value, risks
wfbot item "Loki Prime Set"

# Copy the whisper for the cheapest seller straight to your clipboard
wfbot whisper "Loki Prime Set"

# Watch the market and notify me when something good shows up
wfbot watch --interval 600
```

The first `scan` is slow — it triages the whole tradable catalogue at the API's
rate limit, roughly 10–15 minutes. That result is cached for a day and reused,
so every later scan starts in seconds. `--refresh-universe` redoes it.

Sample output:

```
ITEM              KIND     BUY  SELL  EACH  MARGIN  QTY  TOTAL  VOL/DAY  CONF  SCORE  SELLER
----------------  -------  ---  ----  ----  ------  ---  -----  -------  ----  -----  ------------
Loki Prime Set    flip     96p  117p  +21p  22%     1    21p    21.00    93%   19.55  BulletJumper
Loki Prime Set    crossed  96p  105p  +9p   9%      1    9p     21.00    93%   8.38   BulletJumper
```

* **crossed** — somebody is *bidding* more than somebody else is *asking*. Buy
  from one, sell to the other. No price model involved, so this is the highest
  confidence trade on the board.
* **flip** — the cheapest listing is below what the item actually clears at. Buy
  it, relist one platinum under the next seller.

## Managing your own listings automatically

This is the part that runs unattended.

```bash
wfbot login                  # or: wfbot login --token '<JWT>' --ingame-name 'YourName'
wfbot orders                 # your listings versus the market
wfbot reprice                # dry run: shows every change it would make
wfbot reprice --live         # actually apply them
wfbot autopilot --live       # reprice + hunt for deals, forever
```

For every sell order it finds the cheapest live competitor and sits one
platinum under them; for every buy order it sits one platinum over the richest
live bidder. Both directions are bounded:

* **`sell_floor_ratio`** (default 0.60) — never sell below 60% of fair value,
  however far a lowballer walks the price down.
* **`buy_ceiling_ratio`** (default 0.75) — never bid above 75% of fair value.
* **`min_seconds_between_updates`** (default 15 min per order) — stops you and a
  rival ratcheting each other down all afternoon.
* **`max_updates_per_cycle`**, **`max_plat_in_buy_orders`** — hard caps on how
  much can change, and how much platinum can be committed, in one pass.

Safety defaults you have to deliberately override:

* Everything is a **dry run** unless you pass `--live`.
* `--live` *also* requires `live = true` under `[trade]` in your config. One
  flag alone can never move a price.
* `wfbot reprice --live` asks for confirmation unless you pass `--yes`.
* Every action, planned or executed, is written to the SQLite database and to
  `actions.jsonl`. `wfbot actions` prints the recent history.
* Nothing here can create or delete listings, only reprice the ones you made.

### Logging in

`wfbot login` signs in with your warframe.market email and password and caches
the returned JWT (mode 0600, in your state directory — the password itself is
never stored). If the site asks for a captcha, sign in with a browser, copy the
`JWT` cookie, and hand it over directly:

```bash
wfbot login --token '<paste the JWT here>' --ingame-name 'YourName'
```

Credentials can also come from the `WFM_EMAIL` / `WFM_PASSWORD` environment
variables so nothing lands in your shell history.

## How it decides what something is worth

Fair value is the **lower** of two independent estimates, which keeps a bad
number from turning into a phantom profit:

1. **History** — a volume-weighted median of the last 48 hours of closed sales,
   so one quiet hour at a silly price cannot set the reference. Falls back to
   the 90-day series for slow items.
2. **The book** — the median of the cheapest few live listings, *skipping the
   single cheapest*, which is usually either a typo or the one you are about to
   buy.

When those two disagree by more than 35%, the item is flagged rather than
silently trusted.

Only counterparties who are **`ingame`** count toward the live book. Someone
listed as offline cannot trade with you now, so their price is not a price.
Ranked mods, arcanes and subtyped items are split by rank and subtype before
anything is compared — a rank-0 and a maxed copy are different markets.

Every opportunity carries a **confidence** score (geometric mean of volume,
book depth, price dispersion, listing freshness, and history/book agreement)
and a **score**, which is simply expected platinum: `profit × units ×
confidence`. Position size is capped by what the item actually trades — buying
20 copies of something that sells twice a day means holding 20 copies.

Rivens, Kuva and Tenet weapons are excluded by default: their value comes from
rolls and bonus percentages, not from an order book, so statistical pricing
tells you nothing useful about them.

## Reading Warframe's log

Optional, off by default. Warframe writes a plain-text `EE.log`; tailing it
read-only tells the bot when you are in-game and when someone is trying to
trade with you. No hooks, no injection, no input — the same thing community
overlays have done for years.

```toml
[logwatch]
enabled = true
path = ""   # empty = auto-detect (Windows, and Proton/Wine on Linux)
```

```bash
wfbot logwatch    # tail it and print what matches
```

The log markers change between game updates, which is why every pattern lives
in the config file instead of the source. If a pattern stops matching, grep
your own `EE.log` and edit the list.

## Commands

| Command | What it does |
|---|---|
| `wfbot scan` | Rank profitable trades across the market |
| `wfbot item <name>` | Full detail on one item, with `--whisper` |
| `wfbot watch` | Rescan on a loop and notify |
| `wfbot orders` | Your listings versus the market |
| `wfbot reprice [--live]` | Reprice your listings |
| `wfbot autopilot [--live]` | Reprice and hunt continuously |
| `wfbot whisper <name>` | Build the in-game trade message |
| `wfbot logwatch` | Tail EE.log |
| `wfbot history <name>` | Locally recorded price history |
| `wfbot actions` | Audit log of everything the bot did |
| `wfbot login` | Authenticate for listing management |
| `wfbot config` / `wfbot cache` | Inspect state |

Global flags (`--json`, `--platform`, `-v`, `-q`, `-c/--config`) work on either
side of the command name.

## Being a good API citizen

warframe.market asks for no more than 3 requests per second. wfbot defaults to
2.5, shares one token bucket across all its threads, honours `Retry-After` on
429s, backs the whole pool off after one, and caches aggressively (order books
3 minutes, statistics 6 hours, the item list a week). Don't raise
`requests_per_second` above 3.

## Development

```bash
pip install -e ".[dev]"
python -m pytest          # 96 tests, no network access
```

The valuation and repricing logic is pure functions over an order book plus its
trade history, so all of it is tested offline against fixtures shaped like real
API payloads (`tests/fixtures/`).

```
wfbot/
  api.py        rate-limited, cached, retrying warframe.market client
  models.py     typed views over the API payloads
  analysis.py   fair value, opportunity ranking, price suggestions
  scanner.py    two-stage market scan
  trader.py     manages your own listings, with the guardrails
  storage.py    SQLite price history and the audit trail
  logwatch.py   read-only EE.log tail
  notify.py     desktop notifications, clipboard, whisper templates
  cli.py        command line interface
```

## Limits worth knowing

* Prices come from listings, and listings lie: someone can advertise 96p and
  refuse to sell at 96p. Confidence scoring and staleness filters reduce this;
  they cannot eliminate it.
* `ingame` on warframe.market means "logged into the game", not "reading their
  whispers". Expect some to ignore you.
* This is not investment advice for a video game economy. Start with a small
  budget, watch what the dry runs propose, and only then turn on `--live`.

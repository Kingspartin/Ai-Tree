# Ai-Tree
Visualized mobile ai app

---

## igwatch — Instagram username availability watcher

Watches one or more Instagram usernames and alerts you the moment one looks
free. No dependencies, no API key, no install step: pure Python standard
library, Python 3.9+.

```bash
python3 -m igwatch thenameiwant --desktop
```

That polls every 5 minutes, double-checks anything that looks free, notifies
you on the desktop, and exits once it has told you.

### Install (optional)

Running `python3 -m igwatch` from the repo root always works. To get an
`igwatch` command on your PATH:

```bash
pip install -e .
igwatch thenameiwant --desktop
```

### Getting alerted

Pass as many channels as you like; every alert goes to all of them.

| Flag | What it does |
| --- | --- |
| *(default)* | Prints a banner to the console |
| `--desktop` | Desktop notification (macOS `osascript`, Linux `notify-send`, Windows toast) |
| `--ntfy TOPIC` | Push to your phone via [ntfy.sh](https://ntfy.sh) — install the app, subscribe to the topic |
| `--webhook URL` | POSTs JSON; Slack and Discord webhook URLs are auto-formatted |
| `--email you@example.com` | SMTP mail (see env vars below) |
| `--exec 'CMD'` | Runs a command — `{username}` `{url}` `{status}` `{title}` `{body}` are substituted |
| `--no-console` | Suppress the console banner |

Phone push is the most useful one if you actually want to win the name:

```bash
python3 -m igwatch thenameiwant --ntfy my-private-topic-8f3a --desktop
```

Check your channels work before you rely on them:

```bash
python3 -m igwatch --test-notify --ntfy my-private-topic-8f3a --desktop
```

Email needs credentials in the environment, never on the command line:

```bash
export IGWATCH_SMTP_HOST=smtp.gmail.com
export IGWATCH_SMTP_PORT=587
export IGWATCH_SMTP_USER=you@gmail.com
export IGWATCH_SMTP_PASSWORD='app-password'   # an app password, not your login
python3 -m igwatch thenameiwant --email you@gmail.com
```

### Common recipes

```bash
# Several names at once, checked every 10 minutes, keep going after the first hit
python3 -m igwatch name_a name_b name_c --interval 10m --keep-watching --ntfy my-topic

# One-shot check, for cron or a shell script (exit 0 = available)
python3 -m igwatch thenameiwant --once && say "it is free"

# Paste any form of the name you like
python3 -m igwatch @thenameiwant
python3 -m igwatch https://www.instagram.com/thenameiwant/

# Run it in the background on a server, logging to a file
nohup python3 -m igwatch thenameiwant --ntfy my-topic --interval 15m > igwatch.log 2>&1 &
```

Cron, using the exit code:

```cron
*/15 * * * * cd /path/to/Ai-Tree && python3 -m igwatch thenameiwant --once --ntfy my-topic
```

systemd, if you want it to survive reboots:

```ini
# ~/.config/systemd/user/igwatch.service
[Unit]
Description=Watch an Instagram username
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 -m igwatch thenameiwant --ntfy my-topic --interval 15m --keep-watching
WorkingDirectory=/path/to/Ai-Tree
Restart=always
RestartSec=60

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now igwatch
```

### How it decides

Two independent probes, both hitting endpoints instagram.com itself uses:

1. **`api`** — `/api/v1/users/web_profile_info/`. A `404` or a null user object
   means free; a user object means taken.
2. **`page`** — a plain GET of the profile URL. `404`, or the "Sorry, this page
   isn't available" body, means free.

The default `--strategy auto` runs `api` first and falls back to `page` when
the answer is inconclusive. Pick one explicitly with `--strategy api|page`.

Three things keep it from crying wolf:

- **Confirmation.** An "available" answer is re-checked (`--confirmations 2` by
  default, `--confirm-delay 15s` apart). If the second look disagrees, no alert.
- **Blocked ≠ available.** `401`, `403`, `429`, login walls, and network errors
  are reported as *unknown* or *rate limited*, never as available.
- **Backoff.** Inconclusive answers double the wait, up to `--max-backoff`
  (default 1h), so a throttle doesn't turn into a ban.

### Not getting banned

Anonymous requests to Instagram are rate limited, and hammering them gets your
IP throttled — which makes the tool *less* likely to catch the moment, not
more. Defaults are deliberately calm: 5-minute interval, ±20% jitter, a 60s
hard floor, and at least 5s between any two requests.

If checks keep coming back `rate_limited`, pass a session cookie from a
logged-in browser:

```bash
export IGWATCH_SESSIONID='...'    # devtools → Application → Cookies → sessionid
python3 -m igwatch thenameiwant
```

That is your live Instagram session — treat it like a password, and know that
using it here is at your own risk under Instagram's terms.

### Accuracy caveat

"Available" here means *Instagram serves no profile at that URL*. That is the
best signal obtainable without attempting a signup, but it is not a promise the
name can be registered: Instagram holds recently deleted names for a while, and
reserves banned, trademark-flagged, and impersonation-risk names permanently.
Every alert says so. Go try to claim it — that is the only real test.

### State and repeat alerts

Progress is kept in `~/.local/state/igwatch/state.json` (override with
`--state-file`, disable with `--no-state`) so a restart doesn't re-alert you for
a name it already reported. If a name goes back to taken, the flag clears and
you'll be alerted again next time it frees up. `--repeat-alert` alerts on every
check while the name stays free.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Available (or a clean run / successful `--test-notify`) |
| 1 | Taken (`--once`) |
| 2 | Unknown or rate limited (`--once`) |
| 3 | Bad usage |
| 130 | Interrupted with Ctrl-C |

### All options

```bash
python3 -m igwatch --help
```

### Tests

```bash
python3 -m unittest discover -s tests -t .
```

49 tests, no network access required — the HTTP layer is faked, including
Instagram's login walls, throttling, and soft 404s.

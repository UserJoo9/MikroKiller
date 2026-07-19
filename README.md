# MikroKiller

Multi-adapter, multi-threaded captive portal brute-forcing tool with automatic MAC spoofing, built for authorized penetration testing of MikroTik and similar hotspot authentication systems.

> **Warning:** This tool is intended for **authorized security testing only**. Unauthorized use against networks you do not own or have explicit permission to test is **illegal**. The author assumes no liability for misuse.

---

## Features

- **Multi-adapter binding** — run attacks across multiple network interfaces simultaneously with source-IP-bound HTTP sessions
- **Auto MAC spoofing** — detect bans (403/429 + keyword matching) and automatically rotate MAC addresses to evade IP blocks; MACs are restored on exit via `atexit` handler
- **Smart portal detection** — scan gateways, common router IPs, and given URLs in parallel to auto-discover login portals with form field extraction
- **Pattern analysis** — learn positional character frequency from known credentials and generate statistically similar guesses
- **Multi-auth mode** — username-only, password-only, or both (supports voucher-style hotspots)
- **Dynamic thread scaling** — adjust thread count per adapter in real-time via the GUI (5–20 range)
- **Custom character sets** — digits, letters, alphanumeric, with Luhn checksum validation
- **Notifications** — Telegram Bot API and Discord webhook/bot for real-time alerts on valid finds
- **Profile save/load** — export and import attack configurations as JSON via native file dialogs
- **Stealth mode** — random delays between requests to reduce detection

---

## Version & Changelog

Version is tracked in `config.py` (`APP_VERSION`). Push to `main` with a bumped version triggers an automated GitHub Action that builds a standalone `.exe` with Nuitka and creates a GitHub Release.

### v1.0.0 — Initial release

- Core engine: multi-threaded credential brute-forcing with ThreadPoolExecutor
- GUI: Eel + PyWebView frontend with 4 tabs (Adapter, Configuration, Console, Analysis)
- MAC spoofing: WinReg + PowerShell-based adapter restart
- Portal scanning: parallel HTTP discovery across 12 router IPs × 8 paths
- Pattern analysis: positional frequency tables from colon-delimited or bare-code samples
- Notifications: Telegram + Discord integration
- Lab server: built-in MikroTik hotspot simulator for testing

### Bugs fixed post-release

| # | Bug | Fix |
|---|-----|-----|
| 1 | MAC generation swapped `first_char`/`second_char` | `first_char` now picks from `{2,6,A,E}` (locally-administered unicast) |
| 2 | `tried_pairs.clear()` at 1M caused retries | Changed to trim oldest 25%, keeping 750K most recent |
| 3 | File I/O inside lock slowed `save_valid_pair()` | Lock now only guards state; file writes and side-effects moved outside |
| 4 | Unreachable target continued silently | Aborts with `running=False` on all connection errors |
| 5 | `console_log()` classified `[-]` messages as errors | `[-]` prefix checked before `[+]`/`Failed`/`Error` keywords |
| 6 | Post-spoof no-reconnect after 60s was unrecoverable | Discards spoofing flag gracefully instead of pausing forever |
| 7 | Generator early-return exceeded `max_len` | Clamps `start+contains+end` by trimming `contains` |
| 8 | MAC never restored on exit | Added `atexit` handler `_restore_spoofed_macs()` |
| 9 | Lab `print_stats()` broken | Now prints formatted stats every 5s |
| 10 | Lab `BLOCK_SECS` was cosmetic | `block_start` tracking enforces proper block duration |
| 11 | UI desync on failed Eel call | Try/catch around `api_start_attack()` with `setRunningState(false)` |
| 12 | Silent `except: pass` in Eel callbacks | Changed to `print(file=sys.stderr)` |
| 13–14 | Fragile 1s sleep for Eel startup + TOCTOU race | Replaced with `wait_for_eel()` 5s poll loop at 100ms intervals |
| 15–18 | Dead code (`ProxyManager`, `detect_portal_url`) and empty `__init__.py` files | Removed dead code, added proper exports |
| 19 | Broken import after removing dead code | `from utils.network import get_network_adapters` |

---

## Architecture

### Project structure

```
MikroKiller/
├── app.py                         # Entry point — initializes Eel, polls for readiness, launches PyWebView window
│
├── api.py                         # Eel bridge layer — all @eel.expose functions
│   ├── console_log()              # Eel-safe log wrapper with message type classification
│   ├── api_get/set_adapters()     # Adapter discovery and selection
│   ├── api_smart_setup()          # Portal auto-detection (parallel HTTP scanner)
│   ├── api_start/pause/stop_attack()  # Attack lifecycle
│   ├── api_get_stats()            # Real-time stats polling
│   └── api_resume_after_reconnect()   # Wrong-network recovery
│
├── config.py                      # APP_VERSION, DEFAULT_CONFIG, router IPs, portal paths, keywords
│
├── core/
│   ├── __init__.py                # Exports VoucherCracker, VoucherGenerator, PatternAnalyzer
│   ├── cracker.py                 # Brute-force engine — main loop, thread pool, ban evasion, notifications
│   ├── generator.py               # Credential generation — charsets, Luhn, pattern-based
│   └── pattern_analyzer.py        # Positional frequency analysis from credential samples
│
├── utils/
│   ├── __init__.py                # Exports all public functions
│   ├── network.py                 # OS-level operations — adapter detection, MAC spoofing (WinReg + PowerShell), portal scanning
│   └── logger.py                  # Exception handler setup and file logging
│
├── web/
│   ├── index.html                 # Single-page GUI — 4 tabs + reconnect modal + stats display
│   ├── script.js                  # Frontend logic — Eel callbacks, config serialization, stats ticker
│   └── style.css                  # Dark glassmorphism theme — 775 lines
│
├── lab/
│   ├── lab_server.py              # MikroTik hotspot simulator — 384 valid 8-digit vouchers, rate limiting
│   └── START_LAB.bat              # Quick launcher
│
├── .github/workflows/
│   └── release.yml                # Auto-build with Nuitka + GitHub Release on version bump
│
├── local_config.json              # [runtime] Auto-persisted UI state (gitignored)
├── logs/                          # [runtime] Error logs (gitignored)
├── requirements.txt
├── LICENSE
└── README.md
```

### How it works — data flow

```
┌─────────┐   eel.expose()    ┌───────────┐
│ browser │ ◄──────────────►  │  api.py   │
│(web/)   │   api_*() calls   │ (bridge)  │
└─────────┘                   └─────┬─────┘
      ▲                             │
      │ eel.update_console()        │ calls into core
      │ eel.on_valid_found()        │
      │ eel.on_wrong_network()      ▼
      │ eel.on_attack_stopped() ┌──────────┐
      │                         │ cracker  │
      │                         │ .py      │
      │                         │ (engine) │
      │                         └────┬─────┘
      │                              │
      │                     ┌────────┴────────┐
      │                     │                 │
      │               ┌─────▼─────┐   ┌───────▼──────┐
      │               │ generator │   │  network.py  │
      │               │ .py       │   │  (MAC, scan) │
      │               │           │   │              │
      │               │ pattern_  │   │  HTTP reqs   │
      │               │ analyzer  │   │  → target    │
      │               └───────────┘   └───────┬──────┘
      │                                       │
      │                              requests │ (source-IP
      │                              sessions │  bound per
      │                                       │  adapter)
      │                                       ▼
      │                                 ┌──────────┐
      │                                 │  Router  │
      │                                 │  Portal  │
      │                                 └──────────┘
```

### Threading model

```
MAIN THREAD (app.py)
  └─ pywebview.start()  ← blocks until window closes

EEL THREAD (daemon)
  └─ eel.start()        ← WebSocket server, blocks

API THREAD (daemon, per attack)
  └─ VoucherCracker.start()
       ├─ ThreadPoolExecutor (threads × adapters workers)
       │    └─ each worker → check_pair() → HTTP POST
       └─ _auto_spoof_worker thread (per ban)
            └─ change_mac → wait → verify SSID
```

### Attack flow

1. **Launch** — `python app.py` starts Eel (local HTTP server), polls until ready, then opens PyWebView native window
2. **Select adapters** — pick one or more network adapters from the WMIC-discovered list
3. **Configure** — set target URL, auth mode (username/password/both), field names, character types, length ranges
4. **Optional: Scan** — auto-detect the login portal by probing common router IPs and paths in parallel
5. **Optional: Pattern analysis** — paste known credential samples to generate positional frequency tables
6. **Start** — engine spawns a thread pool with `threads × adapters` workers, each sending POST requests through a source-IP-bound session
7. **On ban** — if 403/429 or ban keywords detected, MAC address is spoofed via WinReg + PowerShell, adapter restarts, connection verified
8. **On valid find** — credential saved to file, Telegram/Discord notification sent, optional auto-stop
9. **Stop/Pause** — engine stops gracefully, threads join

### Response classification

| Signal | Indicates | Action |
|--------|-----------|--------|
| Status 403 or 429 | Rate-limited / banned | Trigger MAC spoof on that adapter |
| Body contains ban keywords | Rate-limited / banned | Trigger MAC spoof on that adapter |
| Body contains fail keywords | Invalid credentials | Log as invalid |
| Body contains `<input type="password">` | Still on login page | Log as invalid |
| Status 302 with no "login"/"error" in Location | Successful auth | Save valid pair |
| Status 200 with success keywords in body | Successful auth | Save valid pair |
| Network timeout / connection error | Transient failure | Return None (retry later) |

---

## Requirements

- **Windows 10/11** (uses Windows Registry for MAC spoofing, WMIC for adapter detection, PowerShell for adapter restart)
- **Python 3.11+**
- **Administrator privileges** (required for MAC spoofing — run terminal as Admin)
- **Microsoft Edge WebView2** (usually pre-installed on Windows 10/11; PyWebView uses it)

## Installation

```bash
git clone https://github.com/YoussefAlkhodary/MikroKiller.git
cd MikroKiller
pip install -r requirements.txt
```

## Usage

### Quick start

1. Open a terminal **as Administrator**
2. Navigate to the project directory
3. Run `python app.py`
4. The GUI window opens with 4 tabs

### Step-by-step

#### 1. Adapter tab
- Available network adapters are listed automatically
- Click on one or more adapter cards to select them
- Selected adapters get a green border highlight
- The attack runs across all selected adapters in parallel

#### 2. Configuration tab

| Setting | Description |
|---------|-------------|
| **Target URL** | The login form submission URL (e.g. `http://10.0.0.1/login`) |
| **Auth Mode** | `Username Only`, `Password Only`, or `Both` |
| **Field Names** | The `name` attributes of the username and password input fields |
| **Char Type** | `Digits (0-9)`, `Letters (a-z)`, or `Alphanumeric` |
| **Length** | Min and max length for generated credentials |
| **Static Value** | If set, this exact value is used instead of generated ones |
| **Prefix/Suffix/Contains** | Fixed substrings to include in generated credentials |
| **Luhn Check** | Only generate credentials that pass Luhn checksum validation |
| **Threads** | Number of threads per adapter (5–20, adjustable live) |
| **Stealth** | Add random delays between requests |
| **Auto Spoof** | Automatically change MAC address when banned |
| **Stop After** | Stop after finding N valid credentials |

Click **Scan** to auto-detect the login portal URL and form fields.

#### 3. Console tab
- Live log output showing engine activity, attempts, bans, and finds
- Start / Pause / Stop buttons
- Real-time stats: tried count, valid finds, errors, elapsed time, requests/second
- Valid hits panel shows discovered credentials

#### 4. Analysis tab
- Paste known credential samples (one per line)
- Click **Analyze** to generate positional frequency tables
- Results inform the generator for statistically similar guesses

### Lab testing

A local test server is included for safe experimentation:

```bash
cd lab
.\START_LAB.bat
```

Then configure MikroKiller:

| Setting     | Value                   |
|-------------|-------------------------|
| Target URL  | `http://localhost:8888`  |
| Auth Mode   | Username Only           |
| Field Name  | `username`              |
| Char Type   | Digits (0-9)            |
| Length      | Min: 8, Max: 8          |

The lab server simulates:
- MikroTik-style login page with 384 valid 8-digit voucher codes
- Rate limiting: 50 requests per 10-second window triggers a 15-second block
- Response patterns matching real MikroTik hotspot behavior

### Wrong network recovery

After a MAC spoof, if the adapter connects to a different network:
1. A modal appears showing the expected vs connected SSID
2. Manually reconnect to the correct network
3. Click **"I'm Connected — Resume"** to verify and continue
4. If SSID doesn't match after 60 seconds post-spoof, the adapter is skipped gracefully

---

## Build & Release

### Versioning

Version is tracked in `config.py`:

```python
APP_VERSION = '1.0.0'
```

To release a new version: bump `APP_VERSION`, commit, and push to `main`.

### Automated builds (GitHub Actions)

A workflow at `.github/workflows/release.yml` triggers on every push to `main`:

1. Reads `APP_VERSION` from `config.py`
2. Compares against the latest `v*` git tag
3. **If version changed** — builds a standalone `.exe` with Nuitka and creates a GitHub Release
4. **If version unchanged** — workflow exits silently, no build or release

The Nuitka build produces a single-file executable:
- `--standalone --onefile` — bundles everything including Python interpreter
- `--windows-console-mode=disable` — GUI-only, no console window
- `--include-data-dir=web=web` — embeds the frontend in the executable
- Output: `MikroKiller-v{VERSION}.exe` attached to the GitHub Release

### Manual build

```bash
pip install nuitka
nuitka --standalone --onefile --windows-console-mode=disable --include-data-dir=web=web --output-dir=dist app.py
```

---

## Configuration Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `target_url` | string | `http://10.0.0.1` | Login form action URL |
| `auth_mode` | string | `both` | `username`, `password`, or `both` |
| `threads` | int | `5` | Threads per network adapter (5–20) |
| `auto_spoof` | bool | `true` | Auto MAC spoof on ban |
| `stealth` | bool | `false` | Add random delays |
| `user_field` | string | `username` | Username input field name |
| `user_char_type` | string | `digits` | `digits`, `letters`, `alphanumeric` |
| `user_min_len` / `user_max_len` | int | `8` / `8` | Generated username length range |
| `pass_field` | string | `password` | Password input field name |
| `stop_after` | int | `1` | Stop after N valid finds |
| `telegram_token` | string | `''` | Telegram Bot API token |
| `telegram_chat` | string | `''` | Telegram chat ID |
| `discord_webhook` | string | `''` | Discord webhook URL |
| `discord_token` | string | `''` | Discord bot token |
| `discord_channel` | string | `''` | Discord channel ID |

Settings are auto-saved to `local_config.json` on every change. Profiles can be manually exported/imported via the **Save**/**Load** buttons in the GUI.

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| GUI Bridge | **Eel** 0.18.2 | Python↔JS via WebSocket, no REST boilerplate |
| Native Window | **PyWebView** 6.2.1 | Wraps Eel in native chromeless window |
| HTTP Client | **requests** ≥2.32.3 | Adapter-based source-IP binding |
| HTTP Core | **urllib3** ≥2.7 | Retry support, shipped with requests |
| Notifications | Telegram / Discord REST APIs | Pure HTTP POST, no SDK needed |
| OS | Windows 10/11 only | WMIC, PowerShell, WinReg for MAC spoofing |

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer

This software is provided for educational and authorized testing purposes only. Always obtain proper written authorization before testing on any network. The developer is not responsible for any misuse or damage caused by this tool.

---

Created by **Youssef Alkhodary**

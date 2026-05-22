# MikroKiller

MikroKiller is a penetration testing tool designed for auditing captive portal / hotspot authentication systems on MikroTik and other router platforms. It uses a multi-adapter, multi-threaded architecture to perform credential brute-forcing with automatic MAC spoofing for ban evasion.

> **Warning:** This tool is intended for authorized security testing only. Unauthorized use against networks you do not own or have explicit permission to test is illegal.

## Features

- **Multi-adapter binding** — Bind to multiple network interfaces simultaneously for increased throughput
- **Auto MAC spoofing** — When a ban is detected (403/429), automatically changes MAC address and reconnects
- **Smart portal detection** — Scans gateways and common router IPs to auto-detect login portals
- **Pattern analysis** — Analyzes known credentials to generate statistically similar guesses
- **Multi-auth mode** — Supports username-only, password-only, or both
- **Dynamic thread scaling** — Adjust thread count per adapter in real-time
- **Custom character sets** — Digits, letters, alphanumeric, Luhn checksum validation
- **Notifications** — Telegram and Discord integration for real-time alerts on valid finds
- **Profile save/load** — Save and load attack configurations

## Requirements

- Python 3.10+
- Windows (uses Windows Registry for MAC spoofing, IP helper API for adapter binding)
- Administrator privileges (required for MAC spoofing)

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/MikroKiller.git
cd MikroKiller
pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

### Lab Testing

A local test server is included for safe experimentation:

```bash
cd lab
.\START_LAB.bat
```

## Architecture

```
app.py                  ← Entry point (Eel GUI + PyWebView)
├── api.py              ← Eel-exposed API layer
├── config.py           ← Default config & constants
├── core/
│   ├── cracker.py     ← Brute-force engine (thread pool, ban evasion)
│   ├── generator.py   ← Credential generator (charsets, Luhn, patterns)
│   └── pattern_analyzer.py ← Statistical pattern learning from samples
├── utils/
│   ├── network.py     ← Adapter detection, MAC spoofing, portal scanning
│   └── logger.py      ← Exception handling & logging
└── web/
    ├── index.html     ← GUI frontend
    ├── script.js
    └── style.css
```

## Configuration

Settings are stored in `local_config.json` (auto-saved). Profiles can be exported/imported via the GUI.

| Key | Description |
|-----|-------------|
| `target_url` | Login form submission URL |
| `auth_mode` | `username`, `password`, or `both` |
| `threads` | Threads per network adapter |
| `auto_spoof` | Enable automatic MAC spoofing on ban |
| `stealth` | Adds random delays between requests |

## Credits

Created by Youssef Alkhodary.

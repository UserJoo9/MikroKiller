# MikroKiller

A multi-adapter, multi-threaded captive portal brute-forcing tool with automatic MAC spoofing, built for authorized penetration testing of MikroTik and similar hotspot authentication systems.

> **Warning:** This tool is intended for **authorized security testing only**. Unauthorized use against networks you do not own or have explicit permission to test is **illegal** and unethical. The author assumes no liability for misuse.

---

## Features

- **Multi-adapter binding** -- run attacks across multiple network interfaces simultaneously
- **Auto MAC spoofing** -- detect bans (403/429) and automatically rotate MAC address to evade IP bans
- **Smart portal detection** -- scan gateways and common router IPs to auto-discover login portals
- **Pattern analysis** -- learn from known credentials to generate statistically similar guesses
- **Multi-auth mode** -- username-only, password-only, or both (supports voucher-style hotspots)
- **Dynamic thread scaling** -- adjust thread count per adapter in real-time via the GUI
- **Custom character sets** -- digits, letters, alphanumeric, with Luhn checksum validation
- **Notifications** -- Telegram and Discord integration for real-time alerts on valid finds
- **Profile save/load** -- export and import attack configurations as JSON
- **Stealth mode** -- random delays between requests to reduce detection

## Requirements

- Python 3.10+
- Windows (uses Windows Registry for MAC spoofing and IP Helper API for adapter binding)
- Administrator privileges (required for MAC spoofing)

## Installation

```bash
git clone https://github.com/YoussefAlkhodary/MikroKiller.git
cd MikroKiller
pip install -r requirements.txt
```

## Usage

Run the GUI:

```bash
python app.py
```

### Lab Testing

A local test server simulating a MikroTik hotspot is included for safe experimentation:

```bash
cd lab
.\START_LAB.bat
```

Then configure MikroKiller with:

| Setting     | Value                      |
|-------------|----------------------------|
| Target URL  | `http://localhost:8888`     |
| Auth Mode   | Username Only              |
| Field Name  | `username`                 |
| Char Type   | Digits (0-9)               |
| Length      | Min: 8, Max: 8             |

## Architecture

```
app.py                   Entry point (Eel + PyWebView)
|-- api.py               Eel-exposed API layer
|-- config.py            Default config & constants
|-- core/
|   |-- cracker.py       Brute-force engine (thread pool, ban evasion)
|   |-- generator.py     Credential generator (charsets, Luhn, patterns)
|   +-- pattern_analyzer.py  Statistical pattern learning from samples
|-- utils/
|   |-- network.py       Adapter detection, MAC spoofing, portal scanning
|   +-- logger.py        Exception handling & logging
+-- web/
    |-- index.html       GUI frontend
    |-- script.js
    +-- style.css
```

## Configuration

Settings are auto-saved to `local_config.json`. Profiles can be exported/imported via the GUI.

| Key | Description |
|-----|-------------|
| `target_url` | Login form submission URL |
| `auth_mode` | `username`, `password`, or `both` |
| `threads` | Threads per network adapter (5--20) |
| `auto_spoof` | Enable automatic MAC spoofing on ban |
| `stealth` | Add random delays between requests |
| `telegram_token` | Telegram Bot API token for alerts |
| `telegram_chat` | Telegram chat ID for alerts |
| `discord_webhook` | Discord webhook URL for alerts |

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer

This software is provided for educational and authorized testing purposes only. Always obtain proper authorization before testing on any network. The developer is not responsible for any misuse or damage caused by this tool.

---

Created by **Youssef Alkhodary**

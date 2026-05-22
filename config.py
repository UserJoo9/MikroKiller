BRAND_NAME = 'MikroKiller'
APP_TITLE = 'MikroKiller'

DEFAULT_CONFIG = {
    'target_url': 'http://10.0.0.1',
    'session_name': 'Session_1',
    'auth_mode': 'both',
    'user_field': 'username',
    'user_static_val': '',
    'user_char_type': 'digits',
    'user_min_len': '8',
    'user_max_len': '8',
    'user_start': '',
    'user_end': '',
    'user_contains': '',
    'user_letter_case': 'lowercase',
    'user_use_luhn': False,
    'pass_field': 'password',
    'pass_static_val': '',
    'pass_char_type': 'digits',
    'pass_min_len': '8',
    'pass_max_len': '8',
    'pass_start': '',
    'pass_end': '',
    'pass_contains': '',
    'pass_letter_case': 'lowercase',
    'pass_use_luhn': False,
    'analytic_mode': False,
    'stealth': False,
    'auto_spoof': True,
    'telegram_token': '',
    'telegram_chat': '',
    'discord_webhook': '',
    'discord_token': '',
    'discord_channel': '',
    'scan_url': '',
    'threads': 50,
    'stop_after': 1
}

COMMON_ROUTER_IPS = [
    '10.0.0.1', '192.168.1.1', '192.168.0.1',
    '192.168.88.1', '172.16.0.1', '10.10.10.1',
    '192.168.100.1', '1.1.1.1',
    'localhost:8888', '127.0.0.1:8888',
    'localhost', '127.0.0.1',
]

PORTAL_PATHS = [
    '', '/login', '/hotspot/login', '/status',
    '/auth', '/portal', '/logon', '/ht/login',
]

SUCCESS_KEYWORDS = ['logout', 'connected', 'active', 'session', 'welcome', 'you are connected']
FAIL_KEYWORDS = ['incorrect', 'invalid', 'fail', 'try again', 'wrong']
BAN_KEYWORDS = ['too many requests', 'blocked', 'denied', 'quota', 'firewall']

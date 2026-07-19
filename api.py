import eel
import threading
import requests
import re
from core.cracker import VoucherCracker
from config import DEFAULT_CONFIG
from utils.network import get_network_adapters

cracker_instance = None
import os
import sys
import json

CONFIG_FILE = 'local_config.json'
app_config = DEFAULT_CONFIG.copy()


def load_local_config():
    global app_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                for k, v in loaded.items():
                    app_config[k] = v
        except Exception as e:
            print(f"Error loading local config: {e}")


load_local_config()
selected_adapter_ips = []


def console_log(message, msg_type='system'):
    try:
        # Check neutral '[-]' prefix first, then positive, then negative keywords
        if message.startswith('[-] '):
            msg_type = 'system'
        elif '[+]' in message or 'Success' in message:
            msg_type = 'success'
        elif '[!]' in message or 'Failed' in message or 'Error' in message:
            msg_type = 'error'
        eel.update_console(message, msg_type)()
    except Exception as e:
        print(f"[Eel Log Error] {e}", file=sys.stderr)


@eel.expose
def api_get_config():
    return app_config


@eel.expose
def api_analyze_samples(samples_text):
    try:
        from core.pattern_analyzer import PatternAnalyzer
        pa = PatternAnalyzer(manual_samples=samples_text)
        pa.load_patterns()
        result = {}
        if pa.user_patterns:
            result['user_patterns'] = [
                {k: round(v, 3) for k, v in pos.items()}
                for pos in pa.user_patterns
            ]
        if pa.pass_patterns:
            result['pass_patterns'] = [
                {k: round(v, 3) for k, v in pos.items()}
                for pos in pa.pass_patterns
            ]
        return result
    except Exception as e:
        return {'error': str(e)}


@eel.expose
def api_auto_save_config(config_dict):
    global app_config
    if isinstance(config_dict, dict):
        app_config.update(config_dict)
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(app_config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error auto-saving config: {e}")
    return False


@eel.expose
def api_get_adapters():
    return get_network_adapters()


@eel.expose
def api_set_adapters(ips):
    global selected_adapter_ips
    selected_adapter_ips = ips if isinstance(ips, list) else []
    return True


@eel.expose
def api_get_default_adapter_ip():
    from utils.network import _get_default_route_local_ip
    return _get_default_route_local_ip() or ''


@eel.expose
def api_smart_setup(target_url):
    try:
        import urllib3, concurrent.futures
        from urllib.parse import urljoin
        from config import COMMON_ROUTER_IPS, PORTAL_PATHS
        import subprocess
        urllib3.disable_warnings()

        candidates = []

        if target_url and target_url.strip():
            url = target_url.strip()
            if not url.startswith('http'):
                url = 'http://' + url
            candidates.append(url)

        try:
            out = subprocess.check_output('ipconfig', shell=True, timeout=5).decode(errors='ignore')
            gateways = re.findall(r'Default Gateway[ .]*:\s*(\d+\.\d+\.\d+\.\d+)', out)
            for gw in gateways:
                for path in PORTAL_PATHS:
                    candidates.append(f'http://{gw}{path}')
        except Exception:
            pass

        for ip in COMMON_ROUTER_IPS:
            for path in PORTAL_PATHS:
                candidates.append(f'http://{ip}{path}')

        seen = set()
        unique_candidates = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        def is_login_page(text):
            low = text.lower()
            return any(k in low for k in ['<input', 'username', 'password', 'voucher', 'login', 'hotspot'])

        def try_fetch(url):
            try:
                r = requests.get(url, timeout=2, verify=False, allow_redirects=True)
                if r.status_code == 200 and is_login_page(r.text):
                    return r
            except Exception:
                pass
            return None

        def parse_portal(resp):
            content = resp.text
            final_url = resp.url

            action_m = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', content, re.I)
            form_action = urljoin(final_url, action_m.group(1) if action_m else '/login')

            inputs = re.findall(r'<input([^>]*)>', content, re.I)
            all_fields = {}
            user_field = None
            pass_field = None

            for attrs in inputs:
                name_m = re.search(r'name=["\']([^"\']+)["\']', attrs, re.I)
                type_m = re.search(r'type=["\']([^"\']+)["\']', attrs, re.I)
                if not name_m:
                    continue
                fname = name_m.group(1)
                ftype = type_m.group(1).lower() if type_m else 'text'
                all_fields[fname] = ftype

                if ftype in ('text', 'email') and not user_field and re.search(
                        r'(user|name|login|email)', fname, re.I):
                    user_field = fname
                if ftype == 'password' and not pass_field:
                    pass_field = fname

            if not user_field:
                for n, t in all_fields.items():
                    if t in ('text', 'email'):
                        user_field = n
                        break

            if not user_field:
                return None

            auth_mode = 'both' if pass_field else 'username'
            result_fields = {'username': user_field}
            if pass_field:
                result_fields['password'] = pass_field

            return {
                'success': True,
                'url': final_url,
                'form_action': form_action,
                'auth_mode': auth_mode,
                'fields': result_fields,
                'all_fields': all_fields,
            }

        found = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
            future_map = {ex.submit(try_fetch, u): u for u in unique_candidates}
            for f in concurrent.futures.as_completed(future_map, timeout=15):
                resp = f.result()
                if resp:
                    parsed = parse_portal(resp)
                    if parsed:
                        found = parsed
                        break

        if found:
            return found

        return {
            'success': False,
            'message': 'No login portal found. Make sure the router/lab is reachable on this network.'
        }

    except Exception as e:
        return {'success': False, 'error': f'Scanner exception: {str(e)}'}


@eel.expose
def api_start_attack(frontend_config):
    global cracker_instance
    app_config.update(frontend_config)
    cracker_instance = VoucherCracker(**app_config, bound_adapter_ips=selected_adapter_ips)
    cracker_instance.log = lambda msg: console_log(msg)

    def _on_wrong_network(expected_ssid, got_ssid, new_mac):
        try:
            eel.on_wrong_network(expected_ssid, got_ssid, new_mac)()
        except Exception as e:
            print(f'Eel wrong_network notify error: {e}')

    cracker_instance.on_wrong_network = _on_wrong_network

    def run_cracker():
        cracker_instance.start()
        try:
            eel.on_attack_stopped()()
            console_log("Engine stopped.", 'warning')
        except:
            pass

    thread = threading.Thread(target=run_cracker)
    thread.daemon = True
    thread.start()
    return True


@eel.expose
def api_pause_attack():
    global cracker_instance
    if cracker_instance:
        cracker_instance.paused = not cracker_instance.paused
        state = "PAUSED" if cracker_instance.paused else "RESUMED"
        console_log(f"[*] Engine {state}", 'warning')
        return cracker_instance.paused
    return False


@eel.expose
def api_update_threads(new_threads):
    global cracker_instance
    if cracker_instance:
        try:
            val = int(new_threads)
            if val > 0:
                cracker_instance.threads = max(min(val, 20), 5)
                return True
        except Exception as e:
            print(f"Error updating threads: {e}")
    return False


@eel.expose
def api_stop_attack():
    global cracker_instance
    if cracker_instance:
        cracker_instance.stop()
        console_log("[*] Stopping engine... Waiting for threads to close.", 'warning')
    return True


@eel.expose
def api_get_stats():
    global cracker_instance
    if cracker_instance and cracker_instance.start_time:
        return cracker_instance.get_stats()
    return {'tried': 0, 'valid': 0, 'errors': 0, 'elapsed': 0, 'rps': 0}


@eel.expose
def api_resume_after_reconnect():
    global cracker_instance
    if cracker_instance:
        from utils.network import get_current_wifi_info
        import time
        ignore_ssids = {'identifying...', 'identifying', 'unidentified network', ''}
        all_ok = True
        failed_adapters = []
        expected_ssids = []

        waiting_ips = list(cracker_instance._waiting_reconnect)
        for ip in waiting_ips:
            alias = cracker_instance.ip_to_alias.get(ip)
            info = get_current_wifi_info(adapter_ip=None, adapter_alias=alias)
            origin = cracker_instance.origin_wifi_info.get(ip, {})
            expected = origin.get('ssid')
            current = info.get('ssid') if info else 'not connected'

            if current.lower().strip() in ignore_ssids:
                time.sleep(3)
                info = get_current_wifi_info(adapter_ip=None, adapter_alias=alias)
                current = info.get('ssid') if info else 'not connected'

            if expected and current == expected:
                cracker_instance._waiting_reconnect.discard(ip)
                cracker_instance._spoofing_ips.discard(ip)
            elif current.lower().strip() in ignore_ssids:
                console_log(f'[*] Adapter {ip} still identifying, force-resuming (user confirmed).', 'warning')
                cracker_instance._waiting_reconnect.discard(ip)
                cracker_instance._spoofing_ips.discard(ip)
            else:
                all_ok = False
                failed_adapters.append(current)
                expected_ssids.append(expected or 'Unknown')

        if all_ok or not cracker_instance._waiting_reconnect:
            cracker_instance.paused = False
            console_log(f'[+] Network verified — resuming attack.', 'success')
            return {'ok': True}
        else:
            console_log(f'[!] Still on wrong network(s): "{", ".join(failed_adapters)}". Expected: "{", ".join(expected_ssids)}"', 'error')
            return {'ok': False, 'current': failed_adapters[0] if failed_adapters else '', 'expected': expected_ssids[0] if expected_ssids else ''}
    return {'ok': False, 'current': '', 'expected': ''}


import webview
from webview import FileDialog
import json
import os


@eel.expose
def api_save_profile(config_dict):
    try:
        if not webview.windows:
            return False
        window = webview.windows[0]
        result = window.create_file_dialog(FileDialog.SAVE, directory=os.getcwd(), save_filename='profile.json')
        if result and len(result) > 0:
            with open(result[0], 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4)
            return True
        return False
    except Exception as e:
        print(f"Save error: {e}")
        return False


@eel.expose
def api_load_profile():
    try:
        if not webview.windows:
            return None
        window = webview.windows[0]
        result = window.create_file_dialog(FileDialog.OPEN, directory=os.getcwd())
        if result and len(result) > 0:
            with open(result[0], 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            return config_dict
        return None
    except Exception as e:
        print(f"Load error: {e}")
        return None

import subprocess
import re
import socket
import requests
import concurrent.futures
from config import COMMON_ROUTER_IPS, PORTAL_PATHS

try:
    import winreg
except ImportError:
    winreg = None


def get_network_adapters():
    adapters = []

    try:
        ps_cmd = (
            'powershell -NoProfile -Command "'
            'Get-NetIPAddress -AddressFamily IPv4 | '
            'Where-Object { $_.IPAddress -notlike \'169.254.*\' -and $_.IPAddress -ne \'127.0.0.1\' } | '
            'Select-Object InterfaceAlias, IPAddress, InterfaceIndex | '
            'ConvertTo-Csv -NoTypeInformation'
            '"'
        )
        out = subprocess.check_output(ps_cmd, shell=True, timeout=10).decode(errors='ignore')
        lines = [l.strip().strip('"') for l in out.strip().splitlines()]

        for line in lines[1:]:
            if not line:
                continue
            parts = [p.strip().strip('"') for p in line.split(',')]
            if len(parts) < 2:
                continue
            alias = parts[0]
            ip = parts[1]

            if not ip or not re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                continue

            skip_keywords = ['loopback', 'tunnel', 'isatap', 'teredo', '6to4',
                             'pseudo', 'vmware', 'virtualbox', 'hyper-v', 'vethernet']
            if any(k in alias.lower() for k in skip_keywords):
                continue

            adapters.append({
                'name': alias,
                'ip': ip,
                'description': alias,
                'is_default': False,
            })

    except Exception:
        pass

    if not adapters:
        try:
            out = subprocess.check_output('ipconfig /all', shell=True, timeout=8).decode(errors='ignore')
            blocks = re.split(r'\r?\n(?=[^\s])', out)

            for block in blocks:
                lines = block.strip().splitlines()
                if not lines:
                    continue

                header = lines[0].strip().rstrip(':')
                skip_keywords = ['loopback', 'tunnel', 'isatap', 'teredo', '6to4']
                if any(k in header.lower() for k in skip_keywords):
                    continue

                ip_match = re.search(r'IPv4 Address[\s.]*:\s*([\d.]+)', block)
                if not ip_match:
                    continue

                ip = ip_match.group(1).strip()
                if ip.startswith('169.254') or ip == '127.0.0.1':
                    continue

                desc_match = re.search(r'Description[\s.]*:\s*(.+)', block)
                description = desc_match.group(1).strip() if desc_match else header

                adapters.append({
                    'name': header,
                    'ip': ip,
                    'description': description,
                    'is_default': False,
                })

        except Exception:
            pass

    default_ip = _get_default_route_local_ip()
    for a in adapters:
        a['is_default'] = (a['ip'] == default_ip)

    adapters.sort(key=lambda x: (0 if x['is_default'] else 1, x['name']))

    return adapters


def _get_default_route_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    try:
        out = subprocess.check_output('route print 0.0.0.0', shell=True, timeout=5).decode(errors='ignore')
        m = re.search(r'0\.0\.0\.0\s+0\.0\.0\.0\s+[\d.]+\s+([\d.]+)', out)
        if m:
            return m.group(1).strip()
    except Exception:
        pass

    return None


class SourceAddressAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, source_address, **kwargs):
        self.source_address = (source_address, 0)
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['source_address'] = self.source_address
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs['source_address'] = self.source_address
        return super().proxy_manager_for(*args, **kwargs)


def get_current_wifi_info(adapter_ip=None, adapter_alias=None):
    alias_filter = ""
    alias = adapter_alias
    if not alias and adapter_ip:
        try:
            ps_alias = f'powershell -NoProfile -Command "(Get-NetIPAddress -IPAddress \'{adapter_ip}\').InterfaceAlias"'
            alias = subprocess.check_output(ps_alias, shell=True, timeout=5).decode(errors='ignore').strip()
            if not alias:
                ps_alias = f'powershell -NoProfile -Command "Get-NetAdapter | Where-Object {{$_.Status -eq \'Up\'}} | Select-Object -ExpandProperty Name"'
                aliases = subprocess.check_output(ps_alias, shell=True, timeout=5).decode(errors='ignore').splitlines()
                if aliases:
                    alias = aliases[0].strip()
        except:
            pass

    if alias:
        alias = alias.replace("'", "''")
        alias_filter = f" | Where-Object InterfaceAlias -eq '{alias}'"

    try:
        ps_cmd = f'powershell -NoProfile -Command "(Get-NetConnectionProfile{alias_filter} | Select-Object -ExpandProperty Name)"'
        out_ps = subprocess.check_output(ps_cmd, shell=True, timeout=5).decode(errors='ignore').strip()
        if out_ps:
            ssid = [line.strip() for line in out_ps.splitlines() if line.strip()][0]
            bssid = ''

            try:
                out_netsh = subprocess.check_output('netsh wlan show interfaces', shell=True).decode(errors='ignore')
                bssid_m = re.search(r'BSSID\s*:\s*([^\r\n]+)', out_netsh)
                if bssid_m:
                    bssid = bssid_m.group(1).strip().upper()
            except:
                pass

            return {
                'ssid': ssid,
                'bssid': bssid
            }
    except:
        pass

    try:
        out = subprocess.check_output(
            'netsh wlan show interfaces', shell=True
        ).decode(errors='ignore')

        ssid_m = re.search(r'SSID\s*:\s*([^\r\n]+)', out)
        bssid_m = re.search(r'BSSID\s*:\s*([^\r\n]+)', out)

        if ssid_m:
            return {
                'ssid': ssid_m.group(1).strip(),
                'bssid': bssid_m.group(1).strip().upper() if bssid_m else '',
            }
    except Exception:
        pass
    return None


def detect_portal_url():
    detected_urls = set()
    gateways = set()

    try:
        result = subprocess.check_output('ipconfig', shell=True).decode(errors='ignore')
        matches = re.findall(r'Default Gateway[ .]*: (\d+\.\d+\.\d+\.\d+)', result)
        gateways.update(matches)

        if not gateways:
            res2 = subprocess.check_output('route print 0.0.0.0', shell=True).decode(errors='ignore')
            matches2 = re.findall(r'\s0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)', res2)
            gateways.update(matches2)
    except:
        pass

    for gw in gateways:
        for path in PORTAL_PATHS:
            detected_urls.add(f'http://{gw}{path}')

    for ip in COMMON_ROUTER_IPS:
        for path in PORTAL_PATHS:
            detected_urls.add(f'http://{ip}{path}')

    def check_url(url):
        try:
            resp = requests.get(url, timeout=2, verify=False, allow_redirects=True)
            if resp.status_code == 200:
                content = resp.text.lower()
                keywords = ['login', 'username', 'password', 'voucher', 'hotspot', 'connect', 'access']
                if any(x in content for x in keywords):
                    return url
        except:
            pass
        return None

    found = None
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_url, u): u for u in detected_urls}
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                found = res
                break

    return found


def get_wifi_adapter_reg(adapter_ip=None):
    if not winreg:
        return None, None

    target_desc = None
    if adapter_ip:
        try:
            ps_cmd = f'powershell -NoProfile -Command "(Get-NetAdapter -InterfaceIndex (Get-NetIPAddress -IPAddress \'{adapter_ip}\').InterfaceIndex).InterfaceDescription"'
            target_desc = subprocess.check_output(ps_cmd, shell=True, timeout=5).decode(errors='ignore').strip()
        except:
            pass

    try:
        root = winreg.HKEY_LOCAL_MACHINE
        path = r'SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}'

        with winreg.OpenKey(root, path) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                subkey_name = winreg.EnumKey(key, i)
                if subkey_name == 'Properties':
                    continue

                try:
                    with winreg.OpenKey(key, subkey_name, 0, winreg.KEY_READ | winreg.KEY_WRITE) as subkey:
                        desc, _ = winreg.QueryValueEx(subkey, 'DriverDesc')
                        if target_desc:
                            if desc.lower() == target_desc.lower():
                                return subkey_name, desc
                        else:
                            if 'Wi-Fi' in desc or 'Wireless' in desc or '802.11' in desc:
                                return subkey_name, desc
                except:
                    continue
    except:
        pass

    return None, None


def change_mac(adapter_ip=None):
    import random
    import time

    adapter_key, driver_desc = get_wifi_adapter_reg(adapter_ip)
    if not adapter_key:
        return (False, 'No Wi-Fi adapter found in Registry.')

    try:
        first_char = random.choice('0123456789ABCDEF')
        second_char = random.choice('26AE')
        rest = ''.join(random.choices('0123456789ABCDEF', k=10))
        new_mac = first_char + second_char + rest

        root = winreg.HKEY_LOCAL_MACHINE
        path = rf'SYSTEM\CurrentControlSet\Control\Class\{{4d36e972-e325-11ce-bfc1-08002be10318}}\{adapter_key}'

        with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, 'NetworkAddress', 0, winreg.REG_SZ, new_mac)

        subprocess.run(
            f'powershell "Get-NetAdapter | Where-Object {{$_.InterfaceDescription -eq \'{driver_desc}\'}} | Disable-NetAdapter -Confirm:$false"',
            shell=True
        )
        time.sleep(1.5)
        subprocess.run(
            f'powershell "Get-NetAdapter | Where-Object {{$_.InterfaceDescription -eq \'{driver_desc}\'}} | Enable-NetAdapter -Confirm:$false"',
            shell=True
        )

        return (True, new_mac)
    except Exception as e:
        return (False, str(e))


def restore_mac(adapter_ip=None):
    import time

    adapter_key, driver_desc = get_wifi_adapter_reg(adapter_ip)
    if not adapter_key:
        return (False, 'No Wi-Fi adapter found')

    try:
        root = winreg.HKEY_LOCAL_MACHINE
        path = rf'SYSTEM\CurrentControlSet\Control\Class\{{4d36e972-e325-11ce-bfc1-08002be10318}}\{adapter_key}'

        with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, 'NetworkAddress')
            except FileNotFoundError:
                pass

        subprocess.run(
            f'powershell "Get-NetAdapter | Where-Object {{$_.InterfaceDescription -eq \'{driver_desc}\'}} | Disable-NetAdapter -Confirm:$false"',
            shell=True
        )
        time.sleep(1.5)
        subprocess.run(
            f'powershell "Get-NetAdapter | Where-Object {{$_.InterfaceDescription -eq \'{driver_desc}\'}} | Enable-NetAdapter -Confirm:$false"',
            shell=True
        )

        return (True, 'MAC restored')
    except Exception as e:
        return (False, str(e))

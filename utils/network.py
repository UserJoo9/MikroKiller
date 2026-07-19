import subprocess
import re
import socket
import requests
import atexit

try:
    import winreg
except ImportError:
    winreg = None

# Track spoofed adapters for automatic MAC restoration on exit
_spoofed_adapter_registry = []


def _restore_spoofed_macs():
    """Restore original MAC of all adapters that were spoofed this session."""
    for adapter_key, driver_desc in _spoofed_adapter_registry:
        try:
            root = winreg.HKEY_LOCAL_MACHINE
            path = rf'SYSTEM\CurrentControlSet\Control\Class\{{4d36e972-e325-11ce-bfc1-08002be10318}}\{adapter_key}'
            with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, 'NetworkAddress')
                except FileNotFoundError:
                    pass
            subprocess.run(
                f'powershell -NoProfile "Restart-NetAdapter -InterfaceDescription \'{driver_desc}\' -Confirm:$false"',
                shell=True, capture_output=True
            )
        except Exception:
            pass


def get_network_adapters():
    adapters = []

    try:
        import csv, io
        out = subprocess.check_output(
            'wmic nicconfig where IPEnabled=TRUE get IPAddress, Description /format:csv',
            shell=True, timeout=5
        ).decode(errors='ignore')

        skip_keywords = ['loopback', 'tunnel', 'isatap', 'teredo', '6to4',
                         'pseudo', 'vmware', 'virtualbox', 'hyper-v', 'vethernet']

        lines = [l for l in out.splitlines() if l.strip()]
        if len(lines) < 2:
            raise ValueError('no data')

        reader = csv.DictReader(lines)
        for row in reader:
            desc = (row.get('Description') or '').strip()
            ips_str = (row.get('IPAddress') or '').strip().strip('{}')
            if not desc or not ips_str:
                continue
            if any(k in desc.lower() for k in skip_keywords):
                continue

            ips = [ip.strip() for ip in ips_str.split(';') if ip.strip()]
            ipv4 = next(
                (ip for ip in ips
                 if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip)
                 and not ip.startswith('169.254')
                 and ip != '127.0.0.1'),
                None
            )
            if not ipv4:
                continue

            adapters.append({
                'name': desc,
                'ip': ipv4,
                'description': desc,
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
        s.settimeout(1)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    try:
        out = subprocess.check_output('route print 0.0.0.0', shell=True, timeout=3).decode(errors='ignore')
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

    adapter_key, driver_desc = get_wifi_adapter_reg(adapter_ip)
    if not adapter_key:
        return (False, 'No Wi-Fi adapter found in Registry.')

    try:
        # Locally-administered unicast MAC: first hex digit ∈ {2,6,A,E}
        first_char = random.choice('26AE')
        second_char = random.choice('0123456789ABCDEF')
        rest = ''.join(random.choices('0123456789ABCDEF', k=10))
        new_mac = first_char + second_char + rest

        root = winreg.HKEY_LOCAL_MACHINE
        path = rf'SYSTEM\CurrentControlSet\Control\Class\{{4d36e972-e325-11ce-bfc1-08002be10318}}\{adapter_key}'

        with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, 'NetworkAddress', 0, winreg.REG_SZ, new_mac)

        subprocess.run(
            f'powershell -NoProfile "Restart-NetAdapter -InterfaceDescription \'{driver_desc}\' -Confirm:$false"',
            shell=True, capture_output=True
        )

        # Register for automatic MAC restoration on exit
        _spoofed_adapter_registry.append((adapter_key, driver_desc))
        if len(_spoofed_adapter_registry) == 1:
            atexit.register(_restore_spoofed_macs)

        return (True, new_mac)
    except Exception as e:
        return (False, str(e))


def restore_mac(adapter_ip=None):
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
            f'powershell -NoProfile "Restart-NetAdapter -InterfaceDescription \'{driver_desc}\' -Confirm:$false"',
            shell=True, capture_output=True
        )

        return (True, 'MAC restored')
    except Exception as e:
        return (False, str(e))

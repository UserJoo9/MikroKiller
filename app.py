import os
import sys
import urllib3
import socket
import threading
import time

urllib3.disable_warnings(urllib3.exceptions .InsecureRequestWarning)

from utils.logger import setup_exception_handlers
setup_exception_handlers()

from config import APP_TITLE

def get_free_port():
    s =socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    port =s.getsockname()[1]
    s.close()
    return port

def main():

    try :
        import eel
        import webview
        import api

        web_dir =os.path .join(os.path .dirname(os.path .abspath(__file__)), 'web')
        eel.init(web_dir)

        port =get_free_port()

        def start_eel():
            try :

                eel.start('index.html', mode =None, block =True, port =port)
            except Exception as e :
                print(f"Eel server stopped: {e}")

        eel_thread =threading.Thread(target =start_eel)
        eel_thread.daemon =True
        eel_thread.start()

        time.sleep(1.0)

        import ctypes
        user32 =ctypes.windll .user32
        sw =user32.GetSystemMetrics(0)
        sh =user32.GetSystemMetrics(1)
        ww, wh =1000, 700
        pos_x =(sw //2)-(ww //2)
        pos_y =(sh //2)-(wh //2)

        window_url =f'http://localhost:{port}/index.html'
        webview.create_window(APP_TITLE, window_url, width =ww, height =wh, x =pos_x, y =pos_y, min_size =(1000, 700), background_color ='#0b0510')
        webview.start()

    except ImportError as e :
        print(f"Failed to start GUI.Missing dependencies: {e}")
        print("Please run: pip install eel pywebview")
        sys.exit(1)

if __name__ =='__main__':
    main()

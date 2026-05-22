import logging
import os
import sys
from tkinter import messagebox

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'cracker_errors.log')

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_error(msg):
    logging.error(msg)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error('Unhandled exception', exc_info=(exc_type, exc_value, exc_traceback))
    try:
        messagebox.showerror(
            'MikroKiller Crash',
            f'An unexpected error occurred.\nDetails saved to \'{LOG_PATH}\'.\n\nError: {exc_value}'
        )
    except:
        pass

def setup_exception_handlers():
    sys.excepthook = handle_exception

    import tkinter as tk
    def tk_handle_exception(self, exc, val, tb):
        handle_exception(exc, val, tb)
    tk.Tk.report_callback_exception = tk_handle_exception

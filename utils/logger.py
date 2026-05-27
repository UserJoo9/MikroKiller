import os
import sys
import logging

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'cracker_errors.log')

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

_logger = logging.getLogger('MikroKiller')


def log_error(msg):
    _logger.error(msg)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    _logger.error('Unhandled exception', exc_info=(exc_type, exc_value, exc_traceback))
    print(f'[FATAL] {exc_type.__name__}: {exc_value}', file=sys.stderr)
    print(f'  Details saved to {LOG_PATH}', file=sys.stderr)


def setup_exception_handlers():
    sys.excepthook = handle_exception

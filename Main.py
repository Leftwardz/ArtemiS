"""Entry point — python main.py ou python Main.py"""
import os
import sys


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


os.chdir(_app_dir())
for _required_dir in ('temp', 'logs'):
    os.makedirs(_required_dir, exist_ok=True)

from app.bootstrap import main

if __name__ == "__main__":
    main()

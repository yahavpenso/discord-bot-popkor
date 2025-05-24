import subprocess
import sys
from watchfiles import run_process

def main():
    # For watchfiles 1.x, the correct signature is:
    # run_process(path, *, target=...)
    run_process('.', target=[sys.executable, 'bot.py'])

if __name__ == '__main__':
    main()

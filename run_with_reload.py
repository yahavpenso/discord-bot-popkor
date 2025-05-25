import subprocess
import sys
from watchfiles import run_process

def start_bot():
    subprocess.run([sys.executable, 'bot.py'])

def main():
    # For watchfiles 0.x, target must be a top-level callable on Windows
    run_process('.', target=start_bot)

if __name__ == '__main__':
    main()

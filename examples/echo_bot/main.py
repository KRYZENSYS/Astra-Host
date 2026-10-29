import os
import time
from datetime import datetime

DATA_DIR = os.getenv("DATA_DIR", "/data")
COUNTER_FILE = os.path.join(DATA_DIR, "counter.txt")

def main():
    print(f"[{datetime.utcnow().isoformat()}] EchoBot starting up...")
    print(f"[{datetime.utcnow().isoformat()}] Using persistent DATA_DIR: {DATA_DIR}")

    os.makedirs(DATA_DIR, exist_ok=True)

    iteration = 0
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                content = f.read().strip()
                if content.isdigit():
                    iteration = int(content)
                    print(f"[{datetime.utcnow().isoformat()}] Resumed counter from previous run: {iteration}")
        except Exception as e:
            print(f"[Warning] Could not read existing counter: {e}")

    while True:
        iteration += 1
        with open(COUNTER_FILE, "w") as f:
            f.write(str(iteration))
        
        print(f"[{datetime.utcnow().isoformat()}] [EchoBot] Iteration #{iteration}: Bot is alive and /data/counter.txt updated.", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    main()

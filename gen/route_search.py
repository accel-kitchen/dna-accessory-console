"""Driver: run route_board.py with random seeds; nets that fail are moved to the front of the order and retried."""
import subprocess, os, sys, json
seed = sys.argv[1]; out = f'gen/_runs/b{seed}.json'
prio = []
for it in range(14):
    env = dict(os.environ, SEED=seed, WS='0.15', CL='0.16', WP='0.2', EDGE='0.56', VIAD='0.56', OUT=out, PRIO='|'.join(prio))
    r = subprocess.run([sys.executable, 'gen/route_board.py'], env=env, capture_output=True, text=True)
    failed = json.load(open(out))['failed']
    print(seed, it, len(failed), failed, flush=True)
    if not failed:
        break
    prio = failed + [n for n in prio if n not in failed]

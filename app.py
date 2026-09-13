"""
Entry point for Render. Render's free tier only supports web services
(processes that bind to a port), not standalone background workers --
so this Flask app exists mainly to give Render something to health-check,
while the actual trading loop runs in a background thread.

IMPORTANT: Render's free web services spin down after ~15 minutes of no
inbound HTTP traffic, which would pause your bot's thread along with it.
See README.md for how to keep it alive for free with an uptime pinger.
"""

import os
import threading

from flask import Flask, jsonify

from bot.main_loop import run_forever
from bot.state import load_state

app = Flask(__name__)

_bot_thread_started = False
_lock = threading.Lock()


def _start_bot_thread():
    global _bot_thread_started
    with _lock:
        if not _bot_thread_started:
            t = threading.Thread(target=run_forever, daemon=True)
            t.start()
            _bot_thread_started = True


@app.route("/")
def index():
    return jsonify({"status": "alive", "message": "Survival trading bot is running."})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/status")
def status():
    state = load_state()
    return jsonify(state)


_start_bot_thread()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

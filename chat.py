"""DevFest Maysan 2026: the same agent, behind a chat page in the browser.

This file adds no agent logic. It reuses the tools, the declarations and
ask_model() from agent.py, plus the extra tools in more_tools.py and
university_tools.py, and runs the same loop one step at a time so the page can
show every tool call as it happens. The approval that agent.py asks
for in the terminal becomes two buttons on the page.

Run:   python chat.py
Then:  the browser opens http://127.0.0.1:8000 (set PORT to change the port)
Needs: the same setup as agent.py (GEMINI_API_KEY in the environment)

The server listens on this computer only. It is a demo, not a deployment.
"""

import contextlib
import io
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import agent
import more_tools  # noqa: F401  (registers two extra tools on the agent)
import university_tools  # noqa: F401  (registers the university assistant's four tools)

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))
PAGE = Path(__file__).with_name("chat.html").read_bytes()
# Files the tools write, shown as panels on the page.
FILES = {
    "notes": Path("notes.json"),        # save_note in agent.py
    "outbox": Path("outbox.json"),      # send_message in more_tools.py
    "requests": Path("requests.json"),  # open_request in university_tools.py
}
MAX_BODY_BYTES = 16_384
MAX_MESSAGE_CHARS = 2_000


class Session:
    """One conversation. The page drives it one step at a time."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.history = []      # everything the model has seen, across turns
        self.queue = []        # tool calls of the current model reply, not yet run
        self.steps_used = 0    # model calls in the current turn
        self.turn_start = 0    # length of history before the current turn
        self.state = "idle"    # idle | running | approval | error

    # -- one user message starts a turn ---------------------------------------
    def start_turn(self, text):
        if self.state == "error":
            # The previous turn never finished: forget it so the history stays valid.
            self.history = self.history[:self.turn_start]
        elif self.state != "idle":
            return [{"type": "error", "text": "The agent is still working on the previous message."}]
        self.turn_start = len(self.history)
        self.history.append(agent.user_message(text))
        self.queue = []
        self.steps_used = 0
        self.state = "running"
        return self.advance()

    # -- one step: ask the model once, then run the tools it asked for --------
    def advance(self):
        if self.state == "approval":
            return [self._approval_event()]
        if self.state == "idle":
            return []
        self.state = "running"
        events = []
        if self.queue:  # tools left over from a retry
            self._run_queue(events)
            return events
        if self.steps_used >= agent.MAX_STEPS:
            self.state = "idle"
            return [{"type": "answer", "text": "Stopped: step limit reached."}]
        log = io.StringIO()
        try:
            with contextlib.redirect_stdout(log):
                reply = agent.ask_model(self.history)
        except SystemExit as exc:  # ask_model gives up with a readable message
            self.state = "error"
            return self._log_events(log) + [{"type": "error", "text": str(exc)}]
        events += self._log_events(log)
        self.steps_used += 1
        self.history += [s.model_dump(exclude_none=True) for s in reply.steps]
        calls = [s for s in reply.steps if s.type == "function_call"]
        if not calls:
            self.state = "idle"
            events.append({"type": "answer", "text": reply.output_text or "(the model returned no text)"})
            return events
        self.queue = calls
        self._run_queue(events)
        return events

    # -- the answer to an approval question ------------------------------------
    def decide(self, allow):
        if self.state != "approval" or not self.queue:
            return [{"type": "error", "text": "Nothing is waiting for approval."}]
        events = []
        call = self.queue.pop(0)
        result = self._execute(call) if allow else {"error": "The user declined this action."}
        self._record(call, result, events)
        self.state = "running"
        self._run_queue(events)
        return events

    # -- internals ---------------------------------------------------------------
    def _run_queue(self, events):
        while self.queue:
            call = self.queue[0]
            if call.name in agent.TOOLS and call.name in agent.NEEDS_APPROVAL:
                self.state = "approval"
                events.append(self._approval_event())
                return
            self.queue.pop(0)
            self._record(call, self._execute(call), events)

    def _execute(self, call):
        if call.name not in agent.TOOLS:
            return {"error": f"Unknown tool {call.name}"}
        try:
            return agent.TOOLS[call.name](**(call.arguments or {}))
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _record(self, call, result, events):
        self.history.append(agent.tool_result(call, result))
        events.append({"type": "tool", "name": call.name, "arguments": call.arguments or {}, "result": result})

    def _approval_event(self):
        call = self.queue[0]
        return {"type": "approval", "name": call.name, "arguments": call.arguments or {}}

    @staticmethod
    def _log_events(log):
        lines = [line.lstrip("! ").strip() for line in log.getvalue().splitlines()]
        return [{"type": "info", "text": line} for line in lines if line]


SESSION = Session()
LOCK = threading.Lock()  # one conversation, one step at a time


def read_lines(path):
    """The last records of a JSON-lines file written by a tool; unreadable lines are skipped."""
    records = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                records.append(record)
    return records[-20:]


class Handler(BaseHTTPRequestHandler):
    server_version = "DevFestAgentChat/1.0"

    def log_message(self, *args):
        pass  # keep the terminal quiet during the demo

    def _send(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, payload):
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def _reply(self, events):
        self._json(200, {"events": events, "state": SESSION.state,
                         "model": agent.MODEL,
                         **{name: read_lines(path) for name, path in FILES.items()}})

    def _local_only(self):
        """Refuse requests that another website or another host name sent here."""
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in allowed:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://{host}" for host in allowed}

    def do_GET(self):
        if not self._local_only():
            return self._json(403, {"error": "forbidden"})
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/state":
            with LOCK:
                return self._reply([])
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._local_only():
            return self._json(403, {"error": "forbidden"})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self._json(415, {"error": "send JSON"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json(400, {"error": "bad length"})
        if not 0 <= length <= MAX_BODY_BYTES:
            return self._json(413, {"error": "message too large"})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._json(400, {"error": "bad JSON"})
        if not isinstance(body, dict):
            return self._json(400, {"error": "bad JSON"})
        with LOCK:
            if self.path == "/api/chat":
                text = body.get("text")
                if not isinstance(text, str) or not text.strip():
                    return self._json(400, {"error": "empty message"})
                return self._reply(SESSION.start_turn(text.strip()[:MAX_MESSAGE_CHARS]))
            if self.path == "/api/continue":
                return self._reply(SESSION.advance())
            if self.path == "/api/approve":
                return self._reply(SESSION.decide(body.get("allow") is True))
            if self.path == "/api/reset":
                SESSION.reset()
                return self._reply([])
        self._json(404, {"error": "not found"})


def main():
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        raise SystemExit(f"Port {PORT} is not available ({exc}). Set PORT to another number and run again.")
    server.daemon_threads = True
    url = f"http://{HOST}:{server.server_port}"
    print(f"Agent chat is running at {url}")
    print("Leave this window open. Press Ctrl+C here to stop.")
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

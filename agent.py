"""DevFest Maysan 2026: the agent that is built step by step in the closing slides.

The code below is the code shown on screen, in the same five steps:
  1. connect to the model
  2. write the tools (plain Python functions)
  3. describe the tools to the model
  4. the agent loop
  5. guardrails: a step limit, human approval before any write, safe tool errors

On top of what the slides show, this file fails fast instead of hanging: every
request has a timeout, the SDK's silent retries are switched off, a busy model
is retried a few times with a visible wait, and on the first request the agent
moves on to the next model in FALLBACK_MODELS.

Run:      python agent.py
Needs:    pip install -r requirements.txt   and GEMINI_API_KEY set in the environment
Optional: GEMINI_MODEL=<model id> to choose the first model to try
"""

import json
import os
import time

from google import genai
from google.genai import types

# --- Step 1: connect to the model -------------------------------------------
REQUEST_TIMEOUT_MS = 30_000  # a busy model can accept the request and never answer
client = genai.Client(
    http_options=types.HttpOptions(
        timeout=REQUEST_TIMEOUT_MS,
        retry_options=types.HttpRetryOptions(attempts=1),  # no silent retries
    )
)
MODEL = "gemini-3.8-flash"
MODEL = os.environ.get("GEMINI_MODEL", MODEL)
FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]
MAX_ATTEMPTS = 4          # tries per request when the models are busy
RETRY_WAIT_SECONDS = 5    # wait grows with each attempt: 5 s, 10 s, 15 s

# --- Step 2: the tools are plain Python functions ---------------------------
RATES = {"USD": 1480, "EUR": 1610}  # demo data


def get_exchange_rate(currency):
    return {"currency": currency, "iqd": RATES[currency]}


def save_note(title, body):
    with open("notes.json", "a", encoding="utf-8") as f:
        f.write(json.dumps({"title": title, "body": body}) + "\n")
    return {"saved": title}


TOOLS = {"get_exchange_rate": get_exchange_rate, "save_note": save_note}

# --- Step 3: describe the tools to the model --------------------------------
DECLARATIONS = [
    {"type": "function",
     "name": "get_exchange_rate",
     "description": "Get today's rate of a currency in Iraqi dinar.",
     "parameters": {"type": "object",
                    "properties": {"currency": {"type": "string"}},
                    "required": ["currency"]}},
    {"type": "function",
     "name": "save_note",
     "description": "Save a note with a title and a body.",
     "parameters": {"type": "object",
                    "properties": {"title": {"type": "string"},
                                   "body": {"type": "string"}},
                    "required": ["title", "body"]}},
]


# --- Helpers ------------------------------------------------------------------
def user_message(text):
    return {"type": "user_input", "content": [{"type": "text", "text": text}]}


def tool_result(call, result):
    return {"type": "function_result", "name": call.name, "call_id": call.id,
            "result": [{"type": "text", "text": json.dumps(result)}]}


def ask_model(history):
    """Send the history and the tools to the model, with a timeout and a fallback.

    The first model that answers is kept for the rest of the task, because the
    reasoning steps a model returns are only valid when sent back to that model.
    A busy model (503, 429, timeout) is retried a few times with a visible wait.
    """
    global MODEL
    first_request = len(history) == 1
    candidates = [MODEL]
    if first_request:
        candidates += [m for m in FALLBACK_MODELS if m != MODEL]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        for name in candidates:
            try:
                reply = client.interactions.create(
                    model=name, input=history, tools=DECLARATIONS, store=False)
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                reason = " ".join(str(exc).split())[:160]
                print(f"! {name} did not answer: {type(exc).__name__}: {reason}")
                if status in (400, 401, 403):
                    raise SystemExit("The request was rejected. Check GEMINI_API_KEY and the model name.")
                continue
            if not reply.steps:
                print(f"! {name} returned an empty reply")
                continue
            if name != MODEL:
                print(f"! using {name} for this task")
                MODEL = name
            return reply
        if attempt < MAX_ATTEMPTS:
            wait = RETRY_WAIT_SECONDS * attempt
            print(f"! waiting {wait} s before attempt {attempt + 1} of {MAX_ATTEMPTS}")
            time.sleep(wait)
    raise SystemExit(
        "No model answered. Wait a minute and run again, or choose another model "
        "by setting GEMINI_MODEL."
    )


# --- Step 5: guardrails ------------------------------------------------------
NEEDS_APPROVAL = {"save_note"}


def run_tool(call):
    if call.name not in TOOLS:
        return {"error": f"Unknown tool {call.name}"}
    if call.name in NEEDS_APPROVAL:
        if input(f"Allow {call.name}? [y/n] ").strip().lower() != "y":
            return {"error": "The user declined this action."}
    try:
        return TOOLS[call.name](**(call.arguments or {}))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


# --- Step 4: the agent loop --------------------------------------------------
MAX_STEPS = 8


def run_agent(task):
    history = [user_message(task)]
    for _ in range(MAX_STEPS):
        reply = ask_model(history)
        history += [s.model_dump(exclude_none=True) for s in reply.steps]
        calls = [s for s in reply.steps if s.type == "function_call"]
        if not calls:
            return reply.output_text
        for call in calls:
            result = run_tool(call)
            print(">", call.name, call.arguments, "->", result)
            history.append(tool_result(call, result))
    return "Stopped: step limit reached."


if __name__ == "__main__":
    print(run_agent("Convert 500 USD to IQD and save it as a note titled DevFest expenses"))

"""DevFest Maysan 2026: the agent that is built step by step in the closing slides.

The code below is the code shown on screen, in the same five steps:
  1. connect to the model
  2. write the tools (plain Python functions)
  3. describe the tools to the model
  4. the agent loop
  5. guardrails: a step limit, human approval before any write, safe tool errors

Run:      python agent.py
Needs:    pip install -r requirements.txt   and GEMINI_API_KEY set in the environment
"""

import json

from google import genai

# --- Step 1: connect to the model -------------------------------------------
client = genai.Client()
MODEL = "gemini-3.8-flash"

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


# --- Helpers: wrap text in the step format the Interactions API expects -----
def user_message(text):
    return {"type": "user_input", "content": [{"type": "text", "text": text}]}


def tool_result(call, result):
    return {"type": "function_result", "name": call.name, "call_id": call.id,
            "result": [{"type": "text", "text": json.dumps(result)}]}


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
        reply = client.interactions.create(
            model=MODEL, input=history, tools=DECLARATIONS, store=False)
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

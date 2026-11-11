"""More tools for the same agent. The loop in agent.py does not change.

Importing this file registers two extra tools:
  get_expenses(project)   reads a small expense table (demo data)
  send_message(to, text)  writes the message to outbox.json; nothing is sent anywhere

send_message changes something outside the conversation, so it is added to
NEEDS_APPROVAL and the agent asks before running it.

Run:  python more_tools.py
The chat page (chat.py) imports this file, so it has these tools too.
"""

import json

import agent

EXPENSES = {"DevFest": {"hall": 400, "printing": 150, "catering": 200}}  # demo data, in USD


def get_expenses(project):
    items = EXPENSES[project]
    return {"project": project, "total_usd": sum(items.values()), "items": len(items)}


def send_message(to, text):
    with open("outbox.json", "a", encoding="utf-8") as f:
        f.write(json.dumps({"to": to, "text": text}) + "\n")
    return {"queued": to}


# The same three moves as in agent.py: the function, its description, its guardrail.
agent.TOOLS.update({"get_expenses": get_expenses, "send_message": send_message})
DECLARATIONS = [
    {"type": "function",
     "name": "get_expenses",
     "description": "Get the total expenses of a project in US dollars.",
     "parameters": {"type": "object",
                    "properties": {"project": {"type": "string"}},
                    "required": ["project"]}},
    {"type": "function",
     "name": "send_message",
     "description": "Send a short text message to a person, for example the accountant.",
     "parameters": {"type": "object",
                    "properties": {"to": {"type": "string"},
                                   "text": {"type": "string"}},
                    "required": ["to", "text"]}},
]
known = {d["name"] for d in agent.DECLARATIONS}
agent.DECLARATIONS += [d for d in DECLARATIONS if d["name"] not in known]  # safe to import twice
agent.NEEDS_APPROVAL.add("send_message")

if __name__ == "__main__":
    print(agent.run_agent(
        "Add up the DevFest expenses and convert the total to IQD. "
        "If it is above 1,000,000 IQD, send the total to the accountant."))

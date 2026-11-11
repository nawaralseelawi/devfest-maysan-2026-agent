"""A second agent on the same loop: a student results and appeals assistant.

Importing this file registers four tools on the agent in agent.py:
  get_my_results(exam_round)     reads the signed-in student's results (demo data)
  review_result(course)          checks one result: do the parts add up to the total?
  check_appeal_window(course)    reads whether an appeal can still be submitted
  submit_appeal(course, reason)  files an appeal in appeals.json, after approval

How the work is split:
  - The code finds hard evidence (a total that does not equal coursework + final).
  - The model may add advice from the marks and from what the student says, and it
    must present that as an estimate, not as evidence.
  - The student decides: nothing is submitted without approval.
  - A committee decides the appeal. No tool here can change a mark.

The student is identified by the program, not by the model: no tool takes a
student number. In a real deployment STUDENT_ID comes from the university login.

All data below is invented for the demo. It is not the regulations or the records
of any real university. Coursework is out of 40 and the final exam out of 60.

Run:  python appeal_tools.py
The chat page (chat.py) imports this file, so it has these tools too.
"""

import json
import os

import agent

STUDENT_ID = "EE-2-0417"  # set by the login, never by the model
PASS_MARK = 50
DAYS_LEFT = 5  # demo: days left in the appeal window; a real system computes it from dates
APPEALS_FILE = "appeals.json"

RESULTS = {"EE-2-0417": {"first": [  # demo marks; the first total is wrong on purpose
    {"course": "Electric Circuits", "coursework": 30, "final": 25, "total": 45, "status": "fail"},
    {"course": "Electronics I", "coursework": 34, "final": 11, "total": 45, "status": "fail"},
    {"course": "Engineering Mathematics", "coursework": 28, "final": 40, "total": 68, "status": "pass"},
], "second": []}}


def find_result(course):
    for result in RESULTS[STUDENT_ID]["first"]:
        if result["course"].lower() == course.strip().lower():
            return result
    raise KeyError(course)


def read_appeals():
    if not os.path.exists(APPEALS_FILE):
        return []
    with open(APPEALS_FILE, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_my_results(exam_round):
    return {"student": STUDENT_ID, "round": exam_round, "results": RESULTS[STUDENT_ID][exam_round]}


def review_result(course):
    r = find_result(course)
    parts = r["coursework"] + r["final"]
    return {"course": r["course"], "recorded_total": r["total"], "sum_of_parts": parts,
            "sum_matches": parts == r["total"], "near_pass": PASS_MARK - 2 <= r["total"] < PASS_MARK,
            "coursework_pct": round(100 * r["coursework"] / 40), "final_pct": round(100 * r["final"] / 60)}


def check_appeal_window(course):
    return {"course": find_result(course)["course"], "open": DAYS_LEFT > 0, "days_left": DAYS_LEFT}


def submit_appeal(course, reason):
    course = find_result(course)["course"]
    if DAYS_LEFT <= 0:
        return {"error": "The appeal window is closed."}
    if any(a["course"] == course for a in read_appeals()):
        return {"error": f"An appeal for {course} already exists."}
    record = {"id": f"A-{len(read_appeals()) + 1}", "student": STUDENT_ID, "course": course, "reason": reason}
    with open(APPEALS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {"submitted": record["id"]}


# The same three moves again: the functions, their descriptions, the guardrail.
agent.TOOLS.update({"get_my_results": get_my_results, "review_result": review_result,
                    "check_appeal_window": check_appeal_window, "submit_appeal": submit_appeal})
COURSE = {"type": "object", "properties": {"course": {"type": "string"}}, "required": ["course"]}
DECLARATIONS = [
    {"type": "function",
     "name": "get_my_results",
     "description": "Get the signed-in student's results in an exam round: coursework out of 40, "
                    "final exam out of 60, recorded total, and pass or fail. The pass mark is 50.",
     "parameters": {"type": "object",
                    "properties": {"exam_round": {"type": "string", "enum": ["first", "second"]}},
                    "required": ["exam_round"]}},
    {"type": "function",
     "name": "review_result",
     "description": "Check one course result for grounds to appeal. Use it on every failed course, then "
                    "suggest an appeal where it finds a problem. A total that does not match the sum of "
                    "its parts is evidence. Anything you infer from the marks or from what the student "
                    "says is only an estimate: say so, and never promise an outcome.",
     "parameters": COURSE},
    {"type": "function",
     "name": "check_appeal_window",
     "description": "Check whether an appeal for a course can still be submitted, and how many days are left.",
     "parameters": COURSE},
    {"type": "function",
     "name": "submit_appeal",
     "description": "Submit an appeal against a course result for the signed-in student. Only after the "
                    "student has asked for it. The reason is one or two factual sentences.",
     "parameters": {"type": "object",
                    "properties": {"course": {"type": "string"}, "reason": {"type": "string"}},
                    "required": ["course", "reason"]}},
]
known = {d["name"] for d in agent.DECLARATIONS}
agent.DECLARATIONS += [d for d in DECLARATIONS if d["name"] not in known]  # safe to import twice
agent.NEEDS_APPROVAL.add("submit_appeal")

if __name__ == "__main__":
    print(agent.run_agent(
        "Show my first-round results. Check every course I failed, and if you find grounds "
        "for an appeal, submit it."))

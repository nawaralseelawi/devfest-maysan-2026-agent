"""A second agent on the same loop: a university services assistant.

Importing this file registers four tools on the agent in agent.py:
  search_regulations(topic)    reads a rule from the regulations (demo text)
  get_exam_schedule(course)    reads the exam dates of a course (demo data)
  get_my_grades(exam_round)    reads the grades of the signed-in student (demo data)
  open_request(kind, details)  files a request in requests.json, after approval

The student is identified by the program, not by the model: get_my_grades and
open_request take no student number, so nobody can ask the model for another
student's record. In a real deployment STUDENT_ID comes from the university login.

All data below is invented for the demo. It is not the regulations or the records
of any real university. A real assistant would search the official regulation
documents (retrieval) and call the registration system instead.

Run:  python university_tools.py
The chat page (chat.py) imports this file, so it has these tools too.
"""

import json
import os

import agent

STUDENT_ID = "EE-2-0417"  # set by the login, never by the model

REGULATIONS = {  # demo text, not real regulations
    "second_round": "Demo rule: a failed course may be retaken once in the second round, by request.",
    "absence": "Demo rule: absence above 10% of a course's hours bars the student from its exam.",
    "deferral": "Demo rule: a student may defer one academic year, by request before the exams.",
    "transcript": "Demo rule: a transcript is issued within five working days of the request.",
}
EXAMS = {  # demo dates
    "electric circuits": {"first_round": "2027-06-14", "second_round": "2027-08-23"},
    "electronics i": {"first_round": "2027-06-17", "second_round": "2027-08-25"},
}
GRADES = {"EE-2-0417": {"first": {"Electric Circuits": 41, "Electronics I": 68}, "second": {}}}  # demo, pass is 50
REQUEST_KINDS = ["second_round", "deferral", "transcript"]
REQUESTS_FILE = "requests.json"


def search_regulations(topic):
    return {"topic": topic, "text": REGULATIONS[topic]}


def get_exam_schedule(course):
    return {"course": course, **EXAMS[course.strip().lower()]}


def get_my_grades(exam_round):
    return {"student": STUDENT_ID, "round": exam_round, "grades": GRADES[STUDENT_ID][exam_round]}


def open_request(kind, details):
    if kind not in REQUEST_KINDS:
        return {"error": f"Unknown request kind {kind}"}
    number = 1
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, encoding="utf-8") as f:
            number += sum(1 for line in f if line.strip())
    record = {"id": f"R-{number}", "student": STUDENT_ID, "kind": kind, "details": details}
    with open(REQUESTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {"opened": record["id"]}


# The same three moves again: the functions, their descriptions, the guardrail.
agent.TOOLS.update({"search_regulations": search_regulations, "get_exam_schedule": get_exam_schedule,
                    "get_my_grades": get_my_grades, "open_request": open_request})
DECLARATIONS = [
    {"type": "function",
     "name": "search_regulations",
     "description": "Read the university rule on a topic. Use it before answering any question about rules.",
     "parameters": {"type": "object",
                    "properties": {"topic": {"type": "string", "enum": list(REGULATIONS)}},
                    "required": ["topic"]}},
    {"type": "function",
     "name": "get_exam_schedule",
     "description": "Get the first-round and second-round exam dates of a course.",
     "parameters": {"type": "object",
                    "properties": {"course": {"type": "string"}},
                    "required": ["course"]}},
    {"type": "function",
     "name": "get_my_grades",
     "description": "Get the signed-in student's grades in an exam round. The pass mark is 50.",
     "parameters": {"type": "object",
                    "properties": {"exam_round": {"type": "string", "enum": ["first", "second"]}},
                    "required": ["exam_round"]}},
    {"type": "function",
     "name": "open_request",
     "description": "Open an official request for the signed-in student.",
     "parameters": {"type": "object",
                    "properties": {"kind": {"type": "string", "enum": REQUEST_KINDS},
                                   "details": {"type": "string"}},
                    "required": ["kind", "details"]}},
]
known = {d["name"] for d in agent.DECLARATIONS}
agent.DECLARATIONS += [d for d in DECLARATIONS if d["name"] not in known]  # safe to import twice
agent.NEEDS_APPROVAL.add("open_request")

if __name__ == "__main__":
    print(agent.run_agent(
        "Did I fail any course? If so, what do the rules say, when is its second-round exam, "
        "and please open a second-round request for it."))

# DevFest Maysan 2026: an AI agent in one file

The code from the talk **"From Gemini to AI Agents: building the next generation of smart applications"**, given at DevFest Maysan 2026 by Nawar S. Alseelawi (University of Misan).

`agent.py` is the agent that was built step by step on screen: about 90 lines of Python, no framework.

```
agent = model + tools + loop + guardrails
```

## What it does

Given the task *"Convert 500 USD to IQD and save it as a note"*, the agent:

1. asks for the exchange rate through a tool,
2. works out the amount,
3. asks to save a note, and waits for your approval before writing,
4. answers.

Nothing in the code says "rate first, then save". The model orders the steps; the program only runs the tools it asks for.

## The five steps in the file

| Step | In the code | Idea |
|---|---|---|
| 1 | `client`, `MODEL`, `ask_model` | Connect to the model, with a timeout and a fallback model |
| 2 | `get_exchange_rate`, `save_note`, `TOOLS` | Tools are plain Python functions |
| 3 | `DECLARATIONS` | Describe each tool to the model: name, description, parameters |
| 4 | `run_agent` | The loop: call the model, run the tools it requests, feed results back, stop when it answers |
| 5 | `MAX_STEPS`, `NEEDS_APPROVAL`, `run_tool` | Guardrails: a step limit, human approval before any write, tool errors returned as data |

## Run it

Requires Python 3.10+ and a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
pip install -r requirements.txt
```

Set the key in the same terminal window, then run. On Windows the default terminal is PowerShell, where `set` does not work:

```powershell
# Windows PowerShell (the prompt starts with PS)
$env:GEMINI_API_KEY="your-key-here"
python agent.py
```

```bat
:: Windows Command Prompt (cmd)
set GEMINI_API_KEY=your-key-here
python agent.py
```

```bash
# macOS / Linux
export GEMINI_API_KEY=your-key-here
python agent.py
```

When the agent asks `Allow save_note? [y/n]`, type `y` and press Enter. The note is appended to `notes.json`.

Expected output (the model's final sentence varies between runs):

```
> get_exchange_rate {'currency': 'USD'} -> {'currency': 'USD', 'iqd': 1480}
Allow save_note? [y/n] y
> save_note {'title': 'DevFest expenses', 'body': '500 USD = 740,000 IQD'} -> {'saved': 'DevFest expenses'}
Done. 500 USD = 740,000 IQD. Saved as "DevFest expenses".
```

## Chat in the browser

`chat.py` puts the same agent behind a chat page. It adds no agent logic: it reuses the tools and the model call from `agent.py`, and uses only the Python standard library for the page.

```
python chat.py
```

The browser opens `http://127.0.0.1:8000`. Type a task in Arabic or English, or click one of the suggestions. Each tool call appears as it happens, the approval question becomes two buttons, and saved notes show up in the `notes.json` panel. The conversation keeps its history until you click the new-chat button or reload the page.

Leave the terminal window open while you use the page, and press Ctrl+C there to stop. If port 8000 is taken, choose another one first: `$env:PORT="8010"` in PowerShell, `export PORT=8010` on macOS or Linux.

The page is served to this computer only (`127.0.0.1`). It is a demo, not something to put on a server.

## More tools, same loop

`more_tools.py` adds two tools without touching the loop: `get_expenses` reads a small expense table, and `send_message` writes a message to `outbox.json` (demo: nothing is sent anywhere) and asks for approval first.

```
python more_tools.py
```

The task has a condition in it: add up the expenses, convert the total, and message the accountant only if the total is above 1,000,000 IQD. The model reads the expenses, asks for the rate, compares, and then asks to send. No line of code fixes that order. The chat page loads these tools too.

## Ideas for your own tools

A tool is one Python function, one entry in `TOOLS`, and one description in `DECLARATIONS`. Tools that only read can run freely. Tools that write, send, pay or delete go in `NEEDS_APPROVAL`.

| Agent | Tools that read | Tools that act (ask first) |
|---|---|---|
| University services assistant | `search_regulations(query)`, `get_exam_schedule(department, stage)`, `get_grades(student_id)` | `open_request(student_id, kind, details)` |
| Local market agent | `get_exchange_rate(currency)` from a live source, `get_price(item, city)`, `compare_prices(item)` | `set_price_alert(item, limit)` |
| Farmer's assistant | `get_weather(city, days)`, `get_crop_price(crop, market)`, `get_irrigation_schedule(district)` | `send_sms(phone, text)` |
| Archive agent | `ocr_document(file)`, `search_archive(query)`, `get_document(doc_id)` | `index_document(file, fields)` |
| Everyday office work | `read_sheet(name, cells)`, `search_files(query)`, `get_calendar(date)` | `send_telegram(chat_id, text)`, `add_event(date, title)` |

These are suggestions, not code in this repository. Start with one read-only tool on data you already have, and write its description as if you were explaining it to a new colleague.

## When a model is busy

Popular models are sometimes overloaded and answer `503 ... experiencing high demand`. The agent does not hang on that: each request has a 30 second timeout, silent retries are off, and on the first request it moves on to the next model in `FALLBACK_MODELS`:

```
! gemini-3.8-flash did not answer: InternalServerError: Error code: 503 - ...
! using gemini-3.5-flash-lite for this task
```

A busy model can also accept the request and stay silent, in which case you wait for the timeout before the agent moves on. The first model that answers is kept for the whole task. If that model becomes busy in the middle of the task, the agent waits and tries it again, up to four attempts (5 s, 10 s, 15 s), printing each wait, and then stops with a clear message. To skip the wait, choose the first model yourself by setting `GEMINI_MODEL` before running, for example `$env:GEMINI_MODEL="gemini-3.5-flash-lite"`.

This path was exercised on the live API on 11 November 2026: `gemini-3.8-flash` timed out, `gemini-3.6-flash` answered 503, and the task completed on `gemini-3.5-flash-lite`.

## Read before you build on it

- **The exchange rates are demo data.** `RATES` is a fixed dictionary inside the file, not a market feed. A real tool would call a live price source.
- **It uses the Interactions API** (`client.interactions.create`) with `gemini-3.8-flash` first, through `google-genai` 2.3 or newer. Model names change; if the model is retired, set `MODEL` to a current one from the [models page](https://ai.google.dev/gemini-api/docs/models).
- **It is a teaching example.** For a real product, add timeouts, per-tool retry limits, logging of every step, input validation in each tool, and an evaluation set. A framework such as [Google ADK](https://adk.dev) gives you most of that.
- **Tool output is data, not instructions.** Anything a tool returns (a web page, a file, an email) can contain text that tries to steer the model. Keep each tool's permissions minimal and require approval for anything that leaves the system.

## Make it yours

Replace the two tools with one from your own work:

1. write a Python function,
2. add it to `TOOLS`,
3. add its entry to `DECLARATIONS` with a clear `description`,
4. if it writes, sends or deletes anything, add its name to `NEEDS_APPROVAL`.

## Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'google'` | The package is not installed for this Python | Run `python -m pip install -r requirements.txt` |
| `No API key was provided`, or status `401` / `403` | The key is missing or wrong in this terminal window. In PowerShell, `set NAME=value` does nothing useful | Set it again in the same window with the PowerShell form `$env:GEMINI_API_KEY="..."` |
| Status `404` or "model not found" | The model name is not available to your key | Change `MODEL` to a current Flash model from the models page |
| Status `429` or `RESOURCE_EXHAUSTED` | Rate limit or quota reached | Wait a minute and run again |
| `No model answered` | Every model in the list was overloaded or timed out | Wait a minute and run again, or set `GEMINI_MODEL` to another model |
| Windows blocks a `.pyd` / `.dll` file during install or import | Smart App Control or a similar policy | Use another machine, or run the file in Google Colab |

## License

MIT. Use it, change it, and build on it freely. See [LICENSE](LICENSE).

---

<div dir="rtl">

## بالعربية

هذا هو الكود الذي بُني خطوة خطوة في محاضرة **«من Gemini إلى AI Agents: بناء الجيل القادم من التطبيقات الذكية»** في ملتقى DevFest ميسان 2026، تقديم د. نوار سعد السيلاوي (جامعة ميسان).

الملف `agent.py` وكيل كامل في نحو 90 سطراً من Python، بلا أي إطار عمل:

**الوكيل = نموذج + أدوات + حلقة + ضوابط**

### ماذا يفعل

تعطيه المهمة: حوّل 500 دولار إلى دينار واحفظ النتيجة كملاحظة. فيطلب سعر الصرف عبر أداة، ويحسب المبلغ، ثم يطلب حفظ الملاحظة وينتظر موافقتك قبل الكتابة، ثم يجيب. لا يوجد في الكود ما يحدد ترتيب الخطوات؛ النموذج هو الذي يرتبها، والبرنامج ينفذ الأدوات التي يطلبها فقط.

### التشغيل

تحتاج Python 3.10 أو أحدث، ومفتاحاً من Google AI Studio. ثبّت الحزمة بالأمر `pip install -r requirements.txt`، وضع المفتاح في متغير البيئة `GEMINI_API_KEY`، ثم شغّل `python agent.py`. وحين يسألك عن السماح بالحفظ اكتب `y`.

في Windows PowerShell يوضع المفتاح بالصيغة `$env:GEMINI_API_KEY="..."`، والأمر `set` لا يعمل هناك. وإذا كان النموذج الأول مشغولاً ينتقل الوكيل تلقائياً إلى النموذج التالي في `FALLBACK_MODELS` ويطبع سطراً يبدأ بعلامة التعجب.

### واجهة الدردشة

الملف `chat.py` يضع الوكيل نفسه خلف صفحة دردشة في المتصفح. شغّل `python chat.py` فيفتح المتصفح العنوان `http://127.0.0.1:8000`. اكتب المهمة بالعربية أو الإنجليزية، فتظهر كل أداة يستدعيها الوكيل لحظة استدعائها، ويتحول سؤال الموافقة إلى زرّين، وتظهر الملاحظات المحفوظة في لوحة `notes.json`. أبقِ نافذة الطرفية مفتوحة، واضغط Ctrl+C فيها للإيقاف. الصفحة تعمل على حاسوبك فقط وليست للنشر على خادم.

### أدوات أكثر والحلقة نفسها

الملف `more_tools.py` يضيف أداتين من دون أي تغيير في الحلقة: `get_expenses` تقرأ جدول مصاريف تجريبياً، و`send_message` تكتب الرسالة في الملف `outbox.json` ولا ترسل شيئاً، وتطلب الموافقة أولاً. شغّله بالأمر `python more_tools.py`. وفي القسم الإنكليزي أعلاه جدول بأفكار أدوات لوكلاء الخدمات الجامعية والسوق المحلي والمزارع والأرشفة.

### تنبيهات

- أسعار الصرف في الملف **بيانات تجريبية ثابتة** وليست سعر السوق.
- الملف **مثال تعليمي**. المنتج الحقيقي يحتاج مهلات زمنية، وسجلاً للخطوات، وتحققاً من المدخلات، ومجموعة اختبار.
- **مخرجات الأداة بيانات وليست أوامر.** أعطِ كل أداة أقل صلاحية ممكنة، واطلب موافقة بشرية على كل فعل يغادر النظام.

### اجعله وكيلك

اكتب دالة من عملك أنت، وأضفها إلى `TOOLS`، وعرّفها في `DECLARATIONS` بوصف واضح، وإن كانت تكتب أو ترسل أو تحذف فأضف اسمها إلى `NEEDS_APPROVAL`.

### الترخيص

الكود منشور بترخيص MIT: استخدمه وعدّله وابنِ عليه بحرية.

</div>

# DevFest Maysan 2026: an AI agent in one file

The code from the talk **"From Gemini to AI Agents: building the next generation of smart applications"**, given at DevFest Maysan 2026 by Nawar S. Alseelawi (University of Misan).

`agent.py` is the agent that was built step by step on screen: about 60 lines of Python, no framework.

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
| 1 | `client`, `MODEL` | Connect to the model |
| 2 | `get_exchange_rate`, `save_note`, `TOOLS` | Tools are plain Python functions |
| 3 | `DECLARATIONS` | Describe each tool to the model: name, description, parameters |
| 4 | `run_agent` | The loop: call the model, run the tools it requests, feed results back, stop when it answers |
| 5 | `MAX_STEPS`, `NEEDS_APPROVAL`, `run_tool` | Guardrails: a step limit, human approval before any write, tool errors returned as data |

## Run it

Requires Python 3.10+ and a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
pip install -r requirements.txt
```

Set the key, then run:

```bash
# Windows (cmd)
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

## Read before you build on it

- **The exchange rates are demo data.** `RATES` is a fixed dictionary inside the file, not a market feed. A real tool would call a live price source.
- **It uses the Interactions API** (`client.interactions.create`) with `gemini-3.8-flash`, through `google-genai` 2.3 or newer. Model names change; if the model is retired, set `MODEL` to a current one from the [models page](https://ai.google.dev/gemini-api/docs/models).
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
| An error mentioning `API key` or status `401` / `403` | The key is missing or wrong in this terminal window | Set `GEMINI_API_KEY` again in the same window, with no spaces or quotes |
| Status `404` or "model not found" | The model name is not available to your key | Change `MODEL` to a current Flash model from the models page |
| Status `429` or `RESOURCE_EXHAUSTED` | Rate limit or quota reached | Wait a minute and run again |
| Windows blocks a `.pyd` / `.dll` file during install or import | Smart App Control or a similar policy | Use another machine, or run the file in Google Colab |

## License

MIT. Use it, change it, and build on it freely. See [LICENSE](LICENSE).

---

<div dir="rtl">

## بالعربية

هذا هو الكود الذي بُني خطوة خطوة في محاضرة **«من Gemini إلى AI Agents: بناء الجيل القادم من التطبيقات الذكية»** في ملتقى DevFest ميسان 2026، تقديم د. نوار سعد السيلاوي (جامعة ميسان).

الملف `agent.py` وكيل كامل في نحو 60 سطراً من Python، بلا أي إطار عمل:

**الوكيل = نموذج + أدوات + حلقة + ضوابط**

### ماذا يفعل

تعطيه المهمة: حوّل 500 دولار إلى دينار واحفظ النتيجة كملاحظة. فيطلب سعر الصرف عبر أداة، ويحسب المبلغ، ثم يطلب حفظ الملاحظة وينتظر موافقتك قبل الكتابة، ثم يجيب. لا يوجد في الكود ما يحدد ترتيب الخطوات؛ النموذج هو الذي يرتبها، والبرنامج ينفذ الأدوات التي يطلبها فقط.

### التشغيل

تحتاج Python 3.10 أو أحدث، ومفتاحاً من Google AI Studio. ثبّت الحزمة بالأمر `pip install -r requirements.txt`، وضع المفتاح في متغير البيئة `GEMINI_API_KEY`، ثم شغّل `python agent.py`. وحين يسألك عن السماح بالحفظ اكتب `y`.

### تنبيهات

- أسعار الصرف في الملف **بيانات تجريبية ثابتة** وليست سعر السوق.
- الملف **مثال تعليمي**. المنتج الحقيقي يحتاج مهلات زمنية، وسجلاً للخطوات، وتحققاً من المدخلات، ومجموعة اختبار.
- **مخرجات الأداة بيانات وليست أوامر.** أعطِ كل أداة أقل صلاحية ممكنة، واطلب موافقة بشرية على كل فعل يغادر النظام.

### اجعله وكيلك

اكتب دالة من عملك أنت، وأضفها إلى `TOOLS`، وعرّفها في `DECLARATIONS` بوصف واضح، وإن كانت تكتب أو ترسل أو تحذف فأضف اسمها إلى `NEEDS_APPROVAL`.

### الترخيص

الكود منشور بترخيص MIT: استخدمه وعدّله وابنِ عليه بحرية.

</div>

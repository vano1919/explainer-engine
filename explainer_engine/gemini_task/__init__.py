"""The Gemini Task route (v4.3, GC-20..GC-27): Claude writes, Gemini Flash in Task mode checks and makes the pictures.

The engine never drives a browser. It writes what the PC session pastes or uploads (the Drive rules pack, the check
messages, the picture batches) and reads back what Gemini answered (reviews, batch reports, downloaded pictures).

Modules: ``texts`` (the manifest's placeholders, filling, gates), ``pack`` (Drive rules pack, build item 1), ``review``
(checks, replies, disagreements, deadlock cards; item 2), ``queue`` (shot_queue.json; item 3), ``batch`` (batch
messages, intake by order, verdicts, redo list; items 4 and 5), ``timing`` (voice first; item 6), ``gate`` (T0; item 7).
CLI: ``python -m explainer_engine.gemini_task --help``. Nothing here is paid and nothing calls Gemini.
"""

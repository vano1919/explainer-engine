"""Labelled values: every parameter that is a choice (not a fact) carries an evidence label.

A labelled value is ``{"value": ..., "status": <label>, "note": "..."}``. QA reads the labels; reports show them.

Labels:
  sourced              taken from an official or primary source (the note names it and its access date)
  measured             measured by us on our own output or hardware
  engineering_default  a working default with no evidence either way (sample rates, chunk sizes, file names)
  hypothesis           an untested idea about the viewer experience, to be tested
  playback_dependent   depends on the viewer's device and room
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/labels.py
# changed: label vocabulary for the explainer channel (directive: observed/measured/inference/hypothesis)

from __future__ import annotations

LABELS = ("sourced", "measured", "engineering_default", "hypothesis", "playback_dependent")


def v(value, status: str, note: str = "") -> dict:
    """A labelled value."""
    if status not in LABELS:
        raise ValueError(f"unknown evidence label {status!r}")
    return {"value": value, "status": status, "note": note}


def plain(node):
    """The value of a labelled value; anything else unchanged."""
    return node["value"] if isinstance(node, dict) and "value" in node else node


def plain_tree(node):
    """Like ``plain``, through nested blocks: a dict of labelled values becomes a dict of values."""
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    if isinstance(node, dict):
        return {k: plain_tree(x) for k, x in node.items()}
    if isinstance(node, list):
        return [plain_tree(x) for x in node]
    return node

#!/usr/bin/env python3
"""The runtime levers of rev 85 do what they say (P2-1, P2-12).

  - the Gemini meter counts every REQUEST by model, including retries and calls
    made with count_call=False, and survives the module being imported twice;
  - Kokoro runs four workers on a four-core runner with the memory for them, two
    otherwise, and VOID_KOKORO_WORKERS wins;
  - main.py's phase clock turns marks into durations.

No network, no API key, no VOID_SQLITE_PATH.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


# --- 1. The meter --------------------------------------------------------------
from summarizer import gemini_client as gc  # noqa: E402


class _Resp:
    def __init__(self, text):
        self.text = text


class _Models:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def generate_content(self, model, contents, config):
        self.sent.append(model)
        return _Resp(self.replies.pop(0))


class _Client:
    def __init__(self, replies):
        self.models = _Models(replies)


if gc.GEMINI_AVAILABLE:
    gc._MIN_INTERVAL = 0.0
    gc.reset_usage()
    gc._client = _Client(['{"a": 1}', "not json", '{"b": 2}', "plain text"])
    gc.generate_json("p", count_call=False, model=gc._FLASH_MODEL)
    gc.generate_json("p", max_retries=1, model=gc._FLASH_MODEL)   # one parse failure, one retry
    gc.generate_text("p")                                            # default (lite) model
    u = gc.get_usage()
    check("a count_call=False request is metered",
          u["uncounted_calls_by_model"].get(gc._FLASH_MODEL) == 1, str(u))
    check("a retry is a second request against the same model",
          u["requests_by_model"].get(gc._FLASH_MODEL) == 3
          and u["calls_by_model"].get(gc._FLASH_MODEL) == 2, str(u))
    check("requests are kept per model", u["requests_by_model"].get(gc._MODEL) == 1, str(u))
    # A second import under the package path shares the same meter.
    spec = importlib.util.spec_from_file_location(
        "pipeline_summarizer_gemini_client_copy", ROOT / "pipeline" / "summarizer" / "gemini_client.py")
    copy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(copy)
    check("a second copy of the module reads the same meter",
          copy.get_usage()["requests_by_model"] == u["requests_by_model"])
    gc.reset_usage()
    gc._client = None
else:
    print("  skip  google-genai not installed: meter behaviour not exercised")
check("get_usage names the flash model the gate reads", gc.get_usage()["flash_model"] == gc._FLASH_MODEL)

# --- 2. Kokoro workers -----------------------------------------------------------
from briefing.tts_engines import KOKORO_WORKER_MB, default_kokoro_workers  # noqa: E402

check("4 cores with room for four sessions: 4 workers",
      default_kokoro_workers(cpu=4, mem_mb=16000, env={}) == 4)
check("2 cores: 2 workers", default_kokoro_workers(cpu=2, mem_mb=16000, env={}) == 2)
check("4 cores but too little memory: 2 workers",
      default_kokoro_workers(cpu=4, mem_mb=4 * KOKORO_WORKER_MB - 1, env={}) == 2)
check("VOID_KOKORO_WORKERS overrides", default_kokoro_workers(
    cpu=4, mem_mb=16000, env={"VOID_KOKORO_WORKERS": "3"}) == 3)
check("a junk override falls back to the default",
      default_kokoro_workers(cpu=4, mem_mb=16000, env={"VOID_KOKORO_WORKERS": "x"}) == 4)

# --- 3. The phase clock ------------------------------------------------------------
src = (ROOT / "pipeline" / "main.py").read_text(encoding="utf-8")
fn = next(n for n in ast.parse(src).body
          if isinstance(n, ast.FunctionDef) and n.name == "phase_durations")
ns: dict = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "main.py", "exec"), ns)
d = ns["phase_durations"]([("a", 0.0), ("b", 10.0), ("a", 25.0)], 30.0)
check("a phase lasts until the next mark, and a re-entered phase accumulates",
      d == {"a": 15.0, "b": 15.0}, str(d))
for name in ("fetch", "scrape", "bias", "cluster", "rank", "rerank", "stage2", "brief_audio"):
    check(f"main.py marks the '{name}' phase", f'_phase("{name}")' in src)

if failures:
    print(f"\nFAIL  {len(failures)} runtime check(s)")
    sys.exit(1)
print("\nPASS  the meter counts every request, Kokoro uses the cores, phases are timed")

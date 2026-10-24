"""
Offline tests for the BATCHED cluster summarization added 2026-08-11.

No network, no real Gemini, no DB: `_smart_generate_json` (and, where needed, the
availability / budget helpers) are monkeypatched so every LLM call is a
deterministic in-process mock. Run with:

    cd pipeline && python -m summarizer.test_batch_summarization

Coverage:
  - the batch PROMPT keeps every story delimited + carries the separation rule
  - graduated batch SCHEDULE chunks the cache-miss list correctly
  - per-cluster INPUT-token budget graduates article depth (solo deep, tail lean)
  - the batched-JSON PARSER splits N entries (array+index / array+position /
    numeric-key fallback / missing story -> None)
  - the batched path applies the SAME per-cluster hygiene as the single path
    (em dash + significance word stripped) and keeps stories STRICTLY separate
  - a missing story triggers a smaller-batch / single RETRY on flash-lite
    (never rule-based), and the flash request count stays bounded by the schedule
  - all scheduled batches run on flash; the overflow retry runs on flash-lite
  - summarize_top50_after_rerank end-to-end: cache hit skipped, misses batched +
    stored, tier stamped 'flash'
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from summarizer import cluster_summarizer as c  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures + mock plumbing
# ---------------------------------------------------------------------------
_STORY_BLOCK_RE = re.compile(
    r"===== STORY (\d+) =====(.*?)"
    r"(?=(?:===== STORY \d+ =====)|(?:===== END OF STORIES =====))",
    re.S,
)


def _art(aid, title, body, source_name="Reuters", tier="us_major",
         lean="center", pub="2026-08-11T10:00"):
    return {
        "id": aid, "title": title, "full_text": body,
        "summary": body[:180], "source_name": source_name, "tier": tier,
        "source_lean_baseline": lean, "published_at": pub,
    }


def _cluster(cid, code, members=4):
    """A cluster whose article titles + bodies all carry a unique CODE_ token so a
    mock can prove which cluster a returned summary belongs to (story separation).
    All members share the code so the on-topic filter keeps them."""
    title = f"{code} regional policy measure advances"
    arts = [
        _art(f"{cid}-{i}",
             f"{code} officials approve regional measure part {i}",
             (f"{code} officials approved the regional measure on Tuesday. "
              f"The plan affects 1200 residents across three districts. "
              f"Governor Reyes signed the order after a 12 to 3 vote. ") * 3,
             source_name=("AP" if i % 2 else "Reuters"),
             pub=f"2026-08-11T1{i}:00")
        for i in range(members)
    ]
    return {"cid": cid, "articles": arts, "title": title, "hash": f"h-{cid}"}


def _batch_summary_for(code):
    """A short grounded-looking brief that carries the story's own code and a
    deliberate em dash + 'significant' so the hygiene chain has something to strip."""
    return (
        f"{code} officials approved the regional measure Tuesday, a significant "
        f"step. Governor Reyes signed the order after a 12 to 3 vote. The plan "
        f"affects 1200 residents across three districts, funding roads and "
        f"clinics. Opponents said the timeline was rushed."
    )


class MockLLM:
    """Records calls and answers batch or single prompts. `drop_indices` omits
    those 1-based story numbers from a batch response (simulates a missing story).
    `fail_batch_once` makes the first batch of size >= `fail_size` return None."""

    def __init__(self, drop_indices=(), flash_exhausted=False):
        self.drop_indices = set(drop_indices)
        self.flash_exhausted = flash_exhausted
        self.calls = []  # list of (kind, model_label, n_stories)

    def __call__(self, prompt, system_instruction=None, max_output_tokens=8192,
                 prefer_provider=None, model=None, temperature=0.0):
        # Emulate _smart_generate_json's own flash -> flash-lite degrade so the
        # label reflects what actually answered.
        wants_flash = (model or "") == c.GEMINI_FLASH_MODEL
        if wants_flash and self.flash_exhausted:
            label = "gemini-flash-lite"
        elif wants_flash:
            label = "gemini-flash"
        else:
            label = "gemini-flash-lite"

        if "===== STORY 1 =====" in prompt:
            entries = []
            present = 0
            for m in _STORY_BLOCK_RE.finditer(prompt):
                k = int(m.group(1))
                block = m.group(2)
                code_m = re.search(r"CODE_[A-Z]+", block)
                code = code_m.group(0) if code_m else f"NOCODE{k}"
                if k in self.drop_indices:
                    continue
                present += 1
                entries.append({
                    "index": k,
                    "headline": f"{code} Officials Approve Regional Policy Measure Today",
                    "summary": _batch_summary_for(code),
                    "consensus": [f"All sources report {code} approved the measure.",
                                  "The vote was 12 to 3.",
                                  "It affects 1200 residents."],
                    "divergence": ["Reuters emphasized cost.",
                                   "AP led with the timeline."],
                    "editorial_importance": 7,
                    "story_type": "policy_action",
                    "has_binding_consequences": True,
                })
            n = len(_STORY_BLOCK_RE.findall(prompt))
            self.calls.append(("batch", label, n))
            return {"stories": entries}, label

        # single-cluster prompt (solo batch or overflow single retry)
        code_m = re.search(r"CODE_[A-Z]+", prompt)
        code = code_m.group(0) if code_m else "CODE_SOLO"
        self.calls.append(("single", label, 1))
        return {
            "headline": f"{code} Officials Approve Regional Policy Measure Today",
            "summary": _batch_summary_for(code),
            "consensus": [f"All sources report {code} approved the measure.",
                          "The vote was 12 to 3.", "It affects 1200 residents."],
            "divergence": ["Reuters emphasized cost.", "AP led with the timeline."],
            "editorial_importance": 7, "story_type": "policy_action",
            "has_binding_consequences": True,
        }, label


class _patched:
    """Context manager: force availability + budget on and swap in a MockLLM."""

    def __init__(self, mock, calls_remaining=999):
        self.mock = mock
        self.calls_remaining = calls_remaining
        self._saved = {}

    def __enter__(self):
        for name in ("_smart_generate_json", "is_available", "calls_remaining"):
            self._saved[name] = getattr(c, name)
        c._smart_generate_json = self.mock
        c.is_available = lambda: True
        c.calls_remaining = lambda: self.calls_remaining
        return self.mock

    def __exit__(self, *a):
        for name, fn in self._saved.items():
            setattr(c, name, fn)


def _records(codes, members=4):
    return [_cluster(f"c{i}", code, members=members)
            for i, code in enumerate(codes)]


# ---------------------------------------------------------------------------
# 1. Batch prompt: delimiters + separation rule + one block per story
# ---------------------------------------------------------------------------
def test_batch_prompt_delimits_every_story():
    recs = _records(["CODE_ALPHA", "CODE_BRAVO", "CODE_CHARLIE"])
    cap = c._batch_article_cap(len(recs))
    blocks = [c._build_batch_story_block(r["articles"], r["title"], i + 1, cap)
              for i, r in enumerate(recs)]
    prompt = c._build_batch_prompt(blocks, len(recs))
    # Three delimited stories, in order.
    assert prompt.count("===== STORY 1 =====") == 1
    assert prompt.count("===== STORY 2 =====") == 1
    assert prompt.count("===== STORY 3 =====") == 1
    assert prompt.index("STORY 1") < prompt.index("STORY 2") < prompt.index("STORY 3")
    assert "===== END OF STORIES =====" in prompt
    # Separation instruction present.
    assert "ABSOLUTE SEPARATION RULE" in prompt
    assert "must NEVER appear" in prompt
    # Each story's own code lives inside its own block only.
    for code in ("CODE_ALPHA", "CODE_BRAVO", "CODE_CHARLIE"):
        assert code in prompt
    # The shared TASK rules ride once (single source of truth).
    assert "TASK 1" in prompt and "TASK 7" in prompt
    assert prompt.rstrip().endswith("}")  # JSON output spec at the tail


def test_batch_prompt_thin_cluster_gets_relax_note():
    recs = _records(["CODE_THIN"], members=3)  # below _THIN_CLUSTER_ARTICLES
    cap = c._batch_article_cap(2)
    block = c._build_batch_story_block(recs[0]["articles"], recs[0]["title"], 1, cap)
    assert "limited source material" in block


# ---------------------------------------------------------------------------
# 2. Schedule chunking + graduated article depth
# ---------------------------------------------------------------------------
def test_schedule_chunks_match_constant():
    recs = list(range(50))
    chunks = c._schedule_chunks(recs)
    assert [len(ch) for ch in chunks] == c._SUMMARY_BATCH_SCHEDULE
    assert sum(len(ch) for ch in chunks) == 50
    # Order preserved, no gaps / dupes.
    assert [x for ch in chunks for x in ch] == recs


def test_schedule_packs_fewer_misses_gracefully():
    # 7 misses (a cache-heavy day): fills 1,1,4 then 1 into the ranks-7-14 slot.
    chunks = c._schedule_chunks(list(range(7)))
    assert [len(ch) for ch in chunks] == [1, 1, 4, 1]


def test_schedule_repeats_last_size_past_schedule():
    chunks = c._schedule_chunks(list(range(60)))
    # 50 consumed by the schedule, remaining 10 packed at the last size (6,6? no
    # -> last size is 6, so 6 then 4). Assert no chunk exceeds the max size.
    assert sum(len(ch) for ch in chunks) == 60
    assert max(len(ch) for ch in chunks) <= max(c._SUMMARY_BATCH_SCHEDULE)


def test_article_depth_graduates_with_batch_size():
    assert c._batch_article_cap(1) == c._MAX_SUMMARY_ARTICLES        # solo -> deepest
    assert c._batch_article_cap(1) >= c._batch_article_cap(8) >= c._batch_article_cap(10)
    assert c._batch_article_cap(10) >= c._BATCH_MIN_ARTICLES_PER_CLUSTER
    # A denser batch really does thin the per-cluster block.
    recs = _records(["CODE_X"] * 10, members=20)
    cap10 = c._batch_article_cap(10)
    block = c._build_batch_story_block(recs[0]["articles"], recs[0]["title"], 1, cap10)
    # No more than cap10 numbered article entries in the block.
    assert len(re.findall(r"^\[\d+\] ", block, re.M)) <= cap10


# ---------------------------------------------------------------------------
# 3. Batched-JSON parser
# ---------------------------------------------------------------------------
def test_parser_array_with_explicit_index():
    raw = {"stories": [{"index": 1, "headline": "A"}, {"index": 3, "headline": "C"},
                       {"index": 2, "headline": "B"}]}
    out = c._extract_batch_entries(raw, 3)
    assert [e["headline"] for e in out] == ["A", "B", "C"]  # placed by index


def test_parser_array_by_position_when_no_index():
    raw = {"stories": [{"headline": "A"}, {"headline": "B"}, {"headline": "C"}]}
    out = c._extract_batch_entries(raw, 3)
    assert [e["headline"] for e in out] == ["A", "B", "C"]


def test_parser_missing_story_is_none():
    raw = {"stories": [{"index": 1, "headline": "A"}, {"index": 3, "headline": "C"}]}
    out = c._extract_batch_entries(raw, 3)
    assert out[0]["headline"] == "A"
    assert out[1] is None            # story 2 absent -> None (drives the retry)
    assert out[2]["headline"] == "C"


def test_parser_numeric_key_fallback():
    raw = {"1": {"headline": "A"}, "2": {"headline": "B"}}
    out = c._extract_batch_entries(raw, 2)
    assert [e["headline"] for e in out] == ["A", "B"]


def test_parser_story_key_fallback():
    raw = {"story_1": {"headline": "A"}, "story_2": {"headline": "B"}}
    out = c._extract_batch_entries(raw, 2)
    assert [e["headline"] for e in out] == ["A", "B"]


def test_parser_non_dict_is_all_none():
    assert c._extract_batch_entries(["x"], 2) == [None, None]


# ---------------------------------------------------------------------------
# 4. Batched path applies per-cluster hygiene AND keeps stories separate
# ---------------------------------------------------------------------------
def test_send_one_batch_hygiene_and_separation():
    recs = _records(["CODE_ALPHA", "CODE_BRAVO", "CODE_CHARLIE"])
    mock = MockLLM()
    with _patched(mock):
        got, failed = c._send_one_batch(recs, c.GEMINI_FLASH_MODEL, "gemini", [])
    assert failed == []
    assert set(got) == {"c0", "c1", "c2"}
    # Per-cluster hygiene ran: the em dash + 'significant' are gone from each.
    for cid, res in got.items():
        assert "—" not in res["summary"] and "–" not in res["summary"]
        assert "significant" not in res["summary"].lower()
        assert res["_generator"] == "gemini-flash"
    # Strict separation: each cluster's summary carries its OWN code and none of
    # the others' codes.
    codes = {"c0": "CODE_ALPHA", "c1": "CODE_BRAVO", "c2": "CODE_CHARLIE"}
    for cid, own in codes.items():
        assert own in got[cid]["summary"]
        for other_cid, other in codes.items():
            if other_cid != cid:
                assert other not in got[cid]["summary"]
    # Exactly ONE request for the whole batch of 3.
    assert len(mock.calls) == 1 and mock.calls[0][0] == "batch"


def test_send_one_batch_solo_uses_single_path_one_request():
    recs = _records(["CODE_SOLO"])
    mock = MockLLM()
    with _patched(mock):
        got, failed = c._send_one_batch(recs, c.GEMINI_FLASH_MODEL, "gemini", [])
    assert set(got) == {"c0"} and failed == []
    assert len(mock.calls) == 1 and mock.calls[0][0] == "single"


# ---------------------------------------------------------------------------
# 5. Missing story -> bounded retry (NEVER rule-based), flash then flash-lite
# ---------------------------------------------------------------------------
def test_send_one_batch_missing_story_reported_as_failure():
    # Direct unit: a 3-story batch whose model omits story 2 returns got={c0,c2}
    # and failed=[c1], so the caller can retry (never silently drop).
    recs = _records(["CODE_ALPHA", "CODE_BRAVO", "CODE_CHARLIE"])
    mock = MockLLM(drop_indices={2})
    with _patched(mock):
        got, failed = c._send_one_batch(recs, c.GEMINI_FLASH_MODEL, "gemini", [])
    assert set(got) == {"c0", "c2"}
    assert [r["cid"] for r in failed] == ["c1"]


def test_missing_story_triggers_retry_not_rule_based():
    # Six misses chunk as [1, 1, 4] (two solos + a batch of four). The model omits
    # STORY 2 of the four-story batch (cluster c3); the run must recover it via a
    # bounded flash-lite OVERFLOW retry, never fall to rule-based.
    codes = ["CODE_A", "CODE_B", "CODE_C", "CODE_D", "CODE_E", "CODE_F"]
    recs = _records(codes)
    # Sanity: the six misses really do form a multi-story batch.
    assert [len(ch) for ch in c._schedule_chunks(recs)] == [1, 1, 4]
    mock = MockLLM(drop_indices={2})   # 2nd story of the batch-of-4 == c3
    with _patched(mock):
        results = c._run_summary_batches(recs, prefer_provider="gemini")
    # Every story resolved (nothing dropped, nothing rule-based).
    assert set(results) == {"c0", "c1", "c2", "c3", "c4", "c5"}
    # The recovered story carries ITS OWN code (correct cluster after retry).
    assert "CODE_D" in results["c3"]["summary"]
    labels = [lbl for (k, lbl, n) in mock.calls]
    # The multi-story batch ran on flash; the overflow retry ran on flash-lite.
    assert any(k == "batch" and lbl == "gemini-flash"
               for (k, lbl, n) in mock.calls)
    assert "gemini-flash-lite" in labels          # overflow spent flash-lite, not flash
    # Bounded: overflow retry stays within its request cap.
    overflow_reqs = sum(1 for lbl in labels if lbl == "gemini-flash-lite")
    assert overflow_reqs <= c._MAX_OVERFLOW_RETRY_REQUESTS


def test_overflow_retry_is_flash_lite_only():
    # Force flash "exhausted": the batch degrades to flash-lite inside the mock,
    # so no story is dropped and no extra flash requests are spent.
    recs = _records(["CODE_A", "CODE_B"])
    mock = MockLLM(flash_exhausted=True)
    with _patched(mock):
        results = c._run_summary_batches(recs, prefer_provider="gemini")
    assert set(results) == {"c0", "c1"}
    # Tier stamped flash-lite (what actually answered) so next run re-attempts.
    assert all(r["_generator"] == "gemini-flash-lite" for r in results.values())


def test_run_batches_flash_request_count_bounded_by_schedule():
    # 50 misses -> exactly len(schedule) flash requests (8), no ballooning.
    recs = _records([f"CODE_S{i}" for i in range(50)])
    mock = MockLLM()
    with _patched(mock):
        results = c._run_summary_batches(recs, prefer_provider="gemini")
    assert len(results) == 50
    flash_reqs = sum(1 for (k, lbl, n) in mock.calls if lbl == "gemini-flash")
    assert flash_reqs == len(c._SUMMARY_BATCH_SCHEDULE) == 8


# ---------------------------------------------------------------------------
# 6. End-to-end: summarize_top50_after_rerank with a fake Supabase
# ---------------------------------------------------------------------------
class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self._filters = {}
        self._update = None

    def select(self, *a, **k):
        return self

    def contains(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def in_(self, col, vals):
        self._filters["in"] = (col, list(vals))
        return self

    def eq(self, col, val):
        self._filters["eq"] = (col, val)
        return self

    def update(self, payload):
        self._update = payload
        return self

    def execute(self):
        if self._update is not None:
            cid = self._filters["eq"][1]
            self.db["clusters"][cid].update(self._update)
            self.db["writes"].append((cid, dict(self._update)))
            return _FakeResult([{"id": cid}])
        if self.name == "story_clusters":
            rows = list(self.db["clusters"].values())
            return _FakeResult(rows)
        if self.name == "cluster_articles":
            col, vals = self._filters["in"]
            links = [l for l in self.db["links"] if l["cluster_id"] in vals]
            return _FakeResult(links)
        if self.name == "articles":
            col, vals = self._filters["in"]
            arts = [self.db["articles"][a] for a in vals if a in self.db["articles"]]
            return _FakeResult(arts)
        if self.name == "sources":
            col, vals = self._filters["in"]
            return _FakeResult([self.db["sources"][s] for s in vals
                                if s in self.db["sources"]])
        return _FakeResult([])


class _FakeSupabase:
    def __init__(self, db):
        self.db = db

    def table(self, name):
        return _FakeTable(self.db, name)


def _build_fake_db(specs):
    """specs: list of (cid, code, source_count, prior_hash, prior_tier). Builds a
    story_clusters + cluster_articles + articles + sources fixture."""
    db = {"clusters": {}, "links": [], "articles": {}, "sources": {}, "writes": []}
    db["sources"]["src-ap"] = {"id": "src-ap", "name": "AP",
                               "tier": "us_major", "political_lean_baseline": "center"}
    db["sources"]["src-re"] = {"id": "src-re", "name": "Reuters",
                               "tier": "us_major", "political_lean_baseline": "center"}
    for rank, (cid, code, sc, phash, ptier) in enumerate(specs):
        db["clusters"][cid] = {
            "id": cid, "title": f"{code} regional measure advances",
            "content_type": "news", "source_count": sc,
            "summary_article_hash": phash, "summary_tier": ptier,
            "summary": "prior summary text", "sections": ["world"],
            "rank_world": 100 - rank,
        }
        for i in range(max(sc, 4)):
            aid = f"{cid}-a{i}"
            db["links"].append({"cluster_id": cid, "article_id": aid})
            db["articles"][aid] = {
                "id": aid, "title": f"{code} officials approve measure {i}",
                "summary": f"{code} short excerpt {i}",
                "full_text": (f"{code} officials approved the regional measure "
                              f"Tuesday. The plan affects 1200 residents. "
                              f"Governor Reyes signed the order. ") * 3,
                "source_id": "src-ap" if i % 2 else "src-re",
                "published_at": f"2026-08-11T1{i}:00", "url": f"http://x/{aid}",
            }
    return db


def test_top50_end_to_end_miss_batched_and_stored():
    # Five misses (no prior hash) + one CACHE HIT (matching hash, tier flash).
    # Five misses chunk [1, 1, 3] -> two solos + a real batch of three.
    specs = [
        ("c0", "CODE_ALPHA", 5, None, None),
        ("c1", "CODE_BRAVO", 5, None, None),
        ("c2", "CODE_CHARLIE", 5, None, None),
        ("c3", "CODE_DELTA", 5, None, None),
        ("c4", "CODE_ECHO", 5, None, None),
        ("c5", "CODE_CACHED", 5, "WILLMATCH", "flash"),
    ]
    db = _build_fake_db(specs)
    supa = _FakeSupabase(db)
    # Make c5 a genuine cache hit: its stored hash must equal the computed hash.
    c5_arts = [db["articles"][l["article_id"]] for l in db["links"]
               if l["cluster_id"] == "c5"]
    db["clusters"]["c5"]["summary_article_hash"] = c._content_hash(c5_arts)

    mock = MockLLM()
    with _patched(mock):
        metrics = c.summarize_top50_after_rerank(supa, edition="world", limit=50)

    assert metrics["cached"] == 1                     # c5 skipped, no LLM call
    assert metrics["summarized"] == 5                 # c0..c4 generated
    written = {cid for cid, _ in db["writes"]}
    assert "c5" not in written                        # cache hit never rewritten
    assert {"c0", "c1", "c2", "c3", "c4"} <= written
    # Stored tier is flash + hash set; each summary carries its OWN code only.
    codes = {"c0": "CODE_ALPHA", "c1": "CODE_BRAVO", "c2": "CODE_CHARLIE",
             "c3": "CODE_DELTA", "c4": "CODE_ECHO"}
    for cid, own in codes.items():
        row = db["clusters"][cid]
        assert row["summary_tier"] == "flash"
        assert row["summary_article_hash"] is not None
        assert own in row["summary"]
        for other_cid, other in codes.items():
            if other_cid != cid:
                assert other not in row["summary"]     # strict separation
    # Batching really happened: at least one flash request carried >1 story, and
    # the five misses cost fewer flash requests than five per-cluster calls.
    flash_reqs = [(k, n) for (k, lbl, n) in mock.calls if lbl == "gemini-flash"]
    assert any(k == "batch" and n >= 2 for (k, n) in flash_reqs)
    assert len(flash_reqs) < 5


def test_top50_opinion_and_thin_are_skipped_no_llm():
    specs = [("c0", "CODE_OP", 5, None, None)]
    db = _build_fake_db(specs)
    db["clusters"]["c0"]["content_type"] = "opinion"   # op-ed: bypass LLM
    supa = _FakeSupabase(db)
    mock = MockLLM()
    with _patched(mock):
        metrics = c.summarize_top50_after_rerank(supa, edition="world", limit=50)
    assert metrics["summarized"] == 0
    assert metrics["skipped"] >= 1
    assert mock.calls == []                            # no request at all


# ---------------------------------------------------------------------------
def _run():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed}/{len(fns)} batch-summarization tests passed")


if __name__ == "__main__":
    _run()

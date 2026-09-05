"""
Tests for pgrest_sqlite.py — the SQLite drop-in for the supabase-py client.

Runs against a REAL staged copy of the production DB (all columns TEXT), plus a
scratch in-memory / temp DB for write-path tests (insert/update/upsert/delete).

Run:  python -m unittest pipeline/utils/test_pgrest_sqlite.py
  or: cd pipeline/utils && python -m unittest test_pgrest_sqlite
"""

import os
import sqlite3
import tempfile
import unittest

import pgrest_sqlite as pg


STAGED_DB = os.environ.get(
    "VOID_STAGED_DB",
    r"C:\Users\aacri\AppData\Local\Temp\claude\C--Users-aacri-claudeprojects-voidnews"
    r"\d98bc31c-be95-4757-962f-2f214e173745\scratchpad\rescue\void_local.db",
)


@unittest.skipUnless(os.path.exists(STAGED_DB), f"staged DB not found: {STAGED_DB}")
class TestReadPath(unittest.TestCase):
    """Read-only assertions against the real staged production data."""

    @classmethod
    def setUpClass(cls):
        cls.sb = pg.create_client(STAGED_DB)

    def test_jsonb_and_array_parsing(self):
        res = (
            self.sb.table("story_clusters")
            .select("id,title,rank_world,bias_diversity,sections")
            .neq("bias_diversity", "")
            .limit(20)
            .execute()
        )
        self.assertTrue(res.data, "expected some clusters")
        # find a row with both populated
        found = None
        for r in res.data:
            if isinstance(r.get("bias_diversity"), dict) and r.get("sections") is not None:
                found = r
                break
        self.assertIsNotNone(found, "expected a cluster with dict bias_diversity")
        self.assertIsInstance(found["bias_diversity"], dict)
        self.assertIsInstance(found["sections"], list)
        self.assertIn("world", found["sections"])

    def test_contains_order_limit(self):
        res = (
            self.sb.table("story_clusters")
            .select("*")
            .contains("sections", ["world"])
            .order("rank_world", desc=True)
            .limit(5)
            .execute()
        )
        self.assertEqual(len(res.data), 5)
        for r in res.data:
            self.assertIn("world", pg._to_array_value(r["sections"]))
        vals = [float(r["rank_world"]) for r in res.data]
        self.assertEqual(vals, sorted(vals, reverse=True),
                         f"rank_world not descending: {vals}")

    def test_order_ascending(self):
        res = (
            self.sb.table("story_clusters")
            .select("id,rank_world")
            .contains("sections", ["world"])
            .order("rank_world")  # default asc
            .limit(5)
            .execute()
        )
        vals = [float(r["rank_world"]) for r in res.data]
        self.assertEqual(vals, sorted(vals))

    def test_in_filter(self):
        # grab a few ids, then re-query with in_
        head = self.sb.table("story_clusters").select("id").limit(3).execute()
        ids = [r["id"] for r in head.data]
        self.assertEqual(len(ids), 3)
        res = self.sb.table("story_clusters").select("id").in_("id", ids).execute()
        got = {r["id"] for r in res.data}
        self.assertEqual(got, set(ids))

    def test_in_empty_matches_nothing(self):
        res = self.sb.table("story_clusters").select("id").in_("id", []).execute()
        self.assertEqual(res.data, [])

    def test_gte_filter(self):
        res = (
            self.sb.table("articles")
            .select("id,word_count")
            .gte("word_count", 100)
            .limit(10)
            .execute()
        )
        for r in res.data:
            self.assertGreaterEqual(float(r["word_count"]), 100)

    def test_eq_and_single(self):
        head = self.sb.table("story_clusters").select("id,title").limit(1).execute()
        one_id = head.data[0]["id"]
        res = (
            self.sb.table("story_clusters")
            .select("id,title")
            .eq("id", one_id)
            .single()
            .execute()
        )
        self.assertIsInstance(res.data, dict)
        self.assertEqual(res.data["id"], one_id)

    def test_single_raises_on_multiple(self):
        with self.assertRaises(pg.SqliteRestError):
            (
                self.sb.table("story_clusters")
                .select("id")
                .contains("sections", ["world"])
                .single()
                .execute()
            )

    def test_maybe_single_none(self):
        res = (
            self.sb.table("story_clusters")
            .select("id")
            .eq("id", "no-such-id-00000000")
            .maybe_single()
            .execute()
        )
        self.assertIsNone(res.data)

    def test_maybe_single_one(self):
        head = self.sb.table("story_clusters").select("id").limit(1).execute()
        one_id = head.data[0]["id"]
        res = (
            self.sb.table("story_clusters")
            .select("id")
            .eq("id", one_id)
            .maybe_single()
            .execute()
        )
        self.assertIsInstance(res.data, dict)
        self.assertEqual(res.data["id"], one_id)

    def test_range_pagination(self):
        page0 = self.sb.table("articles").select("id").order("id").range(0, 4).execute()
        page1 = self.sb.table("articles").select("id").order("id").range(5, 9).execute()
        self.assertEqual(len(page0.data), 5)
        self.assertEqual(len(page1.data), 5)
        self.assertFalse(
            {r["id"] for r in page0.data} & {r["id"] for r in page1.data},
            "range pages overlapped",
        )

    def test_is_null(self):
        # some clusters may have null story_memory_id
        res = (
            self.sb.table("story_clusters")
            .select("id,story_memory_id")
            .is_("story_memory_id", "null")
            .limit(5)
            .execute()
        )
        for r in res.data:
            self.assertIsNone(r["story_memory_id"])

    def test_not_is_null(self):
        res = (
            self.sb.table("story_clusters")
            .select("id,rank_world")
            .not_.is_("rank_world", "null")
            .limit(5)
            .execute()
        )
        for r in res.data:
            self.assertIsNotNone(r["rank_world"])

    def test_match(self):
        res = (
            self.sb.table("story_clusters")
            .select("id,section")
            .match({"section": "world"})
            .limit(5)
            .execute()
        )
        self.assertTrue(res.data)
        for r in res.data:
            self.assertEqual(r["section"], "world")

    def test_projection_restricts_columns(self):
        res = self.sb.table("sources").select("id,name,tier").limit(1).execute()
        self.assertTrue(res.data)
        self.assertEqual(set(res.data[0].keys()), {"id", "name", "tier"})

    def test_unknown_column_raises(self):
        with self.assertRaises(pg.SqliteRestError):
            self.sb.table("story_clusters").select("id").eq("no_such_col", 1).execute()

    def test_embedded_select_nested(self):
        # cluster_articles -> articles -> sources (two-level embed, real data)
        # pick a cluster_articles row
        head = self.sb.table("cluster_articles").select("cluster_id,article_id").limit(1).execute()
        cid = head.data[0]["cluster_id"]
        res = (
            self.sb.table("cluster_articles")
            .select("article_id, articles(id, title, summary, url, source_id, sources(tier, name))")
            .eq("cluster_id", cid)
            .execute()
        )
        self.assertTrue(res.data)
        row = res.data[0]
        self.assertIn("article_id", row)
        art = row.get("articles")
        self.assertIsInstance(art, dict)
        self.assertIn("title", art)
        # nested source (to-one via source_id)
        src = art.get("sources")
        self.assertTrue(src is None or isinstance(src, dict))
        if isinstance(src, dict):
            self.assertLessEqual(set(src.keys()), {"tier", "name"})

    def test_embedded_select_aliased_and_reverse(self):
        # articles embed bias_scores (reverse FK: bias_scores.article_id) + aliased source
        head = self.sb.table("articles").select("id").limit(1).execute()
        aid = head.data[0]["id"]
        res = (
            self.sb.table("articles")
            .select("id, source:sources(name, tier), bias_scores(political_lean)")
            .eq("id", aid)
            .execute()
        )
        row = res.data[0]
        self.assertIn("source", row)           # aliased to-one
        self.assertIn("bias_scores", row)       # reverse to-many -> list
        self.assertIsInstance(row["bias_scores"], list)


class TestWritePath(unittest.TestCase):
    """Insert/update/upsert/delete against a throwaway temp DB."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(self.path)
        conn.executescript(
            """
            CREATE TABLE widgets (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                payload TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """
        )
        conn.commit()
        conn.close()
        self.sb = pg.create_client(self.path)

    def tearDown(self):
        self.sb.close()
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_insert_autogen_id_and_json_roundtrip(self):
        res = (
            self.sb.table("widgets")
            .insert({"name": "alpha", "payload": {"k": 1, "nested": [1, 2, 3]},
                     "tags": ["a", "b"]})
            .execute()
        )
        self.assertEqual(len(res.data), 1)
        row = res.data[0]
        self.assertTrue(row["id"])  # auto-generated uuid
        self.assertIsInstance(row["payload"], dict)
        self.assertEqual(row["payload"]["k"], 1)
        self.assertEqual(row["payload"]["nested"], [1, 2, 3])
        self.assertIsInstance(row["tags"], list)
        self.assertTrue(row["created_at"])       # auto timestamp
        self.assertTrue(row["updated_at"])

        # read back
        back = self.sb.table("widgets").select("*").eq("name", "alpha").single().execute()
        self.assertIsInstance(back.data["payload"], dict)
        self.assertEqual(back.data["payload"]["k"], 1)

    def test_duplicate_unique_raises_with_unique(self):
        self.sb.table("widgets").insert({"name": "dup"}).execute()
        with self.assertRaises(Exception) as ctx:
            self.sb.table("widgets").insert({"name": "dup"}).execute()
        msg = str(ctx.exception).lower()
        self.assertTrue("unique" in msg or "duplicate" in msg,
                        f"message lacked unique/duplicate: {msg}")

    def test_update(self):
        ins = self.sb.table("widgets").insert({"name": "u1", "payload": {"v": 1}}).execute()
        wid = ins.data[0]["id"]
        upd = (
            self.sb.table("widgets")
            .update({"payload": {"v": 99}})
            .eq("id", wid)
            .execute()
        )
        self.assertEqual(upd.data[0]["payload"]["v"], 99)

    def test_upsert_insert_then_update(self):
        # first upsert inserts
        r1 = (
            self.sb.table("widgets")
            .upsert({"id": "fixed-1", "name": "up", "payload": {"n": 1}}, on_conflict="id")
            .execute()
        )
        self.assertEqual(r1.data[0]["payload"]["n"], 1)
        # second upsert on same id updates
        r2 = (
            self.sb.table("widgets")
            .upsert({"id": "fixed-1", "name": "up", "payload": {"n": 2}}, on_conflict="id")
            .execute()
        )
        self.assertEqual(r2.data[0]["payload"]["n"], 2)
        # only one row
        allrows = self.sb.table("widgets").select("id").eq("id", "fixed-1").execute()
        self.assertEqual(len(allrows.data), 1)

    def test_upsert_on_conflict_url_like_column(self):
        r1 = self.sb.table("widgets").upsert(
            {"name": "conflictme", "payload": {"a": 1}}, on_conflict="name"
        ).execute()
        self.assertEqual(r1.data[0]["payload"]["a"], 1)
        r2 = self.sb.table("widgets").upsert(
            {"name": "conflictme", "payload": {"a": 2}}, on_conflict="name"
        ).execute()
        self.assertEqual(r2.data[0]["payload"]["a"], 2)
        cnt = self.sb.table("widgets").select("id").eq("name", "conflictme").execute()
        self.assertEqual(len(cnt.data), 1)

    def test_upsert_ignore_duplicates(self):
        self.sb.table("widgets").insert({"name": "keep", "payload": {"x": 1}}).execute()
        # ignore_duplicates -> DO NOTHING, original value preserved
        self.sb.table("widgets").upsert(
            {"name": "keep", "payload": {"x": 2}}, on_conflict="name",
            ignore_duplicates=True,
        ).execute()
        back = self.sb.table("widgets").select("payload").eq("name", "keep").single().execute()
        self.assertEqual(back.data["payload"]["x"], 1)

    def test_delete(self):
        self.sb.table("widgets").insert({"name": "del1"}).execute()
        self.sb.table("widgets").insert({"name": "del2"}).execute()
        res = self.sb.table("widgets").delete().eq("name", "del1").execute()
        self.assertEqual(len(res.data), 1)
        remaining = self.sb.table("widgets").select("name").execute()
        names = {r["name"] for r in remaining.data}
        self.assertNotIn("del1", names)
        self.assertIn("del2", names)

    def test_insert_unknown_column_raises(self):
        with self.assertRaises(pg.SqliteRestError):
            self.sb.table("widgets").insert({"name": "x", "bogus": 1}).execute()

    def test_contains_dict(self):
        self.sb.table("widgets").insert({"name": "jd", "payload": {"a": 1, "b": 2}}).execute()
        hit = (
            self.sb.table("widgets")
            .select("name")
            .contains("payload", {"a": 1})
            .execute()
        )
        self.assertTrue(any(r["name"] == "jd" for r in hit.data))
        miss = (
            self.sb.table("widgets")
            .select("name")
            .contains("payload", {"a": 999})
            .execute()
        )
        self.assertFalse(any(r["name"] == "jd" for r in miss.data))


@unittest.skipUnless(os.path.exists(STAGED_DB), "staged DB not found")
class TestRPCs(unittest.TestCase):
    """RPCs against a temp COPY of the staged DB (so deletes don't harm it)."""

    def setUp(self):
        import shutil
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        shutil.copyfile(STAGED_DB, self.path)
        self.sb = pg.create_client(self.path)

    def tearDown(self):
        self.sb.close()
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_printed_archive_stats(self):
        res = self.sb.rpc("printed_archive_stats", {}).execute()
        self.assertIsInstance(res.data, dict)
        self.assertIn("days", res.data)
        self.assertIn("stories", res.data)
        self.assertGreater(res.data["stories"], 0)

    def test_cleanup_stale_articles(self):
        before = self.sb.table("articles").select("id").limit(1).execute()
        self.assertTrue(before.data)
        # days=0 -> everything with published_at < now is deleted
        res = self.sb.rpc("cleanup_stale_articles", {"days": 0}).execute()
        self.assertIsInstance(res.data, int)
        self.assertGreaterEqual(res.data, 0)

    def test_cleanup_stale_clusters(self):
        res = self.sb.rpc("cleanup_stale_clusters", {"max_age_days": 3650}).execute()
        self.assertIsInstance(res.data, int)

    def test_cleanup_diagnostic_tables(self):
        res = self.sb.rpc("cleanup_diagnostic_tables", {}).execute()
        self.assertIsInstance(res.data, dict)
        self.assertIn("db_size_mb", res.data)
        self.assertIn("engine_snapshots_pruned", res.data)

    def test_cleanup_stuck_pipeline_runs(self):
        res = self.sb.rpc("cleanup_stuck_pipeline_runs", {"max_minutes": 1}).execute()
        self.assertIsInstance(res.data, int)

    def test_refresh_cluster_enrichment_raises_does_not_exist(self):
        # deliberately signals 'does not exist' so pipeline uses Python fallback
        with self.assertRaises(pg.SqliteRestError) as ctx:
            self.sb.rpc("refresh_cluster_enrichment", {"p_cluster_id": "x"}).execute()
        self.assertIn("does not exist", str(ctx.exception).lower())

    def test_unknown_rpc_raises_does_not_exist(self):
        with self.assertRaises(pg.SqliteRestError) as ctx:
            self.sb.rpc("totally_made_up_fn", {}).execute()
        self.assertIn("does not exist", str(ctx.exception).lower())


class TestStorageStub(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sb = pg.create_client(os.path.join(self.tmp, "x.db"),
                                   storage_root=os.path.join(self.tmp, "._r2_stage"))

    def test_upload_and_url(self):
        bucket = self.sb.storage.from_("ig-renders")
        bucket.upload("2026-08-30/a.png", b"hello-bytes")
        url = bucket.get_public_url("2026-08-30/a.png")
        self.assertIn("ig-renders", url)
        staged = os.path.join(self.tmp, "._r2_stage", "ig-renders", "2026-08-30", "a.png")
        self.assertTrue(os.path.exists(staged))
        with open(staged, "rb") as fh:
            self.assertEqual(fh.read(), b"hello-bytes")


if __name__ == "__main__":
    unittest.main(verbosity=2)

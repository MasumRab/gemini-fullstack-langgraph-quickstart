"""Local SQLite store for Jules session metadata and activity summaries.

Provides structured querying (state, count, delta tracking) and full-text
search via FTS4. Heavy artifact data (git patches, bash output, media)
stays in ``jules_sessions/*.json`` files on the filesystem.

Schema:
  sessions         — metadata + agent notes (lean, indexed, no blobs)
  activities       — per-event summary rows (no patches, no media)
  sessions_fts     — FTS4 index over title, prompt_snippet, notes
  activities_fts   — FTS4 index over summary text
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

STORE_DIR = Path.home() / ".jules"
STORE_DB = STORE_DIR / "store.db"

# Conservative defaults — caller must opt-in for heavy activity fetching
DEFAULT_ACTIVITY_LIMIT = 0       # sessions to fetch activities for
DEFAULT_ACTIVITY_MAX = 20        # max activities per session
DEFAULT_FETCH_THRESHOLD = 20     # skip if known >= this + terminal state

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    state         TEXT NOT NULL DEFAULT 'UNKNOWN',
    title         TEXT,
    prompt_snippet TEXT,
    create_time   TEXT,
    update_time   TEXT,
    pr_url        TEXT,
    repo          TEXT,
    activity_count INTEGER NOT NULL DEFAULT 0,
    notes         TEXT,
    tags          TEXT DEFAULT '[]',
    raw_path      TEXT,
    first_seen    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_seen     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    fetch_count   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS activities (
    session_id    TEXT NOT NULL,
    create_time   TEXT NOT NULL,
    activity_type TEXT,
    originator    TEXT,
    summary       TEXT,
    artifact_count INTEGER NOT NULL DEFAULT 0,
    has_bash_error INTEGER NOT NULL DEFAULT 0,
    raw_path      TEXT,
    PRIMARY KEY (session_id, create_time)
);

CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts4(
    session_id,
    title,
    prompt_snippet,
    notes
);

CREATE VIRTUAL TABLE IF NOT EXISTS activities_fts USING fts4(
    session_id,
    create_time,
    activity_type,
    summary
);

CREATE TABLE IF NOT EXISTS sync_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _extract_session_row(s: dict) -> dict:
    session_id = s.get("name", "").replace("sessions/", "")
    repo = ""
    sc = s.get("sourceContext", {})
    source = sc.get("source", "")
    if source.startswith("sources/github/"):
        repo = source.replace("sources/github/", "")
    pr_url = ""
    for o in s.get("outputs", []):
        pr_url = o.get("pullRequest", {}).get("url", "") or pr_url
    prompt_snippet = (s.get("prompt") or "")[:500]
    return dict(
        session_id=session_id,
        state=s.get("state", "UNKNOWN"),
        title=(s.get("title") or "")[:200],
        prompt_snippet=prompt_snippet,
        create_time=s.get("createTime", ""),
        update_time=s.get("updateTime", ""),
        pr_url=pr_url,
        repo=repo,
    )


def _extract_repo(s: dict) -> str:
    sc = s.get("sourceContext", {})
    source = sc.get("source", "")
    if source.startswith("sources/github/"):
        return source.replace("sources/github/", "")
    return ""


def _extract_activity_row(session_id: str, a: dict) -> dict:
    activity_type = "unknown"
    for key in (
        "agentMessaged", "userMessaged", "planGenerated", "planApproved",
        "progressUpdated", "sessionCompleted", "sessionFailed",
    ):
        if key in a:
            activity_type = key
            break
    summary = ""
    originator = a.get("originator", "")
    if "agentMessaged" in a:
        summary = (a["agentMessaged"].get("agentMessage") or "")[:200]
    elif "userMessaged" in a:
        summary = (a["userMessaged"].get("userMessage") or "")[:200]
    elif "progressUpdated" in a:
        summary = (a["progressUpdated"].get("title") or "")[:200]
    elif "sessionFailed" in a:
        summary = a["sessionFailed"].get("reason", "Unknown reason")[:200]
    artifact_count = len(a.get("artifacts", []))
    has_error = 0
    for art in a.get("artifacts", []):
        if art.get("type") == "bashOutput":
            try:
                text = art.get("text", "")
                if any(e in text for e in ("exit code", "Error", "error", "failed")):
                    has_error = 1
            except Exception:
                pass
    return dict(
        session_id=session_id,
        create_time=a.get("createTime", ""),
        activity_type=activity_type,
        originator=originator,
        summary=summary,
        artifact_count=artifact_count,
        has_bash_error=has_error,
    )


class JulesSessionStore:
    """Local SQLite store for Jules session metadata and activity summaries.

    Usage::

        store = JulesSessionStore()
        store.upsert_session(api_session_dict)
        store.upsert_activities("sessions/123", api_activities_list)

        # Structured queries
        active = store.list_sessions(state="AWAITING_USER_FEEDBACK")

        # Delta tracking
        seen = store.get_activity_count("sessions/123")

        # Full-text search
        results = store.search_sessions("pytest fixture mock")
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else STORE_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def upsert_session(self, session_data: dict) -> None:
        """Insert or update a session from an API response dict."""
        row = _extract_session_row(session_data)
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT activity_count, notes, tags FROM sessions WHERE session_id=?",
                (row["session_id"],),
            ).fetchone()
            if existing:
                activity_count = existing["activity_count"]
                notes = existing["notes"]
                tags = existing["tags"]
            else:
                activity_count = 0
                notes = None
                tags = "[]"
            conn.execute(
                """INSERT INTO sessions
                   (session_id, state, title, prompt_snippet, create_time,
                    update_time, pr_url, repo, activity_count, notes, tags,
                    last_seen, fetch_count)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?, strftime('%Y-%m-%dT%H:%M:%SZ','now'),
                           COALESCE((SELECT fetch_count+1 FROM sessions WHERE session_id=?), 1))
                   ON CONFLICT(session_id) DO UPDATE SET
                       state=excluded.state,
                       title=excluded.title,
                       prompt_snippet=excluded.prompt_snippet,
                       update_time=excluded.update_time,
                       pr_url=excluded.pr_url,
                       repo=excluded.repo,
                       activity_count=excluded.activity_count,
                       last_seen=strftime('%Y-%m-%dT%H:%M:%SZ','now'),
                       fetch_count=excluded.fetch_count""",
                (
                    row["session_id"],
                    row["state"],
                    row["title"],
                    row["prompt_snippet"],
                    row["create_time"],
                    row["update_time"],
                    row["pr_url"],
                    row["repo"],
                    activity_count,
                    notes,
                    tags,
                    row["session_id"],
                ),
            )
            # Sync FTS
            self._sync_session_fts(conn, row["session_id"])

    def _sync_session_fts(self, conn: sqlite3.Connection, session_id: str) -> None:
        row = conn.execute(
            "SELECT title, prompt_snippet, notes FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if not row:
            return
        conn.execute(
            "INSERT OR REPLACE INTO sessions_fts (docid, session_id, title, prompt_snippet, notes) "
            "VALUES ((SELECT docid FROM sessions_fts WHERE session_id=?), "
            "?, ?, ?, ?)",
            (session_id, session_id, row["title"] or "", row["prompt_snippet"] or "", row["notes"] or ""),
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata from the local store (not the API)."""
        sid = session_id.replace("sessions/", "")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id=?", (sid,)
            ).fetchone()
        if not row:
            return None
        return dict(row)

    def list_sessions(
        self,
        state: Optional[str] = None,
        exclude_state: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """Query sessions from the local store with optional filters."""
        q = "SELECT * FROM sessions"
        params: list = []
        clauses: list = []
        if state:
            clauses.append("state=?")
            params.append(state.upper())
        if exclude_state:
            clauses.append("state!=?")
            params.append(exclude_state.upper())
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += f" ORDER BY last_seen {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._conn() as conn:
            rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------

    def upsert_activities(self, session_id: str, activities: List[dict]) -> int:
        """Insert new activity summary rows. Returns count of new rows inserted.

        Uses INSERT OR IGNORE so repeated calls with the same data are safe.
        Updates the parent session's ``activity_count`` after insertion.
        """
        sid = session_id.replace("sessions/", "")
        if not activities:
            return 0
        new_count = 0
        with self._conn() as conn:
            rows = [_extract_activity_row(sid, a) for a in activities]
            for r in rows:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO activities
                           (session_id, create_time, activity_type, originator,
                            summary, artifact_count, has_bash_error)
                           VALUES (?,?,?,?,?,?,?)""",
                        (
                            r["session_id"],
                            r["create_time"],
                            r["activity_type"],
                            r["originator"],
                            r["summary"],
                            r["artifact_count"],
                            r["has_bash_error"],
                        ),
                    )
                    if conn.total_changes:
                        new_count += 1
                except sqlite3.IntegrityError:
                    pass
            # Update delta counter
            total = conn.execute(
                "SELECT COUNT(*) as c FROM activities WHERE session_id=?", (sid,)
            ).fetchone()["c"]
            conn.execute(
                "UPDATE sessions SET activity_count=? WHERE session_id=?",
                (total, sid),
            )
            # Sync FTS
            self._sync_activities_fts(conn, sid)
        return new_count

    def _sync_activities_fts(self, conn: sqlite3.Connection, session_id: str) -> None:
        rows = conn.execute(
            "SELECT create_time, activity_type, summary FROM activities WHERE session_id=?",
            (session_id,),
        ).fetchall()
        # Clear old FTS entries for this session, then re-insert
        conn.execute(
            "DELETE FROM activities_fts WHERE session_id=?", (session_id,)
        )
        for r in rows:
            conn.execute(
                "INSERT INTO activities_fts (session_id, create_time, activity_type, summary) "
                "VALUES (?,?,?,?)",
                (session_id, r["create_time"], r["activity_type"], r["summary"] or ""),
            )

    def get_activity_count(self, session_id: str) -> int:
        """Return how many activities the store has recorded for a session.

        Used for delta tracking — callers can compare this against the
        activity list length to know whether anything changed.
        """
        sid = session_id.replace("sessions/", "")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT activity_count FROM sessions WHERE session_id=?", (sid,)
            ).fetchone()
        return row["activity_count"] if row else 0

    # ------------------------------------------------------------------
    # Full-text search (FTS4)
    # ------------------------------------------------------------------

    def search_sessions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across session titles, prompts, and notes.

        Returns session metadata rows that match ``query``.
        """
        with self._conn() as conn:
            try:
                rows = conn.execute(
                    """SELECT s.* FROM sessions s
                       JOIN sessions_fts fts ON s.session_id = fts.session_id
                       WHERE sessions_fts MATCH ?
                       ORDER BY fts.rank
                       LIMIT ?""",
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                # FTS syntax error (e.g. bad query string) — fallback to LIKE
                like = f"%{query}%"
                rows = conn.execute(
                    """SELECT * FROM sessions
                       WHERE title LIKE ? OR prompt_snippet LIKE ? OR notes LIKE ?
                       LIMIT ?""",
                    (like, like, like, limit),
                ).fetchall()
        return [dict(r) for r in rows]

    def search_activities(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across activity summaries.

        Returns activity rows that match ``query``.
        """
        with self._conn() as conn:
            try:
                rows = conn.execute(
                    """SELECT a.* FROM activities a
                       JOIN activities_fts fts ON a.rowid = fts.docid
                       WHERE activities_fts MATCH ?
                       ORDER BY fts.rank
                       LIMIT ?""",
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                like = f"%{query}%"
                rows = conn.execute(
                    """SELECT * FROM activities
                       WHERE summary LIKE ?
                       LIMIT ?""",
                    (like, limit),
                ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Agent context
    # ------------------------------------------------------------------

    def set_notes(self, session_id: str, notes: str) -> None:
        """Store free-form LLM agent observations about a session."""
        sid = session_id.replace("sessions/", "")
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET notes=? WHERE session_id=?",
                (notes, sid),
            )
            self._sync_session_fts(conn, sid)

    def get_notes(self, session_id: str) -> Optional[str]:
        """Retrieve stored agent notes for a session."""
        sid = session_id.replace("sessions/", "")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT notes FROM sessions WHERE session_id=?", (sid,)
            ).fetchone()
        return row["notes"] if row else None

    def set_tags(self, session_id: str, tags: List[str]) -> None:
        """Tag a session for cross-cutting filtering."""
        sid = session_id.replace("sessions/", "")
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET tags=? WHERE session_id=?",
                (json.dumps(tags), sid),
            )

    def get_tags(self, session_id: str) -> List[str]:
        """Retrieve tags for a session."""
        sid = session_id.replace("sessions/", "")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT tags FROM sessions WHERE session_id=?", (sid,)
            ).fetchone()
        if not row:
            return []
        try:
            return json.loads(row["tags"])
        except (json.JSONDecodeError, TypeError):
            return []

    # ------------------------------------------------------------------
    # High-Water Mark — incremental sync stop condition
    # ------------------------------------------------------------------

    def _get_high_water_mark(self) -> Optional[str]:
        """Return the newest ``create_time`` in the store, or None if empty."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT MAX(create_time) AS hwm FROM sessions"
            ).fetchone()
        return row["hwm"] if row and row["hwm"] else None

    # ------------------------------------------------------------------
    # Batch sync
    # ------------------------------------------------------------------

    def sync_page(
        self,
        client: Any,
        page_size: int = 100,
        activity_limit: int = DEFAULT_ACTIVITY_LIMIT,
        activity_max: int = DEFAULT_ACTIVITY_MAX,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch one page of sessions, upsert, and return a summary.

        Without ``page_token``: fetches page 1 (newest). Uses HWM after each
        session — once ``create_time <= HWM`` is hit, labels remaining items
        ``before_hwm`` and sets ``caught_up=True``.

        With ``page_token``: fetches that specific page and upserts every
        session regardless of HWM (for backfilling older pages).

        Returns:
            total_on_page  — count of sessions in the API response
            new_synced     — sessions newly upserted (always 0 with token,
                             since everything is behind HWM, but upserted anyway)
            before_hwm     — sessions at or before HWM
            caught_up      — True if HWM was hit (page 1 only)
            activities     — count of new activities synced
            next_page_token — token for fetching next page (or None if exhausted)
        """
        hwm = self._get_high_water_mark()
        params = f"pageSize={page_size}"
        if page_token:
            params += f"&pageToken={page_token}"
        data = client._request(f"sessions?{params}")
        batch = data.get("sessions", [])
        if not batch:
            return {
                "total_on_page": 0,
                "new_synced": 0,
                "before_hwm": 0,
                "caught_up": True,
                "activities": 0,
                "next_page_token": None,
            }

        new_synced = 0
        before_hwm = 0
        caught_up = False
        activities = 0
        states: Dict[str, int] = {}
        repos: Dict[str, int] = {}
        with_prs = 0
        # With explicit page_token: upsert everything, don't skip behind HWM
        skip_old = not page_token

        for session in batch:
            create_time = session.get("createTime", "")
            if skip_old and hwm and create_time and create_time <= hwm:
                caught_up = True
                before_hwm += 1
                continue

            self.upsert_session(session)
            new_synced += 1

            s = session.get("state", "UNKNOWN")
            states[s] = states.get(s, 0) + 1
            repo = _extract_repo(session)
            if repo:
                repos[repo] = repos.get(repo, 0) + 1
            for o in session.get("outputs", []):
                if o.get("pullRequest", {}).get("url"):
                    with_prs += 1
                    break

            if activity_limit and new_synced <= activity_limit:
                sess_id = session.get("name", "").replace("sessions/", "")
                known = self.get_activity_count(sess_id)
                if not (known >= activity_max and session.get("state") in (
                    "COMPLETED", "FAILED", "STATE_UNSPECIFIED",
                )):
                    try:
                        act_list = list(
                            client.list_activities(
                                sess_id, page_size=min(activity_max, 50),
                                max_results=activity_max,
                            )
                        )
                    except RuntimeError as e:
                        print(f"  [warn] activity fetch failed for {sess_id}: {e}")
                        act_list = []
                    if len(act_list) > known:
                        self.upsert_activities(sess_id, act_list[known:])
                        activities += len(act_list) - known

        return {
            "total_on_page": len(batch),
            "new_synced": new_synced,
            "before_hwm": before_hwm,
            "caught_up": caught_up,
            "activities": activities,
            "states": states,
            "repos": repos,
            "with_prs": with_prs,
            "next_page_token": data.get("nextPageToken"),
        }

    def sync_all_sessions(
        self,
        client: Any,
        page_size: int = 100,
        activity_limit: int = DEFAULT_ACTIVITY_LIMIT,
        activity_max: int = DEFAULT_ACTIVITY_MAX,
        max_pages: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Sync all pages sequentially, one page at a time.

        Each page is fetched, upserted, summarized, then the next is fetched.
        Stops when HWM is hit, API is exhausted, or ``max_pages`` is reached.

        Args:
            client: A JulesAPIClient instance.
            page_size: API page size.
            activity_limit: Max sessions to fetch activities for (0 = none).
            activity_max: Max activities to fetch per session.
            max_pages: Max pages to fetch (None = until exhausted/caught up).
        """
        sessions_synced = 0
        activities_synced = 0
        pages = 0

        while True:
            result = self.sync_page(
                client,
                page_size=page_size,
                activity_limit=activity_limit - sessions_synced
                if activity_limit else 0,
                activity_max=activity_max,
            )
            sessions_synced += result["new_synced"]
            activities_synced += result["activities"]
            pages += 1

            print(
                f"  Page {pages}: {result['new_synced']} new, "
                f"{result['before_hwm']} cached, "
                f"{result['activities']} activities"
            )

            if result["caught_up"] or not result["next_page_token"]:
                break
            if max_pages and pages >= max_pages:
                break

        return sessions_synced, activities_synced

    def sync_from_api(
        self,
        client: Any,
        limit: int = DEFAULT_ACTIVITY_LIMIT,
        max_results: int = 500,
        activity_max: int = DEFAULT_ACTIVITY_MAX,
    ) -> Tuple[int, int]:
        """Batch sync: fetch sessions from the API and upsert into the store.

        Caps at ``max_results``. Activity sync is opt-in (``limit`` defaults
        to 0). Pass ``limit=50, activity_max=200`` to hydrate.

        Args:
            client: A JulesAPIClient instance.
            limit: Max sessions to fetch activities for (0 = none).
            max_results: Max sessions to scan when listing.
            activity_max: Max activities to fetch per session.
        """
        sessions_synced = 0
        activities_synced = 0
        for session in client.list_sessions(
            page_size=min(max_results, 100), max_results=max_results
        ):
            self.upsert_session(session)
            sessions_synced += 1
            if sessions_synced > limit:
                continue
            sess_id = session.get("name", "").replace("sessions/", "")
            known = self.get_activity_count(sess_id)
            if known >= activity_max and session.get("state") in (
                "COMPLETED", "FAILED", "STATE_UNSPECIFIED",
            ):
                continue
            try:
                activities = list(
                    client.list_activities(
                        sess_id, page_size=min(activity_max, 50),
                        max_results=activity_max,
                    )
                )
            except RuntimeError as e:
                print(f"  [warn] activity fetch failed for {sess_id}: {e}")
                activities = []
            if len(activities) > known:
                inserted = self.upsert_activities(sess_id, activities[known:])
                activities_synced += inserted
        return sessions_synced, activities_synced

    # ------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return summary statistics about the store."""
        with self._conn() as conn:
            sessions = conn.execute(
                "SELECT COUNT(*) as c FROM sessions"
            ).fetchone()["c"]
            activities = conn.execute(
                "SELECT COUNT(*) as c FROM activities"
            ).fetchone()["c"]
            states = conn.execute(
                "SELECT state, COUNT(*) as c FROM sessions GROUP BY state ORDER BY c DESC"
            ).fetchall()
            return {
                "db_path": str(self.db_path),
                "sessions": sessions,
                "activities": activities,
                "states": {r["state"]: r["c"] for r in states},
            }

    def close(self) -> None:
        pass

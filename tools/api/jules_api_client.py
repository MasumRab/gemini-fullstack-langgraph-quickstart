import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Generator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tools.store.jules_store import JulesSessionStore

JULES_API_BASE_URL = "https://jules.googleapis.com/v1alpha"


def get_api_key() -> str:
    """Retrieve the Jules API key from the environment.
    
    Supports JULES_API_KEY (primary).
    """
    key = os.environ.get("JULES_API_KEY")
    if not key:
        print("ERROR: Jules API key not found. Please set JULES_API_KEY.", file=sys.stderr)
        sys.exit(1)
    return key


def _validate_not_placeholder(name: str, value: str) -> None:
    """Reject placeholder/dummy values before they reach the API.

    Catches common patterns a naive agent or user might copy from docs:
      - ``YOUR_``, ``CHANGE_ME``, ``<...>``, ``{{...}}``
      - ``test-key``, ``test_key``, ``your-key-here``
    """
    import re as _re
    placeholders = [
        _re.compile(r) for r in (
            r"^YOUR_", r"CHANGE_ME", r"^<.*>$", r"^\{\{.*\}\}$",
            r"^test[_-]key$", r"^your[_-]key", r"placeholder",
            r"^xxx+$", r"^dummy$",
        )
    ]
    for pattern in placeholders:
        if pattern.search(value):
            print(
                f"ERROR: {name} value \"{value[:40]}\" looks like a placeholder "
                f"(matched: {pattern.pattern}). Set the real API key via env var.",
                file=sys.stderr,
            )
            sys.exit(1)


def jules_request(
    endpoint: str,
    method: str = "GET",
    body: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Make a request to the Jules API with exponential backoff for 429/5xx.

    Args:
        endpoint: API path (e.g. "sessions/abc123").
        method: HTTP method ("GET" or "POST").
        body: JSON-serialisable payload for POST requests.
        api_key: Override the API key. Falls back to environment.
        base_url: Override the base URL.
        max_retries: Number of retries on throttling / server errors.

    Returns:
        Parsed JSON response dict.
    """
    url = f"{base_url or JULES_API_BASE_URL}/{endpoint.lstrip('/')}"
    key = api_key or get_api_key()
    headers = {"X-Goog-Api-Key": key, "Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body else None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=60) as response:
                response_text = response.read().decode("utf-8")
                return json.loads(response_text) if response_text else {}
        except urllib.error.HTTPError as e:
            if e.code in (429,) or 500 <= e.code < 600:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Jules API HTTP {e.code} for {method} {endpoint}: {body_text}"
            ) from e
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(
                f"Jules API connection error for {method} {endpoint}: {e.reason}"
            ) from e

    raise RuntimeError(f"Exhausted retries for {method} {endpoint}")


class JulesAPIClient:
    """Class-based Jules API client.

    All methods delegate to jules_request() with the instance's credentials.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        store: Optional["JulesSessionStore"] = None,
    ):
        self.api_key = api_key or get_api_key()
        _validate_not_placeholder("JULES_API_KEY", self.api_key)
        self.base_url = (base_url or JULES_API_BASE_URL).rstrip("/")
        self._store = store
        self._activity_count_cache: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------

    def _request(
        self, endpoint: str, method: str = "GET", body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an API request using the instance's credentials."""
        return jules_request(
            endpoint, method=method, body=body, api_key=self.api_key, base_url=self.base_url
        )

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def list_sessions(
        self, page_size: int = 50, max_results: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield sessions, handling pagination automatically.

        When ``max_results`` is provided the generator stops early,
        preventing unnecessary page fetches. When ``None`` (default),
        iterates until the API returns no more pages.

        When ``page_token`` is provided, starts from that page cursor
        (used for resumable sync checkpointing).
        """
        remaining = max_results  # None means no limit
        while True:
            effective_page = min(page_size, remaining) if remaining is not None else page_size
            params = f"?pageSize={effective_page}"
            if page_token:
                params += f"&pageToken={page_token}"
            data = self._request(f"sessions{params}")
            for sess in data.get("sessions", []):
                yield sess
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        return
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieve a single session by ID. Auto-upserts to store if configured."""
        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"
        data = self._request(session_id)
        if self._store:
            self._store.upsert_session(data)
        return data

    def get_session_prompt(self, session_id: str) -> Optional[str]:
        """Retrieve the initial user prompt from a session."""
        session = self.get_session(session_id)
        return session.get("prompt")

    def create_session(
        self,
        prompt: str,
        source: str,
        starting_branch: str = "main",
        title: Optional[str] = None,
        automation_mode: Optional[str] = None,
        require_plan_approval: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Create a new Jules session.

        Uses ``POST /v1alpha/sessions`` with the documented payload shape:
            {
              "prompt": "<text>",
              "sourceContext": {
                "source": "sources/github/<owner>/<repo>",
                "githubRepoContext": {"startingBranch": "<branch>"}
              },
              "automationMode": "AUTO_CREATE_PR" | None,
              "title": "<short>",
              "requirePlanApproval": true | false,
            }

        Args:
            prompt: Initial task description sent to Jules.
            source: Resource name of the connected source (e.g.
                ``"sources/github/<owner>/<repo>"``).
            starting_branch: Branch Jules should start from. Defaults to ``"main"``.
            title: Optional short title for the session list view.
            automation_mode: ``"AUTO_CREATE_PR"`` to auto-open a PR, or any
                other mode the API supports. ``None`` (default) means no PR is
                created automatically — you may also explicitly pass
                ``"AUTO_CREATE_PR"`` to opt in.
            require_plan_approval: When True, the session's plan must be
                explicitly approved via :approvePlan before Jules starts work.
                When False (the API default), plans are auto-approved.

        Returns:
            Dict containing the new session resource (includes ``name``,
            ``id``, ``prompt``, etc.).
        """
        body: Dict[str, Any] = {
            "prompt": prompt,
            "sourceContext": {
                "source": source,
                "githubRepoContext": {"startingBranch": starting_branch},
            },
        }
        if title:
            body["title"] = title
        if automation_mode is not None:
            body["automationMode"] = automation_mode
        if require_plan_approval is not None:
            body["requirePlanApproval"] = require_plan_approval
        return self._request("sessions", method="POST", body=body)

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------

    def list_activities(
        self, session_id: str, page_size: int = 50, max_results: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield activities for a session, handling pagination automatically.

        When ``max_results`` is provided the generator makes at most
        ``ceil(max_results / page_size)`` API calls by reducing
        ``pageSize`` on the final request and stopping early. This
        prevents flooding when a session has thousands of activities.
        """
        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"
        page_token = None
        remaining = max_results  # None means no limit
        while True:
            effective_page = min(page_size, remaining) if remaining is not None else page_size
            params = f"?pageSize={effective_page}"
            if page_token:
                params += f"&pageToken={page_token}"
            data = self._request(f"{session_id}/activities{params}")
            for act in data.get("activities", []):
                yield act
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        return
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    # ------------------------------------------------------------------
    # Messaging & Approval
    # ------------------------------------------------------------------

    def send_message(self, session_id: str, text: str) -> Dict[str, Any]:
        """Send a message to a session.

        Uses the documented :sendMessage custom method with payload
        {"prompt": text}. A successful response body is empty.
        """
        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"
        return self._request(
            f"{session_id}:sendMessage", method="POST", body={"prompt": text}
        )

    def approve_plan(self, session_id: str) -> Dict[str, Any]:
        """Approve the current plan for a session.

        Uses the documented :approvePlan custom method.
        """
        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"
        return self._request(f"{session_id}:approvePlan", method="POST", body={})

    def archive_session(self, session_id: str) -> Dict[str, Any]:
        """Archive a session, removing it from the default list view.

        Uses the documented :archive custom method (POST).
        """
        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"
        return self._request(f"{session_id}:archive", method="POST", body={})

    def unarchive_session(self, session_id: str) -> Dict[str, Any]:
        """Unarchive a session, restoring it to the default list view.

        Uses the documented :unarchive custom method (POST).
        """
        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"
        return self._request(f"{session_id}:unarchive", method="POST", body={})

    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Permanently delete a session.

        Uses DELETE /v1alpha/sessions/{id}.
        """
        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"
        return self._request(session_id, method="DELETE")

    # ------------------------------------------------------------------
    # SDK-equivalent features (polling-based, no SDK required)
    # ------------------------------------------------------------------

    def wait_for_state(
        self,
        session_id: str,
        target_state: str,
        timeout: float = 300,
        poll_interval: float = 2,
    ) -> Dict[str, Any]:
        """Poll session until it reaches a target state or timeout.

        Args:
            session_id: The Jules session ID.
            target_state: Target state (e.g. ``"AWAITING_PLAN_APPROVAL"``,
                ``"COMPLETED"``, ``"FAILED"``).
            timeout: Max seconds to wait before raising.
            poll_interval: Seconds between polls.

        Returns:
            Session dict at the target state.

        Raises:
            TimeoutError if the target state is not reached.
        """
        import time as _time
        deadline = _time.monotonic() + timeout
        while _time.monotonic() < deadline:
            session = self.get_session(session_id)
            state = session.get("state", "")
            if state == target_state:
                return session
            if state in ("FAILED", "COMPLETED") and state != target_state:
                return session
            _time.sleep(poll_interval)
        raise TimeoutError(
            f"Session {session_id} did not reach {target_state} "
            f"within {timeout}s (last state: {state})"
        )

    def ask(self, session_id: str, question: str, timeout: float = 120) -> Dict[str, Any]:
        """Send a message and wait for the agent's reply.

        Polls activities until an ``agentMessaged`` activity appears
        that was created after our message.

        Args:
            session_id: The Jules session ID.
            question: The message to send.
            timeout: Max seconds to wait for a reply.

        Returns:
            The agent's reply activity dict.
        """
        import time as _time
        before = _time.monotonic()
        self.send_message(session_id, question)
        deadline = before + timeout
        known = self._store.get_activity_count(session_id) if self._store else 0
        while _time.monotonic() < deadline:
            activities = list(self.list_activities(session_id, page_size=20))
            if self._store:
                self._store.upsert_activities(session_id, activities)
            # Only scan activities we haven't seen before
            for act in activities[known:]:
                if "agentMessaged" in act:
                    return act
            known = len(activities)
            _time.sleep(2)
        raise TimeoutError(
            f"Agent did not reply to {session_id} within {timeout}s"
        )

    def store_activities(self, session_id: str) -> int:
        """Fetch all activities for a session and upsert them into the store.

        Returns the number of newly inserted activity summary rows.
        Requires the client to be initialized with ``store=``.

        Raises:
            RuntimeError: If no store is configured.
        """
        if not self._store:
            raise RuntimeError(
                "store_activities() requires a JulesSessionStore. "
                "Pass store= to JulesAPIClient()."
            )
        sid = session_id.replace("sessions/", "")
        activities = list(self.list_activities(session_id, page_size=100, max_results=500))
        return self._store.upsert_activities(sid, activities)

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def list_sources(self, page_size: int = 100) -> Generator[Dict[str, Any], None, None]:
        """Yield all connected sources, handling pagination automatically.

        Uses GET /v1alpha/sources.
        """
        page_token = None
        while True:
            params = f"?pageSize={page_size}"
            if page_token:
                params += f"&pageToken={page_token}"
            data = self._request(f"sources{params}")
            yield from data.get("sources", [])
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    def get_source(self, owner: str, repo: str) -> Dict[str, Any]:
        """Retrieve a specific GitHub source by owner/repo.

        Uses GET /v1alpha/sources/github/{owner}/{repo}.
        Raises RuntimeError on 404 (source not connected).
        """
        return self._request(f"sources/github/{owner}/{repo}")

    def resolve_source(self, owner_repo: str) -> str:
        """Pre-flight: verify a GitHub source exists and return its resource name.

        Args:
            owner_repo: ``"owner/repo"`` format.

        Returns:
            The full resource name (e.g. ``"sources/github/owner/repo"``).

        Raises:
            RuntimeError: If the source returns 404 (not connected/authorized).
        """
        if "/" not in owner_repo:
            raise ValueError(
                f"Invalid repo format '{owner_repo}'. Use 'owner/repo'."
            )
        owner, repo = owner_repo.split("/", 1)
        self.get_source(owner, repo)
        return f"sources/github/{owner_repo}"

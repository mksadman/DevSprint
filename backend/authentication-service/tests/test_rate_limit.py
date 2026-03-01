"""
Unit tests for Redis-backed rate limiting (app/rate_limit.py).

Redis is mocked throughout — no live Redis or Docker instance required.
The HTTP-level tests use the in-memory SQLite database configured in conftest.py.
"""
from unittest.mock import MagicMock, call, patch

import redis as redis_lib
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.rate_limit import is_rate_limited

# ---------------------------------------------------------------------------
# Unit tests — is_rate_limited() in isolation
# ---------------------------------------------------------------------------


class TestIsRateLimitedUnit:
    """Direct tests of is_rate_limited() with a mocked Redis pipeline."""

    def _make_mock(self, attempt_count: int):
        """Return (mock_client, mock_pipe) configured to return attempt_count."""
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [attempt_count, True]
        mock_client = MagicMock()
        mock_client.pipeline.return_value = mock_pipe
        return mock_client, mock_pipe

    # --- allowed cases -------------------------------------------------------

    def test_first_attempt_allowed(self):
        """Counter == 1  →  must be allowed."""
        mock_client, _ = self._make_mock(1)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is False

    def test_second_attempt_allowed(self):
        """Counter == 2  →  must be allowed."""
        mock_client, _ = self._make_mock(2)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is False

    def test_third_attempt_allowed(self):
        """Counter == 3  →  still within the limit, must be allowed."""
        mock_client, _ = self._make_mock(3)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is False

    # --- blocked cases -------------------------------------------------------

    def test_fourth_attempt_blocked(self):
        """Counter == 4  →  exceeds RATE_LIMIT_MAX_ATTEMPTS (3), must block."""
        mock_client, _ = self._make_mock(4)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is True

    def test_tenth_attempt_blocked(self):
        """Any counter well beyond the limit is also blocked."""
        mock_client, _ = self._make_mock(10)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is True

    # --- fail-open behaviour -------------------------------------------------

    def test_redis_connection_error_fails_open(self):
        """ConnectionError (a RedisError) must cause fail-open (returns False)."""
        mock_client = MagicMock()
        mock_client.pipeline.side_effect = redis_lib.ConnectionError("refused")
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is False

    def test_redis_timeout_error_fails_open(self):
        """TimeoutError (a RedisError) must cause fail-open (returns False)."""
        mock_client = MagicMock()
        mock_client.pipeline.side_effect = redis_lib.TimeoutError("timed out")
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is False

    def test_redis_auth_error_fails_open(self):
        """AuthenticationError (a RedisError) must cause fail-open."""
        mock_client = MagicMock()
        mock_client.pipeline.side_effect = redis_lib.AuthenticationError("NOAUTH")
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is False

    def test_redis_execute_raises_fails_open(self):
        """A RedisError raised during pipeline.execute() must cause fail-open."""
        mock_pipe = MagicMock()
        mock_pipe.execute.side_effect = redis_lib.RedisError("execute failed")
        mock_client = MagicMock()
        mock_client.pipeline.return_value = mock_pipe
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is False

    # --- Redis operation correctness -----------------------------------------

    def test_key_format_is_correct(self):
        """Key must be exactly ``login_attempts:{student_id}``."""
        mock_client, mock_pipe = self._make_mock(1)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            is_rate_limited("student042")
        mock_pipe.incr.assert_called_once_with("login_attempts:student042")

    def test_expire_called_with_nx_flag(self):
        """
        EXPIRE must use nx=True so the window start is never reset by
        subsequent calls within the same fixed window.
        """
        mock_client, mock_pipe = self._make_mock(1)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            is_rate_limited("student001")
        mock_pipe.expire.assert_called_once_with(
            "login_attempts:student001",
            settings.RATE_LIMIT_WINDOW_SECONDS,
            nx=True,
        )

    def test_pipeline_executed_once_per_call(self):
        """Both INCR and EXPIRE are sent in a single pipeline.execute() call."""
        mock_client, mock_pipe = self._make_mock(1)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            is_rate_limited("student001")
        mock_pipe.execute.assert_called_once()

    def test_rate_limit_is_per_student_id(self):
        """Different student_ids use different Redis keys."""
        mock_client, mock_pipe = self._make_mock(1)
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            is_rate_limited("alice")
            is_rate_limited("bob")
        incr_calls = [c.args[0] for c in mock_pipe.incr.call_args_list]
        assert "login_attempts:alice" in incr_calls
        assert "login_attempts:bob" in incr_calls
        assert len(incr_calls) == 2

    # --- window reset simulation ---------------------------------------------

    def test_window_reset_allows_new_attempts(self):
        """
        Simulates TTL expiry: after the key disappears from Redis the counter
        resets to 1, so the student can log in again.
        """
        mock_client = MagicMock()
        mock_pipe = MagicMock()
        mock_client.pipeline.return_value = mock_pipe

        # Simulate: first call is the 4th attempt (blocked), second call is
        # the 1st attempt of a new window (after TTL expired).
        mock_pipe.execute.side_effect = [
            [4, True],   # window active — blocked
            [1, True],   # new window after expiry — allowed
        ]

        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            assert is_rate_limited("student001") is True   # blocked
            assert is_rate_limited("student001") is False  # reset, allowed


# ---------------------------------------------------------------------------
# HTTP-level integration tests via the FastAPI test client
# ---------------------------------------------------------------------------


class TestRateLimitHTTP:
    """
    Tests that exercise POST /login through the TestClient.
    Redis is mocked at the app.rate_limit module level to control the
    per-attempt counter precisely.
    """

    LOGIN_URL = "/login"
    VALID_PAYLOAD = {"student_id": "student001", "password": "password123"}

    def _make_pipeline_mock(self, counts: list[int]):
        """
        Return a mock Redis client whose pipeline().execute() cycles through
        the supplied list of (counter) values, one per call.
        """
        mock_pipe = MagicMock()
        mock_pipe.execute.side_effect = [[c, True] for c in counts]
        mock_client = MagicMock()
        mock_client.pipeline.return_value = mock_pipe
        return mock_client

    def test_first_three_attempts_return_200(self, client: TestClient):
        """Attempts 1–3 must all be allowed (HTTP 200)."""
        mock_client = self._make_pipeline_mock([1, 2, 3])
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            for _ in range(3):
                response = client.post(self.LOGIN_URL, json=self.VALID_PAYLOAD)
                assert response.status_code == 200

    def test_fourth_attempt_returns_429(self, client: TestClient):
        """The 4th attempt within the window must be rejected with HTTP 429."""
        mock_client = self._make_pipeline_mock([1, 2, 3, 4])
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            for _ in range(3):
                resp = client.post(self.LOGIN_URL, json=self.VALID_PAYLOAD)
                assert resp.status_code == 200

            blocked = client.post(self.LOGIN_URL, json=self.VALID_PAYLOAD)
            assert blocked.status_code == 429

    def test_429_response_body(self, client: TestClient):
        """HTTP 429 response must include the prescribed detail message."""
        mock_client = self._make_pipeline_mock([4])
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            response = client.post(self.LOGIN_URL, json=self.VALID_PAYLOAD)
        assert response.status_code == 429
        body = response.json()
        assert "detail" in body
        assert "Too many login attempts" in body["detail"]

    def test_rate_limit_check_before_credential_validation(self, client: TestClient):
        """
        When the rate limit is exceeded, the server must NOT validate credentials.
        This is verified by confirming HTTP 429 is returned even for valid
        credentials — no DB lookup, no JWT — just the 429.
        """
        mock_client = self._make_pipeline_mock([4])
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            response = client.post(self.LOGIN_URL, json=self.VALID_PAYLOAD)
        # Would be 200 if credentials were validated; 429 means RL ran first.
        assert response.status_code == 429

    def test_redis_failure_does_not_block_login(self, client: TestClient):
        """
        When Redis is unavailable, authentication must succeed (fail-open).
        The rate-limit check is skipped; valid credentials still get a JWT.
        """
        mock_client = MagicMock()
        mock_client.pipeline.side_effect = redis_lib.ConnectionError("down")
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            response = client.post(self.LOGIN_URL, json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_metrics_rate_limit_blocks_incremented(self, client: TestClient):
        """
        rate_limit_blocks counter must be incremented exactly once per 429.
        """
        from app.services.metrics import get_snapshot

        before = get_snapshot()["rate_limit_blocks"]

        mock_client = self._make_pipeline_mock([4])
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            client.post(self.LOGIN_URL, json=self.VALID_PAYLOAD)

        after = get_snapshot()["rate_limit_blocks"]
        assert after == before + 1

    def test_metrics_rate_limit_blocks_not_incremented_on_redis_failure(
        self, client: TestClient
    ):
        """
        rate_limit_blocks must NOT be incremented when Redis is down and the
        request is allowed through (fail-open does not count as a block).
        """
        from app.services.metrics import get_snapshot

        before = get_snapshot()["rate_limit_blocks"]

        mock_client = MagicMock()
        mock_client.pipeline.side_effect = redis_lib.ConnectionError("down")
        with patch("app.rate_limit.get_redis_client", return_value=mock_client):
            client.post(self.LOGIN_URL, json=self.VALID_PAYLOAD)

        after = get_snapshot()["rate_limit_blocks"]
        assert after == before  # unchanged

import json
import unittest

from igwatch.checker import AvailabilityChecker, InvalidUsername, normalize_username
from igwatch.http import Response, TransportError
from igwatch.models import Availability


def response(status, body="", url="https://www.instagram.com/x/", headers=None):
    if not isinstance(body, (str, bytes)):
        body = json.dumps(body)
    if isinstance(body, str):
        body = body.encode("utf-8")
    return Response(status=status, headers=headers or {}, body=body, url=url)


class FakeClient:
    """Replays queued responses and records the URLs asked for."""

    def __init__(self, *responses):
        self.queue = list(responses)
        self.calls = []
        self.cookies = {}

    def get(self, url, headers=None):
        self.calls.append(url)
        if not self.queue:
            raise AssertionError(f"unexpected request: {url}")
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class NormalizeUsernameTests(unittest.TestCase):
    def test_accepts_plain_at_and_url_forms(self):
        for raw in [
            "kingspartin",
            "@kingspartin",
            "https://www.instagram.com/kingspartin/",
            "instagram.com/kingspartin",
            "https://instagram.com/kingspartin/?hl=en",
            "  @KingSpartin  ",
        ]:
            self.assertEqual(normalize_username(raw), "kingspartin", raw)

    def test_rejects_impossible_usernames(self):
        for raw in ["", "@", "no spaces", "way" * 20, "bad-dash", "emoji😀"]:
            with self.assertRaises(InvalidUsername, msg=raw):
                normalize_username(raw)


class ApiStrategyTests(unittest.TestCase):
    def check(self, *responses, strategy="api"):
        client = FakeClient(*responses)
        checker = AvailabilityChecker(client=client, strategy=strategy)
        return checker.check("someone"), client

    def test_404_means_available(self):
        result, _ = self.check(response(404, {"message": "User not found"}))
        self.assertIs(result.status, Availability.AVAILABLE)

    def test_null_user_means_available(self):
        result, _ = self.check(response(200, {"data": {"user": None}, "status": "ok"}))
        self.assertIs(result.status, Availability.AVAILABLE)

    def test_user_object_means_taken(self):
        payload = {"data": {"user": {"id": "17841400000", "username": "someone"}}}
        result, _ = self.check(response(200, payload))
        self.assertIs(result.status, Availability.TAKEN)
        self.assertIn("17841400000", result.detail)

    def test_429_is_rate_limited(self):
        result, _ = self.check(response(429, "slow down"))
        self.assertIs(result.status, Availability.RATE_LIMITED)

    def test_401_is_rate_limited_not_available(self):
        # The dangerous false positive: refusing anonymous callers must never
        # be read as "the name is free".
        result, _ = self.check(response(401, {"message": "login_required"}))
        self.assertIs(result.status, Availability.RATE_LIMITED)

    def test_html_login_wall_is_unknown(self):
        result, _ = self.check(response(200, "<!DOCTYPE html><html>login</html>"))
        self.assertIs(result.status, Availability.UNKNOWN)

    def test_network_error_is_unknown(self):
        result, _ = self.check(TransportError("dns go boom"))
        self.assertIs(result.status, Availability.UNKNOWN)
        self.assertIn("dns go boom", result.detail)

    def test_server_error_is_unknown(self):
        result, _ = self.check(response(503, "nope"))
        self.assertIs(result.status, Availability.UNKNOWN)


class PageStrategyTests(unittest.TestCase):
    def check(self, *responses):
        client = FakeClient(*responses)
        checker = AvailabilityChecker(client=client, strategy="page")
        return checker.check("someone")

    def test_404_means_available(self):
        self.assertIs(self.check(response(404, "not found")).status, Availability.AVAILABLE)

    def test_soft_404_body_means_available(self):
        body = "<html><body>Sorry, this page isn't available.</body></html>"
        self.assertIs(self.check(response(200, body)).status, Availability.AVAILABLE)

    def test_rendered_profile_means_taken(self):
        body = '<html><script>{"username":"someone","id":"42"}</script></html>'
        self.assertIs(self.check(response(200, body)).status, Availability.TAKEN)

    def test_login_redirect_is_unknown(self):
        result = self.check(
            response(200, "<html>login</html>", url="https://www.instagram.com/accounts/login/")
        )
        self.assertIs(result.status, Availability.UNKNOWN)

    def test_login_wall_body_is_unknown(self):
        body = '<html><form id="loginForm"></form></html>'
        self.assertIs(self.check(response(200, body)).status, Availability.UNKNOWN)


class AutoStrategyTests(unittest.TestCase):
    def test_falls_back_to_page_when_api_is_blocked(self):
        client = FakeClient(
            response(401, {"message": "login_required"}),
            response(404, "not found"),
        )
        checker = AvailabilityChecker(client=client, strategy="auto")
        result = checker.check("someone")
        self.assertIs(result.status, Availability.AVAILABLE)
        self.assertEqual(result.strategy, "page")
        self.assertEqual(len(client.calls), 2)

    def test_stops_at_the_first_conclusive_answer(self):
        client = FakeClient(response(200, {"data": {"user": {"id": "1"}}}))
        checker = AvailabilityChecker(client=client, strategy="auto")
        result = checker.check("someone")
        self.assertIs(result.status, Availability.TAKEN)
        self.assertEqual(len(client.calls), 1)

    def test_keeps_rate_limited_over_unknown_when_all_inconclusive(self):
        client = FakeClient(response(429, "nope"), response(503, "nope"))
        checker = AvailabilityChecker(client=client, strategy="auto")
        self.assertIs(checker.check("someone").status, Availability.RATE_LIMITED)

    def test_session_id_is_sent_as_cookie(self):
        client = FakeClient(response(404, "not found"))
        AvailabilityChecker(client=client, strategy="api", session_id="abc123").check("someone")
        self.assertEqual(client.cookies["sessionid"], "abc123")


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from graph_rag_demo.backends import BackendError, DeepSeekBackend
from graph_rag_demo.fixtures import mechanism_fixture


def response(value):
    envelope = {"choices": [{"message": {"content": json.dumps(value)}}]}
    return 200, json.dumps(envelope).encode()


class DeepSeekBackendTests(unittest.TestCase):
    def test_missing_api_key_fails_before_request(self):
        called = False

        def request_fn(request, timeout):
            nonlocal called
            called = True
            return response({"ok": True})

        backend = DeepSeekBackend(
            api_key="",
            request_fn=request_fn,
            sleep_fn=lambda _: None,
        )
        with self.assertRaisesRegex(BackendError, "DEEPSEEK_API_KEY"):
            backend._chat_json([{"role": "user", "content": "json"}], 10)
        self.assertFalse(called)

    def test_rate_limit_is_retried_once_and_json_mode_is_sent(self):
        calls = []

        def request_fn(request, timeout):
            calls.append(json.loads(request.data.decode()))
            if len(calls) == 1:
                return 429, b'{"error":"rate limited"}'
            return response({"ok": True})

        backend = DeepSeekBackend(
            api_key="test",
            request_fn=request_fn,
            sleep_fn=lambda _: None,
        )
        result = backend._chat_json([{"role": "user", "content": "json"}], 10)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["response_format"], {"type": "json_object"})

    def test_invalid_json_is_retried_once(self):
        calls = 0

        def request_fn(request, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                envelope = {"choices": [{"message": {"content": "not-json"}}]}
                return 200, json.dumps(envelope).encode()
            return response({"ok": True})

        backend = DeepSeekBackend(
            api_key="test",
            request_fn=request_fn,
            sleep_fn=lambda _: None,
        )
        self.assertEqual(
            backend._chat_json([{"role": "user", "content": "json"}], 10),
            {"ok": True},
        )
        self.assertEqual(calls, 2)

    def test_timeout_is_retried_once(self):
        calls = 0

        def request_fn(request, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise TimeoutError("timed out")
            return response({"ok": True})

        backend = DeepSeekBackend(
            api_key="test",
            request_fn=request_fn,
            sleep_fn=lambda _: None,
        )
        self.assertEqual(
            backend._chat_json([{"role": "user", "content": "json"}], 10),
            {"ok": True},
        )
        self.assertEqual(calls, 2)

    def test_generation_prompt_includes_direction_contract_and_repair_hint(self):
        payloads = []

        def request_fn(request, timeout):
            payloads.append(json.loads(request.data.decode()))
            return response({"ok": True})

        backend = DeepSeekBackend(
            api_key="test",
            request_fn=request_fn,
            sleep_fn=lambda _: None,
        )
        backend.generate_narrative(
            mechanism_fixture(),
            repair_errors=["edge_alignment[0] reverses mechanism direction"],
        )
        user_message = payloads[0]["messages"][1]["content"]
        self.assertIn("机制边方向合同", user_message)
        self.assertIn("reverses mechanism direction", user_message)
        self.assertIn("narrative_source_concept_node_id", user_message)
        self.assertIn("e1:", user_message)


if __name__ == "__main__":
    unittest.main()

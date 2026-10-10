"""Property-based tests for the relay's safety invariants (Hypothesis).

The example-based suite in test_relay.py checks the cases we thought of. These generate
the ones we did not: arbitrary interleavings of holds, settlements and shutdown against
the budget meter, and arbitrary request bodies against the egress policy and the media
bound. Each property is a claim the threat model makes (DESIGN.md T2, T4).

Hypothesis is a test-only dependency (relay/tests/requirements-property.txt). Without
it these tests skip, unless RELAY_REQUIRE_HYPOTHESIS=1 (as in CI), where they fail.
"""
from __future__ import annotations

import base64
import math
import os
from pathlib import Path
import struct
import sys
import unittest
import zlib

RELAY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELAY))

from nexus_relay import media, policy, proxy  # noqa: E402

try:
    from hypothesis import HealthCheck, given, settings, strategies as st
    from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, precondition, rule
except ImportError:  # pragma: no cover - exercised only without the test dependency
    if os.environ.get("RELAY_REQUIRE_HYPOTHESIS") == "1":
        raise
    raise unittest.SkipTest("hypothesis is not installed (pip install -r relay/tests/requirements-property.txt)")

PROFILE = settings(max_examples=int(os.environ.get("RELAY_PROPERTY_EXAMPLES", "300")), deadline=None,
                   suppress_health_check=[HealthCheck.too_slow])
EPS = 1e-6  # float slack, relative to the reservation


# --- T4: the meter never commits more than the reservation -------------------------------
prices = st.fixed_dictionaries(
    {"input": st.floats(0.05, 30), "output": st.floats(0.05, 150)},
    optional={"cache_write": st.floats(0, 40), "cache_read": st.floats(0, 40)},
)


class MeterMachine(RuleBasedStateMachine):
    """Random holds, honest settlements, unknown outcomes and shutdown, in any order.

    Honest means what the provider bills stays within what was held: input tokens within
    the bound passed to `hold` (split across plain, cache-write and cache-read), output
    within the `max_tokens` the meter allowed. Under that assumption the meter promises
    spent + held <= reserved at every step, and nothing changes after close()."""

    @initialize(unit=st.sampled_from(["tokens", "usd"]), price=prices,
                reserved=st.floats(1, 5_000_000), margin=st.integers(0, 8192))
    def setup(self, unit, price, reserved, margin):
        self.meter = proxy.Meter(unit, {"m": price}, reserved, input_margin=margin)
        self.open = {}  # hold id -> (input bound, max_tokens)
        self.closed_spent = None

    @rule(body=st.integers(1, 400_000), requested=st.one_of(st.none(), st.integers(1, 200_000)),
          extra=st.one_of(st.none(), st.integers(0, 1_000_000)))
    def hold(self, body, requested, extra):
        bound = None if extra is None else body + self.meter.input_margin + extra
        try:
            hold_id, max_tokens = self.meter.hold("m", body, requested, input_tokens=bound)
        except proxy.BudgetExceeded:
            return
        assert 1 <= max_tokens and (requested is None or max_tokens <= requested)
        self.open[hold_id] = (body + self.meter.input_margin if bound is None else bound, max_tokens)

    @precondition(lambda self: self.open)
    @rule(data=st.data())
    def settle_honest(self, data):
        hold_id = data.draw(st.sampled_from(sorted(self.open)))
        bound, max_tokens = self.open.pop(hold_id)
        used_in = data.draw(st.integers(0, bound))
        cache_w = data.draw(st.integers(0, used_in))
        cache_r = data.draw(st.integers(0, used_in - cache_w))
        usage = {"input_tokens": used_in - cache_w - cache_r, "cache_creation_input_tokens": cache_w,
                 "cache_read_input_tokens": cache_r, "output_tokens": data.draw(st.integers(0, max_tokens))}
        charged = self.meter.settle(hold_id, "m", usage)
        assert charged >= 0
        assert self.meter.overruns == 0, "an honest response was billed above its hold"

    @precondition(lambda self: self.open)
    @rule(data=st.data())
    def settle_unknown(self, data):
        hold_id = data.draw(st.sampled_from(sorted(self.open)))
        self.open.pop(hold_id)
        held, before = self.meter._holds[hold_id], self.meter.spent
        charged = self.meter.settle(hold_id, "m", None)  # incomplete response: charged its full hold
        assert charged == held and self.meter.spent == before + held, (charged, held)

    @rule()
    def close(self):
        owed = self.meter.spent + sum(self.meter._holds.values())
        self.meter.close()
        if self.closed_spent is None:
            # Unfinished requests are charged at their full holds before cost is recorded.
            assert math.isclose(self.meter.spent, owed, rel_tol=1e-12, abs_tol=1e-9), (self.meter.spent, owed)
            self.closed_spent = self.meter.spent
        self.open.clear()  # late settlements after close are covered by settle_after_close

    @precondition(lambda self: self.closed_spent is not None)
    @rule()
    def hold_after_close(self):
        try:
            self.meter.hold("m", 1, 1)
        except proxy.BudgetExceeded:
            return
        raise AssertionError("a closed meter accepted a new hold")

    @invariant()
    def never_over_reserved(self):
        held = sum(self.meter._holds.values())
        assert self.meter.spent + held <= self.meter.reserved * (1 + EPS) + EPS, \
            (self.meter.spent, held, self.meter.reserved)
        assert self.meter.spent >= 0 and held >= 0

    @invariant()
    def frozen_after_close(self):
        if self.closed_spent is not None:
            assert self.meter.spent == self.closed_spent
            assert self.meter.remaining() == 0.0 and self.meter.exhausted()


TestMeterInvariants = MeterMachine.TestCase
TestMeterInvariants.settings = settings(PROFILE, stateful_step_count=40)


class HoldCoversEveryBillingCategory(unittest.TestCase):
    """Direct form of the honesty assumption: a response that bills the full input bound in
    any single category (plain, cache write, cache read) plus every allowed output token
    costs no more than its hold, whichever category is the most expensive."""

    @PROFILE
    @given(price=prices, reserved=st.floats(1_000, 10_000_000), body=st.integers(1, 200_000),
           requested=st.integers(1, 100_000), extra=st.integers(0, 100_000))
    def test_worst_category_fits_the_hold(self, price, reserved, body, requested, extra):
        bound = body + extra
        for category in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
            meter = proxy.Meter("usd", {"m": price}, reserved, input_margin=0)
            try:
                hold_id, max_tokens = meter.hold("m", body, requested, input_tokens=bound)
            except proxy.BudgetExceeded:
                return
            held = meter._holds[hold_id]
            cost = meter.cost("m", {category: bound, "output_tokens": max_tokens})
            self.assertLessEqual(cost, held * (1 + 1e-12) + 1e-12, (category, price))


class SettleAfterCloseTests(unittest.TestCase):
    @PROFILE
    @given(n=st.integers(1, 6), reserved=st.floats(100_000, 10_000_000))
    def test_late_settlements_never_change_a_frozen_cost(self, n, reserved):
        meter = proxy.Meter("tokens", {}, reserved, input_margin=0)
        holds = []
        for _ in range(n):
            try:
                holds.append(meter.hold("m", 1000, 1000)[0])
            except proxy.BudgetExceeded:
                break
        meter.close()
        frozen = meter.spent
        for hold_id in holds:
            self.assertEqual(0.0, meter.settle(hold_id, "m", {"input_tokens": 1, "output_tokens": 1}))
        self.assertEqual(frozen, meter.spent)


# --- T2: nothing that makes the provider act on the network passes the policy -------------
# The oracle is written out here, independently of policy.py, so that weakening the policy's
# own allowlists cannot also weaken the test.
EGRESS_FIELDS = ("mcp_servers", "container", "service_tier", "speed", "inference_geo")
SAFE_FIELDS = {"/v1/messages": {"model", "messages", "max_tokens", "system", "stop_sequences", "stream",
                                "temperature", "top_p", "top_k", "tools", "tool_choice", "metadata", "thinking",
                                "context_management", "output_config"},
               "/v1/messages/count_tokens": {"model", "messages", "system", "tools", "tool_choice", "thinking",
                                             "context_management", "output_config"}}
SAFE_SOURCES = {"base64", "text", "content"}
SAFE_TOOL_PREFIXES = ("custom", "bash_", "text_editor_", "computer_", "memory_")
DENIED_BETAS = ("mcp-client", "files-api", "code-execution", "web-fetch", "web-search", "skills",
                "container", "agent-", "managed-agents", "fast-mode")
SAFE_BLOCKS = {"text", "image", "document", "tool_use", "tool_result", "thinking", "redacted_thinking",
               "search_result"}
json_leaf = st.one_of(st.none(), st.booleans(), st.integers(-10, 10), st.text(max_size=8))
json_value = st.recursive(json_leaf, lambda c: st.one_of(st.lists(c, max_size=3),
                                                        st.dictionaries(st.text(max_size=6), c, max_size=3)),
                          max_leaves=12)
# Safe requests are built only from allowed parts; the policy must pass every one of them.
# Each forbidden part is then injected alone, at a random depth; the policy must refuse it.
safe_source = st.one_of(st.just({"type": "base64", "media_type": "image/png", "data": "aGk="}),
                        st.just({"type": "text", "media_type": "text/plain", "data": "hi"}))
safe_leaf = st.one_of(
    st.fixed_dictionaries({"type": st.just("text"), "text": st.text(max_size=8)}),
    st.fixed_dictionaries({"type": st.sampled_from(["image", "document"]), "source": safe_source}),
    st.fixed_dictionaries({"type": st.just("tool_use"), "id": st.just("t1"), "name": st.just("Read"),
                           "input": st.just({"url": "https://looks.like.egress/but-is-client-side"})}),
    st.fixed_dictionaries({"type": st.just("thinking"), "thinking": st.just("t"), "signature": st.just("s")}),
)
safe_block = st.recursive(
    safe_leaf,
    lambda inner: st.one_of(
        st.fixed_dictionaries({"type": st.sampled_from(["tool_result", "search_result"]),
                               "content": st.one_of(st.text(max_size=4), st.lists(inner, max_size=3))}),
        st.fixed_dictionaries({"type": st.just("document"),
                               "source": st.fixed_dictionaries({"type": st.just("content"),
                                                                "content": st.lists(inner, max_size=3)})}),
    ),
    max_leaves=8,
)
safe_tool = st.builds(lambda kind: {"name": "t", "input_schema": {}} | ({} if kind is None else {"type": kind}),
                      st.sampled_from([None, "custom", "bash_20250124", "text_editor_20250728",
                                       "computer_20250124", "memory_20250818"]))
safe_message = st.fixed_dictionaries({"role": st.sampled_from(["user", "assistant"]),
                                      "content": st.one_of(st.text(max_size=8), st.lists(safe_block, max_size=3))})
safe_request = st.fixed_dictionaries(
    {"model": st.just("m"), "messages": st.lists(safe_message, min_size=1, max_size=3)},
    optional={"system": st.one_of(st.text(max_size=8), st.lists(safe_block, max_size=2)),
              "tools": st.lists(safe_tool, max_size=3), "thinking": st.just({"type": "enabled", "budget_tokens": 1024}),
              "context_management": st.just({"edits": []}), "metadata": st.just({"user_id": "u"})},
)

FORBIDDEN_BLOCKS = [
    {"type": "image", "source": {"type": "url", "url": "https://attacker.example/i.png"}},
    {"type": "document", "source": {"type": "url", "url": "https://attacker.example/d.pdf"}},
    {"type": "image", "source": {"type": "file", "file_id": "file_1"}},
    {"type": "document", "source": {"type": "file", "file_id": "file_1"}},
    {"type": "server_tool_use", "id": "s", "name": "web_fetch", "input": {"url": "https://attacker.example"}},
    {"type": "web_fetch_tool_result", "tool_use_id": "s"},
    {"type": "container_upload", "file_id": "file_1"},
    {"type": "mcp_tool_use", "id": "m", "name": "x", "server_name": "evil"},
]
FORBIDDEN_TOOLS = [{"type": t, "name": "x"} for t in ("web_search_20250305", "web_fetch_20250910",
                                                       "code_execution_20250825", "mcp_toolset",
                                                       "tool_search_tool_regex_20251119")]
FORBIDDEN_FIELDS = [(f, {"x": 1}) for f in EGRESS_FIELDS] + [("unknown_field", 1)]


def for_path(path: str):
    return safe_request.map(lambda r: {k: v for k, v in r.items() if k in SAFE_FIELDS[path]})


@st.composite
def injected(draw, path: str):
    """(safe request, the same request with exactly one forbidden part placed somewhere)."""
    base = draw(for_path(path))
    req = __import__("copy").deepcopy(base)
    kind = draw(st.sampled_from(["block", "tool", "field"]))
    if kind == "tool":
        req.setdefault("tools", []).insert(draw(st.integers(0, len(req.get("tools", [])))), draw(st.sampled_from(FORBIDDEN_TOOLS)))
    elif kind == "field":
        name, value = draw(st.sampled_from(FORBIDDEN_FIELDS))
        req[name] = value
    else:
        bad = draw(st.sampled_from(FORBIDDEN_BLOCKS))
        for _ in range(draw(st.integers(0, 3))):  # bury it
            bad = draw(st.sampled_from([
                {"type": "tool_result", "tool_use_id": "t", "content": [bad]},
                {"type": "search_result", "source": "s", "title": "t", "content": [bad]},
                {"type": "document", "source": {"type": "content", "content": [bad]}},
            ]))
        where = draw(st.sampled_from(["message", "system"]))
        if where == "system":
            system = req.get("system")
            req["system"] = (system if isinstance(system, list) else []) + [bad]
        else:
            message = req["messages"][draw(st.integers(0, len(req["messages"]) - 1))]
            content = message["content"] if isinstance(message["content"], list) else []
            content.insert(draw(st.integers(0, len(content))), bad)
            message["content"] = content
    return base, req


# Arbitrary JSON, for robustness: the policy must refuse or pass, never crash.
json_leaf = st.one_of(st.none(), st.booleans(), st.integers(-10, 10), st.text(max_size=8))
json_value = st.recursive(json_leaf, lambda c: st.one_of(st.lists(c, max_size=3),
                                                        st.dictionaries(st.text(max_size=6), c, max_size=3)),
                          max_leaves=12)
junk_request = st.dictionaries(st.sampled_from(["model", "messages", "system", "tools", "max_tokens",
                                                "mcp_servers", "x"]), json_value, max_size=5)


def _blocks(value):
    """Every dict reachable as a content block, through the nestings the API defines."""
    if not isinstance(value, list):
        return
    for b in value:
        if isinstance(b, dict):
            yield b
            if b.get("type") in ("tool_result", "search_result"):
                yield from _blocks(b.get("content"))
            src = b.get("source")
            if isinstance(src, dict) and src.get("type") == "content":
                yield from _blocks(src.get("content"))


class PolicyProperties(unittest.TestCase):
    @PROFILE
    @given(path=st.sampled_from(["/v1/messages", "/v1/messages/count_tokens"]), req=junk_request)
    def test_policy_refuses_or_passes_arbitrary_json_and_never_crashes(self, path, req):
        try:
            policy.check_request(path, req)
        except policy.PolicyViolation:
            pass

    @PROFILE
    @given(data=st.data(), path=st.sampled_from(["/v1/messages", "/v1/messages/count_tokens"]))
    def test_safe_requests_pass_and_any_single_forbidden_part_is_refused(self, data, path):
        base, bad = data.draw(injected(path))
        policy.check_request(path, base)  # no false refusals of client-side work
        with self.assertRaises(policy.PolicyViolation):
            policy.check_request(path, bad)

    @PROFILE
    @given(data=st.data(), path=st.sampled_from(["/v1/messages", "/v1/messages/count_tokens"]))
    def test_whatever_passes_contains_nothing_outside_the_safe_set(self, data, path):
        req = data.draw(for_path(path))
        policy.check_request(path, req)
        self.assertLessEqual(set(req), SAFE_FIELDS[path])
        for t in req.get("tools") or []:
            self.assertTrue(t.get("type", "custom").startswith(SAFE_TOOL_PREFIXES), t)
        for root in [m.get("content") for m in req["messages"]] + [req.get("system")]:
            for b in _blocks(root):
                self.assertIn(b.get("type"), SAFE_BLOCKS)
                if b.get("type") in ("image", "document"):
                    self.assertIn(b["source"].get("type"), SAFE_SOURCES)

    @PROFILE
    @given(betas=st.lists(st.one_of(st.sampled_from(["mcp-client-2025-11-20", "files-api-2025-04-14",
                                                     "web-fetch-2025-09-10", "Code-Execution-2025-08-25",
                                                     "fast-mode-2026-02-01", "context-management-2025-06-27",
                                                     "claude-code-20250219"]),
                                    st.text(alphabet="abcdefghij-0123456789", max_size=12)), max_size=4),
           spaces=st.sampled_from([",", ", ", " ,", ",  "]))
    def test_a_denied_beta_anywhere_in_the_header_is_refused(self, betas, spaces):
        header = spaces.join(betas)
        denied = any(b.strip().lower().startswith(DENIED_BETAS) for b in betas)
        try:
            policy.check_betas(header)
            refused = False
        except policy.PolicyViolation:
            refused = True
        self.assertEqual(denied, refused, header)


# --- T4: the media bound covers what the provider bills -----------------------------------
def png_header(width: int, height: int) -> str:
    return base64.b64encode(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)
                            + b"\x08\x02\x00\x00\x00" + struct.pack(">I", zlib.crc32(b"IHDR"))).decode()


class MediaProperties(unittest.TestCase):
    @PROFILE
    @given(sizes=st.lists(st.tuples(st.integers(1, 9000), st.integers(1, 9000)), min_size=1, max_size=20),
           cap=st.sampled_from([1568, 4784]), nest=st.booleans(), body=st.integers(0, 10**6))
    def test_images_are_held_at_least_at_their_billed_visual_tokens(self, sizes, cap, nest, body):
        blocks = [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                               "data": png_header(w, h)}} for w, h in sizes]
        content = [{"type": "tool_result", "tool_use_id": "t", "content": blocks}] if nest else blocks
        bound, has_media = media.input_bound({"messages": [{"role": "user", "content": content}]}, body, 0,
                                             max_image_tokens=cap, max_input_tokens=10**9)
        billed = sum(min(cap, math.ceil(w / 28) * math.ceil(h / 28)) for w, h in sizes)
        self.assertTrue(has_media)
        self.assertGreaterEqual(bound, body + billed)

    @PROFILE
    @given(req=st.one_of(safe_request, junk_request), body=st.integers(0, 10**7), limit=st.integers(100_000, 2_000_000))
    def test_bound_never_crashes_never_undercuts_text_and_never_exceeds_the_input_limit(self, req, body, limit):
        bound, _ = media.input_bound(req, body, 4096, max_input_tokens=limit)
        self.assertLessEqual(bound, limit)
        self.assertGreaterEqual(bound, min(limit, body + 4096))

    @PROFILE
    @given(where=st.sampled_from(["message", "system", "tool_result", "content_source"]), body=st.integers(0, 10**6))
    def test_any_pdf_is_held_at_the_input_limit(self, where, body):
        pdf = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": "JVBE"}}
        wrapped = {"message": pdf, "system": pdf,
                   "tool_result": {"type": "tool_result", "tool_use_id": "t", "content": [pdf]},
                   "content_source": {"type": "document", "source": {"type": "content", "content": [
                       {"type": "tool_result", "tool_use_id": "t", "content": [pdf]}]}}}[where]
        req = {"messages": [{"role": "user", "content": [wrapped] if where != "system" else "x"}]}
        if where == "system":
            req["system"] = [pdf]
        self.assertEqual((777_777, True), media.input_bound(req, body, 0, max_input_tokens=777_777))


if __name__ == "__main__":
    unittest.main()

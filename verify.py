#!/usr/bin/env python3
"""Verify bundled bytes, raw replies, causal inputs and arithmetic. Standard library only."""

import csv
import hashlib
import io
import json
import math
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
WEIGHTS = [[0, 0], [1, 0], [0, 1]]
IDS = ["cash", "asset_a", "asset_b"]


def verify_interface(base):
    """Independently rescore the three published control batches."""
    case = json.loads((base / "case-study.json").read_text())
    with tarfile.open(base / "evidence/interface.tar.gz") as bundle:

        def read(name):
            return json.loads(bundle.extractfile(name).read())

        counts = {}
        for stage in [
            "named_choice_v5_transfer",
            "named_choice_v6_transfer",
            "named_choice_v6_fresh_confirmation",
        ]:
            events = [
                json.loads(line)
                for line in bundle.extractfile(stage + "/requests.jsonl")
                .read()
                .splitlines()
            ]
            requests = {
                e["id"]: e["request"] for e in events if e["event"] == "request_started"
            }
            responses = {
                e["id"]: e["response"] for e in events if e["event"] == "response"
            }
            scores = read(stage + "/scores.json")
            assert len(requests) == len(responses) == len(scores)
            passed = 0
            for score in scores:
                key = score["id"]
                user = json.loads(requests[key]["messages"][1]["content"])
                response = responses[key]
                reply = json.loads(response["choices"][0]["message"]["content"])
                if user["task"] == "latest_feedback":
                    options = max(
                        user["completed_episodes"], key=lambda e: e["episode"]
                    )["options"]
                elif user["task"] == "past_feedback":
                    options = user["completed_episode"]["options"]
                else:
                    assert user["task"] == "current_payoff"
                    options = user["options"]
                best = max(options, key=lambda o: o["net_value"])
                correct = (
                    reply["choice"] == best["option_id"]
                    and abs(reply["selected_value"] - best["net_value"]) <= 1e-6
                    and bool(reply["rationale"].strip())
                    and response["choices"][0]["finish_reason"] == "stop"
                )
                assert correct == score["passed"]
                passed += correct
                if key == case["id"]:
                    assert user == case["user"] and reply == case["reply"]
                    assert best["option_id"] == case["expected"] and not correct
            summary = read(stage + "/summary.json")
            assert summary["passed"] == passed
            counts[stage] = passed
        assert list(counts.values()) == [4, 6, 36]
    assert (
        hashlib.sha256((base / "evidence/interface.tar.gz").read_bytes()).hexdigest()
        == case["interface_bundle_sha256"]
    )
    return sum([6, 6, 36])


def verify(base=HERE):
    if not __debug__:
        raise RuntimeError("Run verification without Python -O")
    base = Path(base)
    for line in (base / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        path = (base / name).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError("checksum path escapes demo")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, (
            f"Checksum mismatch: {name}"
        )
    data = json.loads((base / "pilot.json").read_text())
    assert data["format_version"] == 1
    verify_interface(base)
    archive = base / "evidence/pilot.tar.gz"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == data["evidence_sha256"]
    # Read named members in memory; no extraction or executable code from the archive.
    with tarfile.open(archive, "r:gz") as bundle:

        def read(name):
            member = bundle.getmember(name)
            if not member.isfile():
                raise ValueError("expected regular evidence member")
            return bundle.extractfile(member).read().decode()

        prefix = "native_feedback_v1_main/"
        manifest = json.loads(read(prefix + "manifest.json"))
        events = [
            json.loads(line) for line in read(prefix + "requests.jsonl").splitlines()
        ]
        requests = {
            e["id"]: e["request"] for e in events if e["event"] == "request_started"
        }
        responses = {e["id"]: e["response"] for e in events if e["event"] == "response"}
        assert len(events) == 192 and len(requests) == len(responses) == 96
        assert len({r["id"] for r in responses.values()}) == 96
        assert data["study"]["execution_commit"] == manifest["git_commit"]
        assert data["study"]["system_prompt"] == manifest["config"]["system_prompt"]
        assert data["study"]["design"] == manifest["design"]
        assert data["study"]["schema"] == manifest["schema"]
        table = list(csv.DictReader(io.StringIO(read(prefix + "summary.csv"))))
        checks = 0
        maximum = 0
        paired = []
        model_calls = 0

        def close(actual, expected):
            nonlocal checks, maximum
            error = abs(actual - expected)
            maximum = max(maximum, error)
            checks += 1
            assert error <= 1e-9, (actual, expected)

        k = 0.001

        def net(value):
            return (1 + value) * (1 - k) / (1 + k) - 1

        assert [p["seed"] for p in data["paths"]] == manifest["design"]["seeds"]
        for path in data["paths"]:
            seed = path["seed"]
            prices = path["market_prices"]
            assert len(prices) == 21 and all(
                len(row) == 2 and all(math.isfinite(v) and v > 0 for v in row)
                for row in prices
            )
            assert set(path["runs"]) == {
                "pnl",
                "calibrated",
                "cash",
                "fixed_asset_a",
                "public_signal",
            }
            regrets = {}
            public = {}
            for policy, run in path["runs"].items():
                original = json.loads(read(prefix + f"{seed}-{policy}.json"))
                records = original["records"]
                episodes = run["episodes"]
                assert len(episodes) == len(records) == 10
                assert run["equity"] == original["equity"]
                capital = 10000.0
                phase_base = None
                regret_sum = 0.0
                for i, (e, r) in enumerate(zip(episodes, records)):
                    for a, b in [
                        ("weights", "executed_weights"),
                        ("equity", "equity"),
                        ("realized_return", "realized_return"),
                        ("expected_return", "expected_return"),
                        ("oracle_expected_return", "oracle_expected_return"),
                        ("regret", "regret"),
                        ("costs", "costs"),
                        ("turnover", "turnover"),
                        ("validation_failure", "validation_failure"),
                        ("usage", "usage"),
                    ]:
                        assert e[a] == r[b]
                    assert e["rationale"] == r["proposed"]["reasoning_summary"]
                    assert (
                        e["episode"],
                        e["decision_time"],
                        e["execution_time"],
                        e["outcome_time"],
                    ) == (i, 2 * i, 2 * i + 1, 2 * i + 2)
                    selected = WEIGHTS.index(e["weights"])
                    realized = 0.0
                    costs = turnover = 0.0
                    if selected:
                        change = (
                            prices[2 * i + 2][selected - 1]
                            / prices[2 * i + 1][selected - 1]
                            - 1
                        )
                        realized = net(change)
                        bought = capital / (1 + k)
                        sold = bought * (1 + change)
                        costs = k * (bought + sold)
                        turnover = (bought + sold) / capital
                    capital *= 1 + realized
                    means = [0.012, -0.012] if i < 5 else [-0.012, 0.012]
                    values = [0] + [net(v) for v in means]
                    regret = max(values) - values[selected]
                    for actual, expected in [
                        (e["realized_return"], realized),
                        (e["equity"], capital),
                        (e["costs"], costs),
                        (e["turnover"], turnover),
                        (e["expected_return"], values[selected]),
                        (e["oracle_expected_return"], max(values)),
                        (e["regret"], regret),
                    ]:
                        close(actual, expected)
                    if i < 2:
                        assert selected == ([1, 2] if seed % 2 == 0 else [2, 1])[i]
                        assert (
                            e["request_user"] is None
                            and e["raw_reply"] is None
                            and e["usage"]["calls"] == 0
                        )
                    elif policy in ["pnl", "calibrated"]:
                        key = f"{seed}-{policy}-episode{i}"
                        request = requests[key]
                        response = responses[key]
                        user = json.loads(request["messages"][1]["content"])
                        assert (
                            e["request_user"] == user
                            and e["raw_reply"]
                            == response["choices"][0]["message"]["content"]
                            and e["response_id"] == response["id"]
                        )
                        assert (
                            request["messages"][0]["content"]
                            == data["study"]["system_prompt"]
                        )
                        assert (
                            request["response_format"]["json_schema"]["schema"]
                            == data["study"]["schema"]
                        )
                        assert (
                            request["temperature"],
                            request["seed"],
                            request["max_tokens"],
                        ) == (0, 42, 256)
                        decoded = json.loads(e["raw_reply"])
                        assert (
                            list(decoded) == ["rationale", "choice"]
                            and decoded["rationale"].strip()
                        )
                        assert (
                            selected == IDS.index(decoded["choice"])
                            and decoded["rationale"] == e["rationale"]
                        )
                        assert (
                            e["validation_failure"] is None and e["usage"]["calls"] == 1
                        )
                        u = response["usage"]
                        assert (
                            u["total_tokens"]
                            == u["prompt_tokens"] + u["completion_tokens"]
                        )
                        assert (
                            e["usage"]["input_tokens"] == u["prompt_tokens"]
                            and e["usage"]["output_tokens"] == u["completion_tokens"]
                        )
                        assert (
                            response["choices"][0]["finish_reason"] == "stop"
                            and response["model"] == manifest["config"]["model"]
                        )
                        assert (
                            user["task"] == "market_decision"
                            and user["available_options"] == IDS
                        )
                        assert set(user) == {
                            "task",
                            "public_observation",
                            "available_options",
                            "latest_completed_feedback",
                        }
                        obs = user["public_observation"]
                        assert (
                            obs["time"] == 2 * i
                            and obs["prices"] == prices[max(0, 2 * i - 20) : 2 * i + 1]
                        )
                        public.setdefault((seed, i), []).append(obs)
                        previous = episodes[i - 1]
                        past = (
                            previous["realized_return"]
                            if policy == "pnl"
                            else previous["expected_return"]
                        )
                        feedback = dict(
                            completed_episode=i - 1,
                            outcome_time=2 * i,
                            executed_option=IDS[WEIGHTS.index(previous["weights"])],
                            feedback_type="realized_net_return"
                            if policy == "pnl"
                            else "expected_net_return",
                            reported_return_micro=round(past * 1e6),
                        )
                        assert (
                            user["latest_completed_feedback"] == feedback
                            and e["feedback"] == feedback
                        )
                        close(e["feedback_source"]["raw_return"], past)
                        assert r["predicted_return"] is None
                        model_calls += 1
                    else:
                        assert e["usage"]["calls"] == 0
                    if i == 1:
                        phase_base = capital
                    if i >= 2:
                        regret_sum += regret
                summary = next(
                    row
                    for row in table
                    if int(row["seed"]) == seed and row["condition"] == policy
                )
                close(float(summary["model_phase_ev_regret"]), regret_sum)
                close(float(summary["model_phase_return"]), capital / phase_base - 1)
                regrets[policy] = regret_sum
            assert all(len(obs) == 2 and obs[0] == obs[1] for obs in public.values())
            paired.append(regrets["calibrated"] - regrets["pnl"])
        assert model_calls == 96
        summary = json.loads(read(prefix + "summary.json"))
        close(summary["mean_paired_difference"], sum(paired) / 6)
        return dict(
            status="passed",
            paths=6,
            model_choices=model_calls,
            numeric_checks=checks,
            max_absolute_error=maximum,
            expected_better=sum(v < -1e-12 for v in paired),
            expected_worse=sum(v > 1e-12 for v in paired),
            ties=sum(abs(v) <= 1e-12 for v in paired),
        )


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))

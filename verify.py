#!/usr/bin/env python3
"""Offline replay audit using Python's standard library. Never invokes a model."""

import hashlib
import json
import math
from pathlib import Path
import random
import sys

CONDITIONS = ("public_only", "reliable", "noise", "inverted")
OPTIONS = ("cash", "asset_a", "asset_b")


def check(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def action(values):
    return OPTIONS[max(range(3), key=lambda i: [0.0, *values][i])]


def rules(user):
    p = [user["public_signal_bp"][k] for k in OPTIONS[1:]]
    choices = dict(public_signal=action(p), cash="cash")
    if "completed_calibration" in user:
        h = user["completed_calibration"]
        x = [r[k + "_forecast_bp"] for r in h for k in OPTIONS[1:]]
        y = [r[k + "_settled_bp"] for r in h for k in OPTIONS[1:]]
        f = [user["current_source_forecast_bp"][k] for k in OPTIONS[1:]]
        slope = sum(a * b for a, b in zip(x, y)) / (sum(a * a for a in x) + 150.0**2)
        variance = max(
            sum((b - slope * a) ** 2 for a, b in zip(x, y)) / len(x), 100.0**2
        )
        v = [a / 150.0**2 + slope * b / variance for a, b in zip(p, f)]
        choices.update(naive_follow=action(f), calibrated=action(v))
    return choices


def close(a, b):
    check(
        math.isfinite(a) and math.isfinite(b) and abs(a - b) < 1e-9, "numeric mismatch"
    )


def quantile(v, q):
    pos = (len(v) - 1) * q
    i = int(pos)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (pos - i)


def verify_labels(base, primary, seen_ids):
    path = base / "label-diagnostic.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    check(
        data["version"] == "reliability-labels-v1"
        and data["post_hoc"]
        and data["primary_study_unchanged"],
        "diagnostic scope mismatch",
    )
    swap = {"cash": "cash", "asset_a": "asset_b", "asset_b": "asset_a"}

    def renamed(v):
        if isinstance(v, dict):
            result = {}
            for k, item in v.items():
                key = (
                    k.replace("asset_a", "__TEMP__")
                    .replace("asset_b", "asset_a")
                    .replace("__TEMP__", "asset_b")
                )
                result[key] = renamed(item)
            return result
        if isinstance(v, list):
            return [renamed(x) for x in v]
        if isinstance(v, str):
            return swap.get(v, v)
        return v

    check(set(data["models"]) == set(primary), "diagnostic checkpoint mismatch")
    summaries = {}
    for model, entry in data["models"].items():
        check(
            len(entry["records"]) == 16 and entry["independent_paths"] == 4,
            "diagnostic count mismatch",
        )
        groups = {}
        for r in entry["records"]:
            check(
                r["seed"] in range(62300, 62304)
                and r["condition"] in ["public_only", "inverted"]
                and r["variant"] in ["original", "renamed"],
                "unexpected diagnostic case",
            )
            g = groups.setdefault((r["seed"], r["condition"]), {})
            check(r["variant"] not in g, "duplicate diagnostic cell")
            req, resp = r["request"], r["response"]
            check(
                req["model"] == resp["model"] == primary[model]["alias"],
                "diagnostic model mismatch",
            )
            reference = primary[model]["records"][0]["request"]
            check(
                req["messages"][0] == reference["messages"][0]
                and req["response_format"] == reference["response_format"],
                "diagnostic prompt/schema changed",
            )
            check(
                req["max_tokens"] == 32
                and req["temperature"] == 0
                and req["seed"] == 42,
                "diagnostic decoding changed",
            )
            raw = resp["choices"][0]
            check(raw["finish_reason"] == "stop", "diagnostic output incomplete")
            answer = json.loads(raw["message"]["content"])
            check(
                list(answer) == ["choice"] and answer["choice"] in OPTIONS,
                "diagnostic answer invalid",
            )
            check(r["choice"] == answer["choice"], "diagnostic choice mislabeled")
            physical = (
                swap[answer["choice"]]
                if r["variant"] == "renamed"
                else answer["choice"]
            )
            check(r["physical_choice"] == physical, "diagnostic physical mapping wrong")
            values = r["expected_net_bp"]
            close(r["regret_bp"], max(values) - values[OPTIONS.index(answer["choice"])])
            check(resp["id"] not in seen_ids, "diagnostic raw response reused")
            seen_ids.add(resp["id"])
            g[r["variant"]] = r
        check(
            set(groups)
            == {
                (s, c) for s in range(62300, 62304) for c in ["public_only", "inverted"]
            },
            "diagnostic paired context missing",
        )
        for g in groups.values():
            check(set(g) == {"original", "renamed"}, "diagnostic variant missing")
            original = g["original"]
            changed = g["renamed"]
            user = json.loads(changed["request"]["messages"][1]["content"])
            inverse = json.dumps(renamed(user), separators=(",", ":"))
            check(
                inverse == original["request"]["messages"][1]["content"],
                "renaming did not preserve the physical input and order",
            )
            v = original["expected_net_bp"]
            check(
                changed["expected_net_bp"] == [v[0], v[2], v[1]],
                "diagnostic scoring reference not permuted",
            )
        summary = {}
        for condition in ["public_only", "inverted"]:
            rows = [groups[s, condition] for s in range(62300, 62304)]
            expected = dict(
                paired_contexts=4,
                physical_action_agreement=sum(
                    g["original"]["physical_choice"] == g["renamed"]["physical_choice"]
                    for g in rows
                ),
                original_choices={
                    o: sum(g["original"]["choice"] == o for g in rows) for o in OPTIONS
                },
                renamed_choices={
                    o: sum(g["renamed"]["choice"] == o for g in rows) for o in OPTIONS
                },
            )
            check(entry["summaries"][condition] == expected, "diagnostic summary wrong")
            summary[condition] = expected["physical_action_agreement"]
        summaries[model] = summary
    return dict(
        status="passed",
        post_hoc=True,
        independent_paths=4,
        requests=32,
        physical_action_agreement_out_of_four=summaries,
    )


def verify(base):
    base = Path(base)
    inventory = base / "SHA256SUMS"
    if inventory.exists():
        for line in inventory.read_text().splitlines():
            expected, name = line.split("  ", 1)
            p = (base / name).resolve()
            check(p.is_relative_to(base.resolve()), "checksum path escaped release")
            check(
                hashlib.sha256(p.read_bytes()).hexdigest() == expected,
                "release checksum mismatch: " + name,
            )
    data = json.loads((base / "replay.json").read_text())
    expected = hashlib.sha256(canonical(data["models"]).encode()).hexdigest()
    check(data["data_sha256"] == expected, "replay inventory checksum mismatch")
    check(data["study"] == "reliability-v2" and data["paths"] == 48, "wrong study")
    rng = random.Random(191119)
    indices = [[rng.randrange(48) for _ in range(48)] for _ in range(20000)]
    prompt = None
    response_ids = set()
    comparisons = 0
    validation_count = 0
    paired_truth = {}
    for model, entry in data["models"].items():
        groups = {}
        validation = entry["validation_records"]
        check(len(validation) == 22, "missing control/development records")
        control_count, development_pairs = 0, set()
        for record in validation:
            req, resp = record["request"], record["response"]
            check(
                req["model"] == resp["model"] == entry["alias"],
                "validation checkpoint mismatch",
            )
            check(
                resp["choices"][0]["finish_reason"] == "stop",
                "validation response incomplete",
            )
            decoded = json.loads(resp["choices"][0]["message"]["content"])
            check(
                list(decoded) == ["choice"] and decoded["choice"] in OPTIONS,
                "invalid validation answer",
            )
            check(resp["id"] not in response_ids, "duplicate validation reply")
            response_ids.add(resp["id"])
            u = json.loads(req["messages"][1]["content"])
            if record["stage"] == "controls":
                expected_choice = max(u["options"], key=lambda r: r["net_value"])[
                    "option_id"
                ]
                check(
                    decoded["choice"] == expected_choice == record["expected_choice"],
                    "numeric control failed",
                )
                control_count += 1
            else:
                check(
                    record["stage"] == "development"
                    and 61100 <= record["seed"] < 61104,
                    "development seed mismatch",
                )
                pair = (record["seed"], record["condition"])
                check(pair not in development_pairs, "duplicate development cell")
                development_pairs.add(pair)
        check(
            control_count == 6 and len(development_pairs) == 16,
            "incomplete validation battery",
        )
        check(
            development_pairs
            == {(s, c) for s in range(61100, 61104) for c in CONDITIONS},
            "development cell omitted",
        )
        validation_count += len(validation)
        check(len(entry["records"]) == 192, "missing evaluation cells")
        for r in entry["records"]:
            seed, condition = r["seed"], r["condition"]
            check(condition in CONDITIONS and 62100 <= seed < 62148, "wrong cell")
            g = groups.setdefault(seed, {})
            check(condition not in g, "duplicate cell")
            req, resp = r["request"], r["response"]
            check(
                req["model"] == resp["model"] == entry["alias"], "checkpoint mismatch"
            )
            check(
                req["temperature"] == 0
                and req["seed"] == 42
                and req["max_tokens"] == 32,
                "decoding mismatch",
            )
            check(
                [m["role"] for m in req["messages"]] == ["system", "user"],
                "unexpected messages",
            )
            if prompt is None:
                prompt = req["messages"][0]["content"]
            check(req["messages"][0]["content"] == prompt, "wording changed")
            u = json.loads(req["messages"][1]["content"])
            keys = {
                "task",
                "current_episode",
                "public_signal_bp",
                "available_options",
                "current_decision_time",
            }
            if condition != "public_only":
                keys |= {"completed_calibration", "current_source_forecast_bp"}
            check(set(u) == keys, "unexpected evaluator/label field in input")
            check(
                u["task"] == "source_calibration_decision"
                and u["current_episode"] == 8
                and u["current_decision_time"] == 16,
                "task/time mismatch",
            )
            check(u["available_options"] == list(OPTIONS), "action menu mismatch")
            if condition != "public_only":
                h = u["completed_calibration"]
                check(
                    [e["episode"] for e in h] == list(range(8)),
                    "calibration chronology mismatch",
                )
                check(
                    all(e["forecast_time"] < e["settlement_time"] < 16 for e in h),
                    "future information leaked",
                )
            choice = resp["choices"][0]
            check(choice["finish_reason"] == "stop", "incomplete raw response")
            decoded = json.loads(choice["message"]["content"])
            check(
                list(decoded) == ["choice"] and decoded["choice"] in OPTIONS,
                "invalid answer",
            )
            check(resp["id"] not in response_ids, "repeated response")
            response_ids.add(resp["id"])
            usage = resp["usage"]
            check(
                usage["total_tokens"]
                == usage["prompt_tokens"] + usage["completion_tokens"],
                "token accounting mismatch",
            )
            values = r["expected_net_bp"]
            check(
                len(values) == 3
                and values[0] == 0
                and all(math.isfinite(x) for x in values),
                "invalid scoring reference",
            )
            if seed in paired_truth:
                check(values == paired_truth[seed], "paired latent truth changed")
            else:
                paired_truth[seed] = values

            def regret(c):
                return max(values) - values[OPTIONS.index(c)]

            score = regret(decoded["choice"])
            close(score, r["regret_bp"])
            b = rules(u)
            check(
                b == r["baseline_choices"], "baseline uses different information/rule"
            )
            for k, c in b.items():
                close(regret(c), r["baseline_regret_bp"][k])
                comparisons += 1
            g[condition] = dict(
                regret=score,
                choice=decoded["choice"],
                baseline=r["baseline_regret_bp"],
                baseline_choices=b,
                optimal=score == 0,
                user=u,
            )
            comparisons += 1
        check(set(groups) == set(range(62100, 62148)), "missing paths")
        summary = data["analysis"]["models"][model]
        for seed, g in groups.items():
            check(set(g) == set(CONDITIONS), "incomplete paired path")
            check(
                all(
                    g[c]["user"]["public_signal_bp"]
                    == g["public_only"]["user"]["public_signal_bp"]
                    for c in CONDITIONS
                ),
                "public signal differs within pair",
            )

            def settled(c):
                return [
                    (h["asset_a_settled_bp"], h["asset_b_settled_bp"])
                    for h in g[c]["user"]["completed_calibration"]
                ]

            check(
                settled("reliable") == settled("noise") == settled("inverted"),
                "calibration outcome pairing changed",
            )
        for c in CONDITIONS:
            values = [groups[s][c]["regret"] for s in sorted(groups)]
            close(sum(values) / 48, summary["cells"][c]["mean_regret_bp"])
            comparisons += 1
            cell = summary["cells"][c]
            for key, published in cell["baseline_mean_regret_bp"].items():
                close(
                    sum(groups[s][c]["baseline"][key] for s in groups) / 48, published
                )
                comparisons += 1
            choices = [groups[s][c]["choice"] for s in groups]
            check(
                cell["choices"] == {o: choices.count(o) for o in OPTIONS},
                "choice frequency mismatch",
            )
            check(
                cell["optimal_choices"] == sum(groups[s][c]["optimal"] for s in groups),
                "optimal choice count mismatch",
            )
            for key, count in cell["agreement"].items():
                check(
                    count
                    == sum(
                        groups[s][c]["choice"] == groups[s][c]["baseline_choices"][key]
                        for s in groups
                    ),
                    "baseline agreement mismatch",
                )
            if c == "public_only":
                continue
            for comparison in ["versus_own_public", "versus_calibrated_rule"]:
                differences = [
                    groups[s][c]["regret"]
                    - (
                        groups[s]["public_only"]["regret"]
                        if comparison == "versus_own_public"
                        else groups[s][c]["baseline"]["calibrated"]
                    )
                    for s in sorted(groups)
                ]
                published = summary["contrasts"][c][comparison]
                close(sum(differences) / 48, published["mean_bp"])
                check(len(published["path_values_bp"]) == 48, "missing path contrasts")
                for a, b in zip(differences, published["path_values_bp"]):
                    close(a, b)
                draws = sorted(
                    sum(differences[i] for i in sample) / 48 for sample in indices
                )
                for a, b in zip(
                    [quantile(draws, 0.025), quantile(draws, 0.975)],
                    published["ci95_bp"],
                ):
                    close(a, b)
                check(
                    published["better_paths"] == sum(v < 0 for v in differences),
                    "incorrect path count",
                )
                check(
                    published["tied_paths"] == sum(v == 0 for v in differences),
                    "incorrect tie count",
                )
                check(
                    published["worse_paths"] == sum(v > 0 for v in differences),
                    "incorrect worse count",
                )
                comparisons += 51
    prior = data["prior_interface_attempts"]
    check(len(prior) == 7, "failed interface history omitted")
    check(sum(r["stage"] == "controls" for r in prior) == 6, "prior controls omitted")
    for r in prior:
        response = r["response"]
        check(response["id"] not in response_ids, "prior response reused")
        response_ids.add(response["id"])
        decoded = json.loads(response["choices"][0]["message"]["content"])
        check(decoded["choice"] in OPTIONS, "prior choice invalid")
        if r["stage"] == "development":
            check(len(decoded["rationale"]) > 240, "original interface failure hidden")
        else:
            user = json.loads(r["request"]["messages"][1]["content"])
            best = max(user["options"], key=lambda o: o["net_value"])["option_id"]
            check(decoded["choice"] == best, "prior numeric control mislabeled")
    excluded = data["excluded_candidates"]["phi35_mini"]
    check(len(excluded["records"]) == 6, "excluded candidate controls omitted")
    correct = 0
    for record in excluded["records"]:
        resp = record["response"]
        check(resp["id"] not in response_ids, "excluded response reused")
        response_ids.add(resp["id"])
        check(
            resp["choices"][0]["finish_reason"] == "stop", "excluded control incomplete"
        )
        decoded = json.loads(resp["choices"][0]["message"]["content"])
        check(
            list(decoded) == ["choice"] and decoded["choice"] in OPTIONS,
            "excluded answer invalid",
        )
        u = json.loads(record["request"]["messages"][1]["content"])
        expected = max(u["options"], key=lambda r: r["net_value"])["option_id"]
        correct += decoded["choice"] == expected
        if expected == "cash":
            check(decoded["choice"] != "cash", "excluded cash failure hidden")
    check(
        correct == 4
        and excluded["audit"]["correct_controls"] == 4
        and not excluded["audit"]["gate_passed"],
        "excluded model outcome mislabeled",
    )
    check(len(data["infrastructure_attempts"]) == 2, "adapter history omitted")
    failed_without_response = 0
    for infrastructure in data["infrastructure_attempts"]:
        e = infrastructure["terminal_event"]
        if e["event"] == "failure":
            check(
                infrastructure["reported_token_usage"] is None,
                "failed-request usage invented",
            )
            failed_without_response += 1
        else:
            resp = e["response"]
            check(resp["id"] not in response_ids, "adapter response reused")
            response_ids.add(resp["id"])
            check(
                resp["choices"][0]["finish_reason"] == "length",
                "invalid adapter response hidden",
            )
    check(failed_without_response == 1, "missing pre-generation rejection")
    check(
        data["analysis"]["all_attempts_including_prior_version"]
        == len(response_ids) + failed_without_response,
        "complete attempt accounting mismatch",
    )
    check(
        set(paired_truth) == set(range(62100, 62148)),
        "cross-model path pairing mismatch",
    )
    label_receipt = verify_labels(base, data["models"], set(response_ids))
    print(
        json.dumps(
            dict(
                label_diagnostic=label_receipt,
                status="passed",
                models=list(data["models"]),
                paths=48,
                raw_evaluation_responses=sum(
                    len(m["records"]) for m in data["models"].values()
                ),
                validation_responses=validation_count,
                prior_interface_attempts=len(prior),
                total_recorded_responses=len(response_ids),
                adapter_attempts=len(data["infrastructure_attempts"]),
                numeric_comparisons=comparisons,
                inference_requests=0,
            )
        )
    )


if __name__ == "__main__":
    verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent)

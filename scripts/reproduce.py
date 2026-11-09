"""Recompute paper metrics from the de-identified complete-sequence scores."""
from collections import Counter
import argparse
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (101, 202, 303)
FIELDS = ("mean_mm", "p95_mm", "coverage", "aligned_mean_mm",
          "bad_accepted_fraction", "good_fraction")
SCALES = np.array((1, 1, 100, 1, 100, 100))


def read_csv(name):
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def load_scores():
    scores = {}
    for row in read_csv("localization_sequence_scores.csv"):
        rows = scores.setdefault(row["variant"], {})
        sequence = row["sequence"]
        if sequence in rows:
            raise ValueError(f"Duplicate sequence: {row['variant']} / {sequence}")
        rows[sequence] = row
    baseline = scores["M"]
    if len(baseline) != 97 or set(scores) != {"M"} | {f"{s}{a}" for s in SEEDS for a in "ABC"}:
        raise ValueError("Expected one baseline and nine fixed-1500 variants")
    ids = list(baseline)
    domains = np.array([baseline[i]["domain"] for i in ids])
    groups = {str(k): np.flatnonzero(domains == k) for k in sorted(set(domains))}
    if {k: len(v) for k, v in groups.items()} != {"hemispherical": 52, "rounded": 15, "small_flat": 30}:
        raise ValueError("Unexpected evaluation domains")
    arrays, counts = {}, {}
    for variant, rows in scores.items():
        if rows.keys() != baseline.keys():
            raise ValueError(f"Unmatched sequences: {variant}")
        count = Counter()
        matrix = []
        for i in ids:
            row, ref = rows[i], baseline[i]
            if (row["domain"], row["targets"]) != (ref["domain"], ref["targets"]):
                raise ValueError(f"Denominator mismatch: {variant} / {i}")
            matrix.append([float(row[k]) for k in FIELDS])
            for k in ("eligible_contact", "eligible_nominal_lift", "missed_contact", "false_contact",
                      "unavailable_contact", "unavailable_nominal_lift"):
                count[k] += int(row[k])
        arrays[variant] = np.asarray(matrix) * SCALES
        if (count["eligible_contact"], count["eligible_nominal_lift"],
                count["unavailable_contact"], count["unavailable_nominal_lift"]) != (132595, 91863, 0, 0):
            raise ValueError(f"Unexpected contact denominators: {variant}")
        counts[variant] = count
    return arrays, counts, groups


def estimate(arrays, counts, groups):
    def equal_domain(a):
        return np.mean([a[ix].mean(axis=0) for ix in groups.values()], axis=0)

    rng = np.random.default_rng(20261109)
    boot = {k: rng.choice(ix, (10000, len(ix)), replace=True) for k, ix in groups.items()}
    absolute = {}
    for variant, a in arrays.items():
        n = counts[variant]
        absolute[variant] = list(equal_domain(a)) + [
            100*n["missed_contact"]/n["eligible_contact"],
            100*n["false_contact"]/n["eligible_nominal_lift"],
            n["missed_contact"], n["false_contact"],
        ]
    for arm in "ABC":
        absolute[arm] = np.mean([absolute[f"{s}{arm}"] for s in SEEDS], axis=0).tolist()
    contrasts = {}
    for left, right in (("M", "A"), ("A", "B"), ("M", "B"), ("B", "C")):
        paired = np.stack([arrays[f"{s}{right}"] - arrays[f"{s}{left}" if left != "M" else "M"] for s in SEEDS])
        delta = paired.mean(axis=0)
        draws = np.mean([delta[ix].mean(axis=1) for ix in boot.values()], axis=0)
        contrasts[f"{right}-{left}"] = dict(
            estimate=list(equal_domain(delta)),
            interval=np.quantile(draws, [.025, .975], axis=0).T.tolist(),
            seed_effects=[list(equal_domain(x)) for x in paired],
            domains={k: list(delta[ix].mean(axis=0)) for k, ix in groups.items()},
            positive_sequences=(delta > 0).sum(axis=0).tolist(),
        )
    return dict(absolute=absolute, contrasts=contrasts, n_by_domain={k: len(ix) for k, ix in groups.items()},
                method="10000 percentile bootstrap draws, resampling complete sequences within domain, three trained seeds held fixed")


def compare(actual, expected, where="root"):
    if isinstance(expected, dict):
        if actual.keys() != expected.keys():
            raise ValueError(f"Key mismatch at {where}")
        for k in expected:
            compare(actual[k], expected[k], f"{where}.{k}")
    elif isinstance(expected, list):
        np.testing.assert_allclose(actual, expected, rtol=1e-11, atol=1e-12, err_msg=where)
    elif actual != expected:
        raise ValueError(f"Mismatch at {where}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reproduced"))
    args = parser.parse_args()
    arrays, counts, groups = load_scores()
    result = estimate(arrays, counts, groups)
    expected = json.loads((ROOT / "data" / "expected_paired_effects.json").read_text(encoding="utf-8"))
    compare(result, expected)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "paired_effects.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (args.output / "frozen_localization_table.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["variant","mean_mm","p95_mm","coverage_pct","accepted_within_0p5mm_pct","miss_pct","false_contact_pct"])
        for k in ("M", "A", "B", "C", *(f"{s}{a}" for s in SEEDS for a in "ABC")):
            v = result["absolute"][k]
            writer.writerow([k, f"{v[0]:.3f}", f"{v[1]:.3f}", f"{v[2]:.2f}", f"{v[5]:.2f}", f"{v[6]:.2f}", f"{v[7]:.2f}"])
    print("Verified all 970 replay rows and all four contrasts against the manuscript results.")


if __name__ == "__main__":
    main()

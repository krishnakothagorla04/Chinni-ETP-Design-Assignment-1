#!/usr/bin/env python3
"""
Adaptive CI/CD - pre-build risk predictor (runs INSIDE GitHub Actions).

On every push it:
  1. Extracts pre-build features from the pushed commit using git.
  2. Loads the model trained in Colab (model.joblib).
  3. Predicts failure risk, maps it to a pipeline LANE (LOW/MED/HIGH).
  4. Writes lane/risk/score to $GITHUB_OUTPUT so downstream jobs can adapt.
  5. Writes a visual report card to the Actions run summary + a PR comment.

Feature names match the model trained on the final TravisTorrent dataset.
Features not computable from a single commit (sloc, team_size, test_density,
core_member, proj_fail_rate) are left as NaN and imputed by the model pipeline.
"""
import os, subprocess, json, random, datetime
import numpy as np
import pandas as pd
import joblib

# ---- policy thresholds (from the Colab Pareto analysis) ----
LOW_MAX  = 0.10
HIGH_MIN = 0.20
EXPLORE_RATE = 0.15   # occasionally full-run a LOW commit to recover its true label (RQ3)

DOC_EXT = {".md", ".rst", ".txt", ".adoc"}
SRC_EXT = {".py", ".java", ".js", ".ts", ".go", ".rb", ".c", ".cpp", ".cs", ".yml", ".yaml"}


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def get_diff():
    parent = sh(["git", "rev-parse", "HEAD~1"])
    base = parent if parent else sh(["git", "hash-object", "-t", "tree", "/dev/null"])
    numstat = sh(["git", "diff", "--numstat", base, "HEAD"])
    files = []
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            add, dele, path = parts
            files.append((path, int(add) if add.isdigit() else 0,
                          int(dele) if dele.isdigit() else 0))
    return files


def classify(path):
    ext = os.path.splitext(path)[1].lower()
    low = path.lower()
    if "test" in low or "spec" in low:
        return "test"
    if ext in DOC_EXT or low.startswith("docs/"):
        return "doc"
    if ext in SRC_EXT:
        return "src"
    return "other"


def build_features(feature_names):
    files = get_diff()
    src_churn = test_churn = other_churn = 0
    files_add = files_del = files_mod = 0
    src_files = doc_files = 0
    for path, add, dele in files:
        kind = classify(path); churn = add + dele
        if kind == "test":  test_churn += churn
        elif kind == "src": src_churn += churn; src_files += 1
        elif kind == "doc": doc_files += 1
        else:               other_churn += churn
        if dele == 0 and add > 0: files_add += 1
        elif add == 0 and dele > 0: files_del += 1
        else: files_mod += 1

    total_files = len(files)
    total_churn = src_churn + test_churn + other_churn
    is_docs_only = int(src_files == 0 and doc_files > 0 and total_files > 0)

    known = {
        "src_churn": src_churn, "test_churn": test_churn, "total_churn": total_churn,
        "files_add": files_add, "files_del": files_del, "files_mod": files_mod,
        "total_files": total_files, "src_files": src_files, "doc_files": doc_files,
        "is_docs_only": is_docs_only, "is_pr": 0,
        # not computable from one commit -> NaN (model imputes training median)
    }
    row = {f: known.get(f, np.nan) for f in feature_names}
    return pd.DataFrame([row])[feature_names], known


def explain(known):
    r = []
    if known["is_docs_only"]:
        r.append("documentation-only change (low risk)")
    if known["total_churn"] > 300:
        r.append(f"large code churn ({known['total_churn']} lines)")
    if known["total_files"] > 15:
        r.append(f"many files touched ({known['total_files']})")
    if known["src_churn"] > 100 and known["test_churn"] == 0:
        r.append("substantial source change with no test changes")
    if not r:
        r.append("change shape resembles historically low-risk commits")
    return r


def risk_meter(p, width=20):
    fill = int(round(p * width))
    return "`[" + "#" * fill + "-" * (width - fill) + f"]` **{p*100:.0f}%**"


def build_summary(p, risk, lane, reasons, known):
    action = {
        "LOW":  "**Fast lane** - lint + quick service tests (skips heavy stages)",
        "MED":  "**Standard lane** - lint + full pytest suite across all services",
        "HIGH": "**Extended lane** - full tests + security scan + Docker build + approval gate",
    }[lane]
    reason_md = "\n".join(f"- {x}" for x in reasons)
    return f"""## Pre-Build Risk Prediction

| | |
|---|---|
| **Risk level** | **{risk}** |
| **Risk score** | {risk_meter(p)} |
| **Pipeline lane** | `{lane}` |
| **Files changed** | {known['total_files']} |
| **Code churn** | {known['total_churn']} lines |

### Selected pipeline
{action}

### Why this prediction
{reason_md}

<sub>Predicted by the Adaptive CI/CD risk model before any build stage ran.</sub>
"""


def main():
    bundle = joblib.load("model.joblib")
    model, feats = bundle["model"], bundle["features"]

    X, known = build_features(feats)
    p = float(model.predict_proba(X)[:, 1][0])

    predicted_lane = "LOW" if p < LOW_MAX else ("HIGH" if p >= HIGH_MIN else "MED")
    explored = int(predicted_lane == "LOW" and random.random() < EXPLORE_RATE)
    lane = "MED" if explored else predicted_lane
    risk = {"LOW": "Low", "MED": "Medium", "HIGH": "High"}[lane]
    reasons = explain(known)
    if explored:
        reasons.append("selected for exploration (full run to verify a low-risk prediction)")

    print("=" * 52)
    print("  PRE-BUILD RISK PREDICTION")
    print(f"  Risk score : {p:.3f}")
    print(f"  Risk level : {risk}")
    print(f"  Pipeline   : {lane} lane")
    print(f"  Why        : " + "; ".join(reasons))
    print("=" * 52)

    summary = build_summary(p, risk, lane, reasons, known)
    ss = os.environ.get("GITHUB_STEP_SUMMARY")
    if ss:
        open(ss, "a").write(summary)
    open("risk_summary.md", "w").write(summary)

    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "commit": os.environ.get("GITHUB_SHA", sh(["git", "rev-parse", "HEAD"])),
        "score": round(p, 4), "predicted_lane": predicted_lane,
        "lane_run": lane, "explored": explored,
        "total_files": known["total_files"], "total_churn": known["total_churn"],
        "src_churn": known["src_churn"], "is_docs_only": known["is_docs_only"],
    }
    open("prediction.json", "w").write(json.dumps(record))

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"lane={lane}\nrisk={risk}\nscore={p:.3f}\nexplored={explored}\n")


if __name__ == "__main__":
    main()

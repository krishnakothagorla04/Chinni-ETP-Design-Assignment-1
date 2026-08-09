#!/usr/bin/env python3
"""Close the learning loop: pair the pre-build PREDICTION with the ACTUAL build
outcome and append one row to logs/outcomes.csv. Runs after the lanes finish.

Fast-tracked LOW commits that were not explored have no observed full outcome,
so they are recorded as 'unobserved' - the censored-feedback signal (RQ3)."""
import os, csv, json, datetime

LOG = "logs/outcomes.csv"


def main():
    rec = json.load(open("prediction.json"))
    outcome = (os.environ.get("OUTCOME", "unobserved").strip() or "unobserved")
    if rec.get("lane_run") == "LOW" and not rec.get("explored"):
        outcome = "unobserved"

    row = {
        "logged_at": datetime.datetime.utcnow().isoformat(),
        "commit": rec.get("commit"), "score": rec.get("score"),
        "predicted_lane": rec.get("predicted_lane"), "lane_run": rec.get("lane_run"),
        "explored": rec.get("explored"), "outcome": outcome,
        "total_files": rec.get("total_files"), "total_churn": rec.get("total_churn"),
        "src_churn": rec.get("src_churn"), "is_docs_only": rec.get("is_docs_only"),
    }
    os.makedirs("logs", exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new: w.writeheader()
        w.writerow(row)
    print(f"Logged: lane={row['lane_run']} outcome={row['outcome']} explored={row['explored']}")


if __name__ == "__main__":
    main()

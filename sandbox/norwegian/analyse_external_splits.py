"""Small reproducible summaries for the external split evaluation."""
import json
from pathlib import Path

ROOT = Path(__file__).parent / "external-split-evaluation"
rows = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))["rows"]
for threshold in (2.2262064814567566, 2.5, 2.75, 3.0, 3.25, 3.5, 4.0):
    positives = sum(bool(row["category"] == "joined_error" and row["target_proposal"]
                         and row["target_proposal"]["margin"] > threshold)
                    for row in rows)
    controls = sum(bool(row["category"] == "legitimate_token" and row["target_proposal"]
                        and (row["target_proposal"]["retrieval"] == "authority_override"
                             or row["target_proposal"]["margin"] > threshold))
                   for row in rows)
    print(threshold, positives, controls)

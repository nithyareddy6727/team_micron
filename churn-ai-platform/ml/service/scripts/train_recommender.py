from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

CURRENT_FILE = Path(__file__).resolve()
ML_SERVICE_ROOT = CURRENT_FILE.parent.parent
if str(ML_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_ROOT))

from app.services.model import CollaborativeFilteringModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train collaborative filtering recommender")
    parser.add_argument(
        "--input-csv",
        required=True,
        help="Path to CSV with columns: user_id,item_id,interaction_value",
    )
    parser.add_argument(
        "--output-model",
        default="artifacts/recommender.joblib",
        help="Path to save joblib model artifact",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_csv)
    output_path = Path(args.output_model)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)

    required = {"user_id", "item_id"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if "interaction_value" not in df.columns:
        df["interaction_value"] = 1.0

    df = df[["user_id", "item_id", "interaction_value"]].copy()
    df["user_id"] = df["user_id"].astype(int)
    df["item_id"] = df["item_id"].astype(int)
    df["interaction_value"] = df["interaction_value"].astype(float)

    model = CollaborativeFilteringModel()
    artifacts = model.fit(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(output_path))

    print(
        {
            "status": "ok",
            "model_path": str(output_path),
            "model_version": artifacts.model_version,
            "items": len(artifacts.item_ids),
        }
    )


if __name__ == "__main__":
    main()

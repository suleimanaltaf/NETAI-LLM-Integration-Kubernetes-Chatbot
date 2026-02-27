"""Data preparation for fine-tuning LLMs on network diagnostics data."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_conversation_data(filepath: str | Path) -> list[dict]:
    """Load fine-tuning conversation examples from JSONL format."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Training data not found: {path}")

    # Support both JSON array and JSONL formats
    with open(path) as f:
        content = f.read().strip()

    if content.startswith("["):
        return json.loads(content)

    # JSONL format
    examples = []
    for line in content.split("\n"):
        line = line.strip()
        if line:
            examples.append(json.loads(line))
    return examples


def prepare_training_dataset(
    raw_data_path: str | Path,
    output_path: str | Path,
    validation_split: float = 0.1,
) -> tuple[Path, Path]:
    """Prepare training and validation datasets from raw conversation data.

    Converts network diagnostics conversations into the format expected by
    transformers' SFTTrainer for supervised fine-tuning.

    Returns:
        Tuple of (train_path, val_path)
    """
    examples = load_conversation_data(raw_data_path)
    logger.info("Loaded %d training examples", len(examples))

    # Validate format
    valid_examples = []
    for ex in examples:
        if "messages" in ex and len(ex["messages"]) >= 2:
            valid_examples.append(ex)
        else:
            logger.warning("Skipping invalid example (missing messages): %s", str(ex)[:100])

    # Split into train/val
    split_idx = max(1, int(len(valid_examples) * (1 - validation_split)))
    train_examples = valid_examples[:split_idx]
    val_examples = valid_examples[split_idx:]

    # Write output
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"

    _write_jsonl(train_path, train_examples)
    _write_jsonl(val_path, val_examples)

    logger.info("Prepared %d training and %d validation examples", len(train_examples), len(val_examples))
    return train_path, val_path


def generate_synthetic_examples(
    telemetry_records: list[dict],
    num_examples: int = 50,
) -> list[dict]:
    """Generate synthetic fine-tuning examples from telemetry data.

    Creates question-answer pairs about network metrics that can be used
    to augment the fine-tuning dataset.
    """
    system_msg = {
        "role": "system",
        "content": "You are NETAI, an AI network diagnostics assistant for the National Research Platform.",
    }

    examples = []

    # Group records by host pair
    host_pairs: dict[tuple, list] = {}
    for rec in telemetry_records:
        key = (rec.get("src_host", ""), rec.get("dst_host", ""))
        host_pairs.setdefault(key, []).append(rec)

    for (src, dst), records in host_pairs.items():
        if not src or not dst:
            continue

        # Throughput questions
        throughput_records = [r for r in records if r.get("metric_type") == "throughput"]
        if throughput_records:
            values = [r["value"] for r in throughput_records]
            avg_val = sum(values) / len(values)
            unit = throughput_records[0].get("unit", "Gbps")

            examples.append({
                "messages": [
                    system_msg,
                    {"role": "user", "content": f"What is the current throughput between {src} and {dst}?"},
                    {"role": "assistant", "content": (
                        f"Based on recent measurements, the throughput between {src} and {dst} "
                        f"is averaging {avg_val:.2f} {unit} across {len(values)} test samples. "
                        f"The range observed is {min(values):.2f} to {max(values):.2f} {unit}. "
                        f"{'This is within normal parameters.' if avg_val > 7 else 'This may indicate a performance issue worth investigating.'}"
                    )},
                ]
            })

        # Latency questions
        latency_records = [r for r in records if r.get("metric_type") == "latency"]
        if latency_records:
            values = [r["value"] for r in latency_records]
            avg_val = sum(values) / len(values)

            examples.append({
                "messages": [
                    system_msg,
                    {"role": "user", "content": f"What is the latency between {src} and {dst}?"},
                    {"role": "assistant", "content": (
                        f"The average round-trip latency between {src} and {dst} is {avg_val:.1f} ms. "
                        f"Measurements range from {min(values):.1f} ms to {max(values):.1f} ms. "
                        f"{'Latency is stable and within expected range.' if max(values) < avg_val * 1.5 else 'There are latency spikes that may indicate routing changes or congestion.'}"
                    )},
                ]
            })

        if len(examples) >= num_examples:
            break

    return examples[:num_examples]


def _write_jsonl(path: Path, data: list[dict]) -> None:
    """Write data as JSONL format."""
    with open(path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")

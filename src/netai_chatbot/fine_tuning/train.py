"""Fine-tuning pipeline for domain-specific LLM adaptation.

This module provides the training pipeline for fine-tuning LLMs on
network diagnostics data using Parameter-Efficient Fine-Tuning (PEFT/LoRA).
Designed to run on NRP's GPU-enabled Kubernetes pods.

Usage:
    python -m netai_chatbot.fine_tuning.train \
        --base-model Qwen/Qwen2.5-7B-Instruct \
        --data-dir data/prepared \
        --output-dir models/netai-qwen-lora \
        --epochs 3
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def train(
    base_model: str = "Qwen/Qwen2.5-7B-Instruct",
    data_dir: str = "data/prepared",
    output_dir: str = "models/netai-qwen-lora",
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    max_seq_length: int = 2048,
) -> None:
    """Fine-tune an LLM on network diagnostics data using LoRA.

    This function implements the complete fine-tuning pipeline:
    1. Load the base model with quantization (4-bit via BitsAndBytes)
    2. Apply LoRA adapters for parameter-efficient training
    3. Load and format the training dataset
    4. Train using HuggingFace's SFTTrainer
    5. Save the LoRA adapter weights

    Args:
        base_model: HuggingFace model ID or local path
        data_dir: Directory containing train.jsonl and val.jsonl
        output_dir: Where to save the fine-tuned adapter
        epochs: Number of training epochs
        batch_size: Per-device training batch size
        learning_rate: Learning rate for AdamW optimizer
        lora_r: LoRA rank (higher = more parameters, better quality)
        lora_alpha: LoRA alpha scaling factor
        max_seq_length: Maximum sequence length for training
    """
    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from trl import SFTTrainer
    except ImportError as e:
        logger.error(
            "Fine-tuning dependencies not installed. "
            "Install with: pip install 'netai-chatbot[fine-tuning]'\n%s", e
        )
        raise

    data_path = Path(data_dir)
    train_file = data_path / "train.jsonl"
    val_file = data_path / "val.jsonl"

    if not train_file.exists():
        raise FileNotFoundError(f"Training data not found: {train_file}")

    logger.info("Starting fine-tuning pipeline")
    logger.info("  Base model: %s", base_model)
    logger.info("  Data dir: %s", data_dir)
    logger.info("  Output dir: %s", output_dir)
    logger.info("  Epochs: %d, Batch size: %d, LR: %s", epochs, batch_size, learning_rate)

    # Load quantized base model (4-bit for memory efficiency)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    logger.info("Loading base model with 4-bit quantization...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Configure LoRA
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    logger.info(
        "LoRA applied: %d trainable / %d total parameters (%.2f%%)",
        trainable, total, 100 * trainable / total,
    )

    # Load datasets
    dataset_files = {"train": str(train_file)}
    if val_file.exists():
        dataset_files["validation"] = str(val_file)

    dataset = load_dataset("json", data_files=dataset_files)

    def format_chat(example):
        """Format messages into the chat template expected by the model."""
        text = tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
        return {"text": text}

    dataset = dataset.map(format_chat, remove_columns=["messages"])

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch" if "validation" in dataset else "no",
        bf16=torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
        fp16=not (torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False),
        optim="paged_adamw_8bit",
        report_to="none",
        save_total_limit=2,
    )

    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        processing_class=tokenizer,
        max_seq_length=max_seq_length,
    )

    # Train
    logger.info("Starting training...")
    trainer.train()

    # Save the adapter
    logger.info("Saving LoRA adapter to %s", output_dir)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    logger.info("Fine-tuning complete!")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune LLM for NETAI network diagnostics")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct", help="Base model to fine-tune")
    parser.add_argument("--data-dir", default="data/prepared", help="Directory with train.jsonl and val.jsonl")
    parser.add_argument("--output-dir", default="models/netai-qwen-lora", help="Output directory for adapter")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Per-device batch size")
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--max-seq-length", type=int, default=2048, help="Max sequence length")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    train(**vars(args))


if __name__ == "__main__":
    main()

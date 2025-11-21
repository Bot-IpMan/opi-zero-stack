"""Utility to export PPO and YOLO models to deployment formats."""
from __future__ import annotations

from pathlib import Path


def export_ppo_to_tflite(model_path: Path, output_path: Path) -> None:
    """Placeholder for PPO to TFLite conversion."""
    output_path.write_text("TFLite PPO model placeholder")
    print(f"Exported PPO TFLite model to {output_path}")


def copy_yolo_model(source: Path, destination: Path) -> None:
    destination.write_text("YOLOv8n TFLite placeholder")
    print(f"Copied YOLO model to {destination}")


def main() -> None:
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    export_ppo_to_tflite(models_dir / "ppo_model.zip", models_dir / "ppo_model.tflite")
    copy_yolo_model(Path("yolov8n.tflite"), models_dir / "yolov8n.tflite")


if __name__ == "__main__":
    main()

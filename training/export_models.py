"""Export PPO and YOLO artifacts to TFLite files matching deployment expectations."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

try:
    import tensorflow as tf
except ImportError as exc:  # pragma: no cover - requires optional dependency
    raise SystemExit(
        "TensorFlow is required for export. Install extras with "
        "`pip install -r requirements-export.txt` before running this script."
    ) from exc

from stable_baselines3 import PPO


def _torch_linear_to_tf(layer, activation: str | None = None) -> tf.keras.layers.Layer:
    weight = layer.weight.detach().cpu().numpy().T
    bias = layer.bias.detach().cpu().numpy()
    return tf.keras.layers.Dense(
        weight.shape[1],
        activation=activation,
        kernel_initializer=tf.constant_initializer(weight),
        bias_initializer=tf.constant_initializer(bias),
        trainable=False,
    )


def _build_ppo_tf_model(model: PPO, input_dim: int, action_dim: int) -> tf.keras.Model:
    """Create a frozen Keras model using PPO policy weights."""
    layers: Iterable[tf.keras.layers.Layer] = []
    policy_net = model.policy.mlp_extractor.policy_net
    for i, module in enumerate(policy_net):
        if module.__class__.__name__ == "Linear":
            layers.append(_torch_linear_to_tf(module, activation="tanh"))
        elif module.__class__.__name__ == "Tanh":
            # already captured via activation argument
            continue
        else:
            raise ValueError(f"Unsupported module in policy_net: {module}")
    action_net = model.policy.action_net
    layers.append(_torch_linear_to_tf(action_net, activation=None))

    keras_model = tf.keras.Sequential([tf.keras.layers.InputLayer(input_shape=(input_dim,))] + list(layers))
    return keras_model


def export_ppo_to_tflite(model_path: Path, output_path: Path, input_dim: int = 9, action_dim: int = 6) -> None:
    if not model_path.exists():
        raise SystemExit(
            f"PPO checkpoint {model_path} is missing. Train the model before exporting or "
            "point --model-path to an existing .zip file."
        )

    ppo = PPO.load(model_path, device="cpu")
    keras_model = _build_ppo_tf_model(ppo, input_dim, action_dim)

    concrete_fn = tf.function(lambda x: keras_model(x)).get_concrete_function(
        tf.TensorSpec([None, input_dim], tf.float32)
    )
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_fn])
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(tflite_model)
    print(f"Exported PPO TFLite model to {output_path}")


def export_dummy_yolo(output_path: Path, input_size: Tuple[int, int] = (240, 320)) -> None:
    height, width = input_size

    @tf.function
    def identity_detector(x):
        # x: [None, H, W, 3] -> return dummy detection tensor
        batch = tf.shape(x)[0]
        return tf.zeros([batch, 1, 6], dtype=tf.float32)

    concrete_fn = identity_detector.get_concrete_function(
        tf.TensorSpec([None, height, width, 3], tf.float32)
    )
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_fn])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(converter.convert())
    print(f"Wrote placeholder YOLO model to {output_path}")


def copy_or_create_yolo(source: Path, destination: Path) -> None:
    if source.exists():
        destination.write_bytes(source.read_bytes())
        print(f"Copied YOLO model to {destination}")
    else:
        export_dummy_yolo(destination)


def main() -> None:
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    export_ppo_to_tflite(models_dir / "ppo_model.zip", models_dir / "ppo_model.tflite")
    copy_or_create_yolo(Path("yolov8n.tflite"), models_dir / "yolov8n.tflite")


if __name__ == "__main__":
    main()

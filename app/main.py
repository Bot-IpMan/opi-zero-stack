from contextlib import asynccontextmanager
import json
import logging
import os
import time
from typing import List

import numpy as np
import paho.mqtt.client as mqtt
import serial
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MODEL_PATH = os.getenv("MODEL_PATH", "/app/model.tflite")
SERIAL_DEV = os.getenv("SERIAL_DEV", "/dev/ttyACM0")
USE_DUMMY = os.getenv("DUMMY_MODEL", "0") == "1"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
<<<<<<< HEAD
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger("opi_zero_app")

=======
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("opi_zero_app")

SERIAL_ACK_TIMEOUT = float(os.getenv("SERIAL_ACK_TIMEOUT", "0.75"))
SERIAL_ACK_POLL = float(os.getenv("SERIAL_ACK_POLL", "0.05"))

>>>>>>> 716cb5b (Improve serial ack diagnostics)
interp = None
inp = out = None
ser = None
m = None


def _read_serial_ack() -> List[str]:
    if ser is None or SERIAL_ACK_TIMEOUT <= 0:
        return []

    deadline = time.perf_counter() + SERIAL_ACK_TIMEOUT
    lines: List[str] = []

    while time.perf_counter() <= deadline:
        try:
            waiting = getattr(ser, "in_waiting", 0)
        except Exception as exc:  # noqa: BLE001
            log.warning("Serial in_waiting check failed: %s", exc)
            break

        if waiting:
            try:
                raw = ser.readline()
            except Exception as exc:  # noqa: BLE001
                log.warning("Serial readline failed: %s", exc)
                break

            if not raw:
                continue

            decoded = raw.decode(errors="ignore").strip()
            if decoded:
                lines.append(decoded)
                if len(lines) >= 5:
                    break

            # якщо ще є дані в буфері — дочекаємося наступного циклу без сну
            continue

        # нема що читати — невелика пауза перед наступною перевіркою
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        time.sleep(min(SERIAL_ACK_POLL, remaining))

    return lines

@asynccontextmanager
async def lifespan(app: FastAPI):
    global interp, inp, out, ser, m
    # Serial
    ser = serial.Serial(SERIAL_DEV, 115200, timeout=0.2)
    # Arduino Mega перезавантажується при відкритті послідовного порту —
    # даємо йому час закінчити bootloader і чистимо буфери, інакше перші
    # команди губляться.
    time.sleep(2.0)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    # MQTT
    m = mqtt.Client(client_id="opiz")
    m.connect(os.getenv("MQTT_HOST", "localhost"), 1883, 60)
    m.loop_start()
    # Model (не падаємо, якщо файла нема)
    if not USE_DUMMY and os.path.exists(MODEL_PATH):
        from tflite_runtime.interpreter import Interpreter
        interp = Interpreter(model_path=MODEL_PATH)  # якщо файл є — завантажиться
        interp.allocate_tensors()
        inp, out = interp.get_input_details()[0], interp.get_output_details()[0]
    yield
    # тут можна зупинити клієнти, якщо треба

app = FastAPI(title="OPi Zero Inference", lifespan=lifespan)

class Obs(BaseModel):
    x: List[float]

@app.get("/healthz")
def healthz():
    return {"model_loaded": interp is not None, "model_path": MODEL_PATH}

@app.post("/predict")
def predict(o: Obs):
    if interp is None and not USE_DUMMY:
        raise HTTPException(status_code=503, detail=f"Model not loaded at {MODEL_PATH}")
    if ser is None or not ser.is_open:
        raise HTTPException(status_code=503, detail="Serial port is not available")
    if interp is None and USE_DUMMY:
        y, ms = o.x[:], 0.1  # «глушилка»: повертаємо вхід як вихід
    else:
        arr = np.array([o.x], dtype="float32")
        # підженемо форму
        if tuple(arr.shape) != tuple(inp["shape"]):
            arr = arr.reshape(inp["shape"])
        t0 = time.perf_counter()
        interp.set_tensor(inp["index"], arr)
        interp.invoke()
        y = np.asarray(interp.get_output_tensor(out["index"])).tolist()[0]
        ms = (time.perf_counter() - t0) * 1000.0
    pkt = {"seq": int(time.time() * 1000), "cmd": y}
    payload = json.dumps(pkt)
<<<<<<< HEAD
=======

    try:
        ser.reset_input_buffer()
    except Exception as exc:  # noqa: BLE001
        log.debug("Could not clear serial input buffer: %s", exc)

>>>>>>> 716cb5b (Improve serial ack diagnostics)
    sent = ser.write((payload + "\r\n").encode())
    ser.flush()
    log.info(
        "→ Arduino seq=%s bytes=%s cmd=%s",
        pkt["seq"],
        sent,
        [round(v, 5) for v in y],
    )

<<<<<<< HEAD
    ack = ""
    try:
        if getattr(ser, "in_waiting", 0) == 0:
            time.sleep(0.05)
        if getattr(ser, "in_waiting", 0):
            ack = ser.readline().decode(errors="ignore").strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("Serial ack read failed for seq=%s: %s", pkt["seq"], exc)
    else:
        if ack:
            log.info("← Arduino seq=%s ack=%s", pkt["seq"], ack)
        else:
            log.debug("No ack received from Arduino for seq=%s", pkt["seq"])
=======
    ack_lines = _read_serial_ack()
    if ack_lines:
        for line in ack_lines:
            log.info("← Arduino seq=%s ack=%s", pkt["seq"], line)
    else:
        log.debug("No ack received from Arduino for seq=%s", pkt["seq"])
>>>>>>> 716cb5b (Improve serial ack diagnostics)

    m.publish("arm/metrics", json.dumps({"latency_ms": ms}), qos=0)
    return {
        "seq": pkt["seq"],
        "action": y,
        "latency_ms": ms,
        "serial": {"bytes_written": int(sent), "ack": ack_lines},
    }

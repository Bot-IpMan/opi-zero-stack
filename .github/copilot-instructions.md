# 🤖 GitHub Copilot / Claude Instructions

This guide helps AI coding agents understand the architecture and contribute effectively to this project.

## 🎯 Project Purpose

A distributed robot arm control system using Reinforcement Learning (PPO) for joint control, YOLO for object detection, and serial communication with Arduino. The system learns autonomously in simulation and deploys on resource-constrained hardware (Orange Pi Zero, 512MB RAM).

## 🏗️ Architecture (Critical to Understand)

**One-liner:** PC trains PPO model → Orange Pi Zero runs inference (YOLO + RL) → Arduino controls servos

### Real Architecture (NOT 3 separate systems):

```
PC (training, one-time):
  └── training/ → PPO + PyBullet + ONNX export

Orange Pi Zero (always-on, all services):
  ├── Docker
  ├─ mqtt: broker
  ├─ yolo-detector: camera → detections → MQTT
  ├─ app: MQTT → RL inference → serial
  └─ models: ppo_model.tflite, yolov8n.tflite

Arduino (one-time firmware):
  └── Serial JSON ← → PWM signals
```

**Key insight:** Don't think of this as 3 separate projects. Training happens once on PC, then models are copied to Orange Pi for runtime operation.

## ⚠️ Critical Constraints (Must Know)

### Hardware
- **Orange Pi Zero = 512MB RAM total**
  - All containers combined must use < 400MB
  - Models must be ≤ 200KB (TFLite INT8 only)
  - No CPU feature flags (no SSE4.1/AVX2)

### Software
- **PC without SSE4.1** → use PyTorch 1.13.1 (not 2.1.0)
- **tflite-runtime==2.14.0** (not TensorFlow 2.15)
- **Never compile packages on Orange Pi** (use wheels only)
- **Debian 12+ has different package names** (libglib2.0-0t64, not libglib2.0-0)
- **Docker compose must have memory limits** per service

### Network
- PC and Orange Pi in same local network
- MQTT for inter-component communication
- < 100ms latency required

## 📁 Project Structure

- `training/` → PPO training script (PC only, one-time)
- `yolo-detection/` → YOLO inference daemon (Orange Pi)
- `app/` → RL inference + serial control (Orange Pi)
- `firmware/` → Arduino sketch (compile once, deploy)
- `mosquitto/` → MQTT broker config (runs on Orange Pi)
- `docs/codex_prompt.md` → Full developer guide with 40+ troubleshooting items

## 🔑 Key Patterns

### Package Versions Matter
```
✅ torch==1.13.1, tflite-runtime==2.14.0, opencv-python-headless==4.8.1.78
❌ torch==2.1.0, tensorflow==2.15, opencv-python
```

### Dockerfile Best Practices
```dockerfile
# ✅ Correct (Debian 12+)
RUN apt-get install -y libgl1 libglib2.0-0t64 libgomp1

# ❌ Wrong (Debian 11, not in 12+)
RUN apt-get install -y libgl1-mesa-glx libglib2.0-0
```

### Memory Management
```yaml
# docker-compose.yml - MUST specify mem_limit
services:
  app:
    mem_limit: "120m"
  yolo-detector:
    mem_limit: "200m"
  mqtt:
    mem_limit: "50m"
```

### MQTT Communication Pattern
- YOLO publishes: `arm/vision/objects` (detections)
- App subscribes to vision, runs RL inference
- App publishes: commands to Arduino via serial

## 🚨 Common Mistakes to Avoid

1. **Thinking 3 separate systems exist** → No, all runtime on Orange Pi
2. **Using old tensorflow** → PPO exports to ONNX, Orange Pi uses tflite-runtime only
3. **Compiling packages on Orange Pi** → Results in 2-hour builds, use wheels
4. **Using Debian 11 pakcages in Dockerfile** → Fails on Debian 12
5. **Model > 500KB** → Won't fit in memory constraints
6. **No mem_limit in compose** → Orange Pi will OOM and crash
7. **Editing tflite models directly** → Export from PyTorch → ONNX → TFLite
8. **Running full TensorFlow on Orange Pi** → Use tflite-runtime (5MB vs 500MB)

## ✅ Definition of Done

Before merging any changes:
- [ ] All Dockerfiles build < 5 minutes
- [ ] Training reaches reward > 100
- [ ] Exported model < 500KB
- [ ] `docker compose up` runs successfully on ARM
- [ ] Health check: `curl http://localhost:8000/healthz` → 200 OK
- [ ] MQTT publishes arm/vision/objects and arm/control/action
- [ ] Arduino responds with ACK to serial commands
- [ ] No errors in `docker compose logs`

## 🔍 Debugging Workflow

```bash
# Check what's running
docker compose ps

# Real-time logs
docker compose logs -f app

# Memory usage (< 400MB total!)
docker compose stats

# MQTT traffic
docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/#' -v

# Health endpoint
curl http://localhost:8000/healthz | jq

# Serial communication (if debugging Arduino)
docker compose exec app python -c "import serial; s=serial.Serial('/dev/ttyACM0'); print(s.readline())"
```

## 📊 Success Metrics

| Component | Metric | Good | Bad |
|-----------|--------|------|-----|
| Training | ep_rew_mean | > 100 | < 0 |
| YOLO | FPS | 20-25 | < 10 |
| RL loop | Hz | ≥ 20 | < 5 |
| System | RAM usage | < 400MB | > 450MB |
| Serial | ACK rate | 95%+ | < 50% |

## 🎓 When to Reference Full Guide

- Adding new components → See `docs/codex_prompt.md`
- Debugging issues → Search errors in codex_prompt.md (10+ examples)
- Understanding rewards → Training section explains reward shaping
- Extending YOLO → YOLO detector module pattern
- New sensors → Modify observation space in `robot_arm_env.py`

## 🏁 Typical Contribution Workflow

1. **Read** this file and `.github/requirements.md` (if exists)
2. **Check** `docs/codex_prompt.md` section on your feature
3. **Reference** existing code: `app/main.py` for MQTT pattern, `train_ppo.py` for RL pattern
4. **Test locally** with Docker: `docker compose up -d && docker compose logs -f`
5. **Verify** checklist above before PR
6. **Link** to issue/discussion if architectural decision

## 📞 Key Contacts

- **Architecture questions** → See `README.md` "How it works?" section
- **Hardware constraints** → Check `docs/codex_prompt.md` "Critical Requirements"
- **Training issues** → Debug via TensorBoard at http://localhost:6006
- **Deployment issues** → Check Docker logs: `docker compose logs app`
- **Serial/Arduino issues** → Review `firmware/README.md` and `app/main.py` serial handling

---

**Last updated:** 2024-12-06  
**Version:** 1.0  
**For:** Cursor, GitHub Copilot, Claude, Windsurf

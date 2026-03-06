# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Conda environment: `robomimic` (Python 3.8)

## Common Commands

```bash
# Run Mujoco simulation (standing start)
conda activate robomimic
python deploy_mujoco/deploy_mujoco.py

# Run simulation from lying-down state
python deploy_mujoco/deploy_mujoco.py xml_path=g1_description/g1_29dof_LieDown.xml

# Run real robot deployment
python deploy_real/deploy_real.py

# Debug joystick button/axis indices
python tools/joystick_test.py
```

`deploy_mujoco` uses Hydra; config is at `deploy_mujoco/config/mujoco.yaml`. CLI overrides use `key=value` syntax (no `--`).

## Architecture

### Data Flow

```
JoyStick / RemoteController
        │ skill_cmd, vel_cmd
        ▼
  StateAndCmd  ──────────────────►  FSM.run()
        │                               │
        │                         cur_policy.run()
        │                               │
        ▼                               ▼
  PolicyOutput  ◄──────────  policy writes actions/kps/kds
        │
        ▼
  pd_control → joint torques → MuJoCo / real robot
```

`StateAndCmd` and `PolicyOutput` (defined in `common/ctrlcomp.py`) are the shared data bus. Every policy reads from `StateAndCmd` and writes to `PolicyOutput`.

### FSM

`FSM/FSM.py` instantiates **all** policies at startup and holds references to them. On each control tick it calls `cur_policy.run()` then `cur_policy.checkChange()`. If the returned `FSMStateName` differs from the current state, it calls `exit()` on the old policy, switches, then calls `enter()` on the new one on the next tick.

Every policy inherits `FSMState` (`FSM/FSMState.py`) and must implement `enter()`, `run()`, `exit()`, `checkChange()`.

### Policy Structure

Each policy lives in `policy/<name>/` with:
- `<Name>.py` — inherits `FSMState`, loads ONNX model and YAML config in `__init__`
- `config/<Name>.yaml` — kps, kds, tau_limit, default_angles, scaling factors, ONNX filename
- `model/<name>.onnx` — the neural network

The observation vector is assembled manually in `run()` and fed to `onnxruntime`. Reference motion is **not** a file at deploy time — it is baked into the ONNX weights. A scalar `ref_motion_phase` (elapsed time / total duration) is passed as input so the network knows its position in the motion.

G1 has **29 DOFs**, but most policies control only **23** (wrist/finger joints 19-21 and 26-28 are held at `default_angles`). The `dof23_index` field in each config maps which 23 joints the policy controls.

### Input Devices (Simulation vs Real)

- **Simulation** (`deploy_mujoco`): `common/joystick.py` — pygame, Xbox controller via Linux xpad driver. Default mapping targets **Xbox One on Linux**.
- **Real robot** (`deploy_real`): `common/remote_controller.py` — Unitree wireless remote, parsed from raw SDK bytes via `struct.unpack`. Completely independent from `joystick.py`.

Joystick axis mapping in `deploy_mujoco/deploy_mujoco.py`:
- Axis 0 → `vel_cmd[1]` (left stick X, strafe)
- Axis 1 → `vel_cmd[0]` (left stick Y, forward/back)
- Axis 2 → `vel_cmd[2]` (right stick X, yaw)

### Button → FSMCommand Mapping (simulation)

| Buttons | FSMCommand | Policy |
|---------|-----------|--------|
| Start | POS_RESET | FixedPose |
| R1+A | LOCO | LocoMode |
| R1+X | SKILL_1 | Dance |
| R1+Y | SKILL_2 | KungFu |
| R1+B | SKILL_3 | Kick |
| L1+Y | SKILL_4 | KungFu2 |
| L1+A | SKILL_5 | ASAP |
| L1+X | STAND_UP | HOST (stand from lying) |
| L1 release (R1 held) | PASSIVE | PassiveMode |
| SELECT | — | Exit program |

### Adding a New Policy

1. Create `policy/<name>/` with the three files above
2. Add `FSMStateName` and `FSMCommand` entries in `common/utils.py`
3. Instantiate in `FSM/FSM.py` `__init__` and add a branch in `get_next_policy()`
4. Add button binding in `deploy_mujoco/deploy_mujoco.py` (and `deploy_real/deploy_real.py` if needed)

### Control Timing

Simulation: `simulation_dt=0.003s × control_decimation=7 ≈ 20ms` control period.
Real: `control_dt=0.02s` (20ms).

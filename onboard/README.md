# Onboard — 机载感知服务

本目录包含运行在 **G1 机载电脑**上的感知服务代码。
服务启动后通过 **DDS**（与 Unitree SDK 同网段）实时发布球的位置，
本地电脑连接网线后即可直接订阅，无需 SSH 进机器手动启动额外进程。

---

## 目录结构

```
onboard/
└── perception/
    ├── lidar/
    │   ├── ball_detector.py     ← 主服务：MID360 点云 → 球心检测 → DDS 发布
    │   └── mid360_to_base.py   ← 坐标变换：MID360 系 → pelvis (base) 系
    └── camera/                  ← 预留：相机方案（待实现）
```

---

## DDS 消息

| 字段 | 类型 | 含义 |
|------|------|------|
| `timestamp_us` | uint64 | 发布时刻（µs since epoch） |
| `x / y / z` | float32 | 球心在 **pelvis body 系** 的坐标（m） |
| `valid` | uint8 | `1` = 本帧检测到球；`0` = 未检测到，位置为上一帧 EMA 值 |

- **Topic**：`rt/ball_state`
- **QoS**：BestEffort，KeepLast(1)
- **频率**：约 10 Hz（受 Livox MID360 点云帧率限制）

消息定义和 Publisher / Subscriber 封装见 `common/ball_state_dds.py`。

---

## 快速启动

### 1. 依赖

机载电脑需要安装：

```bash
# ROS2（Humble 或 Foxy）
# livox_ros_driver2（MID360 ROS2 驱动）
# unitree_sdk2_python（用于订阅 /lowstate 获取关节角）
pip install cyclonedds
```

### 2. 启动 MID360 驱动

```bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

### 3. 启动球检测服务

在 `RoboMimicDeploy_G1` 根目录下运行：

```bash
python onboard/perception/lidar/ball_detector.py
```

服务启动后终端会持续打印检测到的球心坐标及每帧耗时。

---

## 本地验证

本地电脑通过网线连接 G1 后，在 `RoboMimicDeploy_G1` 根目录运行：

```bash
python tools/check_ball_state.py
```

正常输出示例：

```
[OK ]  x=+0.823  y=-0.012  z=-0.673  age=85ms
```

- `age` 为数据距当前时刻的延迟，超过 300ms 则显示 `---`（数据过期）。
- 确认能稳定收到数据后，再启动 `deploy_real/deploy_real.py`。

---

## 感知流程（lidar 方案）

```
Livox MID360（点云，~10 Hz）
        │
        │ ROI 滤波 + 反射率阈值
        ▼
候选点云（高反射率球面点）
        │
        │ 最小二乘球心拟合（已知半径 0.115m）
        ▼
球心（MID360 坐标系）
        │
        │ EMA 时间滤波（α=0.6，跳变门限 0.6m）
        ▼
球心（MID360 坐标系，平滑后）
        │
        │ transform_point_mid360_to_base()
        │ （链式正运动学：pelvis → waist → torso → head → MID360）
        │ 使用实时关节角 q_wy / q_wr / q_wp / q_head
        ▼
球心（pelvis body 系）
        │
        │ DDS publish "rt/ball_state"
        ▼
deploy_real.py → state_cmd.ball_pos_b → Score._build_obs()
```

---

## 添加新的感知方案

以相机方案为例，只需：

1. 在 `onboard/perception/camera/` 下新建 `ball_detector.py`
2. 用任意方式（颜色检测、深度相机、神经网络等）获取球在 pelvis 系的坐标
3. 调用相同接口发布：

```python
from common.ball_state_dds import BallStatePublisher
dds = BallStatePublisher(domain_id=0)
dds.publish(x, y, z, valid=True)
```

`deploy_real.py` 和 `Score.py` **无需任何修改**。

---

## 参数调整

`ball_detector.py` 中可调整的检测参数：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `reflect_thr` | 150 | 反射率阈值，球面反射率较高，可从 60 逐步调高 |
| `min_points` | 3 | 候选点数下限，太少则不可靠 |
| `max_range` | 1.8 m | ROI 最大距离 |
| `min_range` | 0.2 m | ROI 最小距离（过滤自身遮挡） |
| `x_low / x_high` | 0~5 m | 仅检测机器人正前方区域 |
| `z_low / z_high` | ±1.5 m | 高度范围 |
| `alpha` | 0.6 | EMA 平滑系数，越大跟踪越灵敏，越小越平滑 |

# openarm_mission — OpenArm v1 双臂纸杯接力：仿真、数据与 π0.5 微调全流程

本目录是基于 [openpi](../) 的独立项目：在 MuJoCo 中搭建 OpenArm v1 双臂
「纸杯接力」任务，用脚本专家通过 100/100 评测后批量采集演示数据，接入
openpi 完成 π0.5 LoRA 微调与闭环评测，并进一步把整条接力拆成左右两个
单臂子任务、用决策树组合两套 LoRA 策略完成完整任务。

```text
任务场景（俯视）

        ┌─────────────┐
        │  桌面 + 水瓶  │
        │             │
   🔴A区 │   中央交接位  │ 🔵B区
        └─────────────┘
         🤖 双臂机器人
```

**任务定义**：右臂从机器人右前方的红色 A 区夹起无把手一次性纸杯，直立放到
桌面中央交接位并退出；左臂从中央重新夹起纸杯，直立放到机器人左前方的蓝色
B 区并退出。要求全程纸杯直立、无 weld 作弊（P4.5 起为纯摩擦抓取）、双手
顺序执行且互锁。

## 总体进度

| 阶段 | 内容 | 结果 | 详细文档 |
| --- | --- | --- | --- |
| P0–P2 | 需求冻结、官方 MJCF 导入、IK / 力矩控制 / 安全限制 | IK 40/40 收敛，长稳 600 s | [phase_docs/p0–p2](phase_docs/) |
| P3 | 真实接触任务：双指接触门控、动态 weld、状态机、成功判定 | 种子 0–9：10/10 | [phase_docs/p3.md](phase_docs/p3.md) |
| P4 | 可恢复双臂脚本专家 + 100 次正式评测 | **100/100**，平均 XY 误差 9.7 mm | [phase_docs/p4.md](phase_docs/p4.md) |
| P4.5 | 无 weld 纯摩擦抓取（软指垫 + 力限位阻抗 + 滑移检测） | **100/100**，平均 XY 误差 28.3 mm | [phase_docs/p4_5.md](phase_docs/p4_5.md) |
| P5 | 20 Hz 同步轨迹采集、域随机化、LeRobot v2 转换 | 200 集 / 86,400 帧，160/20/20 | [phase_docs/p5.md](phase_docs/p5.md) |
| P6 | 接入 openpi：transforms、data config、训练配置 | `OpenArmInputs/Outputs` 等 | [phase_docs/p6.md](phase_docs/p6.md) |
| P7 | π0.5 LoRA 微调与闭环评测 | checkpoint 29999 闭环可跑 | [phase_docs/p7.md](phase_docs/p7.md) |
| P9 | 按真机 OpenArm 数据集格式 v0.3.0 重采 200 条 | 与 `data/real_data/` 同构 | [phase_docs/p9.md](phase_docs/p9.md) |
| P10–P12 | 新布局（26 cm 桌 + 水瓶）、左右臂拆分子任务、双 LoRA + 决策树 | 当前工作重点 | [SUBTASK_PIPELINE.md](SUBTASK_PIPELINE.md) |

> **历史数据说明**：P5（`artifacts/p5/`）与 P9（`artifacts/p9/`）原始数据已于
> 2026-08-08 删除；当前全量数据为最新布局（26 cm 桌 + 水瓶）采集的左右
> 子任务数据集（`artifacts/p12_right_full_20260826/`、
> `artifacts/p12_left_full_20260826/`）。旧数据及归一化统计不适用于当前
> 脚本版本，重采后必须重新计算 normalization stats。

## 任务与数据接口

所有阶段共用一套接口，保证「采集—训练—推理」一致：

- **状态（16 维）**：左右臂各 7 关节角度 + 夹爪开度（米）。
- **动作（14 维）**：`[left dx dy dz dRx dRy dRz gripper, right …]`。
  平移单位米，旋转为旋转向量（弧度），夹爪 `-1` 全开 / `+1` 全闭。
  对齐语义为 `observation[t] -> action[t] -> target[t+1]`，控制频率 `20 Hz`。
- **相机（3 路，本体视角）**：`head` 相机位于双臂上方俯瞰桌面；左右腕相机
  以物理刚体（L 形支架 + 相机壳）安装在 J8/`hand` 上，画面顺时针旋转 90°。
- **语言指令**（`task_modes.py`）：
  - `relay`：双手完整接力；`right`：仅右臂 A 区→中央；`left`：仅左臂中央→B 区。
  - 接力数据按任务阶段逐帧标注当前激活的子任务指令。

## 目录结构

```text
openarm_mission/
├── config.py                   # 场景尺寸、区域位置和控制参数
├── model.py                    # OpenArm v1 MJCF 组合、纸杯、桌面和相机
├── controller.py               # 双臂 DLS IK、力矩 PD 和安全限制
├── task.py                     # P3 接触门控、weld、状态机和成功判定
├── expert.py                   # P4 可恢复双臂脚本专家
├── friction_task.py            # P4.5 无 weld 接触力/滑移状态机
├── friction_expert.py          # P4.5 软指垫纯摩擦双臂专家（支持 --task right/left）
├── dataset.py                  # 数据定义、同步记录、域随机化和子任务标注
├── collect_dataset.py          # 批量采集（--task relay/right/left）
├── convert_to_lerobot.py       # LeRobot v2 转换
├── convert_to_openarm_v03.py   # 转换为真机 OpenArm 数据集格式 v0.3.0
├── task_modes.py               # relay/right/left 模式定义与逐帧指令标注
├── policy_router.py            # 右策略→稳定交接→左策略 的决策树路由
├── policy_eval.py              # 闭环评测（单策略 / --hierarchical 双策略）
├── openarm_sim/                # 回放前端：LeRobot parquet / v0.3.0 / 真机数据
├── openarm_sim2/               # 独立仿真前端：robot6 全身 URDF + 网页面板
├── urdf/                       # robot6 全身 URDF（底盘 + 脊柱 + 双臂 + 颈）
├── bddl/                       # LIBERO 风格任务定义
├── phase_docs/                 # P0–P9 各阶段设计、命令与验证记录
├── tests/                      # 全阶段自动测试
├── smoke_test.py               # 模型、IK、物理和离屏渲染检查
├── fetch_openarm_v1.sh         # 幂等依赖下载脚本
├── SPEC.md                     # 冻结需求和验收口径
├── COMMANDS.md                 # 全部命令速查
├── SUBTASK_PIPELINE.md         # 左右拆分双 LoRA + 决策树完整流程
├── TODO.md                     # 完整 Todo List 与验证记录
└── artifacts/                  # 生成成果；默认不纳入 Git
```

## 快速开始

### 0. 环境准备

```bash
# 在仓库根目录，使用 openpi 主环境 .venv
bash openarm_mission/fetch_openarm_v1.sh   # 下载官方模型（锁定 revision 8955afb5…）
```

无窗口 Linux 需要 EGL 离屏渲染，以下 MuJoCo 命令均带 `MUJOCO_GL=egl`。

```bash
# 冒烟检查：模型、IK、物理与渲染
MUJOCO_GL=egl .venv/bin/python -m openarm_mission.smoke_test

# 全部自动测试（25 项，覆盖 MuJoCo 2.3.7 / 3.2.3）
.venv/bin/python -m unittest discover -s openarm_mission/tests -v
```

### 1. 脚本专家与评测

```bash
# 纯摩擦专家跑一条（P4.5，无 weld）
.venv/bin/python -m openarm_mission.friction_expert --seed 7
MUJOCO_GL=egl .venv/bin/python -m openarm_mission.friction_expert \
  --seed 7 --video --width 720 --height 480      # 带视频

# 100 次正式评测（可换 p4_benchmark 复现 weld 版）
.venv/bin/python -m openarm_mission.p45_benchmark --episodes 100 --workers 4
```

### 2. 采集数据并转换

采集支持三种任务模式；左右拆分流程以 `right` / `left` 各采 200 条：

```bash
MUJOCO_GL=egl .venv/bin/python -m openarm_mission.collect_dataset \
  --task right --output-dir openarm_mission/artifacts/p12_right_full_20260826 \
  --episodes 200 --workers 16 --image-episodes 200
# --task left 同理；长任务加 --resume --max-new-episodes 32 分批恢复
```

两种输出格式：

```bash
# LeRobot v2（openpi 训练输入）
.venv/bin/python -m openarm_mission.convert_to_lerobot \
  --source-dir <采集目录> \
  --output-dir  <采集目录>/lerobot/openarm_right_handoff \
  --repo-id openarm_right_handoff --overwrite

# 真机 OpenArm 数据集格式 v0.3.0（与 data/real_data/ 同构，可被厂商工具链消费）
.venv/bin/python -m openarm_mission.convert_to_openarm_v03 \
  --source <采集目录> --output <采集目录>/openarm_paper_cup_relay
```

### 3. 接入 openpi：LoRA 微调与推理

openpi 侧已注册 4 个配置（[src/openpi/training/config.py](../src/openpi/training/config.py)）：
`pi05_openarm_paper_cup_relay(_lora)`（完整接力）与
`pi05_openarm_right_handoff_lora` / `pi05_openarm_left_delivery_lora`
（左右子任务）。典型流程：

```bash
export HF_LEROBOT_HOME=<LeRobot 数据集目录>

# 归一化统计
python scripts/compute_norm_stats.py --config-name pi05_openarm_right_handoff_lora

# LoRA 微调（从 π0.5 预训练权重出发）
python scripts/train.py pi05_openarm_right_handoff_lora \
  --exp-name right_handoff_lora_20260826 \
  --batch-size 32 --num-train-steps 30000 --save-interval 5000

# 策略服务
python scripts/serve_policy.py policy:checkpoint \
  --policy.config pi05_openarm_right_handoff_lora \
  --policy.dir checkpoints/pi05_openarm_right_handoff_lora/right_handoff_lora_20260826/29999 \
  --port 8001
```

### 4. 闭环评测与决策树

[policy_eval.py](policy_eval.py) 连接策略服务，以滚动重规划消费 14 维 action
chunk，通过双臂互锁镜像训练数据分布，按纸杯位置直接判定成败：

```bash
# 单策略
MUJOCO_GL=egl .venv/bin/python -m openarm_mission.policy_eval \
  --host 127.0.0.1 --port 8000 --episodes 5 --seed 7

# 双 LoRA + 决策树：右策略交接稳定后切换左策略，完成完整接力
MUJOCO_GL=egl .venv/bin/python -m openarm_mission.policy_eval \
  --hierarchical \
  --right-host 127.0.0.1 --right-port 8001 \
  --left-host 127.0.0.1 --left-port 8002 \
  --episodes 5 --start-seed 1000 \
  --video-out openarm_mission/artifacts/eval_dual_lora
```

决策树（[policy_router.py](policy_router.py)）切换条件：杯子位于中央、直立
稳定、接触桌面、右爪全开、右手退出交接区，并冻结双臂短暂停留。最终成功要求
杯子在蓝区、稳定接触桌面、左爪打开且左手退出。**从采集、冒烟到双 LoRA 训练
与决策树评测的完整命令清单见
[SUBTASK_PIPELINE.md](SUBTASK_PIPELINE.md)。**

## 前端工具

| 前端 | 用途 | 启动 |
| --- | --- | --- |
| [openarm_sim/](openarm_sim/) | 姿态回放：LeRobot parquet / v0.3.0 数据 / 真机 episode / OpenArm Panel 实时源 | `MUJOCO_GL=egl .venv/bin/python -m openarm_mission.openarm_sim.server --port 8080` |
| [openarm_sim2/](openarm_sim2/) | robot6 全身 URDF（底盘+脊柱+双臂+颈）独立仿真，网页关节面板 + 自由视角 | `.venv/bin/python -m openarm_mission.openarm_sim2.gui`，打开 `http://localhost:8899` |

## 文档索引

- [COMMANDS.md](COMMANDS.md) — 全阶段命令速查
- [SUBTASK_PIPELINE.md](SUBTASK_PIPELINE.md) — 左右拆分双 LoRA + 决策树流程（当前主线）
- [SPEC.md](SPEC.md) — 冻结需求与验收口径
- [TODO.md](TODO.md) — 完整 Todo List 与逐阶段验证记录
- [phase_docs/](phase_docs/) — P0–P9 设计细节、全部命令与验证结果
- [openarm_sim/ARCHITECTURE.md](openarm_sim/ARCHITECTURE.md) — 回放前端架构
- [openarm_sim2/README.md](openarm_sim2/README.md) — robot6 URDF 导入管线与网页面板

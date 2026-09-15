# OpenArm 双臂纸杯接力 — 仿真、数据与 π0.5 微调

本项目在 MuJoCo 中搭建 OpenArm v1 双臂「纸杯接力」任务，从脚本专家、
批量数据采集，到基于 [openpi](https://github.com/Physical-Intelligence/openpi)
的 π0.5 LoRA 微调与闭环评测，再到左右臂拆分子任务、双 LoRA + 决策树完成
完整任务——一条端到端打通的 VLA 微调全流程。

核心实现位于 [`openarm_mission/`](openarm_mission/)，
**完整文档见 [openarm_mission/README.md](openarm_mission/README.md)**。

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
B 区并退出。要求全程纸杯直立、纯摩擦抓取（无 weld 作弊）、双手顺序执行且互锁。

## 核心成果

| 阶段 | 内容 | 结果 |
| --- | --- | --- |
| 仿真基础 | 官方 MJCF 导入、双臂 DLS IK、力矩控制、安全限制 | IK 40/40 收敛，600 s 长稳 |
| 物理任务 | 双指接触门控、动态 weld、状态机、成功判定 | 种子 0–9：10/10 |
| 脚本专家 | 可恢复双臂专家 + 100 次正式评测（weld 版 / 纯摩擦版） | **两个版本均 100/100** |
| 数据管线 | 20 Hz 同步三相机采集、域随机化、LeRobot v2 / 真机 v0.3.0 双格式 | 200 集 / 86,400 帧 |
| openpi 接入 | `OpenArmInputs/Outputs`、data config、4 个训练配置 | LoRA 微调 + 策略服务 |
| 闭环评测 | 14 维 action chunk 滚动重规划、双臂互锁、按纸杯位置判成败 | checkpoint 29999 闭环可跑 |
| 左右拆分 | `right`/`left` 子任务数据、双 LoRA、决策树路由 | [SUBTASK_PIPELINE.md](openarm_mission/SUBTASK_PIPELINE.md) |

## 端到端流程

```text
MuJoCo 仿真 (P0–P3)
  └─ 脚本专家 + 100/100 评测 (P4/P4.5)
      └─ 200 集三相机演示数据 (P5)
          └─ π0.5 LoRA 微调 (P6–P7, openpi)
              └─ 闭环评测 (policy_eval)
                  └─ 左右拆分双 LoRA + 决策树接力 (P12)
```

接口全程一致：**16 维状态**（左右臂各 7 关节 + 夹爪开度）、
**14 维动作**（双臂笛卡尔增量 + 夹爪，20 Hz）、
**3 路本体视角相机**（head 俯瞰桌面 + 左右腕 L 形支架相机）、
**语言指令**（`relay` / `right` / `left` 三种任务模式）。

## 快速开始

环境准备、专家评测、数据采集、LoRA 训练与闭环评测的完整命令见
**[openarm_mission/README.md](openarm_mission/README.md)**；
各阶段设计细节见 [openarm_mission/phase_docs/](openarm_mission/phase_docs/)。

最小示例——跑通纯摩擦脚本专家：

```bash
bash openarm_mission/fetch_openarm_v1.sh            # 下载官方模型
MUJOCO_GL=egl .venv/bin/python -m openarm_mission.friction_expert --seed 7
```

## 仓库结构

```text
├── openarm_mission/            # ★ 本项目核心实现与文档
│   ├── model.py / controller.py / task.py       # 仿真、IK、物理任务
│   ├── expert.py / friction_expert.py           # 脚本专家
│   ├── dataset.py / collect_dataset.py          # 数据采集
│   ├── convert_to_lerobot.py                    # LeRobot v2 转换
│   ├── convert_to_openarm_v03.py                # 真机 v0.3.0 格式转换
│   ├── policy_router.py / policy_eval.py        # 决策树与闭环评测
│   ├── openarm_sim/                             # 回放前端（parquet/v0.3.0/真机数据）
│   ├── openarm_sim2/                            # robot6 全身 URDF 仿真 + 网页面板
│   └── phase_docs/                              # P0–P9 各阶段文档
├── src/openpi/                 # openpi 框架（含本项目新增的 openarm 配置）
│   └── policies/openarm_policy.py               # OpenArmInputs/Outputs
│   └── training/config.py                       # pi05_openarm_* 训练配置
├── scripts/                    # openpi 训练 / 推理脚本
└── examples/                   # LIBERO、ALOHA、DROID 等示例
```

## 基于 openpi

训练与推理框架为
[Physical Intelligence 的 openpi](https://github.com/Physical-Intelligence/openpi)
（π0 / π0-FAST / π0.5 视觉-语言-动作模型，Apache-2.0）。本仓库在其基础上
新增了 OpenArm 任务的全部配置与工具链，框架本身的安装方式不变：

```bash
GIT_LFS_SKIP_SMUDGE=1 uv sync
GIT_LFS_SKIP_SMUDGE=1 uv pip install -e .
```

| 模式               | 显存要求    | 参考 GPU           |
| ------------------ | ----------- | ------------------ |
| 推理               | > 8 GB      | RTX 4090           |
| 微调（LoRA）       | > 22.5 GB   | RTX 4090           |
| 微调（全参数）     | > 70 GB     | A100 (80GB) / H100 |

模型加载、PyTorch 支持、Docker、多 GPU 训练等框架细节请参考
[上游 README](https://github.com/Physical-Intelligence/openpi#readme)。

## 致谢

- [OpenArm](https://github.com/enactic/openarm)（enactic）：OpenArm v1 双臂硬件与官方 MJCF/描述包
- [openpi](https://github.com/Physical-Intelligence/openpi)（Physical Intelligence）：π0.5 模型与训练推理框架
- [LeRobot](https://github.com/huggingface/lerobot)（Hugging Face）：数据集格式
- [MuJoCo](https://mujoco.readthedocs.io/)：物理仿真

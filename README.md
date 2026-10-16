# Agent 决策研究

研究问题：**Agent 在不确定的长程任务中，如何避免持续采取错误行动？**

当前优先探索 P3（何时、以何种方式改变执行能提高长期任务效用）和 P4（如何估计不确定环境下的多步行动价值）。P1、P2、P5及新增猜想独立保留，不预先限定状态表示、干预类型、记忆模块或训练方法。

## 当前进度

2026-10-16：已完成 Calibration Is Not Control 公开仓库源码审查、隔离环境准备和零收费 CPU Smoke Test。**没有执行真实模型复现，Synthetic 结果不是科研性能结果。**

- [源码审查](reports/CODE_AUDIT.md)
- [环境检查](reports/ENVIRONMENT_CHECK.md)
- [Smoke Test 结果](reports/SMOKE_TEST_RESULTS.md)
- [最小真实复现方案（未启动）](reports/REPRODUCTION_READINESS.md)
- [研究风险](reports/RESEARCH_RISKS.md)

报告区分已实际验证、源码推断和仍未核验。已知问题包括回放不一致样本未剔除、显式 EU 遗漏步数成本、阈值搜索边界缺陷及 Oracle/preview 信息边界。原论文实现未修改。

## 目录

| 路径 | 内容 |
|---|---|
| `reports/` | 审查报告及执行日志、依赖快照 |
| `experiments/cinc_smoke_20261016/` | 独立测试脚本、实际环境测试证据、Synthetic 数据与结果 |
| `UPSTREAM.md` | 论文仓库、锁定 Commit 和数据来源 |
| `SYNC.md` | 从实验室服务器同步到 GitHub 的操作说明 |

数据集、虚拟环境、模型权重、第三方论文仓库和下载缓存留在服务器，不进入本仓库。任务清单仅记录文件路径，不包含数据集本体。报告及测试脚本保留实验时的绝对路径 `/home/hly/agent-research`，它们是审计记录；其他机器重跑时需要适配路径和独立准备环境。

## 重跑已有 CPU 测试

先按[环境报告](reports/ENVIRONMENT_CHECK.md)准备依赖与公开任务数据，并按 [UPSTREAM.md](UPSTREAM.md)取得锁定源码。在原实验室路径下：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13 \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/home/hly/agent-research/.venvs/cinc-audit-py310/bin/python \
/home/hly/agent-research/experiments/cinc_smoke_20261016/smoke.py
```

此操作会更新专用 Smoke Test 输出；首次失败日志也予保留。测试不调用真实语言模型。真实模型方案需要单独安排 GPU 时段，不能自动从 Smoke Test 进入大型实验。

## 真实 Pilot 前的可信性加固

独立分支 `pilot-validity-hardening` 保留原作者实现与旧证据，通过适配器增加双分支回放审计、独立成本重算、冻结任务清单和公平baseline对照。真实模型尚未运行；当前整体 **No-Go**，CPU工程检查结果与剩余条件分别记录：

- [加固内容与方法性改动](reports/PILOT_VALIDITY_FIXES.md)
- [回放验证与CPU测试](reports/REPLAY_VALIDATION_RESULTS.md)
- [公平Baseline与信息边界](reports/FAIR_BASELINE_CHECK.md)
- [真实Pilot Go / No-Go与准确命令](reports/REAL_PILOT_GO_NO_GO.md)

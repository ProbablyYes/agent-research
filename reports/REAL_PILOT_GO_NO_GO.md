# 第一轮真实 Agent Pilot：Go / No-Go

2026-10-16，Asia/Shanghai。**目前整体 No-Go（不能立即启动真实模型Pilot）**。CPU加固验证结果见另外三份报告；没有下载大模型、启动GPU推理或调用付费API。

## 条件与限制

| 条件 | 状态 |
|---|---|
| 原作者Commit与已有结果隔离 | [执行] 原仓库未改；独立研究分支pilot-validity-hardening |
| 双分支逐步回放、无效配对排除和分母 | [执行] CPU审计与故意错配测试验证；见REPLAY_VALIDATION_RESULTS |
| 原版/修正版路由和简单策略 | [执行] 并列保存；见FAIR_BASELINE_CHECK |
| 冻结6任务、输入和配置 | [执行] 最终manifest已生成，hash见下 |
| 真实模型权重与tokenizer在本机可用、版本一致 | **未核验**，本次未下载 |
| vLLM服务版本、驱动兼容、实际加载模型、真实请求 | **未核验**，本次未启动 |
| GPU时段与当前可用显存 | **未预留/未核验**，不以此前空闲状态推断 |
| 完整native隐藏状态等价 | **未解决**；不允许声称可靠因果分叉 |

CPU工程关通过后，只能有条件进入“六初始状态真实模型工程Pilot”。如果验收标准要求证明可靠因果分叉，当前仍然No-Go：导出字段相同并非完整native状态证明。任何后续扩大或时机研究都不是本阶段授权。

## 冻结清单

最终计划：`pilot_validity/plans/real_pilot_final/plan.json`。

SHA256：`3179fa6ce944390a118dc309215acff241d376a721327c4e3f748294be768f61`。

| Split | 实例ID | Prefix |
|---|---|---:|
| train | trial_T20190909_151853_245524 | 0 |
| train | trial_T20190907_224507_776787 | 0 |
| val | trial_T20190908_164236_518264 | 0 |
| val | trial_T20190908_033721_967359 | 0 |
| test | trial_T20190908_022321_380927 | 0 |
| test | trial_T20190909_064053_839817 | 0 |

计划记录绝对task路径、task_type、每任务全部现有数据文件哈希（game.tw-pddl、traj_data.json、initial_state.pddl，存在时receps.json）、prompt构造函数原文、15个源/环境实现文件SHA256、依赖版本与全部运行配置。任务来自上一阶段保存清单的每split前2个，不重新shuffle。`real_pilot`是较早的冻结草案，**最终执行只用real_pilot_final**；较早版本保留供审计。

模型锁定 `Qwen/Qwen2.5-7B-Instruct`，模型与tokenizer revision均 `a09a35458c702b33eeacc393d103063234e8bc28`。候选服务vLLM0.6.6、transformers4.46.3，chat_completions，仅127.0.0.1:18080；temperature0、server seed13，作者HTTP请求本身不带seed。环境单game shuffle沿用TextWorld默认1234，Python/NumPy固定13；不保证跨GPU/kernel完全确定。CPU计划budget3是测试夹具，真实计划budget20，不混用。

**6任务×1个prefix=6个初始状态样本；真实LLM样本本阶段仍为0。** 不能解释成中途干预或时机研究。原base rollout仍完整执行后选第0点，以保留作者采集路径。原版预估最多240次正常模型请求仍适用，重试额外增加HTTP次数；不是GPU吞吐实测。

## 后续准备完成后的准确命令（本次未执行）

必须先由独立阶段准备服务环境和完整锁定模型文件。下列服务命令只接受已有本地snapshot，避免意外下载。若路径/环境缺失即停止，不自动安装或下载。模型和tokenizer的完整文件SHA256在实际准备后才可记录，不能用期望revision冒充已核验。

终端A（获得可用GPU时段后）：

```bash
set -euo pipefail
cd /home/hly/agent-research
CINC_MODEL_DIR=/home/hly/agent-research/data/hf-cinc/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
CINC_SERVER=/home/hly/agent-research/.venvs/cinc-vllm066/bin
CINC_SERVICE_DIR=/home/hly/agent-research/experiments/cinc_service_first
# 存在则停止，避免覆盖以前服务证据
test -f "$CINC_MODEL_DIR/config.json"
test -x "$CINC_SERVER/vllm"
mkdir "$CINC_SERVICE_DIR"
"$CINC_SERVER/python" -m pip freeze > "$CINC_SERVICE_DIR/server-freeze.txt"
unset OPENAI_API_KEY
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2
"$CINC_SERVER/vllm" serve "$CINC_MODEL_DIR" \
  --tokenizer "$CINC_MODEL_DIR" --served-model-name Qwen/Qwen2.5-7B-Instruct \
  --host 127.0.0.1 --port 18080 --dtype half \
  --max-model-len 8192 --max-num-seqs 1 --gpu-memory-utilization 0.60 \
  --seed 13 --enforce-eager > "$CINC_SERVICE_DIR/server-live.log" 2>&1
```

终端B（服务已经就绪后，先保存不可变启动证据，再跑适配器）：

```bash
set -euo pipefail
cd /home/hly/agent-research
source .venvs/cinc-audit-py310/bin/activate
unset OPENAI_API_KEY
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export ALFWORLD_DATA=/home/hly/agent-research/data/alfworld-cinc-audit
CINC_MODEL_DIR=/home/hly/agent-research/data/hf-cinc/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
CINC_SERVICE_DIR=/home/hly/agent-research/experiments/cinc_service_first
CINC_PLAN=/home/hly/agent-research/pilot_validity/plans/real_pilot_final/plan.json
curl -fsS --max-time 10 http://127.0.0.1:18080/health
# 日志在请求后会增长，因此保存固定的启动阶段副本
(set -o noclobber; cat "$CINC_SERVICE_DIR/server-live.log" > "$CINC_SERVICE_DIR/startup-frozen.log")
python -m pilot_validity.attest \
  --plan "$CINC_PLAN" --model-dir "$CINC_MODEL_DIR" \
  --startup-log "$CINC_SERVICE_DIR/startup-frozen.log" \
  --server-freeze "$CINC_SERVICE_DIR/server-freeze.txt" \
  --output "$CINC_SERVICE_DIR/attestation.json"
CINC_RUN_ROOT=$(mktemp -d /home/hly/agent-research/experiments/cinc_real_audited_XXXXXX)
python -m pilot_validity.run run \
  --plan "$CINC_PLAN" --backend http \
  --server-attestation "$CINC_SERVICE_DIR/attestation.json" \
  --output "$CINC_RUN_ROOT/collected" > "$CINC_RUN_ROOT/run.log" 2>&1
```

适配器内部完成冻结和评测，不再对结果调用按test_best选型的路径。已有输出目录将被拒绝；新增实验目录默认不被Git追踪，检查后才显式纳入版本管理。

服务证明是“操作者声明参数+本地权重/配置/tokenizer哈希+版本快照+启动日志”，不是服务器API对实际加载tensor身份的密码学证明。需要人工核对服务进程命令与启动日志；该限制不可通过填写attestation绕过。客户端禁止安装transformers后悄悄切换到completions；源码/依赖/数据变化将使冻结计划校验失败，应另版本明确审查，不能静默重冻。

## 真实Pilot验收

尝试数固定6，最终必须逐项报告有效数/无效数及原因。没有合法训练或验证配对则冻结被阻止；零有效测试配对的utility/regret为null，不能记0。即使存在有效子集，第一轮端到端验收也要求6/6通过；不补抽替代。分支结果需可由轨迹重算；original与corrected同时报告，不根据测试成绩决定保留哪一个。该轮最多证明真实模型工程链路工作，不能证明论文结论或长期决策方法有效。

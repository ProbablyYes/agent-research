# 回放验证与 CPU 回归测试结果

2026-10-16。最终实现修订 `70a3390`，分支 `pilot-validity-hardening`；原作者Commit `9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3`。版本指纹在 `pilot_validity/plans/real_pilot_final/plan.json` 的source_sha256中，完整执行证据在 `experiments/pilot_validity_cpu`。

## 已执行的回放检查

每个reset及每次历史动作后的状态均保存，Continue和Intervene分别在`replay_to_prefix`返回、应用新行动之前检查：

| 字段 | 比较方式 |
|---|---|
| observation | 完整字符串精确相等，不只去空白 |
| admissible_commands | 完整有序列表相等；顺序影响作者fallback行为 |
| done / won | Gym结果逐项比较，额外核对backend won/lost和预算终止一致性 |
| 已执行动作 | 回放动作逐条与原base动作比较，检查prefix历史长度 |
| remaining budget | H-执行动作数，并与Limit.max_episode_steps/nb_steps独立核对 |
| PDDL facts | 原生可访问facts转稳定字符串排序比较，不只观察文本 |
| 其他可访问字段 | moves、backend won/lost、last_command、entity_names、wrapper stack |
| prefix对象 | 观察、合法动作、历史观察和动作与原录制轨迹核对 |

**缺少必需的状态字段时失败关闭**；不把“读不到”当相等。环境完整内部状态、native planner内存及全部RNG没有导出，审计通过仍不是完整等价证明。

## 最终运行结果

[执行] `regression_final.log`：**25项测试通过，0项失败，165.378秒**。包含17项基础单元测试、5项真实环境测试、3项服务来源保护测试。服务来源测试使用临时Synthetic占位文件，没有真实权重或服务。

[执行] 非初始Checkpoint测试采用固定Synthetic动作、真实ALFWorld环境、H=4、Checkpoint=2；原录制状态及两分支重放均覆盖reset、step1、step2，共3个状态。Continue和Intervene均匹配；该任务step2可读取506条PDDL facts，moves=2，剩余预算2。**非初始测试仅验证审计器，不改变真实Pilot只采初始状态的方案。**

[执行] 故意将prefix观察替换为`INTENTIONALLY WRONG`后，两分支审计都失败，原始row、全部观察/状态差异和后续分支结果保留在 `regression_final/real_checkpoint_records.json` 的 `injected_mismatch`。该记录valid_pair=false，不进入有效配对指标。

[执行] 故意将保存的u_continue增加.5，独立重算检出差异并判无效。另有observation、command列表、done/won、步数、预算、隐藏fact、缺失字段和中间历史状态错配的单元测试。作者原始未包装build_rows在相同候选prefix、相同Synthetic模型下的完整row与包装版本相等；上下文退出后原函数引用恢复，原仓库保持干净。

[执行] 最终六任务端到端运行 `run_final`：train2/2、val2/2、test2/2配对有效，合计6/6；每配对Continue+Intervene共12条分支，budget3、prefix0。独立从落盘JSON和作者格式CSV重读，核对won、suffix steps、固定干预成本、步数成本与utility，**12/12一致**。这是Synthetic固定动作的工程验证，不是真实Agent Pilot。

[执行] 无效分母回归：构造2条记录其中1条无效，attempted=2、valid=1、invalid=1、coverage=.5；策略指标n=1。两条都无效时n=0、utility/regret=null。没有合法train/val时冻结报错，不补样本。

## 原 Smoke Test 复用与失败记录

[执行] 旧smoke.py完整重跑，**6个顶层检查全部PASS**，包括三个split的真实reset/step/replay/expert。唯一改动是独立副本中的OUT路径，变换及原脚本SHA256保存在 `reused_smoke/provenance.json`；原脚本及原输出不变。该组不是25项unittest的重复计数。

第一轮回归20/20通过；增加原版原始行对照和局部常数模型序列化后第二轮22/22通过；加入服务来源保护后最终25/25通过。不是筛选性报告：早期全部日志保留。

第一轮端到端 `run_v1` 在模型保存时失败：`AttributeError: Can't pickle local object ...ConstantProbabilityModel`。退出发生在test前；没有替换失败样本。用cloudpickle修复我方保存器后，在相同清单上重跑v2和final，均6/6有效。v1部分输出与错误日志仍在；不是删除失败后声称首次通过。

TextWorld日志含未关闭gamefile的ResourceWarning，为上游行为，未修改核心实现规避。此前pip check元数据问题仍未解决。

## 实际命令

以下均在 `/home/hly/agent-research` 执行，未调用GPU或真实模型：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13 \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
CINC_TEST_OUTPUT=/home/hly/agent-research/experiments/pilot_validity_cpu/regression_final \
.venvs/cinc-audit-py310/bin/python -m unittest discover -s tests/pilot_validity -v

PYTHONDONTWRITEBYTECODE=1 .venvs/cinc-audit-py310/bin/python \
  -m pilot_validity.run prepare --synthetic --output experiments/pilot_validity_cpu/plan_final

PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13 \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
.venvs/cinc-audit-py310/bin/python -m pilot_validity.run run \
  --plan experiments/pilot_validity_cpu/plan_final/plan.json \
  --output experiments/pilot_validity_cpu/run_final --backend synthetic

PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13 \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
.venvs/cinc-audit-py310/bin/python \
  experiments/pilot_validity_cpu/reused_smoke/smoke_output_redirect_only.py

PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13 \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=/home/hly/agent-research .venvs/cinc-audit-py310/bin/python \
  tests/pilot_validity/verify_artifacts.py
```

执行时stdout/stderr分别重定向到同目录 `regression_final.log`、`run_final.log`、`reused_smoke.log`、`artifact_verification.log`。现有plan/run目录禁止覆盖；重新运行请另建带版本号目录，不能删除这批证据。

## 未解决限制

有效=在规定导出字段上通过一致性和成本检查，不等于已证明可靠因果分叉。不同数据集版本或TextWorld内部结构变化必须重新审查；hash校验会阻止沿用旧冻结计划。随机native环境、跨GPU确定性、真实模型响应及服务兼容性没有本阶段证据。完整真实Pilot命令和No-Go条件见 [REAL_PILOT_GO_NO_GO.md](REAL_PILOT_GO_NO_GO.md)。

## 旧五模式补测

[执行] 上一阶段extra_checks.py也已完整复用，只有独立副本OUT路径变化（记录在reused_extra/provenance.json）。五种干预模式各2行、恢复匹配均2/2；作者原始故意错配仍保留1行、匹配0，说明原baseline问题未被静默修正。输出位于 `experiments/pilot_validity_cpu/reused_extra/extra_results.json`，日志 `reused_extra.log`。此组额外执行不计入25项新回归测试。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13 \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
.venvs/cinc-audit-py310/bin/python \
  experiments/pilot_validity_cpu/reused_extra/extra_output_redirect_only.py
```

原作者CSV采用CRLF。普通git diff --check将CR视作行尾空白；为保留原始字节未重写CSV，使用 `git -c core.whitespace=cr-at-eol diff --cached --check` 后通过。源代码AST检查7个文件通过；该格式提示不是实验失败。

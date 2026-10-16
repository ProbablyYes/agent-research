# 零收费 Smoke Test

2026-10-16。所有测试位于仓库外 `/home/hly/agent-research/experiments/cinc_smoke_20261016`。没有真实LLM调用、模型权重下载或GPU计算。使用原实现直接导入，无baseline修改。

## 已执行结果

| 检查 | 结果与范围 |
|---|---|
| 源码语法 | PASS：6个Python源码文件AST解析，无仓库内pyc写入 |
| 指定依赖导入 | PASS：numpy2.2.6、sklearn1.7.2、alfworld0.4.2、textworld1.7.0 |
| 项目导入 | PASS：三个实现模块、两个CLI模块 |
| pip check | FAIL：TextWorld wheel元数据Tag行前空行，header解析Tag为空；实际导入/环境执行通过，未改包元数据 |
| ALFWorld数据枚举 | PASS：作者过滤规则下3553 train、140 valid_seen、134 valid_unseen |
| ALFWorld reset与step | PASS：每split各1个任务，合计3个，返回合法命令、reward、done、won |
| 实际历史回放 | PASS：3个一步prefix观察文本、可行动作、done/won均一致 |
| 实际专家分支 | PASS：3个任务从一步prefix执行环境planner，后续6/7/6步成功；不是LLM成绩 |
| Synthetic训练/评估 | PASS：48 train、24 val、24 test，failure及四类控制器，两种preview模式 |
| 指标手算 | PASS：Synthetic always-continue utility=-.05，success=.5，regret=.755 |
| 固定种子重复 | PASS：完整analyze_run_dir重复结果相同 |
| 特征维数 | PASS：base/no_preview=26，with_preview=47 |
| 未来字段输入排查 | PASS：固定特征后改u_*、correct、未来branch_steps，输入矩阵不变；静态路径亦未读这些字段 |
| LCB公式 | PASS：std等于逐棵树正类概率的numpy总体标准差；单类常数模型std=0 |
| 原作者evaluate CLI | PASS：Synthetic目录实际运行完成，生成controllers-cli.json |

Synthetic数据按四种(continue won,intervene won)组合均匀构建；continue步数5、intervene步数3，成本.01/.05，错误惩罚1。四种oracle效用为.95/.92/0/.95，always-continue效用为.95/-1.05/-1.05/.95；故regret=(0+1.97+1.05+0)/4=.755。**首次测试脚本错误地写成.535，导致断言失败；仅修正本轮独立测试期望值后通过。** 原始日志smoke.log及results-first.json保留，不能把这个自写测试错误归咎论文。

## 可复现逻辑反例（没有修复）

- 成功概率1、continue实际20步：显式EU输出1.0，按作者utility函数实际为.8；说明EU决策缺步数成本，并非提前读取未来长度。
- 所有risk score=0且continue全成功：failure threshold search最佳仍全quit，utility0、regret1；网格无最大分数以上阈值，无法表达always-continue。
- 未被CLI使用的cost-sensitive helper：固定类别概率[.30,.25,.45]，测试行continue=1、verify=-1.05、quit=0；阈值搜索选0并报告utility1，但同阈值应用走三类argmax选quit、utility0。

证据：[results.json](../experiments/cinc_smoke_20261016/results.json)、[smoke-corrected.log](evidence/smoke-corrected.log)、[原始首次日志](evidence/smoke.log)。Synthetic模型效用不能当论文复现结果。

## 重跑与随机性

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13 \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/home/hly/agent-research/.venvs/cinc-audit-py310/bin/python \
/home/hly/agent-research/experiments/cinc_smoke_20261016/smoke.py
```

此命令会重写本轮专用smoke/SYNTHETIC结果，不写论文仓库或原数据。首次运行日志独立保留。测试固定Python random、NumPy seed/default_rng=13，模型RF沿用作者内部固定种子；CPU线程限制1。完整真实环境测试需要数分钟，任务扫描及环境初始化显著占时。

作者采集seed只作用于局部任务shuffle与expert噪声；没有全局Python/NumPy/environment/API完整seed协议。已保存task_manifest.json及env_records.json；同机器本轮一致不代表跨系统/模型严格可重复。

## 范围限制

真实模型prefix数为0；没有证明任何模型性能、校准提升或干预收益。实际环境测试只涉及3个任务和后续补充的短分支路径。没有全量恢复一致性验证，没有模拟付费API，也没有用实际GPU请求估计时间。原仓库最终git状态检查用于确认核心实现未改。

## 补充执行证据

[执行] `extra_checks.py` 用明确标注SYNTHETIC POLICY的固定文本生成器驱动**真实ALFWorld**，没有构造LocalChatModel、没有HTTP请求。H=3、同任务两个prefix实际索引[0,2]。expert_defer、llm_verify、self_reflect_retry、self_replan、self_plan_replan五种模式各生成2行，continue恢复匹配均2/2。步数分别3和1，continue效用-1.03/-1.01，intervene效用-1.08/-1.06，验证环境总步数预算包含回放。因固定动作和3步预算，分支全失败是预期的路径测试结果，不是模型性能失败。

[执行] 将prefix.observation改成明确错误字符串，原build_rows仍返回1行，replay匹配计数0；证明不一致样本没有被拒绝。所有变更仅在内存构造的测试输入，未改baseline。

[执行] 全部可用任务按父目录trial ID比较，三对split交集均0；不代表语义任务/房间独立。评测CLI输出与函数调用结果逐项完全相同。

证据：[extra_results.json](../experiments/cinc_smoke_20261016/extra_results.json)、[extra-checks.log](evidence/extra-checks.log)。补测重跑命令与主测试相同环境变量，将脚本替换为 `extra_checks.py`；需先有task_manifest.json。

[执行] 最终git status --porcelain为空，HEAD仍为锁定commit。未在仓库内创建测试文件或改动核心逻辑。结束检查时GPU约34287MiB、100%负载，是本轮CPU测试之外的活动；未干预该活动，不能沿用开始时空闲状态安排推理。

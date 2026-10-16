# Pilot 实验可信性加固

日期：2026-10-16，Asia/Shanghai。范围限于已有ALFWorld工程Pilot，不开发P3/P4新算法。

## 版本、隔离和证据等级

- 原作者仓库：`/home/hly/agent-research/calibration-is-not-control`，Commit `9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3`。不修改、不checkout其他版本。
- 我方研究仓库：`/home/hly/agent-research`；从 `ff53c120113166c25fd42f0e474b5c17e3693584` 创建独立分支 **pilot-validity-hardening**。实现提交 `d10aca3`、最终实现修订 `70a3390`；后续报告/证据提交不会改变算法源文件。
- 代码：[pilot_validity](../pilot_validity/README.md)，测试：[tests/pilot_validity](../tests/pilot_validity/)。已有报告和 `experiments/cinc_smoke_20261016` 的文件不改；所有新增输出在 `experiments/pilot_validity_cpu`。
- **[执行]** 为真实CPU运行；**[源码]** 为调用路径或代码推论；**[未核验]** 为未运行的真实LLM/更广泛环境结论。Synthetic策略结果不是真实模型成绩。

## 改动分类

| 改动 | 分类 | 是否改变作者原始决策逻辑 |
|---|---|---|
| 环境reset/step记录、逐步回放核对、双分支行动前审计 | 实验验证 | 否，调用原函数；局部包装退出即还原 |
| 用真实状态轨迹独立重算won、suffix步数、成本和utility | 实验验证 | 否；不同则标无效，不改作者原始row |
| 保留原始CSV、所有错配、异常、逐步事件 | 实验验证 | 否；不替换、不补抽失败样本 |
| 有效配对筛选与独立分母 | **评估协议修正** | 变化仅作用于单独标注的valid_pairs结果；不覆盖original_raw |
| 完整阈值边界及所有验证分数断点 | **方法性修正/更完整搜索** | 是，单列corrected；原版original同时保留 |
| Always Continue/Intervene/Quit | 固定策略对照 | 不学习、不按测试结果选赢家 |
| 冻结训练模型/验证阈值，取消test_best选型 | 防泄漏实验协议 | 测试只应用冻结规则；不重写作者文件 |
| 固定6任务清单、文件/源代码/依赖哈希、prompt与接口 | 实验协议 | 固定采样顺序；不再依赖新一次os.walk顺序 |
| 分任务持久化、关闭环境、cloudpickle保存局部常数模型 | 工程修正 | 不改变模型预测或分支行动 |

显式EU保持作者公式，没有额外开发成本预测器；不能把真实未来suffix长度送入决策。已观察的prefix sunk cost单列，suffix cost只在完成后评估，LLM请求/响应虽留档，但费用和延迟没有进入utility。

## 调用与输出

`run.py`仍调用原 `rollout_base_prefix_candidates` 和 `build_rows`。`AuditSession`只在进程内临时替换这两个函数所用的环境factory及`replay_to_prefix`引用，不编辑原源码。录制原base轨迹，然后分别在Continue/Intervene的replay返回处、首个新行动前比较状态。干预限定expert_defer，默认no_preview；不会把这些实现泛称为支持全部未来干预。

每个Checkpoint产生原row、副本、两分支全轨迹、逐项差异、独立重算结果和有效标志。异常也单独落盘；events.jsonl逐事件flush，方便诊断未完成任务。若回放错配，保留作者后续原始分支执行及结果，但不能进入valid_pairs。执行异常可没有完整row，仍占attempted分母，不重新抽任务。

- `original_raw/*_rows.csv`：原作者行格式，未覆写旧CSV。
- `*_records.json`及每任务JSON：原始行与审计证据分离。
- `frozen_controls_before_test.json` / `frozen_models_before_test.pkl`：进入test前冻结；pickle仅为本项目自己生成的可信本地模型，不读取外来pickle。
- `summary.evaluation.valid_pairs`：相同有效集合上的original、corrected及简单策略。
- `summary.evaluation.original_raw`：原作者未过滤参考；显式标记 **UNFILTERED AUTHOR REFERENCE ONLY**，单列raw_rows_evaluated、audit_valid/audit_invalid，禁止当作可靠配对证据。

原作者failure的完整指标另外保存为author_metrics，并与我方独立utility/regret计算核对。未使用测试收益择优家族或阈值。

## 本阶段发现并保留的失败

[执行] 第一轮 `run_v1` 在训练/验证采集后、测试前因作者单类别模型的局部类不能被标准pickle保存而退出。原始日志、部分模型文件、四条已采集记录均保留。修正仅使用环境已存在的cloudpickle并增加序列化回归测试，之后 `run_v2` 完成6任务。最终复核使用相同6任务，未根据结果改任务或收益参数。

[执行] TextWorld自身有未关闭文件的ResourceWarning，保留在测试日志；此前pip check的wheel metadata异常未静默修复。原有EU步数成本遗漏、专家Oracle属性仍存在并明确标记。

## 限制

这是一个六初始状态工程Pilot的审计适配器，不是在线闭环或中途干预实验。隐藏native planner、底层内存状态及全部RNG不能完整导出，`native_state_equivalence_proven=false`。即使导出的PDDL facts和所有可观察字段相同，也只称“可访问状态一致性审计通过”，**不称可靠因果分叉**。发生无效配对时，条件在通过审计的子集上的指标可能有选择偏差；不将其解释为全任务无偏估计。

## 最终验证指纹

[执行] `experiments/pilot_validity_cpu/isolation_integrity.json`保存最终实现完整Commit、7个适配器/测试文件SHA256和旧实验完整性比较。原作者所有上一轮已哈希文件逐字节不变；旧五份报告及原Smoke输出相对ff53c12无差异。最终25项回归通过、复用Smoke的6项通过，最终6/6配对和12/12实际分支成本读回核验通过。真实模型仍未运行；第一次真实Pilot的准确命令、服务准备缺口及限制统一见 [REAL_PILOT_GO_NO_GO.md](REAL_PILOT_GO_NO_GO.md)。

[执行补充] 上一阶段五模式extra_checks也完整重跑通过，并保留原版回放错配反例；详见REPLAY_VALIDATION_RESULTS的补测节。

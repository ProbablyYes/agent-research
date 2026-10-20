# API 真实 Agent 工程 Pilot：完成

2026-10-20，Asia/Shanghai。模型OFOX `openai/gpt-4o-mini`，代码Commit `da6a99e9e4317069de9a03303beaaedda14dcacf`。后端权重/服务revision不可证明，不能冒充Qwen2.5-7B复现。

## 授权和执行边界

此前阶段A因账单上界未证实停止；负责人随后明确要求继续并接受预算不确定性。本轮以**名义目录价预算**执行，reliable_billing_bound仍为false，未伪造价格/模型attestation。授权记录及原账本前后快照见 `reports/evidence/api_authorized_20261020/authorization.json`。同一round_id和账本持续使用，没有清空次数或费用。此前阻断报告完整副本在该目录prior_reports/。

## 实际执行

- Smoke：20环境步，成功=False，协议通过=True，停止原因=budget_exhausted。自然轨迹，不产生反事实分叉。
- Pilot：execution_complete=True；已保存配对6，有效6、无效0；行动前审计12/12通过。
- 实际不同任务实例6个；Smoke复用第一训练任务，不是另抽第7个实例。环境轨迹数19（包括Smoke/base/Continue/Oracle）；总环境步304。
- 请求预留/尝试260，完整成功返回260，未决0；输入112142、输出2141 Token；估算USD0.01810590，实际账单未核验。
- 本轮正常完成，未触发异常停止；没有扩大任务、模型或预算，没有GPU或模型下载。

| 实例 | Split | 配对有效 | Continue成功/步数/U | Oracle Intervene成功/步数/U |
|---|---|---|---|---|
| trial_T20190908_022321_380927 | test | True | False / 20 / -1.200 | True / 7 / 0.880 |
| trial_T20190909_064053_839817 | test | True | False / 20 / -1.200 | True / 8 / 0.870 |
| trial_T20190907_224507_776787 | train | True | False / 20 / -1.200 | True / 7 / 0.880 |
| trial_T20190909_151853_245524 | train | True | False / 20 / -1.200 | True / 7 / 0.880 |
| trial_T20190908_033721_967359 | val | True | False / 20 / -1.200 | True / 7 / 0.880 |
| trial_T20190908_164236_518264 | val | True | False / 20 / -1.200 | True / 8 / 0.870 |


## 冻结策略的测试集结果

以下只使用有效测试配对。original保留作者阈值搜索；corrected使用此前已审计的完整边界。Always策略并列。不是选择测试集赢家；不得据此声称P3/P4算法改进。

| 冻结策略 | n | 平均U | 成功率 | Regret | 干预率 | Quit率 |
|---|---:|---:|---:|---:|---:|---:|
| original | 2 | 0.0 | 0.0 | 0.875 | 0.0 | 1.0 |
| corrected | 2 | 0.875 | 1.0 | 0.0 | 1.0 | 0.0 |
| always_continue | 2 | -1.2 | 0.0 | 2.075 | 0.0 | 0.0 |
| always_verify | 2 | 0.875 | 1.0 | 0.0 | 1.0 | 0.0 |
| always_quit | 2 | 0.0 | 0.0 | 0.875 | 0.0 | 1.0 |
| original_explicit_eu | 2 | 0.875 | 1.0 | 0.0 | 1.0 | 0.0 |


训练/验证/测试仍为原2/2/2，六个Prefix均为初始状态0。冻结事件位置697，首个test任务事件位置698；由持久化事件独立检查先后。冻结模型/阈值文件在Pilot输出目录；原始未过滤参考另存original_raw与summary.evaluation.original_raw，不覆盖valid_pairs。

## 实现与验证

原作者文件及本地Qwen计划保持不变。独立collect.py复用AuditSession、paired_record、freeze_baselines、evaluate_frozen，严格ACTION与confidence解析替换仅发生在进程内，退出恢复原函数。动作不合法、协议异常、环境异常均停止整轮，不fallback或补样。原始输出、prompt、环境反馈和全部审计事件保留。

离线证据：42项API/集成测试通过（197.308秒，包括Mock六任务12分支）；4项结算测试通过（2.719秒）；授权变更定向复测通过。以前CPU回放/成本/分母测试成果保留。本轮读回核对所有已完成分支的won、suffix steps、成本与utility；请求账本、事件Usage及响应文本逐项一致，详见results_verified.json。原版显式EU继续遗漏未来step成本，没有把未来真实长度输入部署策略。另独立读回CSV重算12条分支，与JSON一致；12组回放快照直接比较相等；从CSV重新训练原版failure并仅用val选阈值，其测试指标与保存结果完全一致（extended_checks.json）。

## 实际命令

运行时固定PYTHONDONTWRITEBYTECODE=1、PYTHONHASHSEED=13、OMP_NUM_THREADS=1、OPENBLAS_NUM_THREADS=1、MKL_NUM_THREADS=1，解释器为`.venvs/cinc-audit-py310/bin/python`：

```bash
python -m api_pilot.authorize
python -m api_pilot.collect smoke
python -m api_pilot.collect pilot
python -m api_pilot.export experiments/api_agent_round_20261020/smoke
python -m api_pilot.export experiments/api_agent_round_20261020/pilot
```

这些阶段已经执行；输出目录存在会拒绝重跑。不要删除账本或输出后再试。完整命令日志见reports/evidence/api_authorized_20261020/。

## 工程判定

本次六任务工程验收通过（Go）：完整采集、有效配对、成本读回、冻结顺序和文件隔离均通过。当前已停止全部生成请求；这不自动授权扩大实验。

## 结论边界

这是端到端工程验证，仅6个初始Prefix；不是中途干预时机研究，也不是论文完整复现。expert_defer调用环境Oracle Planner，是能力上界，不是普通LLM交接。可访问状态一致不等于native隐藏状态或完整因果状态等价。单次分支回报并非真实期望价值，极小train/val/test不可支持总体统计。P1/P2/P5与新猜想独立保留，本轮没有新算法开发。已停止，等待科研分析。

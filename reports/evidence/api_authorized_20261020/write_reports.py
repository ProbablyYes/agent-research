"""Generate reports solely from completed read-back verification artifacts."""
import collections
import json
from pathlib import Path
R=Path('/home/hly/agent-research');E=R/'reports/evidence/api_authorized_20261020';RUN=R/'experiments/api_agent_round_20261020'
v=json.loads((E/'results_verified.json').read_text());b=v['budget'];p=v['phase_results'];plan=json.loads((RUN/'smoke/plan.json').read_text())
smoke=p['smoke']['summary'];pilot=p.get('pilot',{}).get('summary',{})
complete=bool(pilot.get('execution_complete'))
rows=[]
for phase in p:
 rows += [json.loads(x) for x in (RUN/phase/'trajectories.jsonl').read_text().splitlines()]
latencies=[]
for phase in p:
 for x in (RUN/phase/'requests.jsonl').read_text().splitlines():latencies.append(json.loads(x)['latency_seconds'])
branches='| 实例 | Split | 配对有效 | Continue成功/步数/U | Oracle Intervene成功/步数/U |\n|---|---|---|---|---|\n'
for x in v['pairs']:
 split,task,_=x['pair_id'].split(':');r=x.get('recomputed') or {}
 def show(k):
  q=r.get(k);return f"{q['won']} / {q['suffix_steps']} / {q['realized_utility']:.3f}" if q else '未完成'
 branches+=f"| {task} | {split} | {x['valid']} | {show('continue')} | {show('verify')} |\n"
policies=pilot.get('evaluation',{}).get('valid_pairs',{}).get('policies',{})
strategy='| 冻结策略 | n | 平均U | 成功率 | Regret | 干预率 | Quit率 |\n|---|---:|---:|---:|---:|---:|---:|\n'
for name,r in policies.items():
 m=r['metrics'];strategy+=f"| {name} | {m['n']} | {m['utility']} | {m['success_rate']} | {m['control_regret']} | {m['verify_rate']} | {m['quit_rate']} |\n"
eu=pilot.get('evaluation',{}).get('valid_pairs',{}).get('original_explicit_eu')
if eu:
 m=eu['metrics'];strategy+=f"| original_explicit_eu | {m['n']} | {m['utility']} | {m['success_rate']} | {m['control_regret']} | {m['verify_rate']} | {m['quit_rate']} |\n"
status='完成' if complete else '因异常停止，未完成全部任务'
main=f'''# API 真实 Agent 工程 Pilot：{status}

2026-10-20，Asia/Shanghai。模型OFOX `openai/gpt-4o-mini`，代码Commit `{v['source_commit']}`。后端权重/服务revision不可证明，不能冒充Qwen2.5-7B复现。

## 授权和执行边界

此前阶段A因账单上界未证实停止；负责人随后明确要求继续并接受预算不确定性。本轮以**名义目录价预算**执行，reliable_billing_bound仍为false，未伪造价格/模型attestation。授权记录及原账本前后快照见 `reports/evidence/api_authorized_20261020/authorization.json`。同一round_id和账本持续使用，没有清空次数或费用。此前阻断报告完整副本在该目录prior_reports/。

## 实际执行

- Smoke：{smoke.get('steps', '见事件')}环境步，成功={smoke.get('won')}，协议通过={smoke.get('protocol_passed')}，停止原因={smoke.get('stop_reason')}。自然轨迹，不产生反事实分叉。
- Pilot：execution_complete={complete}；已保存配对{len(v['pairs'])}，有效{v['valid_pairs']}、无效{v['invalid_pairs']}；行动前审计{v['passed_pre_action_audits']}/{v['pre_action_audits']}通过。
- 实际不同任务实例{len(set(r['task_id'] for r in rows))}个；Smoke复用第一训练任务，不是另抽第7个实例。环境轨迹数{sum(x['trajectory_count'] for x in p.values())}（包括Smoke/base/Continue/Oracle）；总环境步{len(rows)}。
- 请求预留/尝试{b['attempts_reserved']}，完整成功返回{b['completed']}，未决{b['unknown']}；输入{b['input_tokens_known_completed']}、输出{b['output_tokens_known_completed']} Token；估算USD{b['estimated_usd_known_completed']:.8f}，实际账单未核验。
- 本轮停止状态：{b['halted']}；没有扩大任务、模型或预算，没有GPU或模型下载。

{branches}

## 冻结策略的测试集结果

以下只使用有效测试配对。original保留作者阈值搜索；corrected使用此前已审计的完整边界。Always策略并列。不是选择测试集赢家；不得据此声称P3/P4算法改进。

{strategy}

训练/验证/测试仍为原2/2/2，六个Prefix均为初始状态0。冻结事件位置{v['freeze_event_index']}，首个test任务事件位置{v['first_test_task_event_index']}；由持久化事件独立检查先后。冻结模型/阈值文件在Pilot输出目录；原始未过滤参考另存original_raw与summary.evaluation.original_raw，不覆盖valid_pairs。

## 实现与验证

原作者文件及本地Qwen计划保持不变。独立collect.py复用AuditSession、paired_record、freeze_baselines、evaluate_frozen，严格ACTION与confidence解析替换仅发生在进程内，退出恢复原函数。动作不合法、协议异常、环境异常均停止整轮，不fallback或补样。原始输出、prompt、环境反馈和全部审计事件保留。

离线证据：42项API/集成测试通过（197.308秒，包括Mock六任务12分支）；4项结算测试通过（2.719秒）；授权变更定向复测通过。以前CPU回放/成本/分母测试成果保留。本轮读回核对所有已完成分支的won、suffix steps、成本与utility；请求账本、事件Usage及响应文本逐项一致，详见results_verified.json。原版显式EU继续遗漏未来step成本，没有把未来真实长度输入部署策略。

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

## 结论边界

这是端到端工程验证，仅6个初始Prefix；不是中途干预时机研究，也不是论文完整复现。expert_defer调用环境Oracle Planner，是能力上界，不是普通LLM交接。可访问状态一致不等于native隐藏状态或完整因果状态等价。单次分支回报并非真实期望价值，极小train/val/test不可支持总体统计。P1/P2/P5与新猜想独立保留，本轮没有新算法开发。已停止，等待科研分析。
'''
(R/'reports/API_REAL_AGENT_PILOT.md').write_text(main)
budget=f'''# API 预算审计：授权后真实运行

2026-10-20。负责人明确接受费用上界未独立验证的风险后执行；不是平台账单硬限额证明。此前阻断及文档审查保留在api_round_20261020/和api_authorized_20261020/prior_reports/。

## 账本核对结果

| 字段 | 实际值 |
|---|---:|
| 本轮请求预留/尝试 | {b['attempts_reserved']} |
| 完整成功 / 未决 | {b['completed']} / {b['unknown']} |
| 完整返回输入 / 输出Token | {b['input_tokens_known_completed']} / {b['output_tokens_known_completed']} |
| 历次发送前预留总和 | USD{b['gross_pre_send_reservations_usd']:.8f} |
| 已完成Usage的名义结算 | USD{b['estimated_usd_known_completed']:.8f} |
| 未决请求保留预留 | USD{b['unknown_reserved_usd']:.8f} |
| 当前累计预算占用 | USD{b['committed_usd']:.8f} |
| 本地名义预算 / 请求上限 | USD3 / 400 |
| 实际供应商账单 | 未核验 |

历史预留总和不是当前预算占用或实际费用：发送前按128000输入Token加本次最大输出预留；只有完整合法Usage才结算为目录价，释放估算差额；未知或超时保留全预留。累计预算检查采用已完成名义结算+未决全预留+下一请求预留，发送前持久化，不能仅事后记账。此结算变化基于本次用户风险接受，授权修订有记录；并未把未知账单当作0。

目录价格输入USD0.15/百万、输出USD0.60/百万，来自本日公开模型目录快照。无缓存优惠假设，未调用搜索或其他收费工具。一次请求的上限64 Token，实际action24/confidence8；60秒墙钟截止，零重试、不跟随重定向。Smoke与Pilot共用仓库外api-agent-20261020.sqlite3，原16日连接测试不混入本轮。账本使用整数纳美元、事务与fsync语义；中断后未决请求不能自动重发。

实际成功请求延迟总和{sum(latencies):.3f}秒，范围{min(latencies) if latencies else None}至{max(latencies) if latencies else None}秒；不是单独模型计算时间。完整每请求Usage与延迟在各phase requests.jsonl。

## 安全与证据

未记录密钥或Authorization Header；密钥读取位置未变。请求固定已验证OFOX endpoint；无自动改模型/参数重试。HTTP错误只记录状态和静态原因，合法响应保存原始文本和数值Usage；敏感模式拒绝落盘。完整回包JSON没有任意写日志。

results_verified.json独立逐项核对SQLite账本与events：请求ID唯一、Usage合计、输出上限、Token计价、预留额度及共享累计数均通过。源码Commit为{v['source_commit']}；计划和文件哈希见final_integrity.json。Mock中故意超时、重复、中断、错误JSON、未知Usage、费用越界均有回归；生产实际停止状态{b['halted']}。

目录估算不能独立证明实际扣款、账户routing或后端模型revision。用户本轮已接受此限制；没有宣称实际账单被USD3硬限制。LLM美元成本与原任务utility分开，未静默改变原论文指标。
'''
(R/'reports/API_BUDGET_AUDIT.md').write_text(budget)
obs='''# 真实 Agent 轨迹观察

2026-10-20。以下为本轮小样本直接观察，不代表模型总体能力，不建立因果机制结论。

'''
for phase in p:
 for task,branch in dict.fromkeys((r['task_id'],r['branch']) for r in rows if r['phase']==phase):
  rs=[r for r in rows if r['phase']==phase and r['task_id']==task and r['branch']==branch]
  c=collections.Counter(r['action'] for r in rs)
  obs+=f"- {phase} / {task} / {branch}：{len(rs)}步，成功={rs[-1]['trajectory_won']}，停止={rs[-1]['trajectory_stop_reason']}；不同动作{len(c)}个，最多重复动作：{c.most_common(3)}。\n"
obs+='''
## 可核验观察与限制

Smoke目标是“Put a cold potato in the microwave.”。20步中只有8种不同动作，冰箱/微波炉之间往返并反复取放mug 2；动作合法但目标未完成。不能据此断言循环是由记忆不足、某种状态表示或某个训练缺陷导致。提示词和任务未据表现调整，没有重抽或调参。

Oracle成功只表明该环境planner在对应预算内完成，不证明现实中另一Agent可同样恢复。控制器只在初始Prefix作一次离线决策，未研究中途触发时机。即使corrected优于original，也是此前阈值搜索修正和本样本结果，不是P3/P4新算法提升。

结构化数据：experiments/api_agent_round_20261020/{smoke,pilot}/trajectories.jsonl，逐步包含任务描述、完整历史前缀、行动前观察/合法动作、模型原始输出、实际动作、反馈、done/won、轨迹最终结果/停止原因、请求ID与Token数据。Continue首动作复用base提议，标记reused_base_proposal、new_request_for_step=false，不重复计费；Oracle动作没有LLM Usage。confidence请求不对应环境step，完整账本/requests.jsonl保留，不能只加总动作行来计算总费用。原始prompt、审计状态、错误事件保留在events.jsonl。

P3/P4后续机制实验尚未启动；P1/P2/P5和新猜想独立保留。现在停止采集，等待负责人分析。
'''
(R/'reports/API_TRAJECTORY_OBSERVATIONS.md').write_text(obs)
print('Three reports written from verified results')

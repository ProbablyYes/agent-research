"""Render evidence-led reading guides; handcrafted notes, no automated root-cause labels."""
import pathlib,json,csv,collections,statistics,hashlib
P=pathlib.Path(__file__).resolve().parents[1];ROOT=P.parents[1];R=ROOT/'reports';m=json.load(open(P/'PHASE2_SAMPLE_MANIFEST.json'));rows=list(csv.DictReader(open(P/'PHASE2_TRAJECTORY_INDEX.csv')));rowmap={x['task_id']:x for x in rows};frags=json.load(open(P/'evidence/decision_fragments.json'))
# IDs/events selected only for reading; never alter the frozen sample.
notes=[
('task_060','先关闭账户，再处理另一目标',[28,33,34,35,37,38,53,54,59], '用户在 E34 要求先关户；E35 执行关闭，E38 再提出储蓄需求，E53/59 给出选择及未来开户安排；最终 DB reward=0。','是否存在跨目标前提约束，是否应在不可逆操作前查清后续计划？先核对政策和用户许可；不能由先后顺序断言关户造成失败。'),
('task_069','产品组合、先行执行与资格反馈',[24,49,65,70,72,76,78,79,90,100,106], 'E70 关原账户，E76 新开支票账户，E78 储蓄开户在 E79 返回资格不足；随后继续查证，用户另行申请信用卡。','失败可能涉及资格、组合选择或时序；仅有一条执行路径，不能认定提前关户就是根因。开放比较延迟执行、澄清、补充查证等候选。'),
('task_045','清偿准备与目标转向',[27,31,38,42,46,50,62,74,76], '开始请求关信用卡；E42 从支票账户清偿余额，之后讨论保留优惠；E74 应用信用额度补偿，E76 明确账户仍开着。发布 DB reward=1。','字面最初目标与最终用户选择不同。准备行动的价值取决于随后路径；不能把“未关户”自动判失败，也不能从通过评分得出客户长期受益。'),
('task_049','多个子目标具有不同前提',[31,37,41,49,51,57,71,73,83,85,99,113,117], '四卡关闭任务中，出现替换卡运输状态、余额不足、保留优惠等不同分支；实际关闭一张，应用补偿后交接；DB reward=1。','子任务不是可互换的动作计数。反复读取也可能是在核对用户新声明；不能把每次读取算浪费。未观察后续人类处理与用户收益。'),
('task_026','用户授权操作与 Agent 更新交织',[33,39,41,44,49,55,62,65,95,105,107], 'E33 一次提供多个用户可用操作，随后转为逐项提供；用户提交、Agent 查询/更新、再确认。结束时描述五项已更新，DB reward=0。','合作双方动作、事务粒度和最终状态是否一致需逐项核对。完成声明不是最终正确性的证明；评分失败也不能确定是哪一次用户操作引起。'),
('task_037','用户侧参数错误后仍成功',[44,48,57,58,59,60,64,67], '更换卡与争议处理交织；E57 用户工具调用在 E58 缺参数，E59 用户改参数，之后 Agent 提交两项争议；DB reward=1。','修正主体是用户模拟器。成功是“出现错误即失败”的反例；尚不清楚真实用户是否能做同样修正。'),
('task_064','同批调用错误与后续修改',[7,10,11,12,13,14,30,37,38,57,59], 'E10–12 三个 shell 返回都报告不接受 timeout 参数；E13 的调用去掉该参数并获得输出。后续产品组合、用户申请与开户完成，DB reward=1。','三条错误来自先前一批调用，不能称作收到反馈后连续重试三次。这里只识别可观察参数改变，不估计修正收益或根因。'),
('task_005','转交确认后仍继续自动执行',[15,16,18,20,23,24,29,31,32], 'E15/16 确认交接后，用户在 E20 带来声称由主管提供的恢复信息；Agent 又记录验证并修改邮箱，ACTION reward=1。','交接工具是否真结束自动控制、用户模拟器的脚本续接与现实流程是否一致，均需审查。不能把用户声称的主管互动当成已观测人类干预。'),
('task_081','部分处理后交接',[2,13,14,17,23,44,50,54,56], '用户侧早期请求人工，Agent 先查证并冻结三张借记卡，再转交信用卡及其他问题；DB reward=0。','存在继续处理、先采取保护性动作、立即交接等候选，但无同状态比较。发布评分不揭示真实延迟风险，不能断言越早交接越好。'),
('task_092','多卡查证后统一交接',[20,24,31,38,42,43,44,45,46], '先查四张卡与交易，再区分安全问题；E43 提出处理建议，用户同意后 E45 转人工；DB reward=0。','可能涉及部分可自主处理与整体交接的粒度，亦可能是评分条件限制；未观察人工接手结果。不与 task_081 构成配对因果对照。'),
('task_094','核算、资金修正及报告组合',[21,23,36,37,38,39,40], '读取账户及交易，E36 修正利息，E38 提交差异报告，E40 汇报结果；DB reward=1。','读取、计算、写入、报告分属不同作用。action_checks 可有不匹配但 reward_basis=DB；不能以某一辅助 action_match 代替最终评分，更不能反推每个环节必要。'),
('task_076','先比较长期费用，再开账户',[3,6,15,25,29,30,31], '围绕出境两个月的费用及提前入账需求，E15 比较账户条件，E29 开户；DB reward=1。','Agent 谈论未来费用不等于环境模拟了两个月结果。适合读多属性决策，不足以测真实长期回报。'),
('task_014','无显式工具错误的未完成',[19,25,31,32], '搜索促销代码规则后，E25/31 明确不愿猜测格式并建议其他支持渠道；没有写入/交接工具，DB reward=0。','拒绝猜测与失败评分可同时出现。需核对原始用户目标及评分任务；没有异常工具反馈仍可能不满足任务，不强归入错误恢复。'),
('task_001','被评估 Agent 只检索，用户执行申请',[3,6,18,19,20,21], 'Agent 比较卡片及订阅成本，E18 推荐，E19 用户申请，评分 DB=1。','与“必须 Agent 执行写入才有价值”相反的观察。信息建议与用户行为关联，但不能由这一次成功估计信息增益或因果价值。')]
short='# Phase 2 人工精读候选清单\n\n共 14 条，均在冻结的 50 条内；不是再次抽样，不改变基础随机集合。覆盖 8 个评分成功、6 个评分失败；优先级是阅读安排，不是效果排名。每条完整历史均保留，以下编号只标示起读点。\n\n'
for tid,title,es,fact,q in notes:
 r=rowmap[tid];sid=r['sample_id'];base='../public_trajectory_research/phase2/readable/'+sid+'.md';links=' → '.join(f'[E{e}]({base}#e{e})' for e in es)
 short+=f'## {sid}：{title}\n\n来源：{r["sample_group"]}；reward={r["reward"]}（{r["reward_basis"]}）；{r["message_count"]} 条消息。[完整轨迹]({base})。\n\n关键片段：{links}。\n\n**已观察事实：**{fact}\n\n**精读问题与竞争解释：**{q}\n\n分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。\n\n'
(R/'PHASE2_READING_SHORTLIST.md').write_text(short.rstrip()+'\n')
obs='''# Phase 2 决策观察与证据索引

## 状态与范围

完成 50 条新增公开轨迹提取、结构化索引与候选片段整理；尚未完成人类金标准标注、所有文档逐句复核或因果实验。没有 LLM 自动根因分类、收费请求、Agent 新运行或算法开发。Phase 1 结论与原始文件保持不变。

每条完整消息均保留原顺序；E 编号为 messages 索引+1。任务规格与 reward 是分析者事后信息，分区展示；不能把整个已发布前缀当成 Agent 输入。已静态核对源 commit 的 orchestrator.step：工具结果返回调用方；用户工具动作及其结果不直接发给 Agent。索引分别列出 agent_routed_event_ids 与 user_private_event_ids；只把对话正文、Agent 自己的动作/反馈作为路由候选，不包括 raw_data 中的用户私有推理。终止消息可能不再交给 Agent，未重建 provider 的精确输入。工具反馈在该事件返回后才可用。源中的并行调用仍同属一个消息；不同工具名不必意味着重新规划。

## 数据包与抽样分母

源容器 150,287,419 字节，SHA256 `614cdc47ae910fb97936c839e59cf43ec087f9c3c548af395159ea751759c292`。388 次运行，97 个任务、每个 4 Trial；347 条非空终止历史有评分（165 成功、182 失败），41 次 infrastructure_error 无评分。评分 basis 为 DB:314、ACTION:29、DB+NL_ASSERTION:4；后者含发布方自然语言断言判定，本轮未重新调用评审模型，也不将其解释当作根因金标准。347 条的工具调用与返回均能关联，但这不验证隐藏环境或 provider 全部上下文。完整文件下载用于清点，正式研究导出只含本轮 50 条。

96 个任务至少有一条符合条件的完整记录；task_027 的四个 Trial 均没有合格完整记录，未补造或重抽；排除 Phase 1 四任务后，抽样分母为 **92 个独立 task_id**。按预先规则为每个任务选最早可用 Trial，而非最高分 Trial；因此含“排除基础设施失败、优先早期 Trial”的选择偏差。不同 task_id 仍可能共享任务模板、客户或数据库，不等于统计独立分布样本。

计划在 commit `0d01cf6` 冻结，seed=20261020，计划 SHA256 `bcc977681dea4dc83cefb2ec7289750e6200cd19073e68761bcac588a38f6558`。随机部分为 30/92，无按结果重选，结果 13 成功/17 失败。剩余 62 任务中的目标部分按五个预设线索顺序各取 4 条，结果 10 成功/10 失败。各阶段可用分母分别 51、15、42、39、45，线索重叠且分母随先前入选移除；**这些数字不能相加**。完整任务名单、每层可用集合、抽样顺序均在 manifest。

总 50 条、50 个不同 task_id、3,124 消息；Trial 分布 0:42、1:4、2:3、3:1。被评估 Agent 调用 1,544 次；模拟用户 60 次，不混计。目标样本是在结果与线索条件下选择，不能与随机部分混合估计总体频率；整个来源也不是现实用户总体。没有按有趣程度替换基础样本。

## 索引如何解释

CSV 保留：原始首条用户请求的短摘录（不是隐藏目标）、reward/basis、消息数、按 actor 分开的工具、解包后的实际工具名、显式错误、信息工具线索、工具名变化、源成本/usage/duration、原始及可读路径。完整隐藏任务目标在 source_metadata 与每条可读版中；不以用户首句代表全部目标。

`information` 使用工具名前缀启发式，只用于检索候选：shell 可能写入，wrapper 可能只是读取；`noninformation` 也不等于有效状态改变。CSV 的 effective tool names 可辅助复核。错误列只检查 error 字段或以 Error 开头的反馈，未捕获所有业务拒绝/数值偏差；未命中不能证明无错误。工具名变化包括同消息批次内部差异，不能当作策略调整计数。

每条都有完整 candidate_events、原始 /messages 索引、记录前缀范围、静态路由可见/用户私有事件列表、未归类消息清单，见 `public_trajectory_research/phase2/evidence/decision_fragments.json`。此文件是可复核的机械索引，不是真实根因、价值或失败类型标签。没有给所有样本强贴新 taxonomy。

## 问题驱动的候选现象（描述与推断分开）

'''
for tid,title,es,fact,q in notes:
 sid=rowmap[tid]['sample_id'];base='../public_trajectory_research/phase2/readable/'+sid+'.md';links=', '.join(f'[E{e}]({base}#e{e})' for e in es)
 obs+=f'- **{tid} / {title}**：{fact} 证据：{links}。待核验/竞争解释：{q}\n\n'
obs+='''## 50 条逐轨迹候选入口

以下每行均为原始消息定位和来源事实；没有从工具名推断真实根因。信息/其他工具列仅取首个与末个候选，全部中间事件仍在索引与完整轨迹。零显式错误、纯信息行动、用户侧动作和其他未归类行为全部保留。

| 轨迹 / 来源 | 原始首句目标（短摘录） | 评分/basis | 信息候选 | 其他动作候选 | 显式错误反馈 |
|---|---|---|---|---|---|
'''
for r in rows:
 sid=r['sample_id'];base='../public_trajectory_research/phase2/readable/'+sid+'.md';ev=frags[sid]['candidate_events']
 def links(key):
  ns=list(dict.fromkeys(e['event'] for e in ev if e['cue']==key));ns=ns if len(ns)<=2 else [ns[0],ns[-1]]
  return ', '.join(f'[E{x}]({base}#e{x})' for x in ns) or '未命中'
 goal=r['observed_user_goal'][:90].replace('\n',' ').replace('|','/')
 obs+=f'| [{sid}]({base}) / {r["sample_group"]} | {goal}… | {r["reward"]}/{r["reward_basis"]} | {links("information")} | {links("noninformation")} | {links("errors")} |\n'
obs+='''
## 成本、验证和未解决问题

成本/usage 为发布方字段，保留 assistant 与 user 分账；不当成本实验实付账单。没有重定价、核验实际发票、人工交接成本、用户时间效用或长期产品收益。缺失值不补零；无 usage 的消息不估算。最终 reward 不等于扣除成本后的净效用。

实际命令（离线，不执行历史工具命令）：

```bash
python3 public_trajectory_research/phase2/scripts/build.py public_trajectory_research/phase2/raw/source_bundle.json
python3 public_trajectory_research/phase2/scripts/verify.py
python3 public_trajectory_research/phase2/scripts/reports.py
```

验证结果见 evidence/verification.json：冻结计划哈希、独立重算随机样本、50 个任务互异且排除 Phase 1、原始字节和 SHA256、消息渲染往返、工具 actor 与顺序、评分 breakdown 一致性、片段范围全部通过。评分一致性只验证源字段，不是重执行测试器。Phase 1 四条原始哈希不变。

前缀中缺少工具定义全量、隐藏数据库变化与 provider 完整上下文的证据；评分辅助 action_checks 与 DB 判断并不必一致，不能擅自覆盖 reward_basis。尚未建立跨试验控制、同历史替代行动或实际长期回报。先由研究负责人精读，之后才决定研究设计。
'''
(R/'PHASE2_DECISION_OBSERVATIONS.md').write_text(obs)
for name in ['PHASE2_SAMPLE_MANIFEST.json','PHASE2_TRAJECTORY_INDEX.csv']:(R/name).write_bytes((P/name).read_bytes())
print('reports and 14-trace shortlist generated')

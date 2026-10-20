# Phase 2 人工精读候选清单

共 14 条，均在冻结的 50 条内；不是再次抽样，不改变基础随机集合。覆盖 8 个评分成功、6 个评分失败；优先级是阅读安排，不是效果排名。每条完整历史均保留，以下编号只标示起读点。

## task_060_trial0：先关闭账户，再处理另一目标

来源：targeted；reward=0.0（DB）；60 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_060_trial0.md)。

关键片段：[E28](../public_trajectory_research/phase2/readable/task_060_trial0.md#e28) → [E33](../public_trajectory_research/phase2/readable/task_060_trial0.md#e33) → [E34](../public_trajectory_research/phase2/readable/task_060_trial0.md#e34) → [E35](../public_trajectory_research/phase2/readable/task_060_trial0.md#e35) → [E37](../public_trajectory_research/phase2/readable/task_060_trial0.md#e37) → [E38](../public_trajectory_research/phase2/readable/task_060_trial0.md#e38) → [E53](../public_trajectory_research/phase2/readable/task_060_trial0.md#e53) → [E54](../public_trajectory_research/phase2/readable/task_060_trial0.md#e54) → [E59](../public_trajectory_research/phase2/readable/task_060_trial0.md#e59)。

**已观察事实：**用户在 E34 要求先关户；E35 执行关闭，E38 再提出储蓄需求，E53/59 给出选择及未来开户安排；最终 DB reward=0。

**精读问题与竞争解释：**是否存在跨目标前提约束，是否应在不可逆操作前查清后续计划？先核对政策和用户许可；不能由先后顺序断言关户造成失败。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_069_trial0：产品组合、先行执行与资格反馈

来源：random_base；reward=0.0（DB）；107 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_069_trial0.md)。

关键片段：[E24](../public_trajectory_research/phase2/readable/task_069_trial0.md#e24) → [E49](../public_trajectory_research/phase2/readable/task_069_trial0.md#e49) → [E65](../public_trajectory_research/phase2/readable/task_069_trial0.md#e65) → [E70](../public_trajectory_research/phase2/readable/task_069_trial0.md#e70) → [E72](../public_trajectory_research/phase2/readable/task_069_trial0.md#e72) → [E76](../public_trajectory_research/phase2/readable/task_069_trial0.md#e76) → [E78](../public_trajectory_research/phase2/readable/task_069_trial0.md#e78) → [E79](../public_trajectory_research/phase2/readable/task_069_trial0.md#e79) → [E90](../public_trajectory_research/phase2/readable/task_069_trial0.md#e90) → [E100](../public_trajectory_research/phase2/readable/task_069_trial0.md#e100) → [E106](../public_trajectory_research/phase2/readable/task_069_trial0.md#e106)。

**已观察事实：**E70 关原账户，E76 新开支票账户，E78 储蓄开户在 E79 返回资格不足；随后继续查证，用户另行申请信用卡。

**精读问题与竞争解释：**失败可能涉及资格、组合选择或时序；仅有一条执行路径，不能认定提前关户就是根因。开放比较延迟执行、澄清、补充查证等候选。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_045_trial0：清偿准备与目标转向

来源：random_base；reward=1.0（DB）；77 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_045_trial0.md)。

关键片段：[E27](../public_trajectory_research/phase2/readable/task_045_trial0.md#e27) → [E31](../public_trajectory_research/phase2/readable/task_045_trial0.md#e31) → [E38](../public_trajectory_research/phase2/readable/task_045_trial0.md#e38) → [E42](../public_trajectory_research/phase2/readable/task_045_trial0.md#e42) → [E46](../public_trajectory_research/phase2/readable/task_045_trial0.md#e46) → [E50](../public_trajectory_research/phase2/readable/task_045_trial0.md#e50) → [E62](../public_trajectory_research/phase2/readable/task_045_trial0.md#e62) → [E74](../public_trajectory_research/phase2/readable/task_045_trial0.md#e74) → [E76](../public_trajectory_research/phase2/readable/task_045_trial0.md#e76)。

**已观察事实：**开始请求关信用卡；E42 从支票账户清偿余额，之后讨论保留优惠；E74 应用信用额度补偿，E76 明确账户仍开着。发布 DB reward=1。

**精读问题与竞争解释：**字面最初目标与最终用户选择不同。准备行动的价值取决于随后路径；不能把“未关户”自动判失败，也不能从通过评分得出客户长期受益。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_049_trial0：多个子目标具有不同前提

来源：targeted；reward=1.0（DB）；120 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_049_trial0.md)。

关键片段：[E31](../public_trajectory_research/phase2/readable/task_049_trial0.md#e31) → [E37](../public_trajectory_research/phase2/readable/task_049_trial0.md#e37) → [E41](../public_trajectory_research/phase2/readable/task_049_trial0.md#e41) → [E49](../public_trajectory_research/phase2/readable/task_049_trial0.md#e49) → [E51](../public_trajectory_research/phase2/readable/task_049_trial0.md#e51) → [E57](../public_trajectory_research/phase2/readable/task_049_trial0.md#e57) → [E71](../public_trajectory_research/phase2/readable/task_049_trial0.md#e71) → [E73](../public_trajectory_research/phase2/readable/task_049_trial0.md#e73) → [E83](../public_trajectory_research/phase2/readable/task_049_trial0.md#e83) → [E85](../public_trajectory_research/phase2/readable/task_049_trial0.md#e85) → [E99](../public_trajectory_research/phase2/readable/task_049_trial0.md#e99) → [E113](../public_trajectory_research/phase2/readable/task_049_trial0.md#e113) → [E117](../public_trajectory_research/phase2/readable/task_049_trial0.md#e117)。

**已观察事实：**四卡关闭任务中，出现替换卡运输状态、余额不足、保留优惠等不同分支；实际关闭一张，应用补偿后交接；DB reward=1。

**精读问题与竞争解释：**子任务不是可互换的动作计数。反复读取也可能是在核对用户新声明；不能把每次读取算浪费。未观察后续人类处理与用户收益。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_026_trial1：用户授权操作与 Agent 更新交织

来源：random_base；reward=0.0（DB）；108 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_026_trial1.md)。

关键片段：[E33](../public_trajectory_research/phase2/readable/task_026_trial1.md#e33) → [E39](../public_trajectory_research/phase2/readable/task_026_trial1.md#e39) → [E41](../public_trajectory_research/phase2/readable/task_026_trial1.md#e41) → [E44](../public_trajectory_research/phase2/readable/task_026_trial1.md#e44) → [E49](../public_trajectory_research/phase2/readable/task_026_trial1.md#e49) → [E55](../public_trajectory_research/phase2/readable/task_026_trial1.md#e55) → [E62](../public_trajectory_research/phase2/readable/task_026_trial1.md#e62) → [E65](../public_trajectory_research/phase2/readable/task_026_trial1.md#e65) → [E95](../public_trajectory_research/phase2/readable/task_026_trial1.md#e95) → [E105](../public_trajectory_research/phase2/readable/task_026_trial1.md#e105) → [E107](../public_trajectory_research/phase2/readable/task_026_trial1.md#e107)。

**已观察事实：**E33 一次提供多个用户可用操作，随后转为逐项提供；用户提交、Agent 查询/更新、再确认。结束时描述五项已更新，DB reward=0。

**精读问题与竞争解释：**合作双方动作、事务粒度和最终状态是否一致需逐项核对。完成声明不是最终正确性的证明；评分失败也不能确定是哪一次用户操作引起。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_037_trial0：用户侧参数错误后仍成功

来源：random_base；reward=1.0（DB）；68 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_037_trial0.md)。

关键片段：[E44](../public_trajectory_research/phase2/readable/task_037_trial0.md#e44) → [E48](../public_trajectory_research/phase2/readable/task_037_trial0.md#e48) → [E57](../public_trajectory_research/phase2/readable/task_037_trial0.md#e57) → [E58](../public_trajectory_research/phase2/readable/task_037_trial0.md#e58) → [E59](../public_trajectory_research/phase2/readable/task_037_trial0.md#e59) → [E60](../public_trajectory_research/phase2/readable/task_037_trial0.md#e60) → [E64](../public_trajectory_research/phase2/readable/task_037_trial0.md#e64) → [E67](../public_trajectory_research/phase2/readable/task_037_trial0.md#e67)。

**已观察事实：**更换卡与争议处理交织；E57 用户工具调用在 E58 缺参数，E59 用户改参数，之后 Agent 提交两项争议；DB reward=1。

**精读问题与竞争解释：**修正主体是用户模拟器。成功是“出现错误即失败”的反例；尚不清楚真实用户是否能做同样修正。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_064_trial0：同批调用错误与后续修改

来源：targeted；reward=1.0（DB）；60 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_064_trial0.md)。

关键片段：[E7](../public_trajectory_research/phase2/readable/task_064_trial0.md#e7) → [E10](../public_trajectory_research/phase2/readable/task_064_trial0.md#e10) → [E11](../public_trajectory_research/phase2/readable/task_064_trial0.md#e11) → [E12](../public_trajectory_research/phase2/readable/task_064_trial0.md#e12) → [E13](../public_trajectory_research/phase2/readable/task_064_trial0.md#e13) → [E14](../public_trajectory_research/phase2/readable/task_064_trial0.md#e14) → [E30](../public_trajectory_research/phase2/readable/task_064_trial0.md#e30) → [E37](../public_trajectory_research/phase2/readable/task_064_trial0.md#e37) → [E38](../public_trajectory_research/phase2/readable/task_064_trial0.md#e38) → [E57](../public_trajectory_research/phase2/readable/task_064_trial0.md#e57) → [E59](../public_trajectory_research/phase2/readable/task_064_trial0.md#e59)。

**已观察事实：**E10–12 三个 shell 返回都报告不接受 timeout 参数；E13 的调用去掉该参数并获得输出。后续产品组合、用户申请与开户完成，DB reward=1。

**精读问题与竞争解释：**三条错误来自先前一批调用，不能称作收到反馈后连续重试三次。这里只识别可观察参数改变，不估计修正收益或根因。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_005_trial2：转交确认后仍继续自动执行

来源：targeted；reward=1.0（DB）；34 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_005_trial2.md)。

关键片段：[E15](../public_trajectory_research/phase2/readable/task_005_trial2.md#e15) → [E16](../public_trajectory_research/phase2/readable/task_005_trial2.md#e16) → [E18](../public_trajectory_research/phase2/readable/task_005_trial2.md#e18) → [E20](../public_trajectory_research/phase2/readable/task_005_trial2.md#e20) → [E23](../public_trajectory_research/phase2/readable/task_005_trial2.md#e23) → [E24](../public_trajectory_research/phase2/readable/task_005_trial2.md#e24) → [E29](../public_trajectory_research/phase2/readable/task_005_trial2.md#e29) → [E31](../public_trajectory_research/phase2/readable/task_005_trial2.md#e31) → [E32](../public_trajectory_research/phase2/readable/task_005_trial2.md#e32)。

**已观察事实：**E15/16 确认交接后，用户在 E20 带来声称由主管提供的恢复信息；Agent 又记录验证并修改邮箱，ACTION reward=1。

**精读问题与竞争解释：**交接工具是否真结束自动控制、用户模拟器的脚本续接与现实流程是否一致，均需审查。不能把用户声称的主管互动当成已观测人类干预。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_081_trial0：部分处理后交接

来源：targeted；reward=0.0（DB）；57 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_081_trial0.md)。

关键片段：[E2](../public_trajectory_research/phase2/readable/task_081_trial0.md#e2) → [E13](../public_trajectory_research/phase2/readable/task_081_trial0.md#e13) → [E14](../public_trajectory_research/phase2/readable/task_081_trial0.md#e14) → [E17](../public_trajectory_research/phase2/readable/task_081_trial0.md#e17) → [E23](../public_trajectory_research/phase2/readable/task_081_trial0.md#e23) → [E44](../public_trajectory_research/phase2/readable/task_081_trial0.md#e44) → [E50](../public_trajectory_research/phase2/readable/task_081_trial0.md#e50) → [E54](../public_trajectory_research/phase2/readable/task_081_trial0.md#e54) → [E56](../public_trajectory_research/phase2/readable/task_081_trial0.md#e56)。

**已观察事实：**用户侧早期请求人工，Agent 先查证并冻结三张借记卡，再转交信用卡及其他问题；DB reward=0。

**精读问题与竞争解释：**存在继续处理、先采取保护性动作、立即交接等候选，但无同状态比较。发布评分不揭示真实延迟风险，不能断言越早交接越好。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_092_trial3：多卡查证后统一交接

来源：random_base；reward=0.0（DB）；48 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_092_trial3.md)。

关键片段：[E20](../public_trajectory_research/phase2/readable/task_092_trial3.md#e20) → [E24](../public_trajectory_research/phase2/readable/task_092_trial3.md#e24) → [E31](../public_trajectory_research/phase2/readable/task_092_trial3.md#e31) → [E38](../public_trajectory_research/phase2/readable/task_092_trial3.md#e38) → [E42](../public_trajectory_research/phase2/readable/task_092_trial3.md#e42) → [E43](../public_trajectory_research/phase2/readable/task_092_trial3.md#e43) → [E44](../public_trajectory_research/phase2/readable/task_092_trial3.md#e44) → [E45](../public_trajectory_research/phase2/readable/task_092_trial3.md#e45) → [E46](../public_trajectory_research/phase2/readable/task_092_trial3.md#e46)。

**已观察事实：**先查四张卡与交易，再区分安全问题；E43 提出处理建议，用户同意后 E45 转人工；DB reward=0。

**精读问题与竞争解释：**可能涉及部分可自主处理与整体交接的粒度，亦可能是评分条件限制；未观察人工接手结果。不与 task_081 构成配对因果对照。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_094_trial0：核算、资金修正及报告组合

来源：random_base；reward=1.0（DB）；41 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_094_trial0.md)。

关键片段：[E21](../public_trajectory_research/phase2/readable/task_094_trial0.md#e21) → [E23](../public_trajectory_research/phase2/readable/task_094_trial0.md#e23) → [E36](../public_trajectory_research/phase2/readable/task_094_trial0.md#e36) → [E37](../public_trajectory_research/phase2/readable/task_094_trial0.md#e37) → [E38](../public_trajectory_research/phase2/readable/task_094_trial0.md#e38) → [E39](../public_trajectory_research/phase2/readable/task_094_trial0.md#e39) → [E40](../public_trajectory_research/phase2/readable/task_094_trial0.md#e40)。

**已观察事实：**读取账户及交易，E36 修正利息，E38 提交差异报告，E40 汇报结果；DB reward=1。

**精读问题与竞争解释：**读取、计算、写入、报告分属不同作用。action_checks 可有不匹配但 reward_basis=DB；不能以某一辅助 action_match 代替最终评分，更不能反推每个环节必要。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_076_trial0：先比较长期费用，再开账户

来源：random_base；reward=1.0（DB）；32 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_076_trial0.md)。

关键片段：[E3](../public_trajectory_research/phase2/readable/task_076_trial0.md#e3) → [E6](../public_trajectory_research/phase2/readable/task_076_trial0.md#e6) → [E15](../public_trajectory_research/phase2/readable/task_076_trial0.md#e15) → [E25](../public_trajectory_research/phase2/readable/task_076_trial0.md#e25) → [E29](../public_trajectory_research/phase2/readable/task_076_trial0.md#e29) → [E30](../public_trajectory_research/phase2/readable/task_076_trial0.md#e30) → [E31](../public_trajectory_research/phase2/readable/task_076_trial0.md#e31)。

**已观察事实：**围绕出境两个月的费用及提前入账需求，E15 比较账户条件，E29 开户；DB reward=1。

**精读问题与竞争解释：**Agent 谈论未来费用不等于环境模拟了两个月结果。适合读多属性决策，不足以测真实长期回报。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_014_trial0：无显式工具错误的未完成

来源：random_base；reward=0.0（ACTION）；32 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_014_trial0.md)。

关键片段：[E19](../public_trajectory_research/phase2/readable/task_014_trial0.md#e19) → [E25](../public_trajectory_research/phase2/readable/task_014_trial0.md#e25) → [E31](../public_trajectory_research/phase2/readable/task_014_trial0.md#e31) → [E32](../public_trajectory_research/phase2/readable/task_014_trial0.md#e32)。

**已观察事实：**搜索促销代码规则后，E25/31 明确不愿猜测格式并建议其他支持渠道；没有写入/交接工具，DB reward=0。

**精读问题与竞争解释：**拒绝猜测与失败评分可同时出现。需核对原始用户目标及评分任务；没有异常工具反馈仍可能不满足任务，不强归入错误恢复。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

## task_001_trial0：被评估 Agent 只检索，用户执行申请

来源：targeted；reward=1.0（DB）；21 条消息。[完整轨迹](../public_trajectory_research/phase2/readable/task_001_trial0.md)。

关键片段：[E3](../public_trajectory_research/phase2/readable/task_001_trial0.md#e3) → [E6](../public_trajectory_research/phase2/readable/task_001_trial0.md#e6) → [E18](../public_trajectory_research/phase2/readable/task_001_trial0.md#e18) → [E19](../public_trajectory_research/phase2/readable/task_001_trial0.md#e19) → [E20](../public_trajectory_research/phase2/readable/task_001_trial0.md#e20) → [E21](../public_trajectory_research/phase2/readable/task_001_trial0.md#e21)。

**已观察事实：**Agent 比较卡片及订阅成本，E18 推荐，E19 用户申请，评分 DB=1。

**精读问题与竞争解释：**与“必须 Agent 执行写入才有价值”相反的观察。信息建议与用户行为关联，但不能由这一次成功估计信息增益或因果价值。

分析者已知的评价条件位于可读版 task.evaluation_criteria / reward_info；不能假设 Agent 预先知道。每个行动前的信息仅限此前实际路由给 Agent 的对话正文、它自己的工具返回及当时政策；用户私有工具动作/结果与 raw_data 不算直接可见。

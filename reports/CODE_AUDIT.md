# Calibration Is Not Control：源码审查

日期：2026-10-16（Asia/Shanghai）。锁定 commit `9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3`，MIT。仓库 `/home/hly/agent-research/calibration-is-not-control`。

证据等级：**[执行]** 本次运行验证；**[源码]** 对锁定源码的静态追踪，不代表真实模型效果；**[未核验]** 尚无实验依据。已逐行阅读 README、requirements、两个 scripts、三个实现模块，并补读 LICENSE、包入口。原始代码未修改。相对源码引用均基于此 commit；运行证据见 `../experiments/cinc_smoke_20261016/`。

## 1. 任务和 checkpoint 的选择

[源码] `collect_alfworld_branches.py:818` main → `collect_gamefiles`（`alfworld_text.py:64`）：ALFWORLD_DATA 下 `json_2.1.1/train`、`valid_seen`、`valid_unseen` 分别用于 train/val/test。仅保留同时含 traj_data.json、game.tw-pddl、task_type 在允许集合且 game JSON 的 solvable 为真的实例；路径含 movable 或 Sliced 一律排除。因此虽然 one-hot 有七种任务，movable 实际被过滤。os.walk 的结果未排序，随后用 seed/seed+1/seed+2 的局部 Random shuffle，再截取 limit；相同种子不能保证跨文件系统相同实例。

`rollout_base_prefix_candidates:147` 先完整执行 base rollout，每次行动之前记录状态。`select_prefix_indices:129` 在实际 rollout 状态数上等距 linspace + round，默认两个点是初始状态和最后一个未执行动作的状态；不是固定时刻、不保证中期、没有保存环境 checkpoint。短轨迹只有一个状态时只生成一个 prefix。checkpoint 是决策前缀，不是 LLM 训练 checkpoint。LLM 使用 model_path/api_model，未锁权重 revision；API 参数可指向另一模型，代码不校验。

选点依赖已知的轨迹终点：这是一种离线样本选择偏差，不是将未来长度直接输入控制器；不能当作已实现的在线触发机制。

## 2. 状态恢复与一致性

[源码] `replay_to_prefix:204` 新建同一 game 环境 → reset → 重放全部 history_actions，遇 done 提前退出。没有 snapshot、逐步 observation 对齐、隐藏状态比较、seed/state 恢复或 admissible_commands 对齐。`rollout_branch:232`、replan:284、expert:381 只比较终点 observation 去空白后的文本。

不一致不报错、不丢弃；继续产生训练标签。[执行] 独立测试将prefix观察改错后，build_rows仍保留1行、匹配计数0。`build_rows:538` 只累计 continue 分支匹配数；intervention 的匹配标志被丢弃。save_rows 甚至不保存单行 replay_matches_prefix，只在 summary 中保留 continue 的总体匹配率。分支仍沿用原 prefix 的 history 和首动作，若恢复错位会污染配对比较。多处 env 未 close，长采集有资源累积风险。[执行] 小规模真实回放结果另见 SMOKE_TEST_RESULTS；几个样本一致不证明全量一致。

## 3. 分支真值

[源码] Continue 重放至 prefix，执行已记录的 proposed action，此后用同一 base prompt/model 持续执行至 done/won。Intervene 另建环境、重放，执行所选干预，并按模式继续。成功标签为 TextWorld infos.won；不是 LLM 自判，不使用 raw reward 计算效用。每个动作只采一条未来轨迹，不是多次估计真实期望。Quit 不运行环境，直接定义 u_quit=0，是剩余 suffix 的外部选项。历史 sunk cost 不再扣除。环境 max_episode_steps 计入 replay 已走的步骤，因此剩余 budget 应为 H-step_index。

## 4. 干预模式和特权信息

| 模式 | 实际机制 | 决策时信息风险 |
|---|---|---|
| expert_defer（默认） | include_policy_commands=True；循环执行环境 planner 首条命令，每步更新计划；解出/超预算/无计划/截断结束，base 不恢复 | Oracle planner 访问环境状态；不是另一真实语言模型。with_preview 还把 expert 首动作派生特征提前给控制器 |
| llm_verify | 同模型提示改选不同首动作，再正常 base rollout | 有输出 preview；提议不同只是 prompt 要求，extract_action 仍可选回原动作 |
| self_reflect_retry | 同模型生成反思+首动作，再 base rollout | 反思并未持续传递到后续 base prompt；只通过动作及环境后果影响未来 |
| self_replan | 前 repair_horizon 步换 repair prompt，之后 base | 不读 expert；每次观察为干预执行后的真实观察，但 controller 特征只抽取首动作 |
| self_plan_replan | 首步生成 PLAN+ACTION，后续 repair 步带此计划，之后 base | 同上，不是训练/记忆模块 |

expert_noise_rate 随机替换为非计划中的 admissible 命令；expert_max_policy_steps 截断后直接计当时 won。上限 0 仍会执行第一步（限制在 step 后检查）。记录的 first_action 是原计划首动作，不一定等于有噪声时实际执行的首动作；preview 在噪声实验会错配。`verify_tool_success` 对 llm_verify 恒 True，只是可用性占位，不是验证正确。所有 base prompts 也获得环境 admissible_commands；这是环境辅助动作空间，不应描述成无工具自由生成。task_desc/task_type 来自 traj_data 元数据，不是未来标签。

## 5. 特征及部署信息审计

[源码] basic_feature_vector（alfworld_text.py:370）18项：step_index、history_len、任务词数、观察词数、观察字符数、可行动作数、所选动作词数、10类动作 indicator（go/open/close/take/put/heat/cool/clean/toggle/look）、nothing happens。再加 task_type 七维 one-hot=25；policy_learning.py:16 再加 confidence/100=26。history_len 与 step_index 在此采集方式下相同。不是语义历史编码，LLM prompt 最近4条历史，每条观察截到500字符。

verify_feature_vector 14项（进度、命令数、干预动作词数、与continue相等、8动作类型、closed/open）+重复七维 task one-hot=21。with_preview 拼接到26维得到 **47维**，不是40维；no_preview 两支均26维。

confidence 在 prefix 用额外 LLM 请求生成，问的是下一动作是否在正确轨道，不是严格定义的全任务成功概率；解析失败默认为50。extract_action 会模糊匹配、子串匹配，最后静默选择第一个合法动作；因此生成格式失效可能被隐藏。

未发现 no_preview 特征读取 continue/verify_branch_steps、u_*、correct、最终 observation、未来 verify_text。branch_steps 仅用于标签效用与输出；并未在部署公式中扣真实未来步数。with_preview 读取干预首动作派生信息，expert 模式是特权预览，必须单列。完整未来反思文本虽保存，但未作为控制器特征。

## 6. 学习目标、路由及 LCB

[源码] policy_learning.py：RF 200树、depth6、leaf2、n_jobs1。

| 控制器 | 监督目标及路由 |
|---|---|
| failure | 1-continue_correct；score 高先 quit、其次 verify、否则 continue；验证集12分位点双阈值 |
| value | 两个回归器分别拟合 u_continue、u_verify；验证集12个差值分位阈值 × 13个quit floor |
| explicit_eu | 两个分类器预测各分支 won；EU=(1+w)p-w-c_a；选择最大非负EU，否则quit |
| explicit_eu_lcb | p_lcb=clip(p-beta*std,0,1)，代入上述EU；beta_continue 0..1、beta_verify 0..1.5、步长.1；验证集utility选择 |
| two_stage | 第一层 target=max(u_verify,u_quit)>u_continue；第二层仅在第一层正样本训练 u_verify>u_quit；分别阈值路由 |
| cost_sensitive helpers | oracle argmax 三类标签，以最好与次好的utility差（至少.01）加权；两个CLI均未调用，不是默认baseline |

LCB std 为200棵树的成功概率预测总体标准差（ddof=0），无sqrt(n)缩放，无置信覆盖证明，不是环境回报方差；单类别训练返回常概率且std=0。随机森林种子分别固定0/1/2/3/4/5，cost-sensitive为7，不跟CLI seed联动。空训练集合不支持。

explicit_eu/LCB **遗漏 step_cost 的预测项**，而评测效用扣真实suffix步数。value已经在训练标签中包含步数成本。这是目标/决策公式不一致，不是未来长度泄漏。不能通过直接代入测试真实长度来“修复”。

## 7. 分割、选择和泄漏

[源码] 单一采集运行按官方split选择任务，同一 base rollout 全部prefix在同一split；不按行随机分割。不同seed可能重复同一game，但evaluate_controllers逐run独立分析，不合并训练。[执行补充] 本次可用实例的父目录trial ID在三个split间交集均为0；这不证明场景/目标语义独立。代码没有跨split task identity/scene/goal/hash去重断言，没有跨run隔离审计。evaluate.load_rows丢弃gamefile/split/task_type，因此不能从其内部检查数据泄漏；外部任意CSV也被照单接收。

训练真值监督和验证集效用调参是合理开发使用；常规策略决策来自模型预测。`evaluate_controllers.py:216` 的 test_best_family 则明确用测试 control_regret 选最优家族，仅是事后参考。对外成绩应读取 `modes.no_preview.val_selected_policy`，不能报告 test_best_policy 为部署效果。Oracle 的真实u比较也仅是评估参照；`prefix_only_baselines` 里的 oracle 命名不意味着它是可部署prefix-only策略。

## 8. 指标语义

[源码] collect:113：成功效用1-L*s-I*c，失败效用-w-L*s-I*c；默认w=1,c=.05,s=.01。L是prefix后的实际分支步数，Quit=0。evaluate_actions:712 平均选中utility；regret=mean(max三支真实u-选中u)。success_rate 是**prefix样本加权**的所选suffix won，quit记0，不是闭环独立任务成功率。

catastrophic_failure_rate实际上所有未成功的continue/verify（含timeout），quit不计；不是另定义的灾难事件。intervention_rate包含verify和quit；verify_rate才是实际干预分支比率；harmful_intervention_rate仅在被干预/退出的子集中平均 u_selected<u_continue，不是总体比例。固定干预成本均值可算 c*verify_rate；代码不单独报告总步骤/总调用/延迟成本。prompt预览、置信度、规划推理费用未计。

## 9. 额外逻辑问题与鲁棒性

[执行证据见smoke结果] failure阈值网格只覆盖分位数0..0.95且比较>=，不含高于最大score的边界；score恒0时无法选always-continue，即使所有continue成功。two_stage类似缺少完整端点。cost-sensitive阈值搜索对threshold=0与最终应用使用不同规则，存在“验证utility=1、最终utility=0”的反例；未被默认CLI触发。

[源码] evaluate_actions对rows/actions使用zip且无长度检查；非法action被视为quit。空数据、非有限数、schema不一致、config缺失没有严格检查；infer_costs可静默回退默认。采集直到全部拟合/评估后才写CSV，中途失败丢失所有采集成果；输出目录exist_ok且写w，可覆盖同名实验。

[源码] local_llm 无模型版本锁定、API seed；temperature=0不等于跨硬件确定性。HTTP请求实际串行，batch-size不能当远程并发。requirements未装transformers/vllm，远程客户端会落到chat endpoint；若有tokenizer则走completions，prompt边界不同。completions 404回退时rendered prompt及using_chat状态未同步重建，可能双模板/重复前缀。会读取OPENAI_API_KEY并发送到用户指定api_base，故本次未构造真实客户端；以后固定127.0.0.1且取消该变量。无上下文截断，长prompt可能超限。默认嵌入vLLM路径虽存在，CLI默认api-base非空，需传空字符串才启用。

## 10. 论文版本对应性

[文献核验] 最新可访问版本为2026-10-06 v2。26维前缀特征、RF配置、LCB网格、专家干预和效用参数与其描述对应；公开commit没有在线300任务、matched-target scalar、其他基准、bootstrap或完整多run协议。论文要求逐步回放验证、主比较无preview；代码验证不足且采集默认with_preview。论文附录preview维数写40，代码实际47。参见 [v2正文及附录C](https://arxiv.org/html/2606.21399v2)，本地保存原文供查证。

[未核验] 无作者原始实验CSV、模型revision及所有run配置，不能断言任何表格数值复现成功。当前应称“公开ALFWorld分支采集和四类控制器的最小实现审查”，不能称论文完整实现验证。

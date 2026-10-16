# 六任务 API Pilot 草案（未获采集授权）

2026-10-16。**连通性GO；六任务采集当前NO-GO，需负责人检查并授权，且必须先完成云端collector安全阀。** 本次只新增API草案，没有将云端模型接入原本地attestation。

## 计划、版本和任务

机器可读草案：`api_pilot/plans/ofox_gpt4o_mini_draft/plan.json`。
SHA256：`fe8a7cf2d74ef0fcbdf8caf6bf9487b0e00d8988cebd146ea3779596b6952dc5`。
父本地计划SHA256：`3179fa6ce944390a118dc309215acff241d376a721327c4e3f748294be768f61`。
我方父Commit：`891fdc668c0761111c27da5eb06c88ba786b52a8`；独立研究分支pilot-validity-hardening。

[执行] 逐项比较tasks/config与父计划完全相同，源代码/环境实现/依赖/数据文件原校验全部通过。没有新抽样。数据仍是本地ALFWorld json_2.1.1，每任务原有game.tw-pddl/initial_state.pddl/traj_data.json等路径和哈希完整继承。

| Split | Task ID | Prefix |
|---|---|---:|
| train | trial_T20190909_151853_245524 | 0 |
| train | trial_T20190907_224507_776787 | 0 |
| val | trial_T20190908_164236_518264 | 0 |
| val | trial_T20190908_033721_967359 | 0 |
| test | trial_T20190908_022321_380927 | 0 |
| test | trial_T20190909_064053_839817 | 0 |

6任务×1prefix=6个初始状态样本。属于端到端工程Pilot，不是中途干预、时机研究或论文效应复现。

## 固定参数和不同实验条件

- OFOX gateway；模型开发方OpenAI；ID `openai/gpt-4o-mini`；目录owned_by=azure，canonical_slug=gpt-4o-mini-2024-07-18。实际生成响应只返回模型别名，revision/权重/tokenizer/实际路由不可证明。不能声称锁定了2024-07-18具体部署，更不能称Qwen基线。
- 完整endpoint `https://api.ofox.ai/v1/chat/completions`；单user文本、temperature0、streamfalse；无请求seed。stop字段仅在作者confidence请求使用，实际远程兼容性尚未测试，不允许出错后删字段重试。
- seed13；环境1234；OMP/OPENBLAS/MKL线程1、PYTHONHASHSEED13；Train/Val/Test=2/2/2；batch1；no_preview；expert_defer；H20；action24/confidence8/verify24；verify_cost.05、step_cost.01、wrong_penalty1；其余参数完整继承父计划。
- 原prompt模板原文和文件指纹继承。base rollout仍完整执行后选第0点；不改成只执行一次以节省费用，否则变更实验路径。
- 输出预定 `/home/hly/agent-research/experiments/api_pilot_ofox_gpt4o_mini_v1`，已存在即拒绝，不覆盖；目录当前未创建。未来collector必须另留完整代码指纹并生成新的执行冻结版，不能静默编辑本草案。

## 必须保留的实验协议

双分支首个新动作前执行AuditSession严格可访问状态审计；全部原始轨迹/不一致持久化；无效配对排除valid_pairs但保留attempted分母，不补样。独立重算won、suffix steps、intervention cost、realized utility/control regret。保留original和corrected failure routing、三项always策略；训练只用train，阈值只用val，test前冻结，不用测试结果改模型/任务/策略。

显式EU继续保留原公式的未来steps cost遗漏，不输入测试真实suffix长度。API账单与延迟单独记录，不掺入作者utility。expert_defer仍是环境planner Oracle；API不是Intervene模型。隐藏native状态仍不可完整导出，审计通过不等于可靠因果分叉。

## 执行闸门与下一阶段

草案execution.enabled=false、runner=null、authorized_collection_requests=0、authorized_collection_usd=0。唯一获准的连接请求已经消耗。**没有可诚实给出的六任务执行命令：云端collector尚未实现；不得使用原本地runner命令替代。**

后续授权后先完成独立云端adapter/collector及离线回归，再冻结运行计划，给出准确命令并经负责人审查预算。设计安全阀：请求数240、输入每次8192 Token、累计预留预算USD0.35、无重试/无重定向/任何错误即全局停止；详见API_BUDGET_AND_RISKS。计数或价格语义不确定则不发送。当前这些是待实现的采集设计，不冒充已验证功能。

[执行] 新增离线13测试通过；旧本地plan验证通过。真实Agent任务数0；不据连通性成功声称P3/P4改进。P1/P2/P5及新猜想独立保留。

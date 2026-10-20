# 真实 Agent 轨迹观察

2026-10-20。以下为本轮小样本直接观察，不代表模型总体能力，不建立因果机制结论。

- smoke / trial_T20190909_151853_245524 / smoke：20步，成功=False，停止=budget_exhausted；不同动作8个，最多重复动作：[('go to fridge 1', 3), ('open fridge 1', 3), ('close fridge 1', 3)]。
- pilot / trial_T20190909_151853_245524 / base：20步，成功=False，停止=budget_exhausted；不同动作8个，最多重复动作：[('go to fridge 1', 3), ('open fridge 1', 3), ('close fridge 1', 3)]。
- pilot / trial_T20190909_151853_245524 / verify：7步，成功=True，停止=won；不同动作7个，最多重复动作：[('go to diningtable 1', 1), ('take potato 3 from diningtable 1', 1), ('go to fridge 1', 1)]。
- pilot / trial_T20190909_151853_245524 / continue：20步，成功=False，停止=budget_exhausted；不同动作10个，最多重复动作：[('go to fridge 1', 3), ('go to microwave 1', 3), ('open fridge 1', 2)]。
- pilot / trial_T20190907_224507_776787 / base：20步，成功=False，停止=budget_exhausted；不同动作14个，最多重复动作：[('take pan 1 from stoveburner 2', 3), ('take pot 1 from stoveburner 3', 2), ('move pot 1 to stoveburner 1', 2)]。
- pilot / trial_T20190907_224507_776787 / verify：7步，成功=True，停止=won；不同动作7个，最多重复动作：[('go to countertop 1', 1), ('take egg 3 from countertop 1', 1), ('go to microwave 1', 1)]。
- pilot / trial_T20190907_224507_776787 / continue：20步，成功=False，停止=budget_exhausted；不同动作17个，最多重复动作：[('go to stoveburner 1', 2), ('examine stoveburner 1', 2), ('go to cabinet 1', 2)]。
- pilot / trial_T20190908_164236_518264 / base：20步，成功=False，停止=budget_exhausted；不同动作8个，最多重复动作：[('examine garbagecan 1', 5), ('go to garbagecan 1', 4), ('go to drawer 1', 4)]。
- pilot / trial_T20190908_164236_518264 / verify：8步，成功=True，停止=won；不同动作6个，最多重复动作：[('go to sidetable 1', 2), ('go to garbagecan 1', 2), ('take spraybottle 2 from sidetable 1', 1)]。
- pilot / trial_T20190908_164236_518264 / continue：20步，成功=False，停止=budget_exhausted；不同动作8个，最多重复动作：[('examine garbagecan 1', 5), ('go to garbagecan 1', 4), ('go to drawer 1', 4)]。
- pilot / trial_T20190908_033721_967359 / base：20步，成功=False，停止=budget_exhausted；不同动作6个，最多重复动作：[('open fridge 1', 5), ('close fridge 1', 4), ('examine fridge 1', 4)]。
- pilot / trial_T20190908_033721_967359 / verify：7步，成功=True，停止=won；不同动作7个，最多重复动作：[('go to diningtable 1', 1), ('take tomato 3 from diningtable 1', 1), ('go to microwave 1', 1)]。
- pilot / trial_T20190908_033721_967359 / continue：20步，成功=False，停止=budget_exhausted；不同动作6个，最多重复动作：[('open fridge 1', 6), ('close fridge 1', 5), ('examine fridge 1', 3)]。
- pilot / trial_T20190908_022321_380927 / base：20步，成功=False，停止=budget_exhausted；不同动作11个，最多重复动作：[('go to cabinet 1', 3), ('open cabinet 1', 3), ('take soapbottle 3 from cabinet 1', 3)]。
- pilot / trial_T20190908_022321_380927 / verify：7步，成功=True，停止=won；不同动作6个，最多重复动作：[('go to cabinet 4', 2), ('open cabinet 4', 1), ('take cloth 1 from cabinet 4', 1)]。
- pilot / trial_T20190908_022321_380927 / continue：20步，成功=False，停止=budget_exhausted；不同动作11个，最多重复动作：[('go to cabinet 1', 3), ('open cabinet 1', 3), ('take soapbottle 3 from cabinet 1', 3)]。
- pilot / trial_T20190909_064053_839817 / base：20步，成功=False，停止=budget_exhausted；不同动作8个，最多重复动作：[('move soapbottle 2 to garbagecan 1', 7), ('take soapbottle 2 from garbagecan 1', 6), ('go to garbagecan 1', 2)]。
- pilot / trial_T20190909_064053_839817 / verify：8步，成功=True，停止=won；不同动作6个，最多重复动作：[('go to countertop 1', 2), ('go to garbagecan 1', 2), ('take soapbar 2 from countertop 1', 1)]。
- pilot / trial_T20190909_064053_839817 / continue：20步，成功=False，停止=budget_exhausted；不同动作11个，最多重复动作：[('go to garbagecan 1', 3), ('move soapbottle 2 to garbagecan 1', 3), ('examine garbagecan 1', 2)]。

## 可核验观察与限制

Smoke目标是“Put a cold potato in the microwave.”。20步中只有8种不同动作，冰箱/微波炉之间往返并反复取放mug 2；动作合法但目标未完成。不能据此断言循环是由记忆不足、某种状态表示或某个训练缺陷导致。提示词和任务未据表现调整，没有重抽或调参。

Oracle成功只表明该环境planner在对应预算内完成，不证明现实中另一Agent可同样恢复。控制器只在初始Prefix作一次离线决策，未研究中途触发时机。即使corrected优于original，也是此前阈值搜索修正和本样本结果，不是P3/P4新算法提升。

结构化数据：experiments/api_agent_round_20261020/{smoke,pilot}/trajectories.jsonl，逐步包含任务描述、完整历史前缀、行动前观察/合法动作、模型原始输出、实际动作、反馈、done/won、轨迹最终结果/停止原因、请求ID与Token数据。Continue首动作复用base提议，标记reused_base_proposal、new_request_for_step=false，不重复计费；Oracle动作没有LLM Usage。confidence请求不对应环境step，完整账本/requests.jsonl保留，不能只加总动作行来计算总费用。原始prompt、审计状态、错误事件保留在events.jsonl。

P3/P4后续机制实验尚未启动；P1/P2/P5和新猜想独立保留。现在停止采集，等待负责人分析。

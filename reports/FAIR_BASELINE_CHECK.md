# Fair Baseline 与效用审计

2026-10-16。原作者Commit `9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3`；我方最终实现 `70a3390`，独立分支pilot-validity-hardening。所有数值为CPU验证，不是真实LLM实验成绩。

## 原版与修正版

[源码+执行] 继续使用作者fit_failure_baseline；原版threshold_search_failure_scores不改。它用验证风险分数0..0.95的12个分位点，>=规则会导致常数风险时无法表达Always Continue。

corrected只扩大搜索：验证集全部不同风险概率，加-1和2两个有限哨兵（合法概率限制在[0,1]），枚举verify_threshold<=quit_threshold。-1代表所有样本越过下界，2代表所有样本都不到上界，完整表达Always Continue、Always Intervene、Always Quit，以及各验证分数处的切分。保持原Continue→Intervene→Quit的动作顺序，不增加任意动作排列。效用相同时保留固定遍历顺序的首项，无测试集tie-break。

这是更大搜索类的**方法性修正**，不能把它声称为作者原baseline。original与corrected分别保存，预测器、训练集及验证集一致。三个always策略不训练、不按测试集结果选择其中一个当“最终模型”。

## 恒定风险反例（验证集）

[执行] 3行Synthetic数据，风险均0，continue正确且utility=.95；intervene失败utility=-1.08；quit=0。

| 路由 | 验证阈值(verify,quit) | 动作 | Utility | Regret |
|---|---|---|---:|---:|
| original | (0,0) | 全quit | 0 | .95 |
| corrected | (2,2) | 全continue | .95 | 0 |

证据：`experiments/pilot_validity_cpu/artifact_verification.json`。这里是暴露边界缺失的最小反例，不是根据测试集调参的算法效果展示。

## 最终真实环境/Synthetic策略六任务运行

[执行] `run_final/summary.json`，测试集2/2有效，H=3、固定look策略，没有真实LLM。各分支未成功，因而以下结果合理；**修正版没有被包装成必然胜过原版**。

| 策略 | Test utility | Success | Regret |
|---|---:|---:|---:|
| original failure routing | 0 | 0 | 0 |
| corrected failure routing | 0 | 0 | 0 |
| Always Continue | -1.03 | 0 | 1.03 |
| Always Intervene（字段名always_verify） | -1.08 | 0 | 1.08 |
| Always Quit | 0 | 0 | 0 |
| original explicit EU | 0 | 0 | 0 |

原版未过滤CSV重新加载后，直接运行作者fit/threshold/evaluate函数得到的完整failure指标与保存的 `original_raw.policies.original.author_metrics` **逐项完全相等**。valid_pairs中original与corrected使用同一有效配对子集；original_raw作为未过滤参考单独保存，不能拿来宣称可靠配对。

## 测试集信息边界

[执行] 事件记录中冻结事件索引108，首个测试环境事件109；模型、验证阈值、训练/验证ID先落盘，再执行test任务。冻结函数签名只接受train_records、val_records，不接收test。

[执行] 训练并冻结后，将测试continue/verify标签和utility反转到极端值，original、corrected及三个always策略的动作不变，controls不变，仅评估指标变化。另将未来suffix长度改成9999/10000，26维输入矩阵保持不变。没有test_best选择，输出test_selected_policy=null。

不会调用作者脚本中按测试regret选家族的分支。原显式EU模型仅训练分支成功率，使用原公式选择动作；不喂真实suffix成本。未新增成本预测器。

## 独立效用与成本计算

[执行] 从持久化分支轨迹最后状态读won；suffix步数=`len(全部执行动作)-checkpoint_index`，并与最后状态执行计数及CSV步数双重核对。成功计+1、失败计-1；扣step_cost*.01对应实际后缀步数和Intervene固定.05；quit=0。

独立指标为平均所选realized utility；control regret为同一有效配对内max(u_continue,u_verify,0)-u_selected的平均。成功率按有效prefix分母，quit成功记0。25项回归中包含与作者evaluate_actions的utility/success/regret/verify/quit指标一致性测试；独立post-run核验12条实际环境分支的CSV/JSON读回完全一致。

成本分类：

- prefix已观察成本：checkpoint_index*step_cost，单独记录为sunk cost，沿用作者剩余suffix效用定义不重复扣。
- 分支已实现成本：完成后从动作数重算，只用于监督/评估。
- 预测未来成本：本阶段未实现，字段predicted_cost=null。
- LLM推理费用/时延：未计入utility；真实运行会记录prompt、HTTP参数与返回，但不能称已覆盖总系统成本。

原显式EU的未来步数成本遗漏仍存在，明确标为原版限制。把真实测试suffix长度拿来修正部署策略是禁止的，代码没有这条路径。

## 无效样本和分母

每split分别报告attempted/valid/invalid，测试额外报告coverage和invalid IDs。无效pair不进入valid_pairs的训练、验证或测试指标，原row/轨迹保留，不重新抽样。0个有效测试pair时utility、success、regret为null，而不是0；无有效训练或验证pair时停止冻结。original_raw的分母使用raw_rows_evaluated和audit_valid/audit_invalid标记，避免把未过滤记录误写为已通过审计。

排除失败恢复不是随机缺失，valid-pair条件指标可能存在选择偏差；必须同时公布失败样本和覆盖率，不能据此美化总体效果。本轮最终6/6通过不构成未来数据一定无错配的保证。

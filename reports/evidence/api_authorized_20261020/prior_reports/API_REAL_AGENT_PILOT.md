# API 真实 Agent Pilot：阶段 A 阻断

2026-10-20，Asia/Shanghai。**本轮 No-Go，未执行真实 Agent Smoke 或六任务 Pilot。** 用户已授权本轮新增USD3、最多400次；本次停止不是缺少运行授权，而是用户明确要求「如果缺少可靠费用上界……应停止并报告」。

## 实际执行与结果

| 项目 | 本轮实际结果 |
|---|---|
| 公开模型目录查询 | 免认证GET，HTTP200；见catalog_check.json |
| 新增真实模型请求 | **0** |
| 自然Smoke轨迹 / Pilot任务 / 分支轨迹 | **0 / 0 / 0** |
| 输入 / 输出Token | **0 / 0**，本轮没有生成请求 |
| 本轮累计费用预留 / 估算费用 | **USD0 / USD0**；非供应商账单审计 |
| 有效 / 无效Checkpoint | **0 / 0**，未尝试，比例为null |
| 各Baseline效用/Regret/成功率 | **null，未评测**，不能填0 |
| 2026-10-16连接测试 | 历史单次成功，不计入本轮新增预算或Agent轨迹 |

## 阻断证据

[执行] 当前目录确认openai/gpt-4o-mini、128000上下文、max_tokens支持、输入/输出每百万USD0.15/0.60。模型响应Usage格式沿用此前一次成功证据；没有以追加收费请求重新探测。

[公开文档] OFOX有账户全局fallback配置；本轮未获有效配置读回证据，文档未明确证明空fallback数组必然覆盖当前账户默认设置。模型名事后校验只能在可能产生费用后发现换模型，不能成为发送前预算证明。额度变更记录还有110%警告/缓冲描述，不能据此声称账户严格硬封顶USD3。详见 [预算审计](API_BUDGET_AUDIT.md)。

因此未将「目录价乘Token」提升为可靠实际账单上界；真实账本以unverified_billing_bound持久化停止。没有尝试别的模型、扩大预算或修改账户全局配置。

## 本轮实现及其范围

新增 `api_pilot/budget.py`：SQLite持久账本、整数纳美元计价、发送前事务预留、400次总限额、USD3总限额、64 Token绝对输出限额、60秒墙钟截止、零重试、禁止重定向；失败、未知Usage、重复请求、未决请求均停止。复用仓库外现有密钥读取与安全session；不重新索要密钥。旧单次probe及其额度文件不改、不复用。

新增严格ACTION解析，只接受单行ACTION和规范化后的精确admissible match，禁止原作者模糊匹配/首动作fallback。此为显式实验协议变化，不修改作者解析函数。解析失败保留已返回文本并停止，尚未接入真实环境采集。

**范围限制：**完成了传输/预算基础守卫与Mock测试，尚未完成云端collector的环境异常路径、六任务编排及回放端到端集成。由于计费门未通过，没有绕过它继续建设或执行C/D。已有AuditSession/paired_record/冻结Baseline机制保持原样，在新计划中列为必须复用的组件；本轮不声称它们已在真实云端轨迹上通过。

## 计划与源码版本

`api_pilot/plans/round_20261020/plan.json`保存本轮独立计划及source_commit/api_source_sha256；`plan.sha256.json`保存完整哈希。它复制原六任务、任务数据哈希、2/2/2划分、每任务初始Prefix、no_preview/expert_defer/H20、prompt模板与全部原参数，不重新抽样。Smoke只指定第一训练实例，不另抽任务。模型条件明确为OFOX GPT-4o-mini，后端revision未证实；不是本地Qwen基线。

计划执行状态为blocked，collector_integration_complete=false。原Qwen计划与作者Commit `9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3`保持不变。最终指纹及源码Commit见 `reports/evidence/api_round_20261020/final_integrity.json`。

## 验证命令与证据

```bash
PYTHONDONTWRITEBYTECODE=1 .venvs/cinc-audit-py310/bin/python -m unittest discover -s tests/api_pilot -v
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=13 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venvs/cinc-audit-py310/bin/python -m api_pilot.prepare_round
```

第二条仅冻结计划和创建停止状态的账本，没有生成接口调用。create-only拒绝覆盖，不要重复运行来重置账本。最终测试结果见tests_final.log。初次测试失败日志保留：测试误将第156次24-Token预留判为超预算，正确拒绝点为第157次；只修正测试期望，未放宽USD3边界。

## 下一步所需证据

需确认本Key有效fallback/routing设置和计费封顶语义（包括账户额度的缓冲），或取得供应商明确的单请求最大计费规则；无需再提供密钥。不能仅把contract中的false改true或填写伪造attestation。证据补齐后仍须完成collector集成与离线回归，再在既有授权限额内先Smoke、后Pilot。当前不提供假装可执行的六任务命令。

本轮暂停，不开发新算法。P3/P4及独立保留的P1/P2/P5均未改变。可访问状态相等仍不证明完整因果状态等价；expert_defer依赖环境Oracle Planner。

## 本轮最终执行指纹

[执行] 新增和既有API测试合计 **37/37通过，60.550秒**。实现Commit为 `dcc66bd3d6d5f595ab5c5a88dc3935f261a1bae4`。本轮plan SHA256为 `b5f7758bf79ca8604470a2a5d53205305ac2d968affd4bcf43bda39349dca46c`。prepare命令已实际运行并返回BLOCKED，账本为0请求/0预留；原本地plan验证通过。

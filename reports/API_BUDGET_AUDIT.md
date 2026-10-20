# API 新增USD3预算审计

2026-10-20。区分：[执行]本机运行；[Mock]无网络夹具；[文档]供应商公开说明；[未核验]尚无有效证据。

## 当前价格核验与停止依据

[执行] `reports/evidence/api_round_20261020/model.json`由免密钥GET `https://api.ofox.ai/v1/models`取得，HTTP200。不跟随重定向。openai/gpt-4o-mini的prompt/completion单位价为USD0.00000015/0.0000006，context_length128000、max_completion_tokens16384，支持max_tokens、temperature、stop、Chat Completions。旧连接测试实际返回标准Usage三个计数；本轮没有生成调用。

[文档] [定价说明](https://ofox.ai/docs/develop/observability/pricing)明确文本输入、输出及缓存输入计费；[企业说明](https://ofox.ai/enterprise)说明无平台加价，失败请求不收费。这些资料支持名义价格计算，不证明账户有效路由。

[文档] [控制台说明](https://ofox.ai/docs/develop/observability/dashboard)包含全局默认fallback；[fallback说明](https://ofox.ai/docs/develop/advanced/fallback)描述备选模型数组，但本次没有确认空数组覆盖当前全局设置的生效语义。[额度更新记录](https://ofox.ai/docs/changelog)同时描述预算限制及110%警告/缓冲；未核验本Key是否配置额度及其严格截止行为。不能把这些文档解释成已证明USD3实际账单硬上限。

**判断：**名义价格已核验，完整费用上界未核验。遵守用户阶段A第8条，停止在发送前。未把账户设置未知等同于平台必然多收费，也未声称必须通过付费试探才能消除未知。文档审查摘要见source_review.json。

## 账本与预算实现

唯一生产账本位于仓库外 `/home/hly/.config/agent-research/api-agent-20261020.sqlite3`，权限600；round_id=api-agent-20261020。Smoke与Pilot必须共用此路径和round_id。预算为3,000,000,000纳美元（USD3），总数400，禁止各阶段重置。原2026-10-16 probe另属历史实验，其额度文件保持不变。

SQLite BEGIN IMMEDIATE串行化预留；synchronous=FULL及提交在HTTP前完成。请求唯一ID、payload哈希、phase、预留、输出上限、状态落盘；不会落盘认证头或密钥。创建与重开分离：已存在拒绝创建、文件丢失拒绝重开，不自动恢复为零预算。成功也不释放预留；未知发送、超时、中断保留全部预留。未决请求阻止后续请求，不能自动再发送。账本是本地执行约束，不是对恶意删除文件或供应商计费的保证。

名义保守预留使用整个128000输入上下文，不依赖未验证tokenizer字数估算：

- action24时每次128000×150+24×600 = 19,214,400纳美元，即USD0.0192144。
- 64 Token绝对上限时每次USD0.0192384。
- 24 Token同规格最多156次预留后拒绝第157次；64 Token同规格最多155次。
- Smoke≤20次、六任务正常路径≤240次，合计≤260次；总400只是安全阀。全量按最宽64上限预留最多USD5.001984，**不保证能在USD3内完成所有任务**，不能为跑完而释放未对账预留或扩大预算。

这些计算只有在计费规则得到验证后才可用于准入；实际contract.reliable_billing_bound=false，所以生产请求0、预留0。本轮账本快照见budget_snapshot.json。

## HTTP与错误处理

只向已验证ENDPOINT发送；TLS验证开启；requests默认认证/CA环境关闭，代理配置复用；不跟随重定向、重试0、无参数回退、无模型切换代码。60秒SIGALRM墙钟截止覆盖HTTP和解析，socket连接/读取分别10/50秒；不是简单声称read timeout就是总时限。截止不能撤回已被上游接受的请求，所以未知账单保留预留并停止。

模型名、响应格式、finish_reason、Usage类型/合计/界限都检查。额外未知计费字段、非零额外输出类别、非200、非法动作等均停止。错误消息使用固定原因码，不保存服务错误正文、Header或异常原文。异常输入和回包的安全处理已Mock覆盖；真实API协议未重新验证。

## CPU回归证据

新增22项预算/协议测试，另增加进程os._exit中断恢复、实际短墙钟timer两个测试，合计本轮新增24项；连同原13项共37项。最终 **37/37通过，60.550秒**，证据为tests_final.log。

测试覆盖预算边界、400次数、Smoke/Pilot共用、重复请求、发送前跨连接可读预留、已成功预留不退还、未知账单/Usage、未决请求、强制进程退出后重开、HTTP500类/重定向/超时、模型漂移、秘密回包拒绝、ACTION失败不fallback。全部网络为Mock；未知计费测试证明网络和密钥读取均未触发。没有把Mock账单标识为供应商证据。

初轮35项中1项测试期望失败，原因是24输出上限下应在第157次而非156次拒绝；初次日志保留，修正测试后新增两项并重跑。没有改变预算阈值或原Baseline。

## 限制

预算机制不验证供应商合约真伪；不能用人工true标志替代证据。云端collector整合与环境异常端到端停止尚未完成，当前无生产采集CLI。已有作者任务效用继续排除LLM美元成本；预算账本不改变研究utility定义。实际账单无法由本地Token相乘独立证明。

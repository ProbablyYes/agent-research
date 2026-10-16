# API 接口兼容性审查

2026-10-16。依据原作者Commit `9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3`、我方父版本 `891fdc668c0761111c27da5eb06c88ba786b52a8` 和本轮公开目录/单次连接证据。

## 执行验证与未验证边界

[执行] OFOX支持并实际接受了openai/gpt-4o-mini的单用户文本Chat Completions、temperature0、max_tokens16、非流式请求；返回模型名与请求一致、usage可解析。**未发送ALFWorld prompt，未验证stop、confidence前缀、24/8 Token短输出的Agent质量或六任务稳定性。**

[源码] `oversight_branching/local_llm.py`：

- api_base自动追加`/v1/...`，若直接传用户给的完整`https://api.ofox.ai/v1`会变成`/v1/v1/...`。新API草案保存base和完整endpoint，后续适配器直接使用完整endpoint。
- 有transformers且tokenizer可加载时会尝试completions；否则Chat Completions。还可能隐式下载tokenizer。API适配器应固定Chat Completions，不运行该构造逻辑。
- chat请求是单user消息、temperature0、max_tokens、stop。assistant_prefix转为用户消息末尾`Respond starting with: ...`，不能伪造assistant续写。
- `_post_with_retry`对502/503/429/500和超时/连接错误至多5次；400时还可能换max_completion_tokens或删除stop再次提交；completions404也转chat重发。**不可用于本次最多一次请求。**
- 默认requests允许重定向。原错误处理记录response.text前500字符；usage被丢弃，只返回prompt/text。需独立认证传输和费用记录，不能原样复用日志路径。

[源码] `pilot_validity/run.py`：

- MODEL锁定Qwen2.5-7B及revision、本地127.0.0.1:18080。real_model拒绝OPENAI_API_KEY，要求本地权重与服务attestation。源码、包版本、任务文件哈希校验均保留，**没有放宽或伪造**。
- LoggedModel记录prompt/输出，logged_post还记录完整response.text。云端凭据不能进入这些日志，也不能让服务错误正文进入traceback。
- execute逐任务捕获Exception后继续下个任务，这对API失败即停不够。未来API collector必须在传输错误处持久化当前失败和预算，然后终止整个采集；不能简单给原runner注入云端client就声称兼容。
- 正确复用方式是新collector复用AuditSession、paired_record、freeze_baselines、evaluate_frozen等经审计组件；在test生成前冻结train/val规则。新collector仍需验证源码/数据/依赖版本，另建manifest，不覆盖旧plan。

[源码] `alfworld_text.extract_action`先匹配ACTION，再正规化合法动作、模糊匹配cutoff0.6、子串匹配，最后选第一个admissible；没有可行动作则look。解析失败也可能执行有效动作，不能把环境能step当成模型遵守格式。confidence解析失败默认50。未来采集应额外记录解析路径/原始文本/最终动作，但不静默改变作者解析逻辑。

## 本次新增范围

`api_pilot/probe.py`只实现一次安全连通测试，未实现generate_batch或六任务collector；不是声称Agent接口已完成集成。`api_pilot/plans/ofox_gpt4o_mini_draft`是明确禁止执行的独立草案。`pilot_validity/*.py`、原作者文件、旧计划、旧输出没有修改。旧计划仍通过原validate_plan，证据见integrity.json。

离线13项通过不等于API Agent回归通过。后续仍需Mock覆盖累计预算预留/跨进程恢复、任何API错误全局停止、模型/Usage漂移、输入Token限制、所有日志脱敏、Cloud adapter下双分支审计和有效分母。当前没有进行这些尚未实现collector的测试，不将其列为已通过。

## 公开依据

[OFOX Chat Completions](https://ofox.ai/docs/api/openai/chat-completions)、[OFOX Models API](https://ofox.ai/docs/api/openai/models)、[OFOX模型字段及价格单位](https://ofox.ai/docs/develop/models)。本地models.json为实际免认证查询快照；动态目录并非服务版本保证。

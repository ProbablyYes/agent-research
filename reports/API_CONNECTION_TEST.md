# OFOX 单次 API 连通性测试

2026-10-16（UTC+08:00）。**[执行] 连接成功；本阶段真实生成 POST 恰好 1 次。六任务采集 0 次。**

## 配置与安全检查

初次检查：OFOX_API_KEY、OPENAI_API_KEY 均未配置，常用配置位置未发现密钥。请求负责人在服务器终端配置后，实际读取仓库外 `/home/hly/.config/agent-research/ofox.key`，父目录权限700、文件600、文件属当前用户；拒绝文件符号链接。没有从聊天复制密钥到工具命令，没有记录密钥值、长度或指纹。不会将此文件提交Git。

公开文档 [Chat Completions](https://ofox.ai/docs/api/openai/chat-completions) 与用户提供的 `api.ofox.ai` 一致。无密钥 GET `/v1/models`：直连 ConnectTimeout；通过已有系统代理成功 HTTP200、163项。两次均是公开元数据查询，没有认证和生成计费。目录说明见 [Models API](https://ofox.ai/docs/api/openai/models)，实际完整快照及查询证据在 `reports/evidence/api_preflight/`。

[执行] 付费请求唯一目标固定为 `https://api.ofox.ai/v1/chat/completions`，不允许调用者换URL，不跟随任何重定向。requests关闭trust_env（不读netrc、不接受环境CA覆盖），显式沿用无嵌入凭据的HTTPS代理配置，验证目标TLS证书。未记录代理地址。没有向OFOX的其他别名域、Anthropic或Gemini接口发送认证。TLS验证是系统信任链验证，并非证书固定或对代理基础设施的独立审计。

代码：`api_pilot/probe.py`，独立于原作者和冻结本地适配器。发送前仓库外排他创建并fsync单次额度文件 `ofox-connectivity-attempt.json`，超时或进程崩溃也占额度；文件存在则拒绝再次发送。无HTTP重试、无参数回退、无模型fallback；原始请求头、响应头、错误正文、异常消息均不写日志。成功结果仅白名单字段。`.gitignore`增加凭据文件名防护，未来实验目录默认忽略。

## 唯一真实请求结果

| 字段 | 实测 |
|---|---|
| HTTP | 200 |
| Gateway | OFOX |
| 请求模型 / 返回模型 | openai/gpt-4o-mini / openai/gpt-4o-mini |
| 模型开发方 / 目录owned_by | OpenAI / azure（不是实际路由证明） |
| Prompt | Reply with exactly: OK |
| 配置 | temperature=0, max_tokens=16, stream=false；不发送stop |
| 返回格式 | chat.completion；choices[0].message.content |
| 内容验收 | 去首尾空白后等于OK |
| finish_reason | stop |
| Usage | prompt_tokens=12, completion_tokens=1, total_tokens=13 |
| 请求延迟 | 2.957814秒（含连接和代理） |
| 估算费用 | USD 0.0000024；12×0.15/1e6 + 1×0.60/1e6 |
| 实际账单 | **未核验**；没有追加余额/账单认证请求 |
| 异常 / 重试 / 重定向 | 本次POST无异常；0 / 0 |

原始安全结果：`reports/evidence/api_preflight/connection_result.json`；命令输出：`probe_preflight.log`。本次执行命令（**已执行，不要再运行或删除额度文件重试**）：

```bash
PYTHONDONTWRITEBYTECODE=1 .venvs/cinc-audit-py310/bin/python -m api_pilot.probe
```

[执行] 实际请求证明此Key当时可调用该模型该接口；不证明所有模型权限。目录canonical_slug为 `gpt-4o-mini-2024-07-18`，响应只返回别名，无法证明具体权重、实际Azure部署或服务版本。没有使用此结果冒充Qwen实验。

## 离线验证和暂停

[执行] 最终13项单元测试全部通过（0.158秒），仅Mock网络，未再调用生成服务：

```bash
PYTHONDONTWRITEBYTECODE=1 .venvs/cinc-audit-py310/bin/python -m unittest discover -s tests/api_pilot -v
```

涵盖排他额度、超时/500不重试、302不跟随、敏感正文不记录、Usage缺失不算零费用、模型异常、错误JSON、凭据权限/符号链接、任务配置/计划hash隔离。日志 `offline_tests_final.log`。旧本地计划validate_plan通过，原作者工作区干净。完整指纹见 `integrity.json`、`final_integrity.json`。

真实生成额度已用完，立即停止新增API请求。没有启动六任务、GPU、模型下载或新算法实验。

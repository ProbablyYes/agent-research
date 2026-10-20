# 公开轨迹来源审查 — 第一批，2026-10-20

本轮为 **external_public_model_trajectories**；与本实验室此前 GPT-4o-mini/ALFWorld 工程 Pilot 完全分开。未调用收费 API、运行新 Agent、训练模型或修改 Calibration 平台。以下“成功/失败”仅指发布方评分，不是人工裁定的真实任务效用。

## 实际选择与访问结果

| 来源 | 实际检查 | 原始轨迹可访问性 | 本轮决定 |
|---|---|---|---|
| [Failure as a Process](https://arxiv.org/html/2607.09510v1) / [公开包](https://github.com/xz-Sean/cli_trajectory_analysis) | 阅读方法、结果、威胁、README、CODEBOOK；下载一个标注 JSON | README 明示 NO raw trajectories；样例只有标注、短证据及分段，不是完整动作/反馈 | 用于相关工作及方法边界，不作为原始轨迹来源 |
| [Sierra τ²/τ³/τ-bench](https://github.com/sierra-research/tau2-bench) | 官方目录、提交元数据、可视化器 URL 构造、MIT LICENSE、实际 S3 JSON | GET 200；随后带 If-Match 的 Range GET 206；四条完整消息历史可解析并核验 | **唯一选用来源：τ³ / τ-Knowledge banking_knowledge，v1.0.1，GPT-5.6-sol 提交** |
| [SWE-Marathon](https://github.com/abundant-ai/swe-marathon) / [论文](https://www.swe-marathon.org/swe-marathon-paper.pdf) | 论文、README、下载脚本、官网 HTML | README 约 800 GB 日志要求联系作者取 S3 凭据；脚本指定 v1.1/slack-clone/_manifest.json 匿名 GET 返回 403 AccessDenied | 本轮未下载原始轨迹；没有发送邮件或申请凭据。未穷尽网站动态接口，不能断言所有轨迹均不公开 |

来源仓库快照：Failure `ea0a3af006276c31db3807c48b3ef7b5ac2aa72b`；Sierra 目录 `989d3285ae669e49503324bdb9981bf14fccedeb`；SWE-Marathon `8eebe71b0eb1bb7e7f346bb6ac9832bc01cc89db`。URL、下载文件哈希见 `public_trajectory_research/phase1/evidence/source_inventory.json`。此次未再扩展其他 Coding 数据源：两个 Coding 候选的原始访问条件尚不满足，而 Sierra 已满足本轮完整交互审阅需要。这不是对所有 Coding 数据源的排名。

## Failure as a Process 方法与核验边界

论文研究 Terminal-Bench 的三种 scaffold、七种模型组合；报告收集 3,843 次运行，最终保留 1,794 条（610 成功、1,184 失败）。模型包括 Sonnet 4、GPT-5、Gemini 2.5 Pro、Qwen3 Coder 480B、DeepSeek V3.2、Kimi K2、Devstral 2。论文称 71.4% 复用既有公开轨迹，其余补跑；不是本轮新下载得到的原始语料。

其研究范围已经覆盖：错误出现和可观察时刻、事后锁定点、触发因素分类、恢复/失败后续行为、模型及 scaffold 差异，以及仅看前缀的监测。论文采用 Opus 4.6 初稿与双人人工复核，并用 Sonnet 4.6 做前缀监测。不能把这些既有主题直接当作我们的新发现。[论文方法与有效性讨论](https://arxiv.org/html/2607.09510v1)

需要保留的疑点：

- 论文说保留所有 21 组合均可用的 89 任务，又扣除其中 75 次缺失执行；其最终集合不是严格的 89×21 完整矩阵，不能直接称完全配平。
- CODEBOOK 记录单个 LLM 标注流程，并对超过 120 步的轨迹抽读；论文称人类复核完整轨迹。两者可能分别描述初稿与最终复核，但公开包不足以独立核验所有最终人工标签、逐步覆盖和原始证据。不能据此指控造假，也不能替作者消除歧义。
- `t_commit` 是根据实际后续行为定义的事后描述，不证明任何替代干预都无法恢复；前缀采样也使用事后标注位置。
- 仓库 API 未识别许可证，目录未见 LICENSE；论文 CC BY 4.0 不自动赋予仓库全部数据相同许可。仅留本地审查副本。

## τ²、τ³ 与所选版本

[τ² 论文](https://arxiv.org/html/2506.07982v1)研究用户与 Agent 都能改变环境的协作控制；模拟用户不是现实人类。官方仓库把 τ³ 对应到 v1.0 的语音、知识检索域和任务修订。v1.0.1 修复 banking_knowledge 评分；当前 2.0 又修改任务、提示及评审规则。因此本轮不能用当前 main 的任务或分数覆盖历史提交，也不能把 τ³ 当成全新的独立仓库。[官方版本说明](https://github.com/sierra-research/tau2-bench/blob/989d3285ae669e49503324bdb9981bf14fccedeb/README.md)

实际原始对象中：Agent `openai/responses/gpt-5.6-sol`，xhigh；用户模型 `gpt-5.2`，low；retrieval `alltools`；全局 seed 300，本批 trial 0 的 seed 626729；max_steps 200；运行源码 `fc0055dc4e0a316c3f83133267fbd6faaa770992`。发布元数据称评测日 2026-07-22，提交日 2026-08-04，benchmark v1.0.1。后端权重/服务修订无法固定；这里验证的是日志和声明，不独立证明供应商真实运行身份。

它适合第一批的原因是可获得较新模型的完整已发布消息、检索与执行反馈、任务规格及评分依据，且信息检索与行动决策交织。并非因为版本更新本身。限制是金融客服模拟环境，不是 Coding，不是数小时执行，不能外推到所有长程 Agent。

SWE-Marathon 更接近超长程软件工作：20 个任务、隐藏验证与多类验证器，论文分析长程进度和评测规避。脚本区分 v1.0/v1.1，列出 Claude Code/Codex 等与版本化模型配置。任务文件和参考解公开不等于模型轨迹可下载。没有原始日志就不能独立核查其完整性、模型版本或具体评分结果。

## 本地数据、抽样与实际 Schema

目录 `public_trajectory_research/phase1/`；唯一选用原始来源为 manifest 中的 Sierra S3 对象。原对象 150,287,419 字节；初次顺序传输在确认大于预期后中止，临时缓存保留在 `/tmp/public-source-audit/`，未把截断文件当完整 JSON。最终留存并独立 Range 验证前 3,001,199 字节，足够覆盖前十个 simulation；没有声称得到整包 SHA256。原始对象 ETag 不是 SHA256。

选择规则：按发布数组顺序检查前十项，取前两条 reward=1 与前两条 reward=0 的非空完整消息。四条为 task_002/004/007/012，均 trial 0。索引 8 的 task_005 为 infrastructure_error、0 消息、无 reward，保留在 screening，不算任务失败；其他成功记录是未选中，不是删掉异常美化结果。本批为有意平衡的便利样本，2/4 不能估计模型成功率。

实际 Schema：顶层 `timestamp/info/tasks/simulations`；simulation 含 id、task_id、trial、seed、messages、reward_info、termination_reason、duration、cost、policy 等。消息按 role 分型，assistant/user 有 content、tool_calls、usage、raw_data；tool 有 id、requestor、content、error。工具调用参数为对象。评分 basis 分 DB 与 ACTION，不能仅看 db_match。字段类型全集在 `evidence/verification.json`。

原始 simulation 精确字节保留，不重排消息；完整任务与政策保留在 source_metadata。可读版每条消息全字段输出，含工具大段文档、原始响应和 usage，没有把摘要当完整历史。任务规格/评分是分析者事后可见信息，不假设 Agent 当时可见。未证明隐藏推理、完整 provider 请求或未发布内部状态完整。

实际验证命令：

```bash
python3 public_trajectory_research/phase1/scripts/extract.py public_trajectory_research/phase1/raw/source_prefix.bin
python3 public_trajectory_research/phase1/scripts/verify.py
```

四条共 86 消息、41 次工具调用及 41 次匹配返回；哈希、源字节、渲染往返、消息数量、工具关联/先后及发布评分字段一致性全部通过。没有重跑评分器或环境。

许可：Sierra 仓库 MIT 已保存；未找到 S3 对象独立许可。为避免扩大许可假设，原始/可读轨迹和第三方全文只保留本地、不加入 Git；我方报告、脚本、manifest、验证结果可同步。此限制不影响本地四条完整轨迹交付。

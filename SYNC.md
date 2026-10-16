# GitHub 同步

远程仓库：https://github.com/ProbablyYes/agent-research

## 日常更新

在实验室服务器执行：

```bash
cd ~/agent-research
git status
git diff
# 按本次改动选择具体文件，先查看暂存差异
git add README.md UPSTREAM.md SYNC.md .gitignore reports experiments/cinc_smoke_20261016
git diff --cached --stat
git diff --cached
git commit -m "docs: update research audit and experiment evidence"
git push origin main
```

GitHub 不会自动同步本地修改；每次更新需要 commit 和 push。没有配置后台自动上传。原始报告和历史错误证据应保留，不以新结果静默覆盖旧实验结论。

## 新实验

`.gitignore` 默认忽略未来实验目录，避免意外上传大规模运行产物。要保存新实验时，在 `.gitignore` 中显式允许对应目录，检查大小和内容后提交。数据集、模型权重、环境和私钥不提交；保存来源、配置、版本、校验和及适量结果。

## 身份与认证

Git提交署名与GitHub推送认证是两个独立设置。只在本仓库设置署名：

```bash
git config user.name "你的名字"
git config user.email "你的 GitHub 提交邮箱或 noreply 邮箱"
```

推送需要此服务器已获得仓库写入权限。可使用已配置的SSH key，或GitHub HTTPS凭据管理器/CLI认证；不要把访问令牌写入远程URL、脚本、报告或聊天。若使用SSH，完成GitHub账户的公钥登记后再切换：

```bash
git remote set-url origin git@github.com:ProbablyYes/agent-research.git
git push -u origin main
```

在其他机器克隆：

```bash
git clone https://github.com/ProbablyYes/agent-research.git
```

只在工作区干净时拉取他处更新：`git pull --ff-only`。若出现分叉先审查差异，不使用强制推送覆盖远程历史。

## 本实验室服务器配置

本仓库的提交署名为 `jane <3133103927@qq.com>`，仅保存在本地仓库配置。远程使用SSH，仓库级 `core.sshCommand` 指定专用密钥 `~/.ssh/agent_research_github_ed25519`，不修改全局SSH配置。公钥需要在GitHub登记后才能推送。

推荐在本仓库 Settings → Deploy keys 中添加公钥并勾选 Allow write access，将权限限定到这个研究仓库。私钥不上传GitHub、不进入本仓库。GitHub主机公钥从官方HTTPS元数据接口取得，独立保存在 `~/.ssh/agent_research_github_known_hosts`，连接开启严格主机身份校验。

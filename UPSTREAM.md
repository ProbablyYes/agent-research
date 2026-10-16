# 上游与数据来源

本仓库保存实验室研究记录和独立测试，不是论文作者的官方仓库。

- 论文：[Calibration Is Not Control，arXiv v2](https://arxiv.org/abs/2606.21399v2)
- 官方代码：https://github.com/bennidict23/calibration-is-not-control
- 本轮锁定 Commit：`9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3`
- 上游代码许可证：MIT；不代表本研究记录自动继承同一许可证。

在项目根目录准备上游代码（已有目录时不要重复执行）：

```bash
git clone https://github.com/bennidict23/calibration-is-not-control.git
git -C calibration-is-not-control checkout --detach 9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3
```

上游目录通过 `.gitignore` 排除；其完整性记录在 `reports/evidence/final-integrity.json`。

ALFWorld 公开任务文件来源、大小、下载命令见 [ENVIRONMENT_CHECK.md](reports/ENVIRONMENT_CHECK.md)；本次下载 SHA256 已记录在 `reports/evidence/download.log`。独立下载器在 `experiments/cinc_smoke_20261016/download_tasks.py`，不下载模型权重。

本地 `paper-v2.html`、`paper-v2.txt` 和 `get-pip.py` 为外部下载缓存，未纳入Git。报告提及这些文件时指实验室本地副本；需要时从原文链接或 https://bootstrap.pypa.io/get-pip.py 重新取得。

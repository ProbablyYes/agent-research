# 第一个真实模型最小复现：建议，尚未启动

2026-10-16。当前结论：CPU依赖与公开文本任务数据已经准备；真实LLM服务尚未准备，论文完整实验不具备复现证据。以下命令为下一阶段方案，不表示已执行。不得把Synthetic结果写入论文比较表。

## 实验范围与计数

建议先做单模型、单种子、expert_defer、**no_preview**、20步预算，train/val/test各2任务，每任务1个prefix，共6任务、6个初始prefix（2/2/2）。`select_prefix_indices(N,1)`选0，因此只要各split选满2个且reset后能产生至少一个状态，实际就是6；此选择避免把“两点/任务”的上限误称实际数量。真实模型尚未运行，**真实已采集prefix=0**。实际数量必须以输出summary.dataset及CSV行数为准；不满6即验收失败。本方案验证基础管线，不覆盖中途干预问题，不据此收窄P3/P4。

为什么不直接README的8/4/8、每任务2点：后者最多40prefix，短轨迹可少于40；本阶段先做更小的连通性检验，且不预设要复现显著优势。训练仅2行，RF可能退化常数，属于预期的小样本限制。

## 模型和服务环境（未核验）

推荐作者README的 `Qwen/Qwen2.5-7B-Instruct`，官方模型卡参数量7.61B。2026-10-16查询HF API revision为 `a09a35458c702b33eeacc393d103063234e8bc28`。BF16/FP16裸权重约15.22GB十进制≈14.2GiB；加KV cache、运行时预留，估计20–28GiB可运行小并发8K context；建议vLLM memory utilization=.60，约28.8GiB的GPU预算。此为估算，非本机实测。48GB A6000容量上可行，31GiB主机RAM仍需观察加载峰值。来源：[官方模型卡](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)。

为旧驱动单独使用候选vLLM0.6.6服务环境，避免升级CPU审查环境。官方该版本[安装说明](https://docs.vllm.ai/en/v0.6.6/getting_started/installation.html)列出Linux、Python3.9–3.12及CUDA12.1二进制；本机实际加载兼容性仍须验证。不能仅凭nvidia-smi就宣称已可运行。以下环境安装及模型加载均**未执行**，服务启动将下载7B权重，必须等待用户进入下一阶段。

```bash
# 下一阶段才执行：建立独立服务环境，不改现有审查环境
python3 -m venv --without-pip /home/hly/agent-research/.venvs/cinc-vllm066
/home/hly/agent-research/.venvs/cinc-vllm066/bin/python \
  /home/hly/agent-research/reports/evidence/get-pip.py
/home/hly/agent-research/.venvs/cinc-vllm066/bin/python -m pip install \
  'vllm==0.6.6' 'transformers==4.46.3'

# 终端A；此命令会下载权重并占用GPU，当前未执行
unset OPENAI_API_KEY
export HF_HOME=/home/hly/agent-research/data/hf-cinc
export CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=2
/home/hly/agent-research/.venvs/cinc-vllm066/bin/vllm serve \
  Qwen/Qwen2.5-7B-Instruct \
  --revision a09a35458c702b33eeacc393d103063234e8bc28 \
  --tokenizer-revision a09a35458c702b33eeacc393d103063234e8bc28 \
  --host 127.0.0.1 --port 18080 --dtype half \
  --max-model-len 8192 --max-num-seqs 1 \
  --gpu-memory-utilization 0.60 --seed 13 --enforce-eager
```

这里选择当前CPU环境不安装transformers，客户端确定走chat_completions；服务端使用锁定tokenizer。此路径已由源码支持，但真实服务响应尚未测试，也可能与作者当年的completions prompt前缀路径有差异，应在配置中记录，不混合比较。安装vLLM成功后先保存pip freeze和实际torch/CUDA版本；启动失败就停止诊断，不能为解决它修改系统驱动。

## 精确采集和评测命令（未执行）

终端B，在本地服务已就绪且GPU时段已落实后执行：

```bash
set -euo pipefail
source /home/hly/agent-research/.venvs/cinc-audit-py310/bin/activate
unset OPENAI_API_KEY
export ALFWORLD_DATA=/home/hly/agent-research/data/alfworld-cinc-audit
export PYTHONPATH=/home/hly/agent-research/calibration-is-not-control/src
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=13
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CINC_RUN=$(mktemp -d /home/hly/agent-research/experiments/cinc_real_qwen7b_s13_XXXXXX)
printf '%s\n' "$CINC_RUN"
python /home/hly/agent-research/calibration-is-not-control/scripts/collect_alfworld_branches.py \
  --model-path Qwen/Qwen2.5-7B-Instruct \
  --api-base http://127.0.0.1:18080 --api-model Qwen/Qwen2.5-7B-Instruct \
  --api-timeout 60 --intervention-mode expert_defer --verify-mode no_preview \
  --max-episode-steps 20 --train-games 2 --val-games 2 --test-games 2 \
  --prefixes-per-game 1 --seed 13 --batch-size 1 \
  --action-max-tokens 24 --confidence-max-tokens 8 \
  --expert-max-policy-steps -1 --expert-noise-rate 0 \
  --verify-cost 0.05 --wrong-penalty 1 --step-cost 0.01 \
  --output-dir "$CINC_RUN" > "$CINC_RUN/collect.log" 2>&1
python /home/hly/agent-research/calibration-is-not-control/scripts/evaluate_controllers.py \
  "$CINC_RUN" --output-json "$CINC_RUN/controllers.json" > "$CINC_RUN/evaluate.log" 2>&1
```

mktemp确保不覆盖原始数据。evaluate会自动计算两种preview模式，主报告只取 `modes.no_preview.val_selected_policy`，不取 `test_best_policy`。真实输出应另外逐条核对干预分支恢复，因为原summary只检查continue；出现不一致保留原结果并标为无效，不静默修正。当前固定种子未解决os.walk无排序，需保存本次CSV的gamefile清单及数据SHA256，跨机器不能只靠seed。

## 请求量、时间及附加文件

[源码推算] expert模式无专家LLM请求。设6条base轨迹长度B_g、六个continue suffix长度C_i。正常非终止prefix下模型总请求数 `sum(B_g)+6+sum(C_i-1)`；首动作已经在base rollout生成，6是confidence。H=20时上限120+6+114=240请求，最大输出token上限为234*24+6*8=5664；输入token未计。重试可能增加HTTP次数；batch-size对远程请求不是并发。

[未核验估计] 每请求0.3–2秒则LLM服务部分约1–8分钟上限量级；加数据枚举、环境重建、planner和首次模型加载，预留10–30分钟，可能更长。没有跑过本机模型吞吐，不能当测量结果或保证。下载模型时间单列，不包括在此预算。若运行明显异常应停止排障，不自动扩大任务数。

[源码+环境验证] 需要每任务traj_data.json（任务文字/类型）、game.tw-pddl及TextWorld PDDL planner。公开数据包含PDDL，fast-downward已安装；专家由环境planner在线给policy_commands，不需要另下专家LLM、BUTLER checkpoint、MRCNN或视觉ALFRED资源。不需要人工提供expert demonstration文件，但现有traj_data本身就是ALFRED轨迹元数据，应记录其来源。

## 验收及停止条件

1. 恰有2/2/2行真实模型分支数据、6个不同实例；记录真实模型revision、服务版本、生成路径及task manifest。
2. Continue和Intervene都从相同prefix恢复，观察/可行动作/终止标志对齐；不能仅依赖现有summary。
3. u_*能按won、实际suffix步数和成本独立重算；quit=0；regret非负，oracle regret=0。
4. 控制器拟合与CSV重载评估完成，no_preview输入26维；仅验证集调参；没有用测试best成绩代替冻结策略成绩。
5. 有可解释的真实动作与终止记录，不能全靠解析fallback；若全失败仍能说明工程链路运行，但不能说明控制器有效。

成功通过只证明公开管线最小真实模型复现有效。没有统计效力、多seed/多模型/中途prefix、校准/消融/闭环评估，没有重现论文表格；本次发现的评估逻辑问题仍保留。完成此最小实验后也应单独复核，再决定科研实验，不自动进入大规模实验或新算法开发。

[执行补充] 收尾GPU占用已升至约34GB且利用率100%；本次没有启动任何GPU计算。上面的服务命令需要等GPU时段可用后执行，不能把本机开始时空闲误当作资源预约。

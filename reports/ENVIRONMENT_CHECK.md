# 隔离环境检查

2026-10-16，Asia/Shanghai。状态词含义：[执行]已实测，[源码]静态推断，[未核验]未运行。

## 主机与隔离

[执行] Ubuntu 22.04.5 LTS；系统Python 3.10.12；RTX A6000 49140 MiB，驱动535.309.01，nvidia-smi显示CUDA兼容上限12.2（不等于已安装CUDA toolkit）。开始时GPU约673 MiB被桌面进程使用、GPU利用率0%；RAM总31GiB、available28GiB；磁盘available约1.2TB。未终止任何其他进程。gcc/g++/make/git/curl可用，cmake不在系统PATH。

Conda不在PATH，常见个人miniconda/anaconda和/opt/conda目录未发现；这不证明其他用户没有Conda。本任务采用独立venv：

```bash
source /home/hly/agent-research/.venvs/cinc-audit-py310/bin/activate
export ALFWORLD_DATA=/home/hly/agent-research/data/alfworld-cinc-audit
```

[执行] 首次 `python3 -m venv` 因ensurepip缺失失败。未使用sudo/apt，未改系统Python；从官方 https://bootstrap.pypa.io/get-pip.py 下载到 reports/evidence，用该环境bin/python引导pip，随后 `python3 -m venv --without-pip` 补全activate脚本。pyvenv.cfg为include-system-site-packages=false。环境约563MB（安装完成时）。

首次pip安装fast-downward构建时找不到`python`，记录在evidence/pip-install.log；将venv/bin放到PATH后成功，不是修改论文代码。

```bash
PATH=/home/hly/agent-research/.venvs/cinc-audit-py310/bin:$PATH \
CMAKE_BUILD_PARALLEL_LEVEL=2 MAKEFLAGS=-j2 \
/home/hly/agent-research/.venvs/cinc-audit-py310/bin/python -m pip install \
-r /home/hly/agent-research/calibration-is-not-control/requirements.txt
```

[执行] 作者requirements依赖安装完成：numpy2.2.6、scikit-learn1.7.2、alfworld0.4.2、textworld1.7.0、requests2.34.2。四个指定包及全部项目模块正常导入。fast-downward-textworld20.6.4、jericho3.3.1已构建。完整解析版本在 [pip-freeze.txt](evidence/pip-freeze.txt)，安装输出在 [pip-install-retry.log](evidence/pip-install-retry.log)。requests及传递依赖未被作者锁定，此freeze只描述本次环境。

[执行失败/保留] `pip check`报告 `textworld 1.7.0 is not supported on this platform`。已查其WHEEL：Tag行前有空行，已实测邮件metadata解析返回Tag=[]，没有被当作header；直接用packaging解析Tag与系统supported tags交集为True。真实导入正常。没有静默改wheel metadata；实际环境运行结果见SMOKE_TEST_RESULTS。不能把pip check写成通过。

## 任务数据

[执行] 在项目data、个人.cache、/opt及可访问/data中未发现game.tw-pddl。下载前已核实官方Release资产大小与磁盘容量。下载器仅取三个公开任务压缩包，不执行其中脚本，提取前检查路径越界/符号链接和总解压体积上限。

| 官方来源 | 压缩字节 | 解压内容字节 |
|---|---:|---:|
| [0.2.2/json_2.1.1_json.zip](https://github.com/alfworld/alfworld/releases/download/0.2.2/json_2.1.1_json.zip) | 72,018,818 | 1,388,238,167 |
| [0.2.2/json_2.1.1_pddl.zip](https://github.com/alfworld/alfworld/releases/download/0.2.2/json_2.1.1_pddl.zip) | 34,881,784 | 385,547,222 |
| [0.4.0/json_2.1.2_tw-pddl.zip](https://github.com/alfworld/alfworld/releases/download/0.4.0/json_2.1.2_tw-pddl.zip) | 36,493,542 | 344,340,776 |

合计压缩143,394,144字节，解压内容2,118,126,165字节；含压缩包磁盘占用约2.2GiB。实际路径 `/home/hly/agent-research/data/alfworld-cinc-audit/json_2.1.1`（第三个压缩包名字中的2.1.2不等于最终目录名）。SHA256及URL保存在该数据目录download_manifest.json，运行记录evidence/download.log。

已执行的精确下载命令：

```bash
python3 /home/hly/agent-research/experiments/cinc_smoke_20261016/download_tasks.py
```

作者README的标准命令为 `alfworld-download --data-dir "$ALFWORLD_DATA"`，但[官方0.4.2下载器](https://raw.githubusercontent.com/alfworld/alfworld/0.4.2/scripts/alfworld-download)默认额外下载视觉检测器，所以本次未执行。未下载7B/30B、BUTLER、MRCNN或其他权重；未调用推理API。

## 后续环境边界

[未核验] 当前没有安装vLLM/transformers/torch GPU推理栈，没有本地LLM权重。requirements并不提供README里vllm serve所需依赖。真实推理需要另设服务环境，锁定版本并验证驱动兼容；本次未安装或启动它。CPU smoke以单线程BLAS运行；未修改shell启动文件、系统环境、其他用户文件。

[执行补充] 收尾时GPU已为34287MiB、100%利用率。本轮没有GPU进程；机器可用性随其他活动变化，后续启动前必须重新检查，不能视为已预留GPU。最终git状态干净、commit未变。

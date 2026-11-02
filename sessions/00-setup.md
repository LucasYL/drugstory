# 第 0 课：把环境搭起来

> ⏱ 15–25 分钟 · 学到：uv、pytest、「红 → 绿 → 提交」的节奏

这节课不写游戏，只确认一件事：在你的电脑上，「写代码 → 跑测试 → 提交」这条路是通的。以后每节课都走这条路。

## 1. 装 uv

[uv](https://docs.astral.sh/uv/) 是现在最顺手的 Python 项目工具，Python 版本、虚拟环境、依赖一个工具全管。

- macOS / Linux：`curl -LsSf https://astral.sh/uv/install.sh | sh`（macOS 也可以 `brew install uv`）
- Windows（PowerShell）：`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

装完**开一个新终端**，`uv --version` 能打出版本号就行。

## 2. 拿到代码

```bash
git clone https://github.com/LucasYL/coding-practice.git
cd coding-practice
uv sync
```

`uv sync` 会按 `pyproject.toml` 装好合适的 Python 和 pytest，第一次会慢一点。

## 3. 关掉 AI 补全

在编辑器里把 Copilot、Cursor Tab 这类 AI 自动补全关掉（只对这个项目关也行）。普通的语法提示可以留着。这条很重要：手感只能靠自己一个字一个字敲出来。

## 4. 第一次「红 → 绿」

```bash
uv run pytest tests/test_00_setup.py
```

你会看到 2 个红色的 `FAILED`，原因是 `NotImplementedError`。这是正常的：测试已经写好了，代码还没写。

打开 `src/lemonade/hello.py`，把 `raise NotImplementedError` 换成真正的实现，让：

```python
greeting("小明") == "欢迎来到柠檬水摊，小明！"
```

注意逗号和感叹号都是中文全角的。再跑一次测试，全绿就成功了。

## 5. 提交

```bash
git add -A
git commit -m "第 0 课：环境通了"
git push
```

## ✅ 验收

- [ ] `uv run pytest tests/test_00_setup.py` 全绿
- [ ] commit 并 push 了

## 提示

<details>
<summary>提示 1：代码怎么写</summary>

f-string：`f"你好，{name}"`。

</details>

<details>
<summary>提示 2：环境出了问题</summary>

- `uv: command not found`：装完要开新终端。还不行的话，看安装脚本最后打印的提示，把 uv 所在的目录加进 `PATH`
- 下载很慢（比如在国内）：uv 本身可以用 `pip install uv` 装；装依赖可以走镜像：`UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple uv sync`
- 实在不想用 uv（需要 Python 3.11+）：

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate        # Windows：.venv\Scripts\activate
  pip install -e . pytest
  ```

  之后把命令里的 `uv run` 去掉就行，比如直接 `pytest tests/test_00_setup.py`

</details>

## 做完再看

**`uv sync` 做了什么？** 读 `pyproject.toml`，在项目里建一个 `.venv` 虚拟环境，装好依赖，再把你自己的代码以「可编辑模式」装进去。所以测试里能直接 `from lemonade.hello import greeting`，你改了代码也不用重装。`uv.lock` 记下了每个依赖的精确版本，保证每台电脑装出来的环境一模一样，所以它要提交进 git。

**为什么测试先写好？** 测试就是需求：它准确地说明了「做完」长什么样。先看到红、再写到绿，你永远知道自己离完成还有多远。这叫测试驱动开发（TDD）。前几课的测试我来写，越往后越多由你自己写。

---

下一课 → [第 1 课：需求曲线](01-demand.md)

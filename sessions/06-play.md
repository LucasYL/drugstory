# 第 6 课：能玩了！🎉

> ⏱ 25–30 分钟 · 代码：主循环、异常处理、分层 · 设计：反馈要让玩家看得懂

## 这节课做什么

把所有东西接起来：`uv run lemonade`，就能玩一局 14 天的柠檬水摊。

## 规则

`format_report(result, state)` 返回给玩家看的几行字，`state` 是这一天结束之后的状态。至少要有：天气（用 `WEATHER_NAMES` 显示成中文）、做了几杯、卖出几杯、收入、成本、利润、现在的现金。钱都用 `format_money`。具体怎么排版，你自己定。

`main(seed=None, days=DAYS)`：

1. 开场打一句欢迎语（可以用第 0 课的 `greeting`）
2. 每一天：显示第几天、现金、今天的天气 → 用 `input()` 问玩家的决定 → `game.play(...)` → 打印 `format_report(...)`
3. 输入看不懂（`ValueError`）或者钱不够（`NotEnoughCashError`）：打印一行以 `❌` 开头的提示，然后**重新问今天的决定**。不能崩溃，也不能跳过这一天。别的地方不要用 `❌`
4. 游戏结束：打印一行包含「游戏结束」的总结，带上最终的现金

## 开始

- 代码：`src/lemonade/cli.py` 里的 `format_report` 和 `main`
- 测试：`uv run pytest tests/test_06_play.py`
- 再跑一遍全部测试：`uv run pytest`，现在应该全绿了
- **然后玩一局**：`uv run lemonade`

## ✅ 验收

- [ ] 全部测试都绿
- [ ] 完整玩过一局
- [ ] commit + push

## 提示

<details>
<summary>提示 1：思路</summary>

`format_report` 就是拼几行 f-string，再用 `"\n".join(lines)` 连起来。`main` 是一个 `while not game.is_over:` 循环，用 `try/except` 包住「解析输入 + play」这两步。

</details>

<details>
<summary>提示 2：方向</summary>

- 一次接住两种异常：`except (ValueError, NotEnoughCashError) as e:`。`str(e)` 就是抛出时写的那句话
- `continue` 会直接进入下一轮循环。因为 `play` 没成功，所以还是同一天
- 测试是用一个假的 `input` 来喂输入的。你的循环要是多问了一次，测试会直接告诉你

</details>

<details>
<summary>提示 3：伪代码</summary>

```
main(seed, days):
    game = Game(seed=seed, days=days)
    print(greeting("老板"))
    while not game.is_over:
        print(f"—— 第 {game.state.day} 天 · 现金 {format_money(game.state.cash)} · 今天 {WEATHER_NAMES[game.weather]} ——")
        text = input("做几杯、每杯几元？（例如 30 2.5）> ")
        try:
            result = game.play(parse_decision(text))
        except (ValueError, NotEnoughCashError) as e:
            print(f"❌ {e}")
            continue
        print(format_report(result, game.state))
    print(f"游戏结束！最终现金 {format_money(game.state.cash)}")
```

</details>

## 做完再看

**代码：分层。** 现在的结构是这样的：

```
cli.py     界面：只有这里用 print / input     ← 想要网页版，换掉这一层就行
  │
game.py    一局游戏：随机种子、天数、流程
  │
state.py   状态 + step()
  │
rules.py   规则：纯函数
```

每一层只依赖它下面的层。哪天你想要一个好看的网页界面，可以让 AI 写一个新的「皮」去调用 `Game`，下面三层一行都不用改。AI 能不能一下就接上，也是对你接口设计的检验。

**代码：一个小瑕疵。** 钱不够的时候，提示里写的是「分」而不是「元」，因为那句话是 `state.py` 写的，而规则层不知道「元」。怎么改比较好？一个思路是：异常别带写好的句子，而是带上数据（要多少、有多少），让界面层自己组织语言。想改的话，可以当成一道加练题。

**设计：好玩吗？** 认真玩两三局，然后问问自己：好玩吗？大概率不太好玩，你很快会发现每天的最佳做法几乎是固定的。把你的感受记下来。下一段我们先写个 bot 证明这一点，然后动手改设计。

🎉 恭喜，第一个能玩的版本完成了。可以叫 Claude 来 review 这七课的代码。

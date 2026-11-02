# 第 4 课：一局游戏——天气和随机种子

> ⏱ 25 分钟 · 代码：类、`random.Random(seed)`、`@property`、确定性 · 设计：随机性要可控

## 这节课做什么

把「一天」串成「一局」。`Game` 负责三件事：掷骰子决定每天的天气、记住现在是第几天、判断游戏有没有结束。

## 规则

- `Game(seed=None, days=14, start_cash=START_CASH)`
  - 开局是第 1 天，现金是 `start_cash`
  - 每天的天气按 `WEATHER_PROBS` 随机：晴 50%、多云 30%、雨 20%
  - 所有随机数都来自同一个 `random.Random(seed)` 对象。**不要用模块级的 `random.random()`、`random.choice()`**
- `game.state`：当前的 `GameState`
- `game.weather`：今天的天气。早上就知道（暂时 100% 准），读多少次都是同一个值
- `game.play(decision)`：用今天的天气过完今天，返回 `DayResult`。如果游戏还没结束，再决定明天的天气
  - 如果 `step` 抛了异常（比如钱不够），游戏的状态、今天的天气、以后的天气都不能受影响
  - 游戏已经结束了还调用：抛 `GameOverError`
- `game.is_over`：`days` 天都过完了就是 `True`

## 开始

- 代码：`src/lemonade/game.py`
- 测试：`uv run pytest tests/test_04_game.py`

## ✅ 验收

- [ ] 测试全绿
- [ ] commit + push

## 提示

<details>
<summary>提示 1：思路</summary>

在 `__init__` 里就把第一天的天气抽好、存起来。`weather` 只是把存好的值返回。`play` 用完今天的天气，再抽明天的。

</details>

<details>
<summary>提示 2：按概率抽样</summary>

```python
rng = random.Random(42)
rng.choices(["a", "b"], weights=[0.7, 0.3])     # 返回一个列表，比如 ['a']
rng.choices(["a", "b"], weights=[0.7, 0.3])[0]  # 取出那一个
```

`list(WEATHER_PROBS)` 是所有天气，`list(WEATHER_PROBS.values())` 是对应的概率。

</details>

<details>
<summary>提示 3：伪代码</summary>

```
__init__:
    self._rng = random.Random(seed)
    self._days = days
    self.state = GameState(day=1, cash=start_cash)
    self._weather = 抽一次天气

weather:  返回 self._weather
is_over:  返回 self.state.day > self._days

play(decision):
    如果 is_over：抛 GameOverError
    new_state, result = step(self.state, decision, self._weather)  # 出错的话会直接跳出去，后面都不执行
    self.state = new_state
    如果还没结束：self._weather = 再抽一次天气
    返回 result
```

</details>

## 做完再看

**代码：随机种子 = 可复现。** 同一个种子、同样的操作，就是同一个故事。这样玩家报的 bug 能复现，测试能写；以后让 bot 比较两个策略，也能让它们面对一模一样的天气。所有带随机的游戏，工程上都靠这一点。

**代码：为什么不用 `random.random()`？** 模块级的 `random` 是全局共享的：别的代码（比如某个库）多调用一次，你的天气序列就全变了。自己持有一个 `Random` 对象，这局游戏的随机性就只属于它自己。

**代码：失败的操作不能留下半截改动。** `play` 先算出所有结果，最后才更新状态，所以中途出错的时候什么都没变。数据库里管这个叫「原子性」。

**设计：随机要可控。** 随机性让每一局都不一样，但玩家得能理解它、应对它。现在天气早上就公布，而且 100% 准，所以玩家其实没在面对任何风险。记住这一点，第 8 课会改它。

---

下一课 → [第 5 课：读懂玩家的输入](05-input.md)

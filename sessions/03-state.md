# 第 3 课：状态与「过一天」

> ⏱ 20–25 分钟 · 代码：不可变状态、`dataclasses.replace`、自定义异常 · 设计：核心循环

## 这节课做什么

到现在你写的都是规则。这节课把规则串成游戏的心跳：

```
旧状态 + 玩家的决定 + 天气  →  新状态 + 今天的结果
```

不管多复杂的模拟经营游戏，内核都是这样一个函数被一遍遍调用。

## 规则

- `GameState`：`day`（第几天，从 1 开始）、`cash`（现金，单位是分）
- `Decision`：`cups`（做几杯）、`price`（每杯卖多少分）
- `step(state, decision, weather)`：
  - 做这么多杯的成本超过手里的现金：抛 `NotEnoughCashError`（已经在 `state.py` 里定义好了）。钱正好够是可以的
  - 否则用第 2 课的 `sell()` 卖一天，返回 `(新状态, 今天的结果)`：天数加 1，现金加上利润
  - **不能修改传进来的 `state`**，要返回一个新的

## 开始

- 代码：`src/lemonade/state.py`
- 测试：`uv run pytest tests/test_03_state.py`

## ✅ 验收

- [ ] 测试全绿
- [ ] commit + push

## 提示

<details>
<summary>提示 1：思路</summary>

先检查钱够不够，再调用 `sell()`，最后在旧状态的基础上「派生」出新状态。

</details>

<details>
<summary>提示 2：frozen 的 dataclass 怎么「改」</summary>

改不了，但可以造一个新的：

```python
from dataclasses import replace

new = replace(old, cash=old.cash + 100)  # 没写到的字段原样复制
```

或者直接 `GameState(day=..., cash=...)`。

再看一眼 `NotEnoughCashError` 是怎么定义的：自定义异常就是一个继承 `Exception` 的空类。抛的时候带上一句人话：`raise NotEnoughCashError("...")`。

</details>

<details>
<summary>提示 3：伪代码</summary>

```
cost = decision.cups * COST_PER_CUP
如果 cost > state.cash：抛 NotEnoughCashError(f"做 {decision.cups} 杯要 {cost} 分，你只有 {state.cash} 分")
result = sell(decision.cups, decision.price, weather)
new_state = replace(state, day=state.day + 1, cash=state.cash + result.profit)
返回 new_state, result
```

</details>

## 做完再看

**代码：为什么天气是从外面传进来的？** 如果 `step` 自己掷骰子决定天气，你就没法写「雨天做 40 杯会亏 4 块钱」这样的测试了，因为每次跑的结果都不一样。把随机性留在外面，核心逻辑就永远是确定的。下节课专门处理随机。

**设计：核心循环。** 玩模拟经营的人一直在重复：看局面 → 做决定 → 看结果 → 调整。好玩的游戏里，每一轮的决定都有取舍，结果又会改变下一轮的处境。以后你加的每个新系统（口碑、库存、员工……）都可以理解成：给 `GameState` 加字段，给 `step` 加规则。

---

下一课 → [第 4 课：一局游戏](04-game.md)

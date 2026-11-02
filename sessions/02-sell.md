# 第 2 课：卖一天

> ⏱ 20 分钟 · 代码：dataclass、复用已有的函数、边界情况 · 设计：做多了浪费，做少了错过

## 这节课做什么

早上做了 `cups` 杯，每杯定价 `price` 分，在 `weather` 天气下卖一天。结果是什么？

## 规则

- 卖出杯数 = min(做的杯数, 想买的人数)
- 收入 = 卖出杯数 × 价格
- 成本 = 做的杯数 × `COST_PER_CUP`（每杯 0.5 元，卖不掉的也花了钱）
- 利润 = 收入 − 成本，可以是负的
- 没卖完的倒掉，柠檬水不过夜
- 杯数小于 0：抛 `ValueError`。价格或天气不对也是 `ValueError`，不过第 1 课的 `demand()` 已经会检查了，直接复用

## 开始

1. 在 `rules.py` 的 `DayResult` 里加上字段：`weather`（str），以及 `cups_made`、`cups_sold`、`revenue`、`cost`、`profit`（都是 int）
2. 实现 `sell()`
3. `uv run pytest tests/test_02_sell.py`

## ✅ 验收

- [ ] 测试全绿。顺手跑一下 `uv run pytest tests/test_01_demand.py`，确认第 1 课没被改坏
- [ ] commit + push

## 提示

<details>
<summary>提示 1：思路</summary>

先用第 1 课的 `demand()` 算出想买的人数，再一项一项算，最后装进 `DayResult` 返回。

</details>

<details>
<summary>提示 2：dataclass 怎么写</summary>

```python
@dataclass(frozen=True)
class Point:
    x: int
    y: int

p = Point(x=1, y=2)
p.x  # 1
```

写上带类型的字段，`__init__`、`==`、打印格式就都自动有了。

</details>

<details>
<summary>提示 3：伪代码</summary>

```
如果 cups < 0：抛 ValueError
wanted = demand(price, weather)      # 价格和天气的检查顺便就做了
sold = min(cups, wanted)
revenue = sold * price
cost = cups * COST_PER_CUP
返回 DayResult(weather=weather, cups_made=cups, cups_sold=sold,
               revenue=revenue, cost=cost, profit=revenue - cost)
```

</details>

## 做完再看

**代码：`frozen=True`。** 结果算出来以后就不能再改（测试里试图改 `cups_sold` 会报错）。不可变的数据可以放心地传来传去，不用担心哪段代码偷偷改了它。

**代码：`profit` 要不要存？** 它永远等于 `revenue - cost`，存成字段其实是存了一份冗余。另一种写法是用 `@property` 每次现算。两种都能通过测试，想想你更喜欢哪种、为什么。

**设计：做几杯？** 做多了浪费，做少了错过客人。不过现在天气早上就知道，你总能算出「刚好」的杯数，所以这个决定其实没什么难度。第 8 课会让天气预报变得不准，到那时「做几杯」就成了一个真正需要权衡风险的决定。运筹学里管这个叫报童问题（newsvendor problem）。

---

下一课 → [第 3 课：状态与「过一天」](03-state.md)

# 第 1 课：需求曲线

> ⏱ 15–20 分钟 · 代码：纯函数、用整数算钱、参数校验 · 设计：价格和销量的取舍

## 这节课做什么

写柠檬水摊最核心的一条规则：**在这个天气、这个价格下，有多少客人想买。**

## 规则（相当于策划给你的需求）

- 价格极低时会来多少客人，取决于天气：晴 100、多云 60、雨 20（已经写在 `BASE_CUSTOMERS` 里）
- 价格越高客人越少，线性下降。**卖到 5 元（500 分）就一个人都没有了**（`MAX_PRICE`）：

  ```
  想买的人数 = 基础客人数 × (MAX_PRICE − 价格) ÷ MAX_PRICE
  ```

  结果**向下取整**（半个客人不算客人），最少是 0
- 价格小于等于 0：抛 `ValueError`
- 不认识的天气：抛 `ValueError`

例：晴天卖 1 元（100 分），100 × 400 ÷ 500 = 80 人。

## 开始

- 代码：`src/lemonade/rules.py` 里的 `demand()`
- 测试：`uv run pytest tests/test_01_demand.py`

## ✅ 验收

- [ ] 测试全绿
- [ ] `git commit -am "第 1 课：需求曲线"`，然后 `git push`

## 提示（卡住 5 分钟以上再看）

<details>
<summary>提示 1：思路</summary>

两个检查放在最前面。然后查表拿到基础客人数，再乘上「这个价格还剩多少吸引力」。

</details>

<details>
<summary>提示 2：方向</summary>

- 用整数运算：先乘后除。`//` 是向下取整的除法，`7 * 3 // 2` 是 10
- 不让结果变成负数：`max(0, x)`
- `BASE_CUSTOMERS["snowy"]` 抛的是 `KeyError`，不是 `ValueError`。要么先用 `if weather not in BASE_CUSTOMERS:` 检查，要么 `try/except KeyError` 之后再 `raise ValueError(...)`

</details>

<details>
<summary>提示 3：伪代码</summary>

```
如果 price <= 0：抛 ValueError("价格必须大于 0")
如果 weather 不在 BASE_CUSTOMERS 里：抛 ValueError(f"不认识的天气：{weather}")
base = BASE_CUSTOMERS[weather]
返回 max(0, base * (MAX_PRICE - price) // MAX_PRICE)
```

</details>

## 做完再看

**代码：为什么钱用「分」存成整数，不用 float？** 在 Python 里试试 `0.1 + 0.2 == 0.3`。浮点数是二进制的近似值，拿来算钱会一点点累积误差。真实的系统几乎都用最小单位的整数（或者 `Decimal`）存钱，只在显示的时候换算成元。

**代码：纯函数。** `demand` 只看参数、只返回结果，不读会变的全局变量、不打印、不用随机数。这样的函数最好测，也最好推理。整个规则层（`rules.py`）都会是纯函数。

**设计：价格和销量的取舍。** 价格高，每杯赚得多但人少；价格低，人多但每杯赚得少。这是模拟经营里最基本的一种取舍。想一想：每杯成本 0.5 元的话，卖多少钱利润最高？第 7 课会让 bot 去找答案，到时候跟你想的对一下。

---

下一课 → [第 2 课：卖一天](02-sell.md)

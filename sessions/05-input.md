# 第 5 课：读懂玩家的输入

> ⏱ 20–25 分钟 · 代码：字符串处理、输入校验 · 设计：界面说玩家的语言

## 这节课做什么

玩家不会输入「30 杯、250 分」，他们会输入 `30 2.5`。这节课写界面层的两个小工具：把钱显示成 `¥2.50`，把玩家的输入解析成 `Decision`。

## 规则

`format_money(cents)`：

| 输入 | 输出 |
|---|---|
| `275` | `"¥2.75"` |
| `2000` | `"¥20.00"` |
| `5` | `"¥0.05"` |
| `0` | `"¥0.00"` |
| `-50` | `"-¥0.50"` |

`parse_decision(text)`：

- 格式是 `杯数 价格`，价格的单位是元，中间用空格隔开。前后和中间多几个空格都没关系
- `"30 2.5"` → `Decision(cups=30, price=250)`；`"30 3"` → 价格 300；`"30 2.50"` → 价格 250
- 这些情况抛 `ValueError`：
  - 不是正好两部分
  - 杯数不是非负整数（`"2.5"`、`"-5"`、`"abc"` 都不行）
  - 价格不是数字、小于等于 0，或者小数超过两位（`"2.555"`）

## 开始

- 代码：`src/lemonade/cli.py` 里的 `format_money` 和 `parse_decision`
- 测试：`uv run pytest tests/test_05_input.py`

## ✅ 验收

- [ ] 测试全绿
- [ ] commit + push

## 提示

<details>
<summary>提示 1：思路</summary>

- `format_money`：先把符号拿出来，再用整数的 `//` 和 `%` 拆出元和分
- `parse_decision`：先 `split()` 成两段，再分别解析。价格最好别经过 float，可以单独写一个小函数来解析

</details>

<details>
<summary>提示 2：方向</summary>

- `"  12   0.5 ".split()` 得到 `["12", "0.5"]`。不带参数的 `split()` 能处理任意多的空白
- `int("2.5")` 和 `int("abc")` 都会抛 `ValueError`，可以直接利用
- 补零：`f"{5:02d}"` 是 `"05"`
- 拆价格：`"2.75".partition(".")` 得到 `("2", ".", "75")`；小数部分右边补 0：`"5".ljust(2, "0")` 是 `"50"`
- 为什么别用 `round(float(s) * 100)`：它会把 `"2.555"` 悄悄变成 256，而不是报错
- 想用 `Decimal` 也可以，但 `Decimal("abc")` 抛的是 `decimal.InvalidOperation`，它不是 `ValueError`，要接住再转成 `ValueError`

</details>

<details>
<summary>提示 3：伪代码</summary>

```
format_money(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    返回 f"{sign}¥{cents // 100}.{cents % 100:02d}"

parse_price(s):          # 自己写的小帮手
    yuan, _, fen = s.partition(".")
    如果 yuan 不是纯数字，或者 fen 非空但不是纯数字，或者 fen 超过两位：抛 ValueError
    price = int(yuan) * 100 + int(fen.ljust(2, "0"))
    如果 price <= 0：抛 ValueError
    返回 price

parse_decision(text):
    parts = text.split()
    如果 len(parts) != 2：抛 ValueError
    cups = int(parts[0])，如果 cups < 0：抛 ValueError
    返回 Decision(cups=cups, price=parse_price(parts[1]))
```

判断「纯数字」可以用 `str.isdigit()`。

</details>

## 做完再看

**代码：在边界上校验。** 外面进来的数据（玩家输入、文件、网络请求）都不可信，要在进门的地方检查清楚；进了门的数据就可以信任。所以 `parse_decision` 自己检查杯数是不是负的，哪怕后面的 `sell()` 还会再查一次：越早发现，给玩家的提示越准确。

**设计：界面说玩家的语言。** 玩家想的是「元」，引擎算的是「分」。换算只发生在 `cli.py` 这一层，规则层永远不知道「元」的存在。以后要做英文版、换成美元，也只需要改这一层。

---

下一课 → [第 6 课：能玩了！](06-play.md)

# 可视化输出

模板文件位于 Skill 根目录下的 `assets/`，两个文件分别是 `order-confirm.html` 与 `order-detail.html`。顶层 `SKILL.md` 已用加载式引用指向它们，本文件只说明怎么用，不再重复发起引用。

## 一、什么时候出卡片

| 时机 | 用哪张卡 | 前置条件 |
|---|---|---|
| 双预算求解完成、等用户确认下单 | 确认卡 `order-confirm.html` | 已有 `calculate-price` 的报价与 `fat_ratio.py` 的营养结论 |
| `create-order` 成功后 | 订单卡 `order-detail.html` | 已有 `orderId`、`payId`、`expirePayTime` |
| 用户回报支付结果、`query-order` 返回新状态后 | 订单卡 `order-detail.html` 重出一次 | 已有新的 `orderStatus` |

**只在这三个时机出卡片。** 用户只是问某个商品价格或热量、或只做一次校验券时，按精简流程用文字回答，不出卡片。

## 二、三条渲染路径的能力不同

按宿主能力从高到低选择，**不允许因为渲染不可用而少给信息**。

| 路径 | 何时用 | 点击能否回传 | 交互怎么办 |
|---|---|---|---|
| 内联卡片（默认） | 宿主能渲染可视化片段 | **能**，走 `sendPrompt` | 渲染真控件 |
| 导出 HTML | 用户要求保存、分享，或需把取餐二维码拿到线下用 | **不能**，页面已脱离宿主 | 模板内置兜底：点击后在卡内显示一段「请回到对话里发送这句」的文本供复制。**不得在正文里承诺点击会自动执行** |
| Markdown 降级 | 宿主不支持可视化渲染 | 不能，无控件 | 交互项写成编号选项，让用户回数字 |

导出壳：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>麦当劳下单确认</title>
<style>
  body { margin: 0; padding: 24px 16px; background: #F1EFE8;
         display: flex; justify-content: center;
         font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; }
</style>
</head>
<body>
<!-- 在这里粘贴替换后的卡片片段 -->
</body>
</html>
```

模板内的 `var(--color-xxx, 回退值)` 已内置浅色回退，离开宿主样式表也能正常显示，不需要额外改动。

## 三、设计规范

两张卡共用一套 token。**改样式必须回到这一节改，不要在片段里另造颜色和字号**，否则两张卡会分叉。

### 色彩

| 用途 | 取值 | 说明 |
|---|---|---|
| 品牌黄 | `#FFC72C` | 品牌条左段、门店标签圆点、实付区左侧标条、取餐凭证底色、取餐图标底，以及拱门描边。**黄只当底色，唯一的图形用法是拱门，且必衬品牌红底**。黄底上只压深色文字（`#2C2C2A` 8.9:1、`#7A4B00` 4.8:1），绝不压白字 |
| 品牌红 | `#DA291C` | 品牌条右段、拱门底衬、「麦当劳」字标、主推进按钮、实付金额。白字压红底 4.9:1；红字压白底 4.9:1、压灰底 4.5:1，均达标 |
| 正文/标题 | `var(--color-text-primary, #2C2C2A)` | 卡片内所有需要读的文字 |
| 次级文字 | `var(--color-text-secondary, #5F5E5A)` | 标签、地址、说明。**不要用 `#888780`**，它压白底只有 3.3:1，不达标 |
| 分隔线 | `var(--color-border-tertiary, #E3E1D9)` | 1px 实线。不叠加阴影做层次 |
| 内嵌块底色 | `var(--color-background-secondary, #F7F6F2)` | 主数字区、取餐行 |
| 暖色标签底 | `#FFF6DC`／字 `#7A4B00` | 门店来源标签（「已匹配最近门店」） |
| 档位色 | 不油腻 `#3B6D11`／尚可 `#854F0B`／偏油腻 `#A32D2D` | 由 `{{FAT_TIER_COLOR}}` 传入 |
| 状态色 | 待支付 `#FAEEDA`/`#854F0B`；配餐中 `#E6F1FB`/`#185FA5`；已完成 `#EAF3DE`/`#3B6D11`；已取消 `#F1EFE8`/`#5F5E5A` | 由 `{{STATUS_BG}}`/`{{STATUS_FG}}` 传入 |

**品牌黄不能单独用在白底上。** `#FFC72C` 压白底只有 1.6:1，图形和文字都看不见。要把金色拱门画成品牌黄，就必须先给它一块品牌红圆角底衬——黄压红实测 **3.12:1**，过 WCAG 1.4.11 的非文本 3:1 线。其余场合 `#FFC72C` 只作为**底色**出现，负责承载深色内容。这条决定了拱门的两套形态：品牌行里是「红底衬黄拱」，取餐凭证块里是「黄底压深色内容」。

### 字阶与字重

| 层级 | 字号 | 字重 | 用在哪 |
|---|---|---|---|
| 主金额 | 30px（窄屏 26px） | 500 | `{{PAYABLE}}` |
| 取餐号 | 40px（窄屏 32px），等宽 + `letter-spacing:.06em` | 500 | 已分配的 `pickupCode` |
| 指标数字 | 20px | 500 | 热量、脂肪供能比 |
| 卡片标题 | 15px | 500 | 门店名 |
| 正文 | 13px | 400 | 商品名、金额明细、地址 |
| 辅助 | 12px | 400 | 距离、取餐说明 |
| 区块标签 | 11px，`letter-spacing:.06em` | 500 | 「实付」「热量」「商品明细」等小写标签 |

**只用 400 和 500 两个字重**。中文字体在 600 及以上容易跳到 700，视觉过重，且宿主与浏览器表现不一致。

### 结构常量

- 卡片：`max-width:600px`、`border-radius:14px`、`1px` 边框、水平内边距 `20px`
- 内嵌块：`border-radius:12px`
- 小控件与列表项：`border-radius:10px`
- 药丸标签：`border-radius:999px`
- 垂直节奏以 4 为基准（4/8/12/16/20），允许 ±1 微调（11/13/15），区块之间用 1px 分隔线而不是加粗留白
- **顶部品牌条**：`height:6px`，黄 `#FFC72C` 62% + 红 `#DA291C` 38%，两张卡都有
- **品牌行**：紧接品牌条，在内容之上，两张卡都有。左起依次是金色拱门、「麦当劳」、「McDONALD'S」；右端固定留给状态类标签（确认卡放渠道，订单卡放订单状态）

品牌条与品牌行是两张卡共同的头部，改一处就要改另一处，否则两张卡会看起来不像同一个产品。

### 金色拱门

用内联 SVG，不要引外部图片。唯一一份路径数据，直接复制：

```html
<svg width="26" height="22" viewBox="0 0 48 40" fill="none" aria-hidden="true" style="flex-shrink:0;display:block;">
  <rect width="48" height="40" rx="9" fill="#DA291C"/>
  <path d="M5 37.5C5 14.2 9.3 3.2 14 3.2c5.2 0 8.9 15.5 9.8 34.3C24.7 18.7 28.4 3.2 33.6 3.2c4.7 0 9 11 9 34.3" stroke="#FFC72C" stroke-width="5.4" stroke-linecap="round" stroke-linejoin="round" transform="translate(24 20) scale(.8) translate(-24 -20)"/>
</svg>
```

尺寸固定 26×22，不缩放。**三层缺一不可**：

1. `<rect>` 品牌红圆角底衬（`rx:9`，铺满 48×40 视框）。少了它，黄色描边压白底只有 1.6:1，等于没画。
2. `<path>` 金色拱门，品牌黄 `#FFC72C` 描边、`stroke-width:5.4`。拱门靠**描边**成形而不是填充，改 `stroke-width` 会改粗细比例，不要动。
3. `transform` 把拱门缩到 0.8 并居中。原始路径在视框里几乎顶满四边，直接叠上去描边会被底衬裁掉。

`aria-hidden="true"` 必须保留——它是装饰，屏幕阅读器读「麦当劳」那三个字就够。

### 无障碍

- 所有文字对比度 ≥4.5:1；`#888780` 只允许出现在非文字元素上
- 按钮触摸高度 ≥40px（`padding:11px` + 13px 字号）
- 按钮带 `:focus-visible` 焦点环，键盘可见
- 窄屏（≤430px）下：双栏指标改单栏、按钮行改纵向堆叠
- 尊重 `prefers-reduced-motion`，关闭过渡动画
- 卡片开头有视觉隐藏的 `<h2>` 摘要，供屏幕阅读器读出这是哪张卡

## 四、交互控件

### 回传机制

模板末尾定义了函数 `act(text)`：宿主提供 `sendPrompt` 时调用它，点击产生的文本**以用户身份成为一条对话消息**，Agent 按普通输入接住执行；宿主没提供时，改在卡片内显示同样的一段可复制文本，不让点击落空。

因此**每个控件的文案必须自带完整指代**，不能只写「确认」「好的」——回传后 Agent 只能看到这句话本身，看不到点击发生在哪张卡上。写法是「动作 + 对象 + 关键事实」：

| 控件 | 回传文本写法 |
|---|---|
| 确认并下单 | `按当前方案下单：<门店名>·实付 <x> 元·<餐品简称>` |
| 换门店 | `换成门店 <storeCode> <门店名>` |
| 调整方案 | `调整方案：<要改的维度，如「再便宜 5 元」>「换成不油腻的」` |
| 查询支付状态 | `我付好了，查一下订单 <orderId> 的状态` |
| 取消订单 | `取消订单 <orderId>` |

### 按钮清单与授权边界

| 卡片 | 控件 | 回传后 Agent 要做什么 |
|---|---|---|
| 确认卡 | 确认并下单 | 复述门店、金额、餐品后调 `create-order` |
| 确认卡 | 换门店 | **重跑逐家校验**：用新门店的渠道参数重取菜单、券、报价，再重出确认卡 |
| 确认卡 | 调整方案 | 回到双预算求解，按新约束重算 |
| 订单卡 | 查询支付状态 | `query-order` 取最新状态后重出订单卡 |
| 订单卡 | 取消订单 | **先复述订单号、金额、门店、商品，取得一次明确确认**再调 `cancel-order` |

**点击构成用户确认，但只限非破坏性动作。** 下单、换门店、调整方案属于用户主动推进，回传即视为确认；**取消订单是破坏性动作，控件只发起请求，不直接执行**。任何控件都不构成「无需确认即执行删除、覆盖、扣费」的授权。

### 按钮外观

真控件用 `button` 标签，配三种 class，不要自己拼样式：

| class | 用在哪 | 外观 |
|---|---|---|
| `mcd-primary` | 主推进动作（确认并下单、我付好了查状态） | 红底白字，`flex:1.5` |
| `mcd-ghost` | 次要动作（调整方案） | 透明底 + 边框，`flex:1` |
| `mcd-danger` | 破坏性动作（取消订单） | 透明底，红字，悬停才染色 |
| `mcd-store` | 换门店列表项 | 整行可点，左门店名右距离 |

按钮行容器用 `class="mcd-actions"`，`display:flex;gap:10px`。触发 `sendPrompt` 的按钮按平台惯例在文案末尾加 `↗`。同一行最多两个；换门店是列表，每项独占一行。

## 五、模板占位符映射

### 确认卡（order-confirm.html）

| 占位符 | 取值来源 |
|---|---|
| `{{STORE_LABEL}}` | 门店上方的小字标签。自动匹配到时填「已匹配最近门店」；用户自己指定门店填「指定门店」；麦乐送与团餐填「可配送门店」 |
| `{{STORE_NAME}}` | 门店查询接口或 `query-meals` 返回的门店名称 |
| `{{ADDRESS}}` | 到店自取与得来速填门店地址；麦乐送与团餐填 `delivery-query-addresses` 对应的配送地址 |
| `{{STORE_DISTANCE}}` | 到店与得来速填「距「<锚点文本>」<x> 米」，超过 1000 米换算为公里保留一位小数；麦乐送与团餐填「该地址可配送门店，接口不提供距离」。渲染在门店来源标签的同一行右端 |
| `{{CHANNEL}}` | 渠道标签：到店自取、得来速、麦乐送、企业团餐。渲染在品牌行右端，与拱门、「麦当劳」同一行 |
| `{{STORE_OPTIONS_BLOCK}}` | 换门店控件区，见第七节。无可换门店时整块留空 |
| `{{ITEMS_BLOCK}}` | 方案商品，含换配与特调标注，见第七节 |
| `{{PAYABLE}}` | `calculate-price` 的 `data.price` ÷ 100，保留两位，**含 `¥` 符号**。整块用品牌黄左标条强调，金额本身用品牌红 |
| `{{ENERGY}}`、`{{ENERGY_UNIT}}` | `fat_ratio.py` 的 `energyKcal`；无营养数据时两处都填 `—` |
| `{{FAT_PERCENT}}`、`{{FAT_TIER}}` | `fat_ratio.py` 的 `fatEnergyPercent` 与 `tier`；无数据时填 `—` |
| `{{FAT_BAR_WIDTH}}` | 刻度条填充宽度，**必须是 `<数字>%` 形式，取值等同脂肪供能比的百分数**（如 `39.7%`）。**无营养数据时填 `0%`，绝不能留空或填 `—`**——留空会让浏览器按 `auto` 渲染成满格，直接把「没数据」显示成「满格」，是误导性错误 |
| `{{FAT_TIER_COLOR}}` | `不油腻` 用 `#3B6D11`；`尚可` 用 `#854F0B`；`偏油腻` 用 `#A32D2D` |
| `{{AMOUNT_BLOCK}}` | 金额明细行，见第七节。报价只返回总额、拆分不出明细时整块留空 |
| `{{NOTICE_BLOCK}}` | 双维度提示，可空；见第七节 |
| `{{TAKEWAY}}` | `takeWayList` 中选定项的文案 |
| `{{ACTIONS_BLOCK}}` | 确认并下单与调整方案控件，见第七节 |

### 订单卡（order-detail.html）

| 占位符 | 取值来源 |
|---|---|
| `{{STORE_NAME}}` | 订单返回的门店名称 |
| `{{ADDRESS}}` | 门店地址，或外送订单的收货地址 |
| `{{ORDER_ID}}` | `create-order` 的 `orderId`，模板已加「订单号」前缀，只填数字 |
| `{{STATUS_TEXT}}` | `orderStatus` 的**中文文本**，不取 `status` 数字码 |
| `{{STATUS_BG}}`、`{{STATUS_FG}}` | 待支付 `#FAEEDA`/`#854F0B`；配餐中 `#E6F1FB`/`#185FA5`；已完成 `#EAF3DE`/`#3B6D11`；已取消 `#F1EFE8`/`#5F5E5A` |
| `{{PICKUP_CODE_BLOCK}}` | 取餐凭证区，三态处理见第六节 |
| `{{ITEMS_BLOCK}}` | 订单内的商品与子项 |
| `{{AMOUNT_BLOCK}}` | 金额明细行，见第七节 |
| `{{DELIVERY_BLOCK}}` | 仅外送与团餐填；`deliveryInfo` 的收件人、地址、预计送达 |
| `{{EXPIRY_BLOCK}}` | 仅未支付时填；`expirePayTime` |
| `{{ACTIONS_BLOCK}}` | 按订单状态给控件，见第七节 |

## 六、取餐号的三态处理

`pickupCode` 只在门店接单配餐后才被分配。实测三种状态：

| 状态 | `pickupCode` 实测值 | 卡片怎么显示 |
|---|---|---|
| 下单后未支付 | `""` 空串 | 显示「支付后生成」，并说明取餐号在支付并进入配餐后才有 |
| 已取消 | `""` 空串 | 同未支付 |
| 已完成 | `35054` | 用 40px 等宽数字展示，占满凭证区 |

**绝不**在 `pickupCode` 为空时拿订单号、`payId` 或任何数字顶替。宁可显示「支付后生成」，也不给一个用户到了门店却取不到餐的号码。

凭证区是订单卡的视觉焦点——用户站在柜台前举着手机看的就是这一块，所以它整块用品牌黄 `#FFC72C` 打底，是卡片里唯一的满色区。两种形态占同样的位置和体量，不因为「还没分配」就缩成一行小字。

黄底上的文字**只能取深色**：已分配用 `#2C2C2A`（8.9:1），未分配用 `#7A4B00`（4.8:1）。不要用白字，白字压品牌黄只有 1.9:1。

未支付时的凭证区片段：

```html
<div style="margin:14px 20px 0;padding:15px 16px;border-radius:12px;background:#FFC72C;">
  <p style="margin:0;font-size:11px;font-weight:500;letter-spacing:.06em;color:#7A4B00;">取餐号</p>
  <p style="margin:5px 0 0;font-size:13px;line-height:1.5;color:#7A4B00;">支付后生成，门店接单配餐时分配</p>
</div>
```

已分配时的凭证区片段：

```html
<div style="margin:14px 20px 0;padding:15px 16px;border-radius:12px;background:#FFC72C;">
  <p style="margin:0;font-size:11px;font-weight:500;letter-spacing:.06em;color:#7A4B00;">取餐号</p>
  <p class="mcd-num mcd-code" style="margin:4px 0 0;font-size:40px;font-weight:500;letter-spacing:.06em;line-height:1.05;color:#2C2C2A;font-family:var(--font-mono,ui-monospace,Consolas,monospace);font-variant-numeric:tabular-nums;">{{PICKUP_CODE}}</p>
</div>
```

`lockerCode`（取餐柜密码）与 `lockerQrCode`（取餐柜二维码）非空时，在上面这块的下面接一行同样黄色底的说明，或按接口返回的原始指令渲染二维码：以图片语法输出，图片地址取 `lockerQrCode` 字段的值，不要改写该地址。二维码是深色前景，压品牌黄底可扫。

## 七、可复用区块

**每个 BLOCK 占位符自带完整的外层盒模型（`padding` / `border-top` / `margin`）**，模板只决定它插在哪个位置。唯一例外是 `{{ITEMS_BLOCK}}`——它的区块标题固定在模板里，所以它只输出商品行，不带外层内边距。这样设计是为了让空块天然无痕：换了裁剪条件导致某块为空时，不会留下一道孤立的边框。

### `{{STORE_OPTIONS_BLOCK}}`

只在到店自取与得来速下提供，且必须取自第二步**顺延过程中已经查过的门店**，不为凑选项而多调接口。列表项用 `mcd-store`：

```html
<div style="padding:14px 20px 16px;border-top:1px solid var(--color-border-tertiary,#E3E1D9);">
  <p style="margin:0 0 10px;font-size:11px;font-weight:500;letter-spacing:.06em;color:var(--color-text-secondary,#5F5E5A);">附近还有这两家，点一下就换过去重新算</p>
  <div style="display:grid;gap:8px;">
    <button type="button" onclick="act('换成门店 1960207 麦当劳武汉白沙洲龙湖天街餐厅')" class="mcd-store"><span>麦当劳武汉白沙洲龙湖天街餐厅</span><span class="mcd-go mcd-num" style="flex-shrink:0;font-size:12px;color:var(--color-text-secondary,#5F5E5A);font-variant-numeric:tabular-nums;">1710 米 ↗</span></button>
    <button type="button" onclick="act('换成门店 1960208 麦当劳武汉保利心语餐厅')" class="mcd-store"><span>麦当劳武汉保利心语餐厅</span><span class="mcd-go mcd-num" style="flex-shrink:0;font-size:12px;color:var(--color-text-secondary,#5F5E5A);font-variant-numeric:tabular-nums;">1855 米 ↗</span></button>
  </div>
</div>
```

麦乐送与团餐下没有距离可用，此时该区块只列出可配送门店供选择，不标距离、不排序。

### `{{ITEMS_BLOCK}}`

每个商品一行，子项缩进在下方。有换配或特调时在右侧加标注。**不输出外层内边距**。

```html
<div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;">
  <span style="font-size:13px;font-weight:500;">麦香鸡中套餐　<span style="font-weight:400;color:var(--color-text-secondary,#5F5E5A);">×1</span></span>
  <span class="mcd-num" style="flex-shrink:0;font-size:13px;font-weight:500;font-variant-numeric:tabular-nums;">¥27.50</span>
</div>
<div style="margin-top:9px;padding-left:11px;border-left:2px solid var(--color-border-tertiary,#E3E1D9);display:grid;gap:6px;">
  <div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;">
    <span style="font-size:13px;color:var(--color-text-secondary,#5F5E5A);">麦香鸡</span>
    <span style="font-size:12px;color:#854F0B;">不要生菜</span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;">
    <span style="font-size:13px;color:var(--color-text-secondary,#5F5E5A);">无糖可口可乐中杯</span>
    <span style="font-size:12px;color:#185FA5;">同价换配</span>
  </div>
</div>
```

子项用**左侧 2px 竖线**表示从属关系，替代原来的色块占位——色块既占地方又不承载信息。**不要引用 `productImage`** 的远程地址：该域不在内联渲染的允许来源内，能否加载未经验证，用错会直接白屏。

多个商品时重复上面的整块，块与块之间留 `14px` 间距。

### `{{AMOUNT_BLOCK}}`

自带 `border-top`，空块无痕。

```html
<div style="padding:14px 20px 16px;border-top:1px solid var(--color-border-tertiary,#E3E1D9);">
  <p style="margin:0 0 9px;font-size:11px;font-weight:500;letter-spacing:.06em;color:var(--color-text-secondary,#5F5E5A);">费用构成</p>
  <div style="display:grid;gap:7px;">
    <div style="display:flex;justify-content:space-between;font-size:13px;"><span style="color:var(--color-text-secondary,#5F5E5A);">商品小计</span><span class="mcd-num" style="font-variant-numeric:tabular-nums;">¥27.50</span></div>
    <div style="display:flex;justify-content:space-between;font-size:13px;"><span style="color:var(--color-text-secondary,#5F5E5A);">无糖可口可乐中杯换配</span><span class="mcd-num" style="color:#3B6D11;font-variant-numeric:tabular-nums;">¥0.00</span></div>
    <div style="display:flex;justify-content:space-between;font-size:13px;font-weight:500;margin-top:3px;padding-top:9px;border-top:1px solid var(--color-border-tertiary,#E3E1D9);"><span>实付</span><span class="mcd-num" style="font-variant-numeric:tabular-nums;">¥27.50</span></div>
  </div>
</div>
```

优惠或换配的金额变化用 `#3B6D11` 表示省钱。金额一律取自 `calculate-price` 或订单返回值，不自行推算。外送场景必须把运费与打包费单列，不并入商品小计。

### `{{NOTICE_BLOCK}}`

只在存在需要用户同时看两个数字的情形时填，否则整块删掉。典型是换配后热量下降但脂肪供能比上升：

```html
<div style="margin:12px 20px 0;padding:11px 13px;border-radius:10px;background:#FAEEDA;border-left:3px solid #854F0B;">
  <p style="margin:0;font-size:12px;line-height:1.6;color:#854F0B;">换无糖可乐省 147 大卡，但脂肪供能比由 32.4% 升至 39.7%，档位从「不油腻」降为「尚可」。两个数字要一起看。</p>
</div>
```

### `{{DELIVERY_BLOCK}}` 与 `{{EXPIRY_BLOCK}}`

只在对应场景填。`DELIVERY_BLOCK` 用于外送与团餐的收件人、地址、预计送达；`EXPIRY_BLOCK` 只在订单未支付时填，显示支付截止时间。两块都是自带 `border-top` 的说明区：

```html
<div style="padding:14px 20px 16px;border-top:1px solid var(--color-border-tertiary,#E3E1D9);">
  <p style="margin:0 0 9px;font-size:11px;font-weight:500;letter-spacing:.06em;color:var(--color-text-secondary,#5F5E5A);">配送信息</p>
  <div style="display:grid;gap:7px;font-size:13px;">
    <div style="display:flex;justify-content:space-between;"><span style="color:var(--color-text-secondary,#5F5E5A);">收件人</span><span>张三</span></div>
    <div style="display:flex;justify-content:space-between;gap:16px;"><span style="flex-shrink:0;color:var(--color-text-secondary,#5F5E5A);">地址</span><span style="text-align:right;">幸福小区 8 栋</span></div>
  </div>
</div>
```

未支付时的支付截止提示用同一结构，标题换成「支付」，正文写「请在 <`expirePayTime`> 前完成支付，超时订单将自动取消」。

### `{{ACTIONS_BLOCK}}`

自带底部内边距与外层分隔，插在卡片末尾。确认卡的形态，第一个控件是主推进：

```html
<div class="mcd-actions" style="padding:14px 20px 18px;border-top:1px solid var(--color-border-tertiary,#E3E1D9);background:var(--color-background-secondary,#F7F6F2);display:flex;gap:10px;">
  <button type="button" onclick="act('按当前方案下单：麦当劳武汉板桥地铁A口得来速餐厅·实付 27.50 元·麦香鸡中套餐')" class="mcd-primary" style="flex:1.5;padding:11px 0;border-radius:10px;">确认并下单 ↗</button>
  <button type="button" onclick="act('调整方案：想要更便宜的')" class="mcd-ghost" style="flex:1;padding:11px 0;border-radius:10px;">调整方案 ↗</button>
</div>
```

订单卡的形态按状态给：未支付时两个控件；已完成时只留查询；已取消时不渲染控件。

```html
<div class="mcd-actions" style="padding:14px 20px 18px;border-top:1px solid var(--color-border-tertiary,#E3E1D9);background:var(--color-background-secondary,#F7F6F2);display:flex;gap:10px;">
  <button type="button" onclick="act('我付好了，查一下订单 <订单号> 的状态')" class="mcd-primary" style="flex:1.5;padding:11px 0;border-radius:10px;">我付好了，查状态 ↗</button>
  <button type="button" onclick="act('取消订单 <订单号>')" class="mcd-danger" style="flex:1;padding:11px 0;border-radius:10px;">取消订单 ↗</button>
</div>
```

取消控件照原样输出即可，二次确认由 Agent 在收到回传后完成。

## 八、Markdown 降级等价模板

宿主不支持内联渲染时按此输出，**信息项与卡片完全一致**，不得因为降级而省略。交互项改成编号选项，让用户回数字：

```markdown
## 待确认下单

**麦当劳武汉板桥地铁A口得来速餐厅**（已匹配最近门店）
巡司河片区8#-1（地块4）
距「湖北工业大学」656 米
渠道：到店自取

### 商品
| 商品 | 数量 | 金额 |
|---|---|---|
| 麦香鸡中套餐 | 1 | ¥27.50 |

子项：麦香鸡（不要生菜）、中薯条、无糖可口可乐中杯（同价换配）

### 营养
- 热量：658 大卡
- 脂肪供能比：39.7%（尚可）

### 金额
- 商品小计：¥27.50
- 实付：¥27.50

### 取餐
- 取餐号：支付后生成
- 取餐方式：外带

### 你要做什么
1. 按当前方案下单
2. 换门店：白沙洲龙湖天街（1710 米）
3. 换门店：保利心语（1855 米）
4. 调整方案

回复序号即可。
```

## 九、纪律

1. 输出前逐项检查，**不得残留任何 `{{...}}` 占位符**。
2. 卡片里的金额、热量、脂肪供能比必须来自工具或脚本的返回，**一处都不许估**。取不到就填 `—` 并在正文说明原因。
3. **`{{FAT_BAR_WIDTH}}` 必须按第五节规则填成百分比**，无营养数据时填 `0%`。这一项填错的后果是视觉上说谎，不是排版难看。
4. 卡片不是唯一出口。降级路径的信息项必须与卡片对齐，不能因为换了形态就少给字段。
5. 卡片只承载「要核对的事实」。方案之间的取舍理由、超标多少、为什么推荐这个，写在正文里，不塞进卡片。
6. **每个控件的回传文案必须自带完整指代**（门店名、金额、订单号、`storeCode`），不能依赖上下文——Agent 只看到那句话本身。只有「确认」二字的载荷一律视为无效，要重新问。
7. **破坏性动作的控件只发起请求，不直接执行。** 取消订单的回传必须先复述订单号、金额、门店、商品，取得一次明确确认后才调 `cancel-order`。
8. **换门店的回传必须重跑校验**：用新门店的渠道参数重取菜单、券、报价，不沿用旧门店的商品码与价格。
9. 导出 HTML 路径下点击无法回传，模板会自动显示可复制文本，**不得在正文里声称点击会自动执行**。
10. **改样式回到第三节改。** 不要在片段里临时另造颜色、字号或圆角，那会让两张卡分叉，也会让无障碍对比度失去已验证的基准。
11. **`<style>` 里的每条 class 选择器都必须带 `.mcd-card` 前缀**（含 `@media` 内部）。内联渲染时这段样式会注入宿主页面，裸类选择器（如 `.mcd-num`）会外溢到宿主自己的元素上，是实打实的污染。
12. **品牌元素按第三节的固定写法用，不改尺寸、描边宽度和颜色。** 金色拱门是「品牌红圆角底衬 + 品牌黄描边」的三层 SVG（26×22，`stroke-width:5.4`），把它改成填充、去掉底衬、或放大缩小，都会立刻显出「山寨」感——品牌识别的可信度全靠这几处不走样。
13. **品牌黄要么铺成面，要么衬在品牌红上，不要单独画在白底上。** 黄压白底 1.6:1，图形放上去等于没画；黄压红 3.12:1，才够 WCAG 非文本 3:1 的线。拱门是全篇唯一用黄画图形的地方，所以它自带底衬。

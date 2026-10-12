# MCP 集成说明

本文件说明 `mcd-hui-life` 实际使用的麦当劳 MCP Server、工具、调用流程与业务价值。所有工具名、参数与错误码均来自 2026-10-12 的真实调用，未做推测。

## 一、接入的 MCP Server

| 项目 | 值 |
|---|---|
| 服务名 | `mcd-mcp` |
| 服务形态 | 远程托管的 Streamable HTTP MCP Server |
| 接入地址 | `https://mcp.mcd.cn` |
| 鉴权方式 | 请求头 `Authorization: Bearer <MCP Token>` |
| 限流 | 每分钟 600 次，超限返回 429 |
| 鉴权失败 | 返回 401 |
| 官方入口 | https://open.mcd.cn/mcp |
| 官方文档 | https://github.com/M-China/mcd-mcp-server |
| 服务规则 | https://cdn.mcd.cn/cms/pages/MCPServerRules.html |
| Token 申请 | 打开 https://open.mcd.cn/mcp → 右上角「登录」手机号验证 → 右上角「控制台」→「激活」→ 同意服务协议 → 复制 Token |

### 双端接入

**WorkBuddy 连接器**：左侧边栏「专家·技能·连接器」→「连接器」页签 → 右上角「自定义连接器」→「配置 MCP」，填入 `mcp-config.example.json` 的内容并把 `YOUR_MCP_TOKEN` 替换为实际 Token，保存后回到列表把 `mcd-mcp` 启用并「信任」。

**其他 MCP 客户端**：`mcp-config.example.json` 是标准 `mcpServers` 结构，可直接被支持 Streamable HTTP 的客户端读取。

### 凭据处理

Token 代表该账号在 MCP 开放能力上的完整权限，包含会员资产读取与下单，视同高敏感凭据：

- 只存放于客户端连接器配置，**不进本仓库任何文件**。
- `mcp-config.example.json` 只保留占位符 `YOUR_MCP_TOKEN`。
- 不在对话、日志或错误信息中回显完整 Token。
- 轮换：回到控制台重新激活取得新 Token 并替换；撤销：在控制台使旧 Token 失效或删除连接器条目。

## 二、实际使用的工具

关键路径上共使用下列 17 个工具，按在流程中的角色分组。**没有一个是可有可无的**，每个都对应一个其他工具无法替代的口径。

### 探测与时间

| 工具 | 入参 | 为什么必须用它 |
|---|---|---|
| `now-time-info` | 无 | 唯一无副作用的只读探测，用于验证鉴权与连通；同时提供当前时间，用于判定落在哪个餐段 |

### 门店与菜单

| 工具 | 关键入参 | 为什么必须用它 |
|---|---|---|
| `query-nearby-stores` | `beType`、`searchType`（`searchType=2` 时还需 `city`、`keyword`） | 到店自取与得来速的唯一门店来源；得来速的 `beCode` 只在这里返回；`searchType=2` 是**唯一能拿到距离**的口径（单位米、升序） |
| `delivery-query-addresses` | — | 麦乐送与企业团餐场景取地址，进而取 `beCode` |
| `delivery-query-stores` | `addressId`、`beType` | 外送与团餐的门店来源，同时返回该渠道的 `beCode`（下单必传） |
| `query-meals` | `storeCode`、`orderType`、`beType`（外送另需 `beCode`） | 唯一菜单来源。菜单**按时段动态变化**，10:27 返回早餐、10:37 返回午餐；**外送与到店是两套独立菜单**，同名产品的商品码与价格都不同 |
| `query-meal-detail` | `storeCode`、`orderType`、`beType`、`code` | 唯一能把套餐与券商品拆成组成品的工具，返回 `rounds[].choices[]` 与 `diffPrice` |

### 券

| 工具 | 关键入参 | 为什么必须用它 |
|---|---|---|
| `query-my-coupons` | 无 | 展示用户卡包资产。**注意：它不校验门店、渠道与时段**，结果不能直接当可用券 |
| `query-store-coupons` | `storeCode`、`orderType`、`beType` | 唯一权威口径。只有它返回下单单据所需的 `couponId`、`couponCode` 与券商品 `productCode` |
| `available-coupons` | 无 | 用户问「有什么可以领」时列出可领项 |
| `auto-bind-coupons` | 无 | 领取券后再回到 `query-store-coupons` 复核 |

### 营养

| 工具 | 关键入参 | 为什么必须用它 |
|---|---|---|
| `list-nutrition-foods` | 无 | 唯一营养数据来源。返回 160 行表格，**只有菜名，没有任何商品编码**，因此必须做名称映射 |

### 报价、下单与订单

| 工具 | 关键入参 | 为什么必须用它 |
|---|---|---|
| `calculate-price` | `storeCode`、`orderType`、`beType`、`items[]`（含 `couponId`、`couponCode`、`roundList`） | **唯一价格真值**。返回单位是分，展示时除以 100 |
| `create-order` | 同上，另加 `takeWayCode`、`addressId`、`remark`、`needTableware` | 创建订单。`takeWayCode` 必须取自 `calculate-price` 返回的 `takeWayList[].code`，不能自造 |
| `query-order` | 订单号 | 支付后查询最新订单状态。状态判断用 `orderStatus` 文本，不按 `status` 数字码（见下） |
| `cancel-order` | 订单号、`cancelReasonCode` | 用户要求取消时执行，实测返回 `cancelResult: true` |
| `order-list` | — | 取历史点单频次，用于估算开卡回本所需顿数 |
| `query-meal-assistance` | — | 企业团餐下单路径的必需项，用它的返回值取 `gmServiceCode`；到店与外送路径不使用 |

## 三、调用流程

```text
① 探测             now-time-info
                       ↓
② 定门店渠道        query-nearby-stores
                   delivery-query-addresses → delivery-query-stores
                       ↓
③ 取菜单与券        query-meals
                   query-store-coupons  ←── available-coupons → auto-bind-coupons（按需）
                       ↓
④ 构建候选集        query-meal-detail（券商品与套餐拆解）
                   list-nutrition-foods → nutrition_map.py（本地映射）
                       ↓
⑤ 求解双预算        组合剪枝（本地）→ calculate-price 验证前 20 个以内候选
                       ↓
⑥ 判定清淡          fat_ratio.py（本地）
                       ↓
⑦ 输出方案          按固定模板渲染，标注差距、无数据项与未参与比较的券
                       ↓
⑧ 下单             create-order → query-order / cancel-order
```

### 渠道传参矩阵

传错 `beCode` 会直接报错，这是集成中最容易踩的坑。

| 用户场景 | `beType` | `orderType` | `beCode` |
|---|---|---|---|
| 到店自取 | 1 | 1 | **不传**（传了会报错） |
| 得来速 | 5 | 1 | **必传**，来自 `query-nearby-stores` |
| 麦乐送 | 2 | 2 | **必传**，来自 `delivery-query-stores` |
| 企业团餐 | 6 | 2 | **必传**，来自 `delivery-query-stores` |

### 门店定位与距离（2026-10-12 实测）

定位「离用户最近的门店」只有一条可用路径：`query-nearby-stores` 的 `searchType=2`，靠 `city` + `keyword` 做地理编码，返回按 `distance`（米）升序的列表。

| 方式 | 返回距离 | 结论 |
|---|---|---|
| `searchType=2`（`city` + `keyword`） | `data[].distance`，单位米，升序 | **唯一可用于「最近」的口径** |
| `searchType=1`（收藏餐厅） | 恒为 `0` | 只能当「常用门店」，判断不了远近 |

同一锚点的实测（`beType=1`）：

| 锚点 | 门店与距离（米） |
|---|---|
| `湖北工业大学` | 板桥地铁A口 656 / 白沙洲龙湖天街 1710 / 保利心语 1855 / 保利新武昌 2214 / 南湖 3073 |
| `洪山区珞狮路` | 揽胜汇 731 / 保利心语 1506 / 板桥地铁A口 2503 / 华中农业大学荟园 2522 / 书城路硅巷 2572 |

**距离是相对锚点算的，锚点措辞一变结果就变。** 接口不收坐标，返回的 `longitude`/`latitude` 恒为 `0.0`——MCP **拿不到设备定位**，所以「最近」只能由用户给出的位置词、已存配送地址或直接询问得出，不能凭空假定。

`searchType=2` 的返回还带 `businessStatus` 与营业起止时间。**营业时段按门店走且差异很大**，同一锚点下并存 `07:00–22:00`、`10:00–22:00`、`00:00–23:59`、`07:00–02:30`，早晨可能最近那家还没开门——所以距离只决定候选顺序，还要逐家校验「营业中 → 券可用 → 能报价」，第一个通过的才是命中门店。

**外送侧的定位能力更弱。** `delivery-query-stores` 的返回里**没有 `distance` 字段**，也没有 `address` 字段，同一地址可命中多家可配送门店（实测「湖北工业大学」→ `1960361` + `1960208`），无从比较远近，只能列出来让用户选。

`beCode` 观察到渠道后缀模式（得来速 `+41`、麦乐送 `+02`），但**这是观察不是规则**，`beCode` 一律取自接口返回值。

### 下单链路实测（2026-10-12）

用一笔真实最小订单跑通了全链路：到店自取、单品、**不使用任何券**（避免消耗用户券资产），建单后立即取消。

| 环节 | 工具 | 实测结果 |
|---|---|---|
| 报价 | `calculate-price` | 圆筒冰淇淋 `515837` 返回 `price: 500`（分）= **5.00 元**；`takeWayList` 给出 `eat-in` 堂食 与 `locker-in` 外带 |
| 建单 | `create-order` | 传 `takeWayCode: locker-in`、到店自取**不传** `beCode`，成功返回 `orderId`、`payId`、`payH5Url` |
| 金额一致 | — | 报价 500 分 = **5 元**，订单 `realTotalAmount` = **5 元**，`totalDiscountAmount` = 0，两处一致 |
| 取餐方式 | — | `takeWayCode: locker-in` 正确落为 `takeWay` = **外带** |
| 查单 | `query-order` | `orderStatus` = `待支付` |
| 取消 | `cancel-order` | 传 `cancelReasonCode: 1`，返回 `cancelResult: true` |
| 复核 | `query-order` | `orderStatus` = `订单已取消` |

**未支付订单自带 15 分钟支付窗口**：`create-order` 返回的 `expirePayTime` = 下单时间 + 15 分钟（实测 11:18:10 下单 → 11:33:10 过期）。这是「建单后用户不支付」场景的兜底机制。

#### 换配与特调的实测对照

第二笔验证用同一商品（麦香鸡中套餐 `9900005453`，27.5 元）下了两笔订单，唯一区别是**是否携带选配参数**：

| | 携带 `roundList` + `modification` | 不携带 |
|---|---|---|
| 订单 `comboItemList` | `麦香鸡 生菜(不要)` / `中薯条` / **`无糖可口可乐中杯`** | `麦香鸡` / `中薯条` / **`可乐中杯`** |
| 订单金额 | 27.5 元 | 27.5 元 |

两笔金额完全相同，交付内容不同。**漏传选配不会报错、不会改价，只会静默还原成默认配置**——用户看到的是无糖可乐，拿到的是含糖可乐，而账单上没有任何异常。这条把「下单参数必须与报价逐字一致」从契约推断变成了实测结论。

配套发现的字段差异：`order-list` 的子项用 `productCode` / `name` / `quantity`，订单详情用 `itemName` / `itemQuantity`。**两者能反映的配置范围不同**——同一套餐的两笔订单在 `order-list` 里，饮料一项分别是 `无糖可口可乐中杯`（`3071`）与 `可乐中杯`（`3050`），**换配可见**；但主品两笔都只写作「麦香鸡」，看不出「生菜(不要)」。核对换配可用 `order-list`，**核对特调必须用 `query-order`**。

#### 订单状态字段的实测陷阱

官方工具文档把 `orderStatus` 描述为数字码（`1` 待支付、`7` 已取消、`10` 配餐中…），**实测不符**：

| 时刻 | `orderStatus`（实测为中文文本） | `status`（实测为数字） | 文档对 `status` 的说明 |
|---|---|---|---|
| 建单后 | `待支付` | `10` | 10 = 配餐中-餐厅确认配餐中　**不符** |
| 取消后 | `订单已取消` | `60` | 60 **不在文档列举的取值内** |

**结论**：判断订单状态一律用 `orderStatus` 的**中文文本**，不按数字码分支。`status` 字段的语义与文档不一致，不能作为判定依据。这条不实测发现不了。

#### 订单详情返回的凭证字段与生成时机

`query-order` 返回的字段比工具文档列出的多，其中四项直接决定用户能不能取到餐：

| 字段 | 含义 | 实测 |
|---|---|---|
| `pickupCode` | **取餐号** | 已完成订单返回 `35054`；两笔未支付/已取消订单均返回空串 |
| `lockerCode` | 取餐柜密码 | 完成态为外带时为空，未启用柜机 |
| `lockerQrCode` | 取餐柜二维码 | 同上 |
| `storeAddress` | 门店地址 | `白沙洲大道187号`，到店场景下就是用户要去的地址 |

**取餐号三态实测**（同一接口，仅订单状态不同）：

| 订单 | 状态 | `pickupCode` |
|---|---|---|
| 已完成单 | 订单已完成 | `35054` |
| 已取消单 A | 订单已取消 | `""` |
| 已取消单 B | 订单已取消 | `""` |

**结论**：取餐号由门店接单配餐时分配，**下单后、支付前必然为空**。任何在下单确认阶段就展示取餐号的做法都是错的，只能显示「支付后生成」。这条直接影响确认界面的设计——界面上必须为它留位置，但不能填数字。

接口在返回体里内嵌了一句渲染指令，要求 `lockerQrCode` 非空时以图片形式输出。这说明图形化输出是接口设计者预留的方向，不是额外发挥。

同批发现的其余可用字段：

| 字段 | 用途 |
|---|---|
| `productImage` | 商品图片地址。域不在内联渲染的允许来源内，**未验证能否加载**，不要写进模板 |
| `couponList[].couponName` / `.discountAmount` | 本单实际使用的券与优惠额，比 `totalDiscountAmount` 更可信 |
| `productPrice` / `realTotalAmount` / `realDeliveryPrice` / `realPackingFeeTotalPrice` / `tablewarePrice` | 金额分项，可直接用于界面的金额明细 |
| `deliveryInfo.expectDeliveryTime` | 预计送达时间。**未支付时为空串**，不能拿来承诺送达时间 |
| `deliveryInfo.riderNickName` / `.riderMobilePhone` | 配送骑士，仅配送中出现 |
| `orderProductList[].price` | 单品原价，可用于展示「省了多少」 |

注意 `totalDiscountAmount` 在优惠订单上实测为 `0`，而同一订单的 `couponList[].discountAmount` 为 `10.9`。**要展示优惠金额时用 `couponList`，不要用 `totalDiscountAmount`。**

#### 麦乐送（外送）链路的实测差异

用门店 `1960208`（`beCode` `196020802`）配地址 `<addressId>` 跑通麦乐送全链路，商品为苹果片 `906102`，建单后立即取消。

| 环节 | 实测结果 |
|---|---|
| 定位门店 | `delivery-query-stores`（`beType=2`）返回 2 家可送门店，额外返回 `beCode`、`reservation` 与按日期分组的 `reservationTimeOptions` |
| 取菜单 | `query-meals` 带 `beType=2`、`beCode`，返回的是**外送专属菜单** |
| 报价 | `calculate-price` 带 `beCode`，**不接受** `addressId`（schema 无此字段） |
| 建单 | `create-order` 带 `beCode` 与 `addressId`，**不传** `takeWayCode`，成功返回订单号与支付链接 |
| 金额一致 | 商品 7.5 + 运费 6 + 打包费 0.8 = **14.3 元**，与报价 1430 分逐项一致 |
| 查单 | `orderStatus` = `待支付`；`deliveryInfo` 完整回显收件人、地址、配送方式 |
| 取消 | `cancelResult: true`；复核 `orderStatus` = `订单已取消` |

**外送与到店的四处参数差异**

| | 到店自取 | 麦乐送 |
|---|---|---|
| `addressId` | 不接受 | **仅 `create-order` 需要** |
| `takeWayCode` | 必传 | **禁用**（外送报价不返回 `takeWayList`） |
| 报价附加字段 | 无 | `deliveryPrice`、`packingPrice`、`tablewarePrice` |
| 订单详情 | 无 `deliveryInfo` | 多出 `deliveryInfo` 块 |

**外送菜单与到店菜单是两套独立商品。** 同名产品在两条渠道的商品码与价格都不同：到店「麦香鸡中套餐」为 `9900005453` / 27.5 元，外送「麦香鸡套餐」为 `9900003041` / 33.5 元。把到店商品码拿去外送报价，直接返回 `60006`。

**附加费让「省钱」的结论可能反转。** 苹果片单商品 7.5 元，加 6 元运费与 0.8 元打包费后实付 14.3 元，附加费占 **47.6%**；同款套餐外送 41.4 元 vs 到店 27.5 元，差 **50.5%**。外送没有起送门槛，但低价单的附加费占比极高。

**两个字段陷阱。** 报价 `productList` 里混入「打包服务费」伪商品行（`productCode` `920174`、`quantity` 不是份数、`subtotal` 恒为 0），按 `productList` 求和会算错；未支付的外送订单 `expectDeliveryTime` 返回空串，不能据此承诺送达时间。

### 调用预算

单次会话内 `calculate-price` 控制在 20 次以内，配合本地剪枝先用价格与热量排序，只把排名靠前的少量组合送去报价，避免触发每分钟 600 次的限流。

## 四、四条铁律与实测证据

这四条都是先踩坑、再用真实调用定位出来的，是本 Skill 区别于「直接问模型」的核心：

### 1. 菜单返回 ≠ 可售

10:31 用菜单里返回的商品调用 `calculate-price`，返回 `60006`「商品已售罄或不可售」。同时段门店营业信息显示早餐 05:14–10:15 已结束、午餐 10:44 未开始——正处于**餐段空窗期**。菜单接口不会因为停售就把餐品摘掉。

**处理**：任何进入推荐结果的商品都必须先经报价接口确认可售；空窗期直接告知下一餐段开始时间。

### 2. 菜单价 ≠ 成交价

以「燕麦奶铁」实测：菜单 `currentPrice` 为 **9.9 元**，`calculate-price` 返回 **2300 分 = 23 元**，相差 **13.1 元**。原因是菜单上的 9.9 元带有 `discountType: 随单购麦金卡优惠` 标记，必须同时购买麦金卡才成立。

**处理**：对外只报报价接口的金额；需持卡的方案标注「需持卡」，不当作可成交价。

### 3. 卡包券 ≠ 可用券

同一时刻，`query-my-coupons` 返回 **11 张**券，`query-store-coupons` 只返回 **2 张**。差异来自前者不校验门店、渠道与时段。

**处理**：券必须经门店券接口交叉校验后才能参与比较；未通过校验的券列出券名与有效期窗口，说明原因，不让它参与比较。

### 4. 券是特价商品，不是折扣

`query-store-coupons` 返回的「王牌小食拼」对应商品码 `9900016371`，是一个**独立商品码**，自带组成与价格，`promotionId` 为 `112458029`。它不是订单级折扣。

**处理**：券必须当商品处理——用 `query-meal-detail` 拆成组成品、用组成品营养求和、用 `calculate-price` 单独验证券价。

### 附：同价换配是免费的操作空间

券商品拆解后，同一轮内 `diffPrice` 为 `+ ¥0` 的选项互为等价备选。实测「王牌小食拼」可等价换成 **15 种**组合（如把含糖可乐换成无糖可乐，价格不变）。这是双预算优化中不用多花钱就能调整营养的主要抓手。

## 五、业务价值

| 价值点 | 不接入 MCP 时 | 接入 MCP 后 | 实测依据 |
|---|---|---|---|
| 价格真实 | 用菜单价会**低估**实际花费，差额可达数倍 | 用报价接口成交价 | 燕麦奶铁菜单价 9.9 元、成交价 23 元，仅为成交价的 43% |
| 可售真实 | 会推荐买不到的商品 | 每个候选都验证可售 | `60006` 空窗期实例 |
| 券真实 | 会把不可用券算进去 | 门店券接口交叉校验 | 卡包 11 张 vs 门店 2 张 |
| 营养可算 | 只能报菜名热量，无法拆套餐 | 券商品拆解后逐项求和 | 王牌小食拼 → 2 个组成品 |
| 能真正下单 | 只能给推荐 | 可创建订单、查询状态并取消 | 已跑通真实最小订单：建单成功、报价与订单金额一致（均 5 元）、`cancel-order` 返回 `cancelResult: true`、复核为「订单已取消」 |

**一句话**：麦当劳 MCP 同时暴露了「菜单」「券」「报价」「营养」「下单」五套互相独立的数据源，它们之间存在菜单价与成交价、卡包券与可用券、菜单在售与真实可售三组系统性偏差。本 Skill 的价值就是把这三组偏差逐一用交叉校验消掉，让「省钱 + 控卡」这两个目标建立在真实可成交的数字上，而不是菜单上的名义数字。

## 六、未使用的工具与原因

| 工具组 | 未使用的原因 |
|---|---|
| `campaign-calendar`、`query-promotions` | 属于活动日历与促销查询，与双预算求解无直接关系 |
| `draw-lottery`、`query-lottery-info`、`query-my-prizes`、`query-survey-coupon` | 抽奖与问卷券，产出不确定，不参与确定性求解 |
| `query-my-account` | 会员资产总览，本 Skill 只读券与订单，不需要账户全量信息 |
| `mall-*`（积分商城 6 个） | 积分兑换是另一条业务线 |
| `party-*`（生日会 5 个）、`party-order-create` | 生日会场地预约与团单，超出点餐范围 |
| `delivery-create-address` | 会写入真实地址簿，属于改变用户状态的操作，本 Skill 不代为新增地址。实测另有一重障碍：`delivery-query-addresses` 返回的电话是**脱敏**的（`138****0000`），而本工具要求 11 位纯数字，既有联系人的信息无法直接复用 |

## 七、核验信息

| 项目 | 值 |
|---|---|
| 核验日期 | 2026-10-12 |
| 核验环境 | WorkBuddy 连接器 `mcd-mcp`，客户端配置 `{"type":"streamablehttp","url":"https://mcp.mcd.cn"}` |
| 核验门店 | 到店：武汉光谷通信广场餐厅（1960090）、武汉江夏永旺梦乐城餐厅（1960242）、武汉洪山万科广场餐厅（1960264）、武汉板桥地铁A口得来速餐厅（1960361）、武汉白沙洲龙湖天街餐厅（1960207）、武汉保利心语餐厅（1960208）；麦乐送：武汉保利心语餐厅（1960208，`beCode` 196020802） |
| 门店定位核验 | 锚点「湖北工业大学」返回 656 / 1710 / 1855 / 2214 / 3073 米（升序）；收藏餐厅模式 `distance` 恒为 `0`；`delivery-query-stores` 无 `distance` 字段，同一地址返回 2 家可配送门店 |
| 下单实测量 | 2026-10-12 共 4 笔真实订单（到店 3 + 麦乐送 1），全部取消，均未使用券 |
| 服务版本依据 | 官方仓库 `M-China/mcd-mcp-server` README 2026-10-01 更新内容 |
| 限流参数 | 每分钟 600 次（来源：官方服务规则页） |

价格、供应、券适用性与工具行为均可能随麦当劳官方调整而变化，以实时调用结果为准。

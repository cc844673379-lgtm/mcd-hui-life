# 依赖配置与故障恢复

本 Skill 依赖三项，全部为必需项。依赖 id 与 `skill-dependencies.json` 中的声明一一对应：

| 依赖 id | 类型 | 说明 | 缺失后果 |
|---|---|---|---|
| `mcd-mcp` | MCP 连接器 | 麦当劳中国 MCP 服务，承载门店、菜单、券、报价、下单与营养数据 | 全部功能不可用 |
| `python-runtime` | 本地运行环境 | 运行 `scripts/` 下的归一化与营养计算脚本，仅用标准库 | 营养映射与清淡判定降级为人工核对 |
| `network` | 网络连通 | 访问远程 MCP 服务 | 全部功能不可用 |

配置齐全时跳过本文件，直接执行。

## 一、麦当劳 MCP 连接器（`mcd-mcp`）

**用途**：提供门店、菜单、券、报价、下单与营养数据的全部能力。不可用时核心流程无法进行。

**受影响功能**：全部功能。

### 支持版本与前置条件

- 服务形态：远程托管的 MCP Server，接入地址 `https://mcp.mcd.cn`，传输协议 Streamable HTTP。
- 前置条件：需要麦当劳中国 MCP Token；客户端需支持 Streamable HTTP；服务面向中国大陆地区。
- 核验日期：2026-10-12。适用版本：官方 `mcd-mcp-server` 仓库 README 于 2026-10-01 更新的内容。

### 官方入口

| 项目 | 地址 |
|---|---|
| 产品主页 | https://open.mcd.cn/mcp |
| 官方文档 | https://github.com/M-China/mcd-mcp-server |
| 登录与 Token 申请 | https://open.mcd.cn/mcp |
| 服务规则 | https://cdn.mcd.cn/cms/pages/MCPServerRules.html |
| 客户端接入文档 | https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Connector |

### 申请 Token 的逐步操作

1. 打开 https://open.mcd.cn/mcp。
2. 点击右上角「登录」，使用手机号完成验证登录。登录成功后右上角按钮变为「控制台」。
3. 点击右上角「控制台」打开控制台弹窗。
4. 点击「激活」申请 MCP Token。
5. 阅读并同意服务协议。
6. Token 申请成功后一键复制。

### 权限范围

麦当劳未提供细粒度权限划分，一个 Token 即代表该账号在 MCP 开放能力上的完整权限，包含会员资产读取与下单。因此视同高敏感凭据管理。

### 凭据存放

Token 只写入 WorkBuddy 连接器配置中 `mcd-mcp` 条目的 `Authorization` 请求头，格式为 `Bearer <Token>`。

- 不得粘贴到对话、日志或错误信息中。
- 不得写入本 Skill 的任何文件，不得提交到公开仓库。
- 本仓库的 `mcp-config.example.json` 只保留环境变量占位符。

### 最小验证

调用 `mcd-mcp` 的 `now-time-info`。该工具无入参、只读、不涉及资产，能返回当前时间即说明鉴权与连通正常。

验证通过后按下述格式写入临时文件 `probe-results.json`，供环境检查器使用。

键名必须与 `skill-dependencies.json` 严格对齐，分两级：第一级是**依赖 id**，第二级是**该依赖下的 check id**。`check_type` 必须等于清单中该 check 的 `type`，`target` 必须等于清单中的 `target`。键名或类型对不上时，检查器会返回 `configuration_invalid`。`checked_at` 必须为 UTC 的 `YYYY-MM-DDTHH:MM:SSZ` 格式（以 `Z` 结尾）。

```json
{
  "mcd-mcp": {
    "mcp-probe": {
      "check_type": "mcp_probe",
      "target": "mcd-mcp",
      "status": "ready",
      "reason_code": "ok",
      "checked_at": "2026-10-12T02:57:21Z"
    },
    "auth-probe": {
      "check_type": "auth_probe",
      "target": "mcd-mcp",
      "status": "ready",
      "reason_code": "ok",
      "checked_at": "2026-10-12T02:57:21Z"
    }
  }
}
```

注意清单中的 `mcp-registered` 检查类型是 `mcp`，由检查器直接读取本机 MCP 配置文件判定，**不需要**也不应写进 `probe-results.json`。

`status` 为 `ready` 时 `reason_code` 必须为 `ok`；为 `missing` 或 `unavailable` 时必须使用其他原因码，例如 `auth_expired_or_invalid`、`quota_or_rate_limit`、`service_error`、`network_or_timeout`、`mcp_not_registered`。

### 异常处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 返回 401 | Token 无效、过期或未提供 | 回到控制台重新激活并替换连接器中的 Token |
| 返回 429 | 超过每分钟 600 次限流 | 降低调用频率，参考 `references/mcp-call-chain.md` 的调用预算 |
| 连接被拒绝或超时 | 连接器未启用或未信任 | 在连接器管理页确认 `mcd-mcp` 已启用并完成信任 |
| 工具列表为空 | 配置已写入但未信任 | 在自定义连接器入口对新服务器点击「信任」后重试 |

### 轮换与撤销

- **轮换**：回到 https://open.mcd.cn/mcp 的控制台重新激活取得新 Token，替换连接器中的旧值。
- **撤销**：在控制台使旧 Token 失效，或在客户端删除 `mcd-mcp` 连接器条目并停用。

### 安全要求

- 只有本 Skill 需要读取门店、券与订单时才调用对应工具，不做超出当前请求的批量拉取。
- 下单、取消订单属于改变真实状态的操作，必须取得用户明确确认后才执行。
- 任何情况下都不在对话中回显完整 Token。

## 二、Python 运行环境（`python-runtime`）

**用途**：运行 `scripts/check_environment.py`、`scripts/nutrition_map.py`、`scripts/fat_ratio.py`。

**受影响功能**：营养映射与清淡判定。不可用时价格与券相关功能仍可继续，但营养结论无法给出。

### 官方入口

| 项目 | 地址 |
|---|---|
| 官方主页 | https://www.python.org/ |
| 官方文档 | https://docs.python.org/3/ |

### 支持的版本与前置条件

- 最低版本：Python 3.10。核验日期：2026-10-12。
- 依赖：仅标准库，无需安装任何第三方包，不需要联网。
- 系统自带的 Python 即可，不必新建虚拟环境。

### 验证

```text
python scripts/check_environment.py
```

能输出 JSON 即说明环境可用。

### 安全要求

三个脚本均为只读计算：不联网、不调用 MCP、不读取任何凭据，仅在显式传入 `--output` 时写入指定路径，不修改任何配置。

### 异常处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 提示找不到 `python` | 未安装或未加入 PATH | 从 https://www.python.org/ 安装，参考 https://docs.python.org/3/ 配置 PATH |
| 版本低于 3.10 | 使用了较旧的系统 Python | 安装 3.10 以上版本后重新运行 |
| 脚本报语法错误 | 解释器版本过旧 | 同上，升级解释器 |

### 降级

Python 不可用时跳过脚本，按 `references/nutrition-mapping.md` 与 `references/nutrition-standards.md` 的规则手工比对与计算，并在输出中标注「未运行脚本验证」。人工计算有出错风险，结论标记为部分验证；恢复后重新运行脚本核对。

## 三、网络连通（`network`）

**用途**：访问远程 MCP 服务。

**受影响功能**：全部功能。

- 验证目标：`https://open.mcd.cn/mcp`，GET 请求返回 200。
- 该探测只验证平台可达性，不代表 MCP 会话与鉴权状态；鉴权状态由连接器的最小验证覆盖。
- 网络不可用时无法产出任何真实方案，停止流程并说明需要恢复网络。

## 就绪路由

运行下列命令，按返回的 `status` 处理：

```text
python scripts/check_environment.py --network --probe-results probe-results.json
```

| status | 处理 |
|---|---|
| `ready` | 跳过本文件，直接进入正常流程 |
| `partial` | 继续执行，在结果中标注受影响功能、限制与降级范围 |
| `needs_setup` | 只展示缺失必需项的配置步骤，完成后重新检查 |
| `unavailable` | 按 `reason_code` 区分认证、限流、服务与版本问题，给出恢复步骤 |

已通过的项目不重复引导。重新检查时只报告状态变化与仍未满足的项目。

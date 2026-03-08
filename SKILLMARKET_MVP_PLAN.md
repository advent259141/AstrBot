# AstrBot 接入 SkillMarket（MVP）实施计划

> 日期：2026-02-28  
> 目标：仅实现最基础交互能力（拉取基础信息、下载安装、安装后上报下载）

---

## 1. 范围定义

### 1.1 本期要做

1. AstrBot Dashboard 展示 SkillMarket 基础列表
2. 支持一键下载安装 Skill（GitHub zip）
3. 安装成功后异步上报下载量 +1
4. 未配置市场地址时优雅降级
5. 尽量复用已有 AstrBot 组件与状态管理逻辑，减少新增代码

### 1.2 本期不做

- Star / 举报 / 评论
- Skill 详情富文本渲染
- SkillMarket 账号体系打通
- 复杂缓存协商（ETag/304）
- 推荐算法/个性化

---

## 2. 对接接口约定

## 2.1 SkillMarket -> AstrBot（读取）

- `GET {skill_market_url}/api/skills?page=1&size=20&sort=downloads`

AstrBot 前端只消费基础字段：

- `id`
- `name`
- `display_name`
- `description`
- `github_url`
- `category`
- `tags`
- `download_count`
- `star_count`
- `updated_at`

## 2.2 AstrBot 内部安装接口

- `POST /api/skills/install_from_url`
- body:

```json
{
  "url": "https://github.com/{owner}/{repo}/archive/refs/heads/main.zip",
  "github_url": "https://github.com/{owner}/{repo}"
}
```

后端流程：下载 zip -> `install_skill_from_zip` -> 返回安装结果。

## 2.3 AstrBot -> SkillMarket（上报）

- `POST {skill_market_url}/api/skills/report-install`
- body:

```json
{
  "github_url": "https://github.com/{owner}/{repo}"
}
```

说明：失败静默，不影响安装成功。

---

## 3. 代码改造清单（文件级）

## 3.1 后端（AstrBot）

### A. `astrbot/dashboard/routes/skills.py`

新增：

1. 路由注册：`/skills/install_from_url`
2. 请求体解析与 URL 校验
3. 下载 zip 到 temp 目录
4. 调用 `SkillManager().install_skill_from_zip(...)`
5. 异步上报 `_report_install_to_market(github_url)`
6. 异常与临时文件清理

### B. `astrbot/core/config/default.py`（或对应配置元数据文件）

新增配置项：

- `skill_market_url: ""`

要求：可在 Dashboard 配置中读取/保存。

---

## 3.2 前端（AstrBot Dashboard）

> 尽量复用现有 Extension/Skills 页面结构，不新建复杂路由。

优先复用（不重复造轮子）：

- 现有 `SkillsSection` 页面结构与样式
- 现有加载态/提示组件与 toast 交互方式
- 现有 axios 请求封装与错误处理模式
- 现有已安装 Skill 列表接口与刷新逻辑

### A. `dashboard/src/components/extension/SkillsSection.vue`

新增“在线 Skill 市场”区块：

1. 列表加载
2. 卡片展示（基础字段）
3. 安装按钮
4. 查看仓库按钮
5. 加载态/空态/错误态

### B. （按需）新增 API 封装文件

建议新增 `dashboard/src/api/skillsMarket.js`：

- `fetchSkillMarketList(baseUrl, params)`
- `installSkillFromUrl(payload)`

### C. 已安装状态对比

- 读取 `/api/skills` 本地列表
- 通过仓库地址或 skill 名称标记“已安装”

---

## 4. 关键流程

## 4.1 页面加载

1. 读取配置中的 `skill_market_url`
2. 若为空：展示“未配置市场地址”提示
3. 若非空：拉取 `/api/skills` 列表并渲染

## 4.2 点击安装

1. 前端拼接 zip 下载 URL
2. 调用 `/api/skills/install_from_url`
3. 成功后刷新本地已安装列表并更新 UI

## 4.3 安装后上报

1. 后端安装成功后启动异步任务
2. 请求 SkillMarket `report-install`
3. 上报失败仅记录日志，不返回前端错误

---

## 5. 异常处理策略

1. 市场不可达：前端提示“市场暂不可用”
2. zip 下载失败：返回明确错误（网络/404/超时）
3. 安装失败：返回技能包校验或解压错误
4. 上报失败：静默，避免影响主链路

---

## 6. 验收标准（DoD）

1. 已配置 `skill_market_url` 时可看到市场列表
2. 可从市场一键安装 Skill
3. 安装成功后本地列表可见该 Skill
4. SkillMarket 侧下载计数可增长
5. SkillMarket 不可用时，AstrBot 其他功能不受影响

---

## 7. 实施顺序

1. 完成后端 `/api/skills/install_from_url`
2. 完成 `skill_market_url` 配置项
3. 完成前端列表与安装按钮
4. 联调下载上报
5. 回归测试与错误处理

---

## 8. 回滚策略

- 前端通过开关（`skill_market_url` 为空）直接隐藏市场区块
- 后端保留原有 `/api/skills/upload` 手动安装能力
- 异步上报逻辑可单独禁用，不影响安装主流程

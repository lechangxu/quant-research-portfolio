# QuantMind 本体（Ontology）：Objects / Links / Actions

> [English version](04-domain-ontology-operations-layer.md) · [HTML 展示版](quantmind-ontology.html)

> **是什么**：QuantMind 域的 typed 模型 —— 这个系统里有哪些对象（objects）、
> 对象之间的血缘与依赖（links）、以及谁被允许对对象做什么动作（actions + gates）。
>
> **为什么写**：2026-09-06 判例 —— alpha158 / extended 两张因子表同时缺席四份
> 独立维护的字面量清单，停更 42 天无人发现，182 个目录因子里 92 个静默消失。
> 根治不是「多加几个检查」，而是**把域建模成本体**：一张注册表作为唯一真源，
> 所有清单、监控、目录、API 从它派生。本文是那次根治的完整描述。
>
> Palantir 管这叫 Ontology；我们管这叫 registry + manifest。同一件事。

---

## 1. Objects（类型化对象）

| Object | 真身 | 关键属性 | 说明 |
|---|---|---|---|
| **DataSource** | tushare / akshare / cninfo / 东财 | 可达性、频率、出口约束 | 原始数据源。境外 IP 被封是已知约束（架构决策：内地服务器唯一计算方） |
| **RawTable** | `daily_data`、财务/公告/研报表 | schema、max(trade_date) | 落地原始数据，一切派生物的根 |
| **FactorTable** | `scripts/factors/registry.py::FACTOR_TABLES`（8 张注册表） | `columns`（声明式或 schema 发现）、`max_lag`、`writer`、`category` | **核心 object**。每张表是注册条目，不是文件 |
| **Factor** | 表内列（3 张声明式表共 258 列 + 5 张 schema 发现表） | 中文标签（`LABELS`）、类别 | 目录/API/IC 报告展示的最小单位 |
| **ICStats** | `factor_ic_stats.json` + `factor_ic_meta.json` | IC 值、区间、计算日 | 因子有效性的度量对象，内地算、HK 只读 |
| **Manifest** | `manifest.json` | `max_trade_date`、`created_at`、`degraded` | **一次同步的完成证明**。原子写，是跨机信任的唯一凭证 |
| **IntelReport** | `users.db::daily_intel_reports` | 日期、叙事文本 | 面向用户的产品对象，HK 本地生成（数据快照的消费者） |
| **User** | `users.db` | 认证、订阅 | 产品对象 |
| **Deployment** | HK（aiyangu.com，nginx+FastAPI:8011）/ 内地（<mainland-relay>，relay） | 角色、systemd 单元、crontab | 双机拓扑本身就是本体的一部分：内地=唯一计算方，HK=纯消费者 |

### Object 注册条目示例（唯一真源，真实代码）

```python
# scripts/factors/registry.py —— FACTOR_TABLES: tuple[FactorTable, ...]
FactorTable("price_factors",       tuple(PRICE_FACTOR_COLS),   max_lag=2, writer="scripts.factors.cli update",              category="技术因子")
FactorTable("alpha158_factors",    tuple(ALPHA158_COLS),       max_lag=2, writer="scripts.factors.cli update",              category="技术因子")
FactorTable("extended_factors",    tuple(EXTENDED_FACTOR_COLS),max_lag=2, writer="scripts.factors.cli update",              category="其他")
FactorTable("fundamental_factors", None,                       max_lag=3, writer="scripts/backfill_fundamental_factors.py", category="质量")
FactorTable("holder_factors",      None,                       max_lag=7, writer="scripts/backfill_holder.py (周一 20:00)", category="股东")
# ... 共 8 张；columns=None → 列由 SQLite schema 发现，写库后仍须与实际 schema 对账（A2）
```

新增一张因子表 = 在这里登记一次。登记即被巡检、进目录、进 IC、进部署审计 ——
**不需要任何人记得去改第二份清单**。这就是本体相对「配置文件集合」的区别。

---

## 2. Links（血缘与依赖）

```mermaid
graph LR
    subgraph Sources[DataSources]
        TS[tushare] -->|A股行情/财务| SS
        AK[akshare] -->|中继| SS
        CN[cninfo 公告] --> SS
        EM[东财研报] --> SS
    end

    subgraph Mainland[内地 <mainland-relay> — 唯一计算方]
        SS[sync-data-server.sh<br/>07/12/20 工作日] --> RAW[(RawTables<br/>daily_data 等)]
        RAW --> FT[(FactorTables ×8<br/>registry 派生)]
        FT --> IC[ICStats<br/>compute_factor_ic]
        IC --> MF[manifest.json<br/>原子写]
        SS -->|关键阶段失败 exit 1| NO[/不写 manifest/]
    end

    subgraph HK[HK aiyangu.com — 纯消费者]
        SYN[sync-db.sh 21:00] -->|校验 manifest 新鲜| SNAP[(DB 快照<br/>原子换)]
        SNAP --> API[FastAPI :8011<br/>搜索/情报/因子研究]
        SNAP --> RPT[IntelReport<br/>HK 本地生成]
    end

    MF --> SYN
    NO -->|HK 不拉| WD[看门狗告警]
    FT -.->|MAX(trade_date) vs daily_data| FW[check_freshness.py<br/>每日巡检]
    FW -->|超 max_lag| WD
```

血缘一句话：**Source → Raw → FactorTable → ICStats → Manifest → HK 快照 → 产品面**。
每一环的「完成」都不是进程自报，而是下游可独立验证的物证（manifest / max(trade_date) / schema 对账）。

---

## 3. Actions（动作 + 许可门）

动作不是「函数」，是**带前置条件、验证证据、失败路径的操作**。许可表：

| Action | 触发 | 前置（gate） | 完成证据（不接受自报） | 失败路径 |
|---|---|---|---|---|
| `daily-update`（抓数→因子→IC） | cron 07/12/20 | flock 防重入；launcher 统一入口 | manifest 原子写（含 max_trade_date） | 关键阶段 exit 1 → 不写 manifest → HK 停拉 → 告警 |
| `sync-to-hk` | cron 21:00 | manifest 新鲜校验 | 原子换 DB + `ActiveState=active` 断言 | 校验失败 → 保留旧快照，服务不中断 |
| `register-factor-table` | 人工（开发） | registry 登记（唯一入口） | schema 对账（声明列 vs 实际列，A2） | 对账失败 → 部署审计 `--audit` 红 |
| `backfill-*` | 人工/补数 | 容差内不得与 daily update 竞争 | 写库行数 + freshness 复测 | 退出 0 但写 0 行 = **假完成**，freshness 看门狗次日抓 |
| `deploy` | 人工 push | CI `check_sql.py` 绿（本地≠CI，已踩坑） | `verify_update_server.sh --audit` 实弹 | 红 → 回滚上一快照 |
| `ic-recompute` | cron / 随更新 | 因子表新鲜（max_lag 内） | IC 文件 mtime + 区间对账 | 过期因子 → IC 标 degraded |

### 门的谱系（为什么这么设计）

- **A2 对账门**：永不接受进程自报的成功。`systemctl restart` 退 0 ≠ 服务在跑；
  backfill 退 0 ≠ 写了数据。每个 action 的「完成证据」列就是 A2 的物化。
- **假完成（false-completion）是头号敌人**：09-06 事故的本质不是「没人检查」，
  是四份清单各自以为对方在检查。本体化后，被巡检集合 = 注册集合，**恒等式成立**，
  不存在「漏登记的新表逃出监控」这个失败模式。
- **degraded 是一等公民**：manifest 带 `degraded` 标志 —— 允许带病交付，
  但病必须显式声明、随数据流到消费者，不许静默。

---

## 4. Governance（本体自身的变更治理）

- **门的成文法**：repo `CLAUDE.md` 的 A1–A7（判据四问 / 对账门 / 改动幅度门 / 契约门 /
  有界门 / 启动前置门 / 元规则「过期的门比没有门更危险」）是本体的宪法；
  每条门带 Q4 验证记录（把被检的东西弄坏、判据必须变红 —— 业界叫 mutation testing）。
- **注册表即 PR 对象**：改 registry = 改本体，走 git review；
  `scripts/factors/test_registry.py` 保证注册表自身一致性。
- **派生恒等式有测试**：`check_arch_drift.py` / `check_claims.py` 防止代码漂移出本体描述。
- **跨机契约文件化**：`docs/architecture.md` 是双机拓扑的真身文档，
  与 crontab（`install-cron.sh` 幂等安装）互为对账。
- **事故台账回流**：每次本体失效（09-06 静默消失 / 10-13 HK OOM / 10-26 磁盘+GFW 双重故障）
  都产生一条新 gate 或新属性（如 manifest 的 `degraded`），写回本体。本体是**长出来的**，不是设计出来的。

---

## 5. FDE 词汇翻译表（面试用）

| Palantir / FDE 词汇 | 本仓对应 | 一句话 |
|---|---|---|
| Ontology | `registry.py` + `manifest.json` + 本文 | 客户域的 typed objects/links/actions |
| Ontology Proposal（branch→review→merge） | git PR + `test_registry.py` + CI `check_sql.py` | 本体变更走评审流，不落盘不进生产 |
| Actions（带权限的操作） | §3 许可表：前置 gate + 完成证据 + 失败路径 | 动作是带闸的，不是裸函数 |
| Ship on day one | backfill 脚本当日写当日跑，但证据不齐不上生产面 | 快，但快不过对账门 |
| False-completion 防御 | A2 对账门 + freshness 看门狗 | 完成必须由下游物证证明 |
| 反馈回灌产品 | 事故台账 → 新 gate → 注册表新属性 | 本体从事故里长出来 |
| Durable execution | flock + 原子 manifest + 快照原子换 + 崩溃后不重放已完步 | 手写等价物；产品化版本 = Temporal |

---

## 6. 证据锚点（全部可查）

- 注册表：`scripts/factors/registry.py`（文件头注释记录了 09-06 判例全文）
- 新鲜度看门狗：`scripts/check_freshness.py`（WATCHED 从 registry 派生，注释写明原因）
- 架构与双机拓扑：`docs/architecture.md`
- 工程质量门七条：`docs/2026-09-07_工程质量门方案.md`
- 部署审计：`scripts/factors/verify_update_server.sh --audit`
- cron 幂等安装：`scripts/install-cron.sh`

---

*2026-11-18 建。本体即代码，代码即证据；本文只描述已存在的东西，不是规划。*

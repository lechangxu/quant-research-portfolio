# Quant Research Portfolio

[![tests](https://github.com/lechangxu/quant-research-portfolio/actions/workflows/tests.yml/badge.svg)](https://github.com/lechangxu/quant-research-portfolio/actions/workflows/tests.yml)

[简体中文](README.zh-CN.md) | [English](README.md)

**生产级系统化交易方法论 —— 只保留与真金白银交手后仍然成立的部分。**

本仓公开我在生产环境跑过的量化交易系统（加密永续合约与 A 股）背后的*研究过程*：实盘与回测的偏差如何审计，新因子在触碰资金之前如何被门禁拦下，以及被否决的想法留下了什么。

> **这是什么：** 工程与研究严谨性的证据。
> **这不是什么：** 策略代码、因子配方、参数、权重，或任何能复现实盘组合的东西。那些保持私有。

---

## 为什么公开方法论而不是代码？

开源回测框架很多而且很好 —— [vectorbt](https://github.com/polakowo/vectorbt)、[QLib](https://github.com/microsoft/qlib)、[freqtrade](https://github.com/freqtrade/freqtrade)、[Lean](https://github.com/QuantConnect/Lean)。它们给你一台引擎。它们给不了你的，是引擎撞上生产时会发生什么：

- 实盘净值曲线走平，而回测 OOS 说策略该赚钱。**为什么？**
- 一个新因子样本内 IC 很漂亮。**它在组合层面、在 2 倍费率下还能通过 out-of-sample A/B 吗？**
- 一层纸面上看起来很保守的风控，实际是个吸收态，永久锁死 87% 的持仓。**你的框架测试套件能抓到吗？**

这些文档是我的答案，写在事情发生的当时，对着实盘系统。

## 技术栈

| 层 | 内容 |
|---|---|
| 语言 | Python 3.10+（`framework/pyproject.toml` 的 `requires-python`） |
| 软件包 | `quantgate` —— `pip install -e "framework[dev]"` |
| 运行时依赖 | pandas >= 2.0、numpy >= 1.24、requests >= 2.28 |
| 开发依赖 | pytest >= 7.0 |
| 测试 | pytest —— `framework/tests` 下 14 个测试 |
| CI | GitHub Actions，Python 3.12 |

## 目录

| 文档 | 主题 |
|---|---|
| [01 — 实盘与回测偏差审计](docs/01-live-vs-backtest-divergence-audit.md) | 一个生产加密永续系统与其回测之间的九处偏差，按严重程度排序。包含：一个吸收态移动止损（86.8% 的滚动起点回测路径被永久锁死，中位存活 59 days）、一个尾部依赖筛查（去掉样本内最好的 1.4% 的交易日，收益归零），以及一个单元测试从未抓到的维度不匹配根因。 |
| [02 — 因子 A/B 验收协议](docs/02-factor-ab-protocol.md) | 任何新因子在获得权重之前、必须在*组合*层面通过的四条硬阈值。一条命令，PASS/FAIL，无例外。在 OOS 站不住的样本内改善，就按它的本来面目分类：一次样本内幻觉。 |
| [03 — 负结果日志](docs/03-negative-results-log.md) | 被*否决*的因子与设计改动 —— 连同杀死它们的数字一起公开。因为一个只展示赢家的研究过程是营销，不是研究。 |
| [`framework/` — quantgate](framework/README.md) | A/B 门禁的可运行实现，~400 lines 有测试的 Python：免密钥 Binance 数据适配器、无前视回测器、四条阈值写成常量，`run_ab()` → PASS/FAIL。文档证明思考，这个证明交付。`pip install -e ".[dev]" && pytest && python examples/run_ab_demo.py` |

## 方法论要点

- **滚动起点存活分析**，用于探测风控层里的吸收态（你的持仓进入后再也出不来的状态，即使它是「设计出来的」，也与 bug 无法区分）。
- **扰动测试**，针对部分 K 线 / 数据时点保真度 —— 量化实盘信号换手中多少是噪声、多少是真 edge，以及 rank 重叠（Jaccard）指标在哪些地方会失准。
- **尾部依赖筛查**：剥掉最好的 *k* 天，看还剩下什么。如果什么都不剩，你拿到的是彩票，不是策略。
- **隔离矩阵偏差审计**：在回测与实盘配置之间一次只改一个组件，测各自的 ΔSharpe，排序，按严重程度依次修复。
- **组合级 OOS A/B 门禁**：每个候选因子都过，在真实费率与 2 倍费率下，并带有逐年一致性要求。

## 与巨头们的定位

我构建在开源生态*之上*，而不是重新实现它。我做的比较性声明都是明确的、有基准的：

- **对比 vectorbt / backtrader**：它们给你事件模拟；这里的文档覆盖它们没有的部分 —— 你的研究配置与生产执行层之间的偏差审计。
- **对比 QLib**：QLib 给你 ML 流水线与因子动物园；文档 02 是治理层，决定任何因子（ML 发现的或手写的）能否触碰资金。
- **对比 freqtrade / Lean**：它们给你实盘管线；文档 01 是当管线与研究结论不一致时该做什么。

这里的任何内容都不是从上述项目抄来的；凡是用了它们的思路，都注明了出处。偏差审计与 A/B 门禁的写法，来自我自己生产系统的原创工作。

## 免责声明

这些文档中的所有数字都是**研究产物**，仅为演示方法论而公开。它们**不构成投资建议**，不是任何形式的推介，也不代表任何产品的预期业绩。历史业绩 —— 实盘或模拟 —— 都不保证未来结果。绝对收益数字与可识别的策略细节已被刻意移除；风险调整类统计量得以保留，因为它们是方法论证据。

## 联系

欢迎量化研究、回测基础设施与交易系统可靠性方向的机会。本仓的 GitHub issues 是联系我最好的方式。

"""The gate: four hard OOS thresholds, one verdict.

Implements ../docs/02-factor-ab-protocol.md. The thresholds live here as
constants and nowhere else; changing them without changing the doc is
exactly the failure mode the protocol exists to prevent.

    | check                          | threshold |
    |--------------------------------|-----------|
    | OOS ΔSharpe                    | >= +0.15  |
    | OOS MaxDD deterioration        | <= 3pp    |
    | OOS ΔSharpe at 2x fees         | >= +0.10  |
    | OOS yearly improvement share   | >= 2/3    |

All four pass -> PASS. Any one fails -> FAIL, weight stays zero.
"Improved IS, didn't improve OOS" is reported as what it is:
an in-sample hallucination.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .backtest import backtest
from .metrics import max_drawdown, sharpe, yearly_sharpe

# --- The four thresholds. Change the doc in the same commit, or don't change them.
MIN_OOS_DSHARPE = 0.15
MAX_DD_WORSEN_PP = 0.03
MIN_OOS_DSHARPE_2X_FEE = 0.10
MIN_YEAR_IMPROVEMENT_SHARE = 2 / 3


@dataclass
class Check:
    name: str
    value: float
    threshold: str
    passed: bool


@dataclass
class Verdict:
    passed: bool
    checks: list[Check] = field(default_factory=list)
    is_sharpe_a: float = float("nan")
    is_sharpe_b: float = float("nan")
    oos_sharpe_a: float = float("nan")
    oos_sharpe_b: float = float("nan")
    note: str = ""

    def render(self) -> str:
        lines = [
            f"IS   Sharpe  A {self.is_sharpe_a:+.3f} → B {self.is_sharpe_b:+.3f}",
            f"OOS  Sharpe  A {self.oos_sharpe_a:+.3f} → B {self.oos_sharpe_b:+.3f}",
            "",
            f"{'check':<38}{'value':>10}  {'threshold':<12}result",
        ]
        for c in self.checks:
            lines.append(
                f"{c.name:<38}{c.value:>10.3f}  {c.threshold:<12}{'PASS' if c.passed else 'FAIL'}"
            )
        lines += ["", f"VERDICT: {'PASS' if self.passed else 'FAIL — weight stays 0'}"]
        if self.note:
            lines.append(f"note: {self.note}")
        return "\n".join(lines)


def run_ab(
    prices: pd.DataFrame,
    factor_scores: dict[str, pd.DataFrame],
    weights_a: dict[str, float],
    weights_b: dict[str, float],
    oos_start: str,
    fee_bps: float = 10.0,
    **bt_kwargs,
) -> Verdict:
    """Run committed weights (A) against one candidate change (B).

    Windows: IS = before `oos_start`; OOS = from `oos_start`. The 2x-fee
    check reruns arm B on the OOS window with doubled fees — the edge must
    survive costs doubling.
    """
    oos_ts = pd.Timestamp(oos_start, tz="UTC")

    ret_a = backtest(prices, factor_scores, weights_a, fee_bps=fee_bps, **bt_kwargs)
    ret_b = backtest(prices, factor_scores, weights_b, fee_bps=fee_bps, **bt_kwargs)
    ret_b_2x = backtest(prices, factor_scores, weights_b, fee_bps=2 * fee_bps, **bt_kwargs)

    a_is, b_is = ret_a[ret_a.index < oos_ts], ret_b[ret_b.index < oos_ts]
    a_oos, b_oos = ret_a[ret_a.index >= oos_ts], ret_b[ret_b.index >= oos_ts]
    b_oos_2x = ret_b_2x[ret_b_2x.index >= oos_ts]

    d_sharpe = sharpe(b_oos) - sharpe(a_oos)
    dd_worsen = max_drawdown(a_oos) - max_drawdown(b_oos)  # >0 means B's DD is deeper
    d_sharpe_2x = sharpe(b_oos_2x) - sharpe(a_oos)

    ya, yb = yearly_sharpe(a_oos), yearly_sharpe(b_oos)
    years = ya.index.intersection(yb.index)
    share = float((yb[years] > ya[years]).mean()) if len(years) else 0.0

    checks = [
        Check("OOS ΔSharpe", d_sharpe, f">= {MIN_OOS_DSHARPE:+.2f}", d_sharpe >= MIN_OOS_DSHARPE),
        Check("OOS MaxDD deterioration", dd_worsen, f"<= {MAX_DD_WORSEN_PP:.2f}", dd_worsen <= MAX_DD_WORSEN_PP),
        Check("OOS ΔSharpe @ 2x fees", d_sharpe_2x, f">= {MIN_OOS_DSHARPE_2X_FEE:+.2f}", d_sharpe_2x >= MIN_OOS_DSHARPE_2X_FEE),
        Check("OOS yearly improvement share", share, f">= {MIN_YEAR_IMPROVEMENT_SHARE:.2f}", share >= MIN_YEAR_IMPROVEMENT_SHARE),
    ]

    note = ""
    if sharpe(b_is) > sharpe(a_is) and d_sharpe < MIN_OOS_DSHARPE:
        note = "improved IS, not OOS — in-sample hallucination"

    return Verdict(
        passed=all(c.passed for c in checks),
        checks=checks,
        is_sharpe_a=sharpe(a_is),
        is_sharpe_b=sharpe(b_is),
        oos_sharpe_a=sharpe(a_oos),
        oos_sharpe_b=sharpe(b_oos),
        note=note,
    )

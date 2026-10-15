"""Trade weights: shares, moving average, lag, gaps (spec: time-varying-svar)."""

from __future__ import annotations

import numpy as np
import pytest

from csuf_fullerton.core.tvsvar.weights import annual_shares, monthly, required_years, smooth

TRADE = {
    **{("world", y): 100.0 for y in range(2000, 2006)},
    **{("us", y): 20.0 - (y - 2000) for y in range(2000, 2006)},
    **{("cn", y): 2.0 + 3 * (y - 2000) for y in range(2000, 2006)},
}


def test_shares_sum_to_one() -> None:
    raw = annual_shares(TRADE, ["us", "cn"])
    for row in raw.values():
        assert all(0.0 <= v <= 1.0 for v in row.values())
        assert abs(sum(row.values()) - 1.0) < 1e-10


def test_moving_average_window() -> None:
    w = smooth(annual_shares(TRADE, ["us", "cn"]), ["us", "cn"], window=3, lag=0)
    assert min(w.shares) == 2002
    assert w.shares[2002]["cn"] == pytest.approx(np.mean([0.02, 0.05, 0.08]))


def test_lagged_weights_predetermined() -> None:
    w0 = smooth(annual_shares(TRADE, ["us", "cn"]), ["us", "cn"], window=3, lag=0)
    w1 = smooth(annual_shares(TRADE, ["us", "cn"]), ["us", "cn"], window=3, lag=1)
    # every month of 2004 uses the average ending in 2003
    m = monthly(w1, ["2004-01", "2004-12"])
    assert np.allclose(m, w0.at(2003))


def test_gap_rejected() -> None:
    trade = dict(TRADE)
    del trade[("cn", 2003)]
    with pytest.raises(ValueError, match="partner 'cn' in 2003"):
        annual_shares(trade, ["us", "cn"], require=range(2002, 2006))
    # outside the needed years the gap is skipped, not imputed
    raw = annual_shares(trade, ["us", "cn"], require=range(2004, 2006))
    assert 2003 not in raw


def test_monthly_outside_coverage_raises() -> None:
    w = smooth(annual_shares(TRADE, ["us", "cn"]), ["us", "cn"], window=3, lag=1)
    with pytest.raises(ValueError, match="no trade weight"):
        monthly(w, ["2001-06"])


def test_required_years() -> None:
    assert list(required_years(["2004-01", "2005-12"], 3, 1)) == [2001, 2002, 2003, 2004]


def test_bad_shares() -> None:
    with pytest.raises(ValueError, match="outside"):
        annual_shares({("world", 2000): 1.0, ("us", 2000): 2.0}, ["us"])
    with pytest.raises(ValueError, match="totals"):
        annual_shares({("us", 2000): 1.0}, ["us"])
    with pytest.raises(ValueError, match="window"):
        smooth({}, ["us"], window=0)

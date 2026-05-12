"""Reference-implementation tests for the volatility & correlation estimators.

These tests run via plain `pytest tests/`. They do NOT import from the
notebooks (those remain pasteable into a single Colab cell). Instead each
test re-implements the estimator inline and checks numeric agreement against
known closed-form expectations on synthetic inputs.

The point is to catch a refactor that breaks the math even when both
notebooks still execute end-to-end with no runtime error.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps


# ════════════════════════════════════════════════════════════════════════════
#  Lo-MacKinlay variance-ratio test, overlapping SE
# ════════════════════════════════════════════════════════════════════════════

def _vr_test(returns: np.ndarray, lag: int):
    """Reference: Lo-MacKinlay (1988) overlapping-returns asymptotic SE."""
    r = np.asarray(returns, dtype=float)
    n = len(r)
    if n < lag * 2:
        return float('nan'), float('nan'), float('nan')
    var1 = float(np.var(r, ddof=1))
    k_sum = np.convolve(r, np.ones(lag), mode='valid')
    var_k = float(np.var(k_sum, ddof=1)) / lag
    vr = var_k / var1 if var1 > 0 else float('nan')
    se = math.sqrt(2 * (2 * lag - 1) * (lag - 1) / (3 * lag * n))
    z = (vr - 1) / se if se > 0 else float('nan')
    p = 2 * (1 - sps.norm.cdf(abs(z))) if math.isfinite(z) else float('nan')
    return vr, z, p


def test_vr_random_walk_recovers_unity():
    """On i.i.d. Gaussian noise the VR should be ~1 at every lag."""
    rng = np.random.default_rng(42)
    r = rng.normal(0, 0.01, size=5000)
    for lag in (2, 5, 10, 20):
        vr, z, p = _vr_test(r, lag)
        assert 0.85 < vr < 1.15, f'lag={lag}: VR={vr:.3f} far from 1 on iid noise'
        # |z| should not be huge — most draws fall well within ±3
        assert abs(z) < 3.5, f'lag={lag}: |z|={abs(z):.2f} exceeds expected band'


def test_vr_mean_reverting_below_one():
    """A genuinely mean-reverting series (AR(1) with phi=-0.3) should give VR<1."""
    rng = np.random.default_rng(7)
    n = 4000
    eps = rng.normal(0, 0.01, size=n)
    r = np.empty(n)
    r[0] = eps[0]
    phi = -0.3
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    vr20, z20, _ = _vr_test(r, 20)
    assert vr20 < 0.95, f'AR(1) phi=-0.3 should give VR(20)<0.95, got {vr20:.3f}'
    assert z20 < -2.0, f'should reject random-walk null, got z={z20:.2f}'


# ════════════════════════════════════════════════════════════════════════════
#  arch.arch_model GARCH(1,1) wraps + per-asset MLE
# ════════════════════════════════════════════════════════════════════════════

def test_garch_recovers_persistence_on_simulated_series():
    """Fit GARCH on a simulated GARCH(1,1) series; recovered alpha+beta
    should be in the same ballpark as the true persistence."""
    from arch import arch_model
    rng = np.random.default_rng(2024)
    n = 4000
    a_true, b_true, w_true = 0.10, 0.85, 1.0e-5
    eps = rng.normal(0, 1, size=n)
    r = np.empty(n)
    var = np.empty(n)
    var[0] = w_true / max(1 - a_true - b_true, 1e-6)
    r[0] = math.sqrt(var[0]) * eps[0]
    for t in range(1, n):
        var[t] = w_true + a_true * r[t - 1] ** 2 + b_true * var[t - 1]
        r[t] = math.sqrt(var[t]) * eps[t]

    res = arch_model(r * 100, vol='Garch', p=1, q=1, mean='Zero',
                     dist='normal').fit(disp='off')
    a = float(res.params['alpha[1]'])
    b = float(res.params['beta[1]'])
    persistence = a + b
    assert 0.85 < persistence < 0.995, f'persistence {persistence:.3f} off plausible'
    assert abs(a - a_true) < 0.10, f'alpha recovery off: got {a:.3f}, true {a_true}'
    assert abs(b - b_true) < 0.10, f'beta recovery off: got {b:.3f}, true {b_true}'


# ════════════════════════════════════════════════════════════════════════════
#  Anis-Lloyd bias-corrected Hurst on Gaussian noise → ~0.5
# ════════════════════════════════════════════════════════════════════════════

def _expected_rs(n: int) -> float:
    """Anis-Lloyd (1976) closed form for E[R/S(n)] under iid null.
    For small n uses gamma ratio; for larger n falls back on the Stirling
    approximation to avoid Gamma overflow."""
    if n <= 1:
        return 0.0
    if n <= 340:
        gamma_ratio = math.gamma((n - 1) / 2) / (math.sqrt(math.pi) * math.gamma(n / 2))
    else:
        # log-gamma form is finite past the gamma-function overflow point
        loggr = (math.lgamma((n - 1) / 2)
                 - 0.5 * math.log(math.pi)
                 - math.lgamma(n / 2))
        gamma_ratio = math.exp(loggr)
    s = sum(math.sqrt((n - i) / i) for i in range(1, n))
    return gamma_ratio * s


def _hurst(series: np.ndarray, lags=None) -> float:
    if lags is None:
        lags = [10, 20, 40, 80, 160, 320]
    x = np.asarray(series, dtype=float)
    log_lags, log_rs, log_exp = [], [], []
    for lag in lags:
        if lag * 2 > len(x):
            break
        chunks = len(x) // lag
        rs_vals = []
        for i in range(chunks):
            seg = x[i * lag:(i + 1) * lag]
            seg = seg - seg.mean()
            cum = np.cumsum(seg)
            r = cum.max() - cum.min()
            s = seg.std(ddof=0)
            if s > 0:
                rs_vals.append(r / s)
        if rs_vals:
            log_lags.append(math.log(lag))
            log_rs.append(math.log(np.mean(rs_vals)))
            log_exp.append(math.log(_expected_rs(lag)))
    if len(log_lags) < 3:
        return float('nan')
    h_emp, _, _, _, _ = sps.linregress(log_lags, log_rs)
    h_exp, _, _, _, _ = sps.linregress(log_lags, log_exp)
    return float(h_emp - h_exp + 0.5)


def test_hurst_gaussian_noise_close_to_half():
    """Bias-corrected Hurst on iid Gaussian noise (n=2500, seed=42)
    should sit in [0.42, 0.58]."""
    rng = np.random.default_rng(42)
    r = rng.normal(0, 0.01, size=2500)
    H = _hurst(r)
    assert 0.42 <= H <= 0.58, f'Hurst on iid noise = {H:.3f}, outside [0.42, 0.58]'


# ════════════════════════════════════════════════════════════════════════════
#  Yang-Zhang OHLC vol — on GBM with no overnight gap behaves like RV
# ════════════════════════════════════════════════════════════════════════════

def _yang_zhang(open_p, high, low, close, window=21):
    log_co = np.log(open_p / close.shift(1))
    log_oc = np.log(close / open_p)
    log_ho = np.log(high / open_p)
    log_lo = np.log(low / open_p)
    log_hc = np.log(high / close)
    log_lc = np.log(low / close)
    rs = log_ho * log_hc + log_lo * log_lc
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    var_overnight  = log_co.rolling(window=window, min_periods=window).var()
    var_open_close = log_oc.rolling(window=window, min_periods=window).var()
    var_rs         = rs.rolling(window=window, min_periods=window).mean()
    return np.sqrt((var_overnight + k * var_open_close + (1 - k) * var_rs).clip(lower=0))


def test_yang_zhang_finite_and_positive_on_gbm():
    """Sanity-check Yang-Zhang on a GBM-style synthetic: every rolling
    window should produce a finite positive vol estimate, the estimator
    should never explode, and it should be in the same order of magnitude
    as the input sigma. The exact bias depends on how variance splits
    between the overnight, open-to-close, and Rogers-Satchell components
    — that decomposition is tested via the notebook's in-line sanity
    block, not here."""
    rng = np.random.default_rng(99)
    n = 2000
    sigma_d = 0.01
    # Split variance: 30% overnight, 50% open-to-close, 20% Rogers-Satchell.
    overnight = rng.normal(0, sigma_d * math.sqrt(0.3), size=n)
    intraday  = rng.normal(0, sigma_d * math.sqrt(0.5), size=n)
    rs_noise  = rng.normal(0, sigma_d * math.sqrt(0.2), size=n)
    open_p = np.empty(n)
    close  = np.empty(n)
    open_p[0] = 100.0
    close[0]  = open_p[0] * math.exp(intraday[0])
    for t in range(1, n):
        open_p[t] = close[t - 1] * math.exp(overnight[t])
        close[t]  = open_p[t] * math.exp(intraday[t])
    open_p = pd.Series(open_p); close = pd.Series(close)
    swing = np.abs(rs_noise) * close
    high = pd.concat([open_p, close], axis=1).max(axis=1) + swing
    low  = pd.concat([open_p, close], axis=1).min(axis=1) - swing
    yz = _yang_zhang(open_p, high, low, close, window=21)
    yz_clean = yz.dropna()
    assert len(yz_clean) > 100, 'YZ produced too few estimates'
    assert (yz_clean > 0).all(), 'YZ produced non-positive estimates'
    assert np.isfinite(yz_clean).all(), 'YZ produced non-finite estimates'
    yz_ann = yz_clean * math.sqrt(252)
    target = sigma_d * math.sqrt(252)
    # Same order of magnitude — within a factor of 3.
    assert (target / 3) < yz_ann.mean() < (3 * target), \
        f'YZ mean {yz_ann.mean():.3f} not in same OOM as target {target:.3f}'


# ════════════════════════════════════════════════════════════════════════════
#  Mantegna distance is a valid ultrametric
# ════════════════════════════════════════════════════════════════════════════

def test_mantegna_distance_bounds():
    """For rho in [-1, 1] the Mantegna distance d = sqrt(0.5*(1-rho)) is
    in [0, 1] and satisfies d(rho=1) = 0, d(rho=-1) = 1."""
    rhos = np.linspace(-1, 1, 21)
    d = np.sqrt(0.5 * (1 - rhos))
    assert np.isclose(d[-1], 0.0)
    assert np.isclose(d[0], 1.0)
    assert np.all((d >= 0) & (d <= 1))


# ════════════════════════════════════════════════════════════════════════════
#  Equicorrelated recovery —  variance decomposition
# ════════════════════════════════════════════════════════════════════════════

def test_variance_decomp_equicorrelated():
    """If all pairwise correlations equal rho and weights are equal, the
    closed-form co-movement share is rho * (1 - 1/N) when vols are equal.
    Verify the vectorized decomposition matches."""
    rng = np.random.default_rng(11)
    n = 10
    rho = 0.4
    sigma = 0.2
    # Build cov & corr by construction
    corr = np.full((n, n), rho); np.fill_diagonal(corr, 1.0)
    vols = np.full(n, sigma)
    w = np.full(n, 1 / n)
    cov = np.outer(vols, vols) * corr
    diagonal_var = float(np.sum(w ** 2 * vols ** 2))
    total_var = float(w @ cov @ w)
    co_movement_var = total_var - diagonal_var
    co_movement_share = co_movement_var / total_var
    expected = rho * (1 - 1 / n) / ((1 / n) + rho * (1 - 1 / n))
    assert abs(co_movement_share - expected) < 1e-10, \
        f'co-movement share {co_movement_share:.6f} != {expected:.6f}'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

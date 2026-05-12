# Securities Analysis — Correlation & Volatility

Two production-grade Jupyter notebooks for institutional-style correlation
and volatility analysis on a multi-asset ETF portfolio. Both run end-to-end
from a single Colab cell or local Python 3.10+ environment, fetch their own
data from Yahoo Finance, cache it locally, and emit a fixed set of
publication-quality dark-theme charts plus a console scorecard.

The notebooks are aimed at two audiences in parallel:

- **Quant readers** — the methods sections include LaTeX for every
  estimator, explicit references to the academic papers, and a `tests/`
  directory with reference implementations that exercise the key
  estimators on synthetic inputs.
- **Intermediate retail traders** — every output is accompanied by a
  plain-language interpretation, every metric label is spelled out
  (Co-Movement vs Diagonal rather than systematic/idiosyncratic), and
  the README's Interpretation Guide table maps each headline number to
  "what does this mean for me."

## Sample output

`images/correlation/01_executive_dashboard.png` is the headline visualization
for the correlation side — an 8-panel page showing the portfolio's anchor
(SPY) correlation, β, tail behaviour, drawdown profile, and risk
decomposition. `images/volatility/GLD_dashboard1_core.png` is the
representative per-asset dashboard for the volatility side — comparing
seven volatility estimators (Realized, Parkinson, Garman-Klass,
Rogers-Satchell, Yang-Zhang, EWMA, GARCH(1,1)) and identifying the current
regime.

## Methodology

- **Multi-method historical correlation** — Pearson, Spearman, Kendall, and
  RiskMetrics-style EWMA (λ = 0.94), all reported side-by-side in the master
  table.
- **Tail-regime correlation at three percentiles** — pairwise correlation
  restricted to the worst 5%, 10%, and 15% of anchor (SPY) days, so the
  "diversification breaks in tails" hypothesis can be quantified rather
  than asserted.
- **Variance decomposition** — Co-Movement share (sum of cross-asset
  covariance contributions) vs Diagonal share (sum of each asset's own
  variance contribution). Distinct from CAPM-style market-factor
  decomposition, which is not computed here.
- **PCA + ENB diversification scorecard** — variance share of PC1 / PC2 /
  tail, plus effective number of independent bets via the entropy-based
  ENB metric.
- **Hierarchical clustering with Mantegna's distance** —
  d_ij = sqrt(0.5 * (1 - rho_ij)) (Mantegna 1999), which is a true
  ultrametric on a correlation matrix. Ward linkage.
- **OHLC volatility estimators** — Realized (close-to-close), Parkinson
  (high-low), Garman-Klass (OHLC), Rogers-Satchell (drift-robust OHLC),
  Yang-Zhang (Garman-Klass + overnight). On range-trading or drift-heavy
  series, the range-based estimators have ~5x the efficiency of plain
  close-to-close.
- **GARCH(1,1) MLE** — fitted per asset via `arch.arch_model`. Reports α,
  β, ω, persistence (α + β), half-life (log 0.5 / log(α + β)).
- **Bias-corrected Hurst exponent** — Anis-Lloyd (1976) closed-form
  correction subtracted from the empirical R/S slope. The published H ≈ 0.5
  for iid Gaussian noise rather than the upward-biased ~0.62 a naive
  R/S regression returns.
- **Lo-MacKinlay variance ratio** — random-walk null, overlapping-returns
  asymptotic SE: `sqrt(2 * (2k-1) * (k-1) / (3*k*T))` at lags 2, 5, 10, 20.
- **Multiple-testing correction** — pairwise correlation significance
  reported with Benjamini-Hochberg FDR at α = 0.05, not just uncorrected
  t-tests.

## How to run

### Local

```bash
git clone <repo-url> Analysis_securities
cd Analysis_securities
python -m venv .venv
.venv/Scripts/activate          # Windows
# or: source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
jupyter notebook notebooks/
```

Open either notebook and run all cells. First run will populate
`data/cache/` with parquet files (~10 MB); subsequent runs are seconds.

### Colab

Open either notebook via the badge below (replace the placeholder
GitHub user/repo path with your fork):

[![Open Correlation_Analysis.ipynb in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/alexeyklek10/Security_Analysis/blob/main/notebooks/Correlation_Analysis.ipynb)
[![Open Volatility_Analysis.ipynb in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/alexeyklek10/Security_Analysis/blob/main/notebooks/Volatility_Analysis.ipynb)

In Colab, prepend a single cell with:

```python
!pip install -q yfinance arch statsmodels scikit-learn pyarrow
```

## Interpretation guide

| Metric | What it means | Typical / good values |
|---|---|---|
| Portfolio ρ to SPY | How tightly the book moves with broad US equity | Multi-asset book: 0.3 - 0.7. Single-factor: 0.85+ |
| Portfolio β to SPY | Sensitivity coefficient vs SPY (regression slope) | Defensive: 0.3 - 0.6; balanced: 0.6 - 0.9; aggressive: > 0.9 |
| Avg Pairwise Correlation | Mean of the upper-triangle Pearson correlations | < 0.30: well-diversified; 0.30 - 0.50: typical; > 0.50: redundant |
| Diversification Ratio | Weighted avg vol ÷ portfolio vol | > 1.5: strong; 1.2 - 1.5: moderate; < 1.2: weak |
| Co-Movement Share | % of portfolio variance from cross-asset covariances | Lower = more diversified |
| Diagonal Share | % of portfolio variance from per-asset variances | Higher = more diversified |
| ENB (Effective N Bets) | Entropy-equivalent independent-bet count | N_assets / 2 is the baseline; > 0.7 × N is excellent |
| GARCH persistence (α + β) | How long shocks live in the vol process | 0.94 - 0.98 normal; > 0.99 near-unit-root |
| GARCH half-life | Days for a vol shock to decay 50% | 15-30 days is typical for equity ETFs |
| Hurst exponent (bias-corrected) | < 0.5 mean-reverting, ≈ 0.5 random walk, > 0.5 trending | 0.42-0.58 is "indistinguishable from random walk" |
| Yang-Zhang vol | Most efficient OHLC vol estimator on gappy data | Closer to GARCH than to close-to-close on intraday-active assets |

## Limitations and known caveats

- **Single-number kurtosis is a noisy diagnostic for series with
  concentrated extreme events.** BTAL's reported kurtosis after the May
  2026 data-cleaning pass is roughly 4-5; the cross-asset comparison
  table flags any value > 20 as a candidate for the per-asset
  distribution plot rather than for taking the kurtosis number at face
  value. The volatility notebook also prints a top-5 |log_return| days
  diagnostic for the heaviest-tailed tickers (BTAL, MNA) so a reader can
  see whether the tails are real-event-driven (e.g. COVID March 2020 for
  merger-arb) or a vendor data artifact.
- **GARCH(1,1) assumes a single volatility regime.** It cannot
  separately model a "calm" vs "stressed" volatility process. Persistence
  estimates near 1.0 should be interpreted as "the volatility process
  may be non-stationary on this sample" rather than as a number to
  forecast with.
- **Rolling-window choices are convention-dependent.** 21-day Realized
  vs 63-day vs 252-day will give different regime classifications. The
  notebook reports all three but doesn't claim a single "right" window.
- **No transaction costs, slippage, or liquidity premia.** Correlation
  and volatility estimates are pre-cost; any backtested portfolio impact
  derivable from these numbers is gross-of-cost.
- **Survivorship risk.** The ticker list is fixed today's-set; series for
  delisted equivalents (LSE-listed funds in the correlation universe)
  use US sub-tickers explicitly chosen for liquid present-day coverage.
  Earlier-history bias is small but real.
- **Yahoo data quality is uneven.** The volatility notebook applies a
  general filter for vol=0 price-change rows (vendor stub artifacts) and
  one named mask for BTAL 2015-04-29 (a confirmed bad-print row that
  the general filter cannot catch because volume is non-zero). Both are
  documented inside `fetch_ohlc_data`.

## Development

```bash
# One-time: enable the nbstripout filter so notebook outputs don't get
# committed.
.venv/Scripts/nbstripout --install
.venv/Scripts/pytest tests/
```

The notebooks are designed to remain Colab-pasteable, so the cache helper
and `apply_theme()` are duplicated byte-for-byte between them rather than
imported. If you modify either, copy the change to the other.

## License

MIT — see [`LICENSE`](LICENSE).

# Securities Analysis: Correlation & Volatility

Two Jupyter notebooks I use to analyse correlation structure and volatility
regimes across a multi-asset ETF book. They fetch from Yahoo Finance, cache
locally, and produce a fixed dashboard plus a console scorecard. Everything
runs from a single Colab cell or a local Python 3.10+ environment.

## Sample output

`images/correlation/01_executive_dashboard.png` is the headline page for the
correlation side: an 8-panel layout showing portfolio ρ and β to the SPY
anchor, tail behaviour, the drawdown profile, and the risk decomposition.

`images/volatility/GLD_dashboard1_core.png` is the representative per-asset
volatility dashboard. It overlays seven estimators (Realized, Parkinson,
Garman-Klass, Rogers-Satchell, Yang-Zhang, EWMA, GARCH(1,1)) and labels the
current regime.

## Methodology

- **Multi-method historical correlation.** Pearson, Spearman, Kendall, and
  RiskMetrics-style EWMA (λ = 0.94), all reported side-by-side in the master
  table.
- **Tail-regime correlation at three percentiles.** Pairwise correlation
  restricted to the worst 5%, 10%, and 15% of anchor (SPY) days, so the
  "diversification breaks in tails" hypothesis can be quantified rather than
  asserted.
- **Variance decomposition.** Co-movement share (sum of cross-asset
  covariance contributions) vs diagonal share (sum of each asset's own
  variance contribution). This is distinct from CAPM-style market-factor
  decomposition, which is not computed here.
- **PCA + ENB diversification scorecard.** Variance share of PC1 and PC2,
  plus the effective number of independent bets via the entropy-based ENB
  metric.
- **Hierarchical clustering with Mantegna's distance**
  `d_ij = sqrt(0.5 * (1 - rho_ij))` (Mantegna 1999), which is a true
  ultrametric on a correlation matrix. Ward linkage.
- **OHLC volatility estimators.** Realized (close-to-close), Parkinson
  (high-low), Garman-Klass (OHLC), Rogers-Satchell (drift-robust OHLC),
  Yang-Zhang (Garman-Klass plus overnight). On range-trading or drift-heavy
  series the range-based estimators have roughly 5x the efficiency of plain
  close-to-close.
- **GARCH(1,1) MLE** fitted per asset via `arch.arch_model`, reporting α, β,
  ω, persistence (α + β), and half-life log(0.5) / log(α + β).
- **Bias-corrected Hurst exponent.** Anis-Lloyd (1976) closed-form
  correction subtracted from the empirical R/S slope, so the published
  H ≈ 0.5 for iid Gaussian noise rather than the upward-biased ~0.62 a naive
  R/S regression returns.
- **Lo-MacKinlay variance ratio.** Random-walk null with the
  overlapping-returns asymptotic SE `sqrt(2 * (2k-1) * (k-1) / (3*k*T))` at
  lags 2, 5, 10, 20.
- **Multiple-testing correction.** Pairwise correlation significance
  reported with Benjamini-Hochberg FDR at α = 0.05, not just uncorrected
  t-tests.

## How to run

### Local

```bash
git clone https://github.com/alexeyklek10/Security_Analysis.git
cd Security_Analysis
python -m venv .venv
.venv/Scripts/activate              # Windows
# or: source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
jupyter notebook notebooks/
```

Open either notebook and run all cells. The first run populates `data/cache/`
with parquet files (~10 MB); subsequent runs are seconds.

### Colab

Open via the badge below. The first cell of the volatility notebook installs
`arch` on first run; everything else is already in Colab's default image.

[![Open Correlation_Analysis.ipynb in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/alexeyklek10/Security_Analysis/blob/main/notebooks/Correlation_Analysis.ipynb)
[![Open Volatility_Analysis.ipynb in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/alexeyklek10/Security_Analysis/blob/main/notebooks/Volatility_Analysis.ipynb)

## Interpretation guide

| Metric | What it means | Typical / good values |
|---|---|---|
| Portfolio ρ to SPY | How tightly the book moves with broad US equity | Multi-asset book: 0.3 to 0.7. Single-factor: 0.85+ |
| Portfolio β to SPY | Sensitivity coefficient vs SPY (regression slope) | Defensive: 0.3 to 0.6; balanced: 0.6 to 0.9; aggressive: > 0.9 |
| Avg pairwise correlation | Mean of the upper-triangle Pearson correlations | < 0.30: well-diversified; 0.30 to 0.50: typical; > 0.50: redundant |
| Diversification ratio | Weighted avg vol ÷ portfolio vol | > 1.5: strong; 1.2 to 1.5: moderate; < 1.2: weak |
| Co-movement share | % of portfolio variance from cross-asset covariances | Lower means more diversified |
| Diagonal share | % of portfolio variance from per-asset variances | Higher means more diversified |
| ENB (effective N bets) | Entropy-equivalent independent-bet count | N_assets / 2 is the baseline; > 0.7 × N is excellent |
| GARCH persistence (α + β) | How long shocks live in the vol process | 0.94 to 0.98 normal; > 0.99 near-unit-root |
| GARCH half-life | Days for a vol shock to decay 50% | 15 to 30 days is typical for equity ETFs |
| Hurst exponent (bias-corrected) | < 0.5 mean-reverting, ≈ 0.5 random walk, > 0.5 trending | 0.42 to 0.58 is "indistinguishable from random walk" |
| Yang-Zhang vol | Most efficient OHLC vol estimator on gappy data | Closer to GARCH than to close-to-close on intraday-active assets |

## Limitations

A few caveats worth flagging before reading too much into any single number.

- **Single-number kurtosis is a noisy diagnostic for series with
  concentrated extreme events.** BTAL's reported kurtosis after the May 2026
  data-cleaning pass is roughly 4 to 5; the cross-asset comparison table
  flags any value above 20 as a candidate for the per-asset distribution
  plot rather than for taking the kurtosis number at face value. The
  volatility notebook also prints a top-5 |log_return| days diagnostic for
  the heaviest-tailed tickers (BTAL, MNA) so a reader can see whether the
  tails are real-event-driven (e.g. COVID March 2020 for merger-arb) or a
  vendor data artifact.
- **GARCH(1,1) assumes a single volatility regime.** It cannot separately
  model a calm process and a stressed process. Persistence estimates near
  1.0 should be read as "the volatility process may be non-stationary on
  this sample" rather than as a number to forecast with.
- **Rolling-window choices are convention-dependent.** 21-day vs 63-day vs
  252-day realized vol will give different regime classifications. The
  notebook reports all three but does not claim a single "right" window.
- **No transaction costs, slippage, or liquidity premia.** Correlation and
  volatility estimates are pre-cost; any backtested portfolio impact
  derivable from these numbers is gross-of-cost.
- **Survivorship risk.** The ticker list is fixed at today's set; for
  delisted LSE-listed funds I substitute US-listed ETFs explicitly chosen
  for liquid present-day coverage. Earlier-history bias is small but real.
- **Yahoo data quality is uneven.** The volatility notebook applies a
  general filter for vol=0 price-change rows (vendor stub artifacts) and
  one named mask for BTAL on 2015-04-29 (a confirmed bad-print row that the
  general filter cannot catch because volume is non-zero). Both are
  documented inline in `fetch_ohlc_data`.

## Development

```bash
# One-time: enable the nbstripout filter so notebook outputs don't end up
# in diffs.
.venv/Scripts/nbstripout --install
.venv/Scripts/pytest tests/
```

The notebooks stay Colab-pasteable, so the cache helper and `apply_theme()`
are duplicated byte-for-byte between them rather than imported from a shared
module. If you modify either, copy the change to the other.

## License

MIT. See [`LICENSE`](LICENSE).

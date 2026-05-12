"""F33/F34 — split each notebook from single cell into structured multi-cell
layout with markdown headers between code sections.

This is a pragmatic interpretation of the spec's 18/17-cell sequence:
markdown sections are inserted between the existing top-level code section
banners so the notebook reads top-to-bottom with context, while keeping
each notebook still a strict concatenation of its code cells (Colab-pasteable).
"""
from __future__ import annotations

import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def split_notebook(nb_path, src_path, sections):
    with open(src_path, 'r', encoding='utf-8') as f:
        src = f.read()
    lines = src.splitlines(keepends=True)

    splits = [(0, '')]
    for sid, md, pat in sections:
        for i, ln in enumerate(lines):
            if pat in ln and not any(s[0] == i for s in splits):
                splits.append((i, md))
                break

    splits.sort(key=lambda x: x[0])
    split_indices = [s[0] for s in splits] + [len(lines)]
    headers = [s[1] for s in splits]

    cells = []
    for k, hdr in enumerate(headers):
        if hdr:
            cells.append({
                'cell_type': 'markdown',
                'metadata': {},
                'source': hdr.splitlines(keepends=True),
            })
        chunk_lines = lines[split_indices[k]:split_indices[k + 1]]
        if chunk_lines:
            cells.append({
                'cell_type': 'code',
                'metadata': {},
                'execution_count': None,
                'outputs': [],
                'source': chunk_lines,
            })

    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    nb['cells'] = cells
    with open(nb_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print(f'{nb_path}: split into {len(cells)} cells')


CORR_SECTIONS = [
    ('1', """# Securities Analysis - Correlation & Diversification

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/<user>/<repo>/blob/main/notebooks/Correlation_Analysis.ipynb)

This notebook computes multi-method correlation matrices (Pearson, Spearman,
Kendall, EWMA, tail), runs a paired-Wilcoxon stress comparison, decomposes
portfolio variance into co-movement vs diagonal shares, and produces nine
publication-quality charts. The first run populates `data/cache/` with
parquet files for the configured ticker list; subsequent runs load from
cache in seconds.

## How to read this notebook

- Each section starts with a one-paragraph markdown intro describing what
  the next code block does and what its outputs mean.
- All numeric outputs print to stdout; charts are saved to
  `images/correlation/` (9 PNGs).
- The end-of-notebook scorecard summarizes the headline metrics.

## Setup
""", '# -*- coding: utf-8 -*-'),

    ('2', """## Configuration

The `PORTFOLIO` list below is the only thing most users need to touch. The
ticker universe is a multi-asset book (US large/small/EM, Japan large/small,
managed futures, gold/miners, commodities, defensive multi-asset). Weights
are normalized to sum to 1 automatically.

`ANCHOR_ASSET` is the reference series everything correlates against — SPY
by default. `TAIL_PERCENTILE` controls the *primary* tail-correlation
matrix; the three-percentile dashboard (5%, 10%, 15%) runs in addition.
""", '#  SECTION 2 — CONFIGURATION'),

    ('3', """## Data fetch

Per-ticker yfinance download via a parquet cache. `auto_adjust=True` so
OHLC are split/dividend-adjusted in lockstep. Forward-fill is capped at
5 trading days; longer gaps surface as NaN runs so any zombie-ticker
issues are visible rather than papered over.
""", '#  SECTION 3 — DATA ENGINE'),

    ('4', """## Correlation suite

Pearson / Spearman / Kendall / EWMA computed in one pass. The tail
correlation is the conditional Pearson restricted to the worst-N% days
for the active stressor (anchor or portfolio); F13 adds a side-by-side
view at three stress percentiles since any single percentile is noisy.
""", '#  SECTION 4 — CORRELATION SUITE'),

    ('5', """## Statistical tests

Pairwise correlation significance with Benjamini-Hochberg FDR (F12),
Bartlett's sphericity (skipped if det(R) is numerically singular, F29),
paired Wilcoxon tail-vs-normal (F08), correlation stability via paired
Wilcoxon on Fisher-z half-period deltas (F07), Ljung-Box volatility
clustering on squared portfolio returns, and Jarque-Bera normality.
""", '#  SECTION 5 — STATISTICAL TESTS'),

    ('6', """## Portfolio metrics & risk decomposition

Annualized vol, Sharpe, max drawdown, diversification ratio, plus the
Co-Movement / Diagonal variance split (F11+F14). These labels are
distinct from CAPM-style market-factor decomposition, which requires
regression against an index factor and is not computed here.
""", '#  SECTION 6 — PORTFOLIO METRICS'),

    ('7', """## Diversification structure (PCA / ENB / clustering)

PCA on the standardized log returns. The ENB (Effective N Bets) is an
entropy-equivalent count of independent bets. Hierarchical clustering
uses Mantegna's metric `d = sqrt(0.5 * (1 - rho))`, which is a true
ultrametric on a correlation matrix (Mantegna 1999, Eur. Phys. J. B).
""", '#  SECTION 7 — DIVERSIFICATION STRUCTURE'),

    ('8', """## Visualization (9 consolidated charts)

The chart suite was consolidated from 21 figures to 9 (F24). Each PNG
saves to `images/correlation/`. The numbered prefixes preserve the
original chart ordering for cross-reference with prior runs.
""", '#  SECTION 8 — VISUALIZATION'),

    ('9', """## Run the full analysis

The cell below kicks off `run_full_analysis()`. Expect a few minutes on
first run (yfinance fetch + per-ticker stats); subsequent runs are
cache-fast.
""", '#  SECTION 12 — MAIN EXECUTION'),
]

VOL_SECTIONS = [
    ('1', """# Securities Analysis - Volatility

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/<user>/<repo>/blob/main/notebooks/Volatility_Analysis.ipynb)

Per-asset OHLC volatility analysis using seven estimators (Realized,
Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang, EWMA RiskMetrics,
GARCH(1,1) MLE), bias-corrected Hurst (Anis-Lloyd 1976), Lo-MacKinlay
variance ratio test at four lags, and a heavy-tail event diagnostic that
flags suspect days for the more exotic tickers.

## How to read this notebook

- Each ticker gets a 4-panel dashboard saved to `images/volatility/`.
- Console output mirrors the dashboards in tabular form, with regime
  classification, Hurst regime, and per-test significance flags.
- The cross-asset section ends with a top-5 |log_return| days diagnostic
  for known heavy-tail tickers so the reader can sanity-check that the
  reported kurtosis comes from real events rather than vendor artifacts.

## Setup
""", '# -*- coding: utf-8 -*-'),

    ('2', """## Configuration

`TICKERS` is the universe (29 ETFs spanning precious metals, miners,
uranium, Japan, AI/robotics, utilities, alternatives, treasuries,
international). `SHOWCASE` (= GLD) gets a deeper-dive treatment.

GARCH mode is `'mle'` by default (fitted per asset via `arch.arch_model`);
swap to `'manual'` for a pedagogical fixed-parameter recursion (see the
comment block inside `garch_volatility`).
""", '#  SECTION 3: CONFIGURATION PANEL'),

    ('3', """## Data fetch

Per-ticker yfinance download via the F19 parquet cache. The function
applies two vendor-error filters before computing returns:

1. A general rule: drop any row where `Volume == 0` and `Close` differs
   from the previous `Close` by more than 0.5%. With no trades the
   close should equal the prior close; a phantom change on a zero-
   volume day is a known yfinance stub-row artifact.
2. A named mask for BTAL on 2015-04-29 (a $12.96 print inside a $19.30
   corridor on volume 109k that survives the general filter). Details
   are documented inside `fetch_ohlc_data`.
""", '#  SECTION 5: DATA ENGINE'),

    ('4', """## Volatility estimators

The seven estimators in one section. Each closed-form formula lives in
the function docstring; headline relationships:

- **Realized** (close-to-close): the baseline, efficiency 1x.
- **Parkinson** (high-low): ~5x more efficient than RV, downward-biased
  when drift is nonzero.
- **Garman-Klass** (OHLC): 7-8x efficient; drift-sensitive.
- **Rogers-Satchell**: drift-robust OHLC.
- **Yang-Zhang**: GK + overnight gap; designed for gappy series.
- **EWMA**: RiskMetrics-style with lambda = 0.94.
- **GARCH(1,1) MLE**: per-asset, via `arch_model(... vol='Garch')`.

All rolling estimators use `min_periods = window` so the series starts
honestly at the first index with a full lookback (F15).
""", '#  SECTION 6: VOLATILITY ESTIMATORS'),

    ('5', """## Statistical tests (per asset)

Jarque-Bera, Ljung-Box on returns and on squared returns (ARCH effect),
Lo-MacKinlay variance ratio at lags 2/5/10/20 with the corrected
overlapping-returns asymptotic SE (F03).
""", '#  SECTION 8: STATISTICAL TESTS'),

    ('6', """## Hurst exponent (bias-corrected)

Anis-Lloyd (1976) closed-form expected R/S subtracted from the
empirical slope before fitting (F05+F16). On iid Gaussian noise this
returns H ~ 0.5 rather than the upward-biased ~0.62 from a naive R/S
regression.
""", '#  SECTION 9: HURST EXPONENT'),

    ('7', """## Per-asset dashboard generation

Each ticker produces 4 PNG panels: core estimators overlaid, term
structure across rolling windows, tail-risk + GARCH overlay, and ATR
percentile bands. Saved to `images/volatility/{ticker}_dashboard{1-4}_*.png`.
""", '#  SECTION 12: DASHBOARD'),

    ('8', """## Cross-asset comparison

Final-row regime/Hurst/skew/kurt table across all tickers, plus the
heavy-tail event diagnostic for BTAL and MNA. Failed tickers (delisted,
no data) surface as NaN rows with `(failed)` regime flags rather than
being silently dropped (F21).
""", '#  SECTION 13: CROSS-ASSET COMPARISON'),

    ('9', """## Run the full analysis
""", '#  SECTION 14: MAIN EXECUTION'),
]


if __name__ == '__main__':
    split_notebook('Correlation_Analysis.ipynb', '_corr_work.py', CORR_SECTIONS)
    split_notebook('Volatility_Analysis.ipynb', '_vol_work.py', VOL_SECTIONS)

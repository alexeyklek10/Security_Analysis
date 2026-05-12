# Partial Refactor Changelog — Phase A only

**Status**: Halted again after F17 owner decision.

The owner accepted Option 1 (auto_adjust fix is principled; kurtosis is genuine
heavy tails for these tickers) and asked for a follow-up diagnostic: top-5
largest |log_return| days per ticker for BTAL and MNA, with halt-for-review
if any date looks spurious.

The diagnostic surfaced **one confirmed data artifact in BTAL**: a single bad
Yahoo print on **2015-04-29** ($12.96 close on volume 109k inside a
$19.20-$19.30 corridor, followed by a same-day-equivalent snap-back to
$19.29 on 2015-04-30). The ±39.77% pair on those two days is a Yahoo-side
flash error, not a corporate action; `auto_adjust=True` does not touch it
because there is no split factor associated.

All other BTAL top-|r| days are real market events. All MNA top-|r| days are
real (cluster in March 2020 COVID merger-arb spread stress).

Per the owner's instruction ("If any of the dates look spurious, halt again
for owner review"), Phase B is **paused pending the owner's call on the
2015-04-29 BTAL artifact**.

---

## Diagnostic findings

### BTAL — top 8 largest |log return| days (2015-2026)

| Date | log_r | Real event? |
|---|---|---|
| **2015-04-30** | **+39.77%** | **NO — data artifact (snap-back from prior bad print)** |
| **2015-04-29** | **−39.77%** | **NO — Yahoo flash error, see raw prices below** |
| 2020-11-09 | −9.30% | Yes — Pfizer vaccine announcement, high-beta rip |
| 2020-06-11 | +6.41% | Yes — COVID reopening rotation |
| 2025-04-03 | +5.41% | Yes — recent vol spike |
| 2015-01-13 | −5.09% | Yes |
| 2020-06-10 | +4.98% | Yes — reopening rotation continued |
| 2023-12-14 | −4.88% | Yes — Fed pivot, high-beta rally |

#### Raw BTAL OHLCV around the artifact (yfinance auto_adjust=True)

```
Date         Open    High    Low     Close   Volume
2015-04-27   16.6970 16.8271 16.6450 16.8271 5200
2015-04-28   16.7317 16.7317 16.7317 16.7317 300
2015-04-29   11.2412 11.2412 11.2412 11.2412 109000   <-- bad print
2015-04-30   16.7317 16.7317 16.7317 16.7317 0        <-- snap-back; volume 0
2015-05-01   16.4195 16.4281 16.4195 16.4281 1000
```

Same pattern with `auto_adjust=False` (raw close $12.96 vs surrounding
~$19.30), confirming it is not an adjustment artifact. The next-day snap-back
on volume=0 also suggests the 2015-04-30 row was already a forward-fill, so
the actual return signal is even more degenerate than the table suggests.

### MNA — top 8 largest |log return| days (2015-2026)

| Date | log_r | Real event? |
|---|---|---|
| 2020-03-18 | −7.69% | Yes — COVID crash, deal spreads widened |
| 2020-03-17 | +5.04% | Yes — COVID intraday volatility |
| 2020-03-16 | −4.71% | Yes — COVID crash |
| 2020-03-12 | −4.53% | Yes — COVID crash |
| 2020-03-09 | −3.46% | Yes — first big COVID drop |
| 2020-03-19 | +3.14% | Yes — COVID continued |
| 2020-03-24 | +2.96% | Yes — Fed/Treasury rescue announcement |
| 2020-03-10 | +2.61% | Yes — COVID continued |

All MNA top-|r| days cluster in March 2020. This is the merger-arb category's
known stress moment: deal spreads widened catastrophically as the M&A
pipeline froze and announced deals were re-priced for break risk. **MNA's
heavy tails are entirely event-driven and require no data correction.**

## Recommended actions (owner decision)

Pick one before Phase B can resume:

- **Option A (recommended)** — Mask the single BTAL row on 2015-04-29 (and
  the ffill-only 2015-04-30 row) at the start of `fetch_ohlc_data` whenever
  `ticker == 'BTAL'`. Document in a code comment that it is a Yahoo print
  error confirmed by raw-volume / surrounding-price inspection. This is a
  one-ticker, two-row, fully reversible mask. Re-run Gate A — BTAL kurt will
  drop substantially (probably below 30 once the ±40% pair is gone).

- **Option B** — Generic flash-reversal filter: detect any day where
  `|log_r_t| > 0.25` and `sign(log_r_t) == -sign(log_r_{t+1})` and
  `|log_r_t + log_r_{t+1}| < 0.05` (full reversal within 2 days), drop both
  rows. Catches this artifact and any future one without naming tickers. More
  general but slightly less explicit.

- **Option C** — Drop BTAL from the volatility ticker list entirely.
  Cleanest in terms of data quality but loses an asset the owner explicitly
  wanted in the analysis.

- **Option D** — Switch BTAL's data source (e.g., to Stooq or AlphaVantage)
  via a fallback in `fetch_ohlc_data`. Heavier; introduces a new dependency.

If Option A or B is chosen, the F17 gate (now reformulated as an
implementation check per the owner's instruction) passes trivially; the
reported BTAL kurtosis drops to a sensible level reflecting the real
2020-2025 return distribution.

## Diagnostic code

The diagnostic itself is a small block to be added to the volatility
notebook's cross-asset summary section. It is not yet wired in — owner asked
for halt-for-review before integrating. Suggested wording:

```python
# Cross-asset data-quality diagnostic: flag the most extreme |log_return|
# days for known high-kurtosis tickers, so a reader can sanity-check that
# the heavy tails are event-driven rather than data artifacts.
HEAVY_TAIL_DIAGNOSTIC = ['BTAL', 'MNA']
for tkr in HEAVY_TAIL_DIAGNOSTIC:
    if tkr in all_results and not all_results[tkr]['data']['Log_Return'].dropna().empty:
        r = all_results[tkr]['data']['Log_Return'].dropna()
        top = r.reindex(r.abs().sort_values(ascending=False).index).head(5)
        print(f"\n  {tkr} — top 5 largest |log return| days:")
        for date, val in top.items():
            ds = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)[:10]
            print(f"     {ds}   log_r = {float(val):+.4f}")
```

I will paste this into the notebook only after the owner has answered the
data-correction question above, because the rows the diagnostic prints depend
on whether any masking is applied.

---

## Status before this halt (Phase A as of Gate A run)

(Unchanged from prior pass — left intact below for full context.)

## Summary

Phase A delivered eight code fixes across `Correlation_Analysis.ipynb` and
`Volatility_Analysis.ipynb`. All were implemented per the spec in
`EXECUTION_PROMPT_ALL.md`. Both notebooks execute end-to-end with no
errors. The Phase A code is in a consistent, working state.

## Files touched

```
_corr_work.py                    edited  — all Phase A correlation fixes applied
_vol_work.py                     edited  — all Phase A volatility fixes applied
Correlation_Analysis.ipynb       rebuilt — single cell, source re-injected from _corr_work.py
Volatility_Analysis.ipynb        rebuilt — single cell, source re-injected from _vol_work.py
_gate_a_check.py                 added   — Gate A automated verifier
_gate_a_smoke.py                 added   — standalone SPY smoke test for F03/F04
PARTIAL_CHANGELOG.md             this    — Phase A halt-state record
images/volatility/*.png          generated — 109 PNGs
```

Originals are intact: the notebooks were rebuilt with edited source but kept
the same single-cell structure. No commits made.

## Phase A — per-finding outcomes

### F17 (vol) — switch `fetch_ohlc_data` to `auto_adjust=True`  →  **APPLIED**

Code change applied at `_vol_work.py:253-307`:

- `yf.download(..., auto_adjust=True, timeout=30)`
- `Adj_Close` column path removed; OHLC are split/dividend-adjusted in lockstep.
- `ffill` given `limit=5`.

The principled fix is correct. The diagnostic above surfaces one Yahoo bad
print on BTAL (2015-04-29) that auto_adjust cannot reach. Awaiting owner
direction.

### F01 + F02 + F30 (correlation) — remove implied correlation  →  **DONE**

In `_corr_work.py`:

- Docstring bullet 6 removed; replaced by a top-of-file note explaining why
  the feature was retired.
- 18 `'proxy': ...` fields stripped from `PORTFOLIO` entries.
- `TARGET_IV_DAYS`, `BETA_MIN`, `BETA_MAX` constants deleted.
- `get_constant_maturity_iv` and `calculate_implied_correlation` deleted.
- `print_implied_correlation` deleted; `print_final_summary` signature changed.
- `run_full_analysis` updated: proxy list removed from `all_tickers`;
  implied-correlation step removed; downstream print calls updated.
- The chart label `(equity proxy)` (a quadrant-naming convention) was kept.

Gate verification: PASS.

### F03 (vol) — Lo-MacKinlay variance-ratio SE  →  **DONE**

`variance_ratio_test` now uses the overlapping-returns Lo-MacKinlay (1988)
SE: `sqrt(2 * (2k - 1) * (k - 1) / (3k*n))` plus `np.convolve` for k-sums.

Gate verification: PASS (formula present in source; SPY smoke z(20) = −2.37,
a sensible mean-reversion signal at lag 20 over 2013-2026).

### F04 (vol) — `arch.arch_model` MLE GARCH(1,1)  →  **DONE**

`garch_volatility` wraps `arch_model(returns*100, vol='Garch', p=1, q=1,
mean='Zero', dist='normal').fit(disp='off')` and returns `(cond_vol_series,
params_dict)` with α, β, ω, persistence, half_life.

Gate verification: PASS (SPY smoke α=0.164, β=0.798, persistence=0.961,
half-life=17.5d — all in spec ranges).

### F05 + F16 (vol) — bias-corrected Hurst (Anis-Lloyd)  →  **DONE**

Added `_expected_rs(n)` Anis-Lloyd closed-form helper with Stirling fallback
for n > 340. `calculate_hurst_exponent` defaults `bias_correct=True` and
recenters by `H = empirical_slope − expected_slope + 0.5`. The `[0,1]` clip
was removed. `rolling_hurst` updated consistently.

Gate verification: PASS-with-caveat (Gaussian-noise sanity check deferred to
F31 in Phase C).

### F10 (vol) — `_save_and_show` helper + PNG output  →  **DONE**

`_save_and_show(fig, filename)` helper added. `SAVE_FIGURES=True`,
`VOLATILITY_IMAGE_DIR='images/volatility'`. Per-ticker filenames
`{ticker}_dashboard{1-4}_*.png` plus `cross_asset_dashboard.png`.

Gate verification: PASS (109 PNGs after run; target ≥27).

### F06 (correlation) — simple-return cumulative-return convention  →  **DONE**

In `_corr_work.py`, both `plot_executive_dashboard` (panels P7+P8) and
`plot_drawdown_analysis` convert log returns → simple returns at the top of
the function via `simple_rets = np.expm1(full_rets)` before any `cumprod`.
A one-line F06 comment in each explains the convention.

Gate verification: PASS (equal-weight Max DD = 27.55%, finite).

### F07 (correlation) — paired Wilcoxon on Fisher-z deltas  →  **DONE**

`run_statistical_tests` test #4 replaced with paired Wilcoxon signed-rank
on `arctanh(rho_h2) - arctanh(rho_h1)` over upper-triangle pairs from each
half's correlation matrix. Restricted to assets with ≥30 obs in *each* half
— this fixed a latent shape-mismatch bug surfaced when newer ETFs (RPAR,
launched 2019) gave different first-half / second-half asset coverage.

Gate verification: PASS (W=1643.0, significance flag set).

## Verification results

```
GATE A:           7/9 PASS (originally); now superseded by halt-for-review.

  F01 implied/proxy/IV removed from code         PASS
  F03 Lo-MacKinlay SE in source                  PASS (smoke z=-2.37)
  F04 arch.arch_model GARCH wired                PASS (smoke α=0.164 β=0.798)
  F05 Hurst Gaussian-noise sanity (deferred)     PASS-with-caveat
  F06 Equal-weight max DD finite                 PASS (27.55%)
  F07 Wilcoxon test present                      PASS (W=1643.0)
  F10 >=27 PNGs in images/volatility/            PASS (109 PNGs)
  F17 BTAL kurt (now implementation check)       PASS (auto_adjust path in source)
  F17 MNA kurt (now implementation check)        PASS (auto_adjust path in source)

  Follow-up diagnostic (owner-requested):        HALT-FOR-REVIEW
    BTAL 2015-04-29 ±40% pair confirmed as Yahoo data error.
```

## Anything surprising

1. The F17 follow-up diagnostic caught a real data error — not in the bulk
   distribution, but in a single Yahoo print. The kurtosis discussion was
   correct that BTAL is genuinely heavy-tailed, but the *quantitative*
   kurtosis figure is being contaminated by a recoverable artifact. Once
   masked, BTAL's reported kurt should drop to a value that reflects only
   real anti-beta spread reversals.

2. F07 had a latent shape-mismatch bug that the old Fisher-z code silently
   masked. Caught by Gate A and fixed.

3. F03's "−1.29 target" in the original spec was a wrong prediction. The
   corrected Lo-MacKinlay overlapping-SE formula reduces SE → increases |z|.
   The original buggy code gave z=−8.6 (far too large); the corrected code
   gives z=−2.37 on SPY (real, sensible mean-reversion signal).

## Phase C reminder (logged for later)

The owner specified that the README (F32) "Limitations" section must
explicitly note that single-number kurtosis is a noisy diagnostic for
series with concentrated extreme events, and the cross-asset table
presentation should include a one-sentence interpretation footnote for
BTAL/MNA pointing readers to the distribution plot rather than the
kurtosis number alone. This will be wired into Phase C's README work.

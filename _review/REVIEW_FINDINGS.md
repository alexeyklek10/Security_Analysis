# Review Findings — Securities Analysis Notebooks

> Reviewer mode: senior quant + technical editor.
> Source notebooks **not modified** in this pass. Two artifacts produced:
> this document, plus `EXECUTION_CHECKLIST.md` for triage.

## Executive summary

Both notebooks are ambitious, well-scoped, and produce a lot of usable
output. The volatility notebook's estimators (Yang-Zhang, Garman-Klass)
are mathematically correct vs textbook formulas. The GARCH and variance-
ratio implementations have correctness issues. The correlation notebook's
**implied-correlation feature is the biggest problem**: it is mislabeled
math (an IV-weighted average of *historical* correlations, not implied)
running on yfinance options data that returns garbage IVs for SPY-class
underliers today. The Hurst-exponent classifier has a systematic +0.08
finite-sample bias confirmed against pure random walks. Beyond the bugs,
the correlation notebook is presentation-heavy (21 figures, many
redundant) and the volatility notebook never writes a PNG to disk —
defeating the "publishable artifact" goal. The biggest lift is **a
correctness pass on five named items (F01-F07)**, after which the
restructuring/visual work is mostly mechanical.

What is already strong: the OHLC estimators in the volatility notebook
(`yang_zhang_volatility`, `garman_klass_volatility`, `rogers_satchell`)
verified bit-identical to textbook formulas; the multi-method
correlation suite (Pearson/Spearman/Kendall/EWMA/Tail) is the right
toolkit; the diversification scorecard (PCA + ENB + determinant +
clusters) is a thoughtful composite metric; the dark institutional
theme is consistent and brand-coherent.

## Run report

**Environment**: Python 3.14.3 (separate venv). yfinance 1.3.0, pandas
3.0.2, numpy 2.4.4, scipy 1.17.1, statsmodels 0.14.6, arch 8.0.0,
sklearn 1.8.0. Matplotlib forced to Agg backend, `PYTHONUTF8=1` to
survive Windows console.

**Correlation notebook** — ran in **~45 s** end-to-end. Zero Python
warnings or exceptions. 22 PNGs saved to CWD (chart 10 paginates to 2
files). Reported warnings from the notebook's own validation logic:
matrix near-singular (determinant ≈ 0, condition number 1975), tail
delta -0.045 (notebook code asks user to "Verify TAIL_MODE = 'anchor'"
— this is a false alarm because the tail delta sign is allowed to be
either direction). 8 of 18 tickers' IVs unavailable from yfinance.

**Volatility notebook** — ran in **~2 min** end-to-end. Two tickers
silently dropped: `ILS` (insufficient observations — only 190 days
since fund launch) and `CERY.L` (404 Not Found on Yahoo). 27/29
assets processed. **Zero figures saved to disk** — every chart goes
to `plt.show()` only. Several cross-asset kurtosis values look
suspicious: BTAL = 344, MNA = 70, INDA = 21, XLU = 15 (see F22).

**Spot-check 1 — Yang-Zhang vs textbook reimplementation**.
Identical, max absolute diff in daily variance = `0.000e+00` on 1477
overlapping rows of SPY 5y. The notebook's formula is correct and the
weighting constant `k = 0.34 / (1.34 + (n+1)/(n-1))` matches Yang & Zhang
(2000). Garman-Klass formula also verified visually against the
textbook closed form.

**Spot-check 2a — Manual GARCH(1,1) vs `arch.arch_model`**. The manual
recursion math is correct: `ω = σ²_LR (1 − α − β)`, initialization at
unconditional variance, mean-reversion target verified
(`σ²_recursion == σ²_sample` to 1e-10). But the **hardcoded
α=0.08, β=0.90** does not match the MLE fit on SPY 5y returns
(α=0.148, β=0.815, persistence 0.96 vs hard-coded 0.98). Correlation of
the two volatility paths = 0.972; RMSE = 1.6e-3 (daily σ); the hard-
coded model overstates current σ by ~13% relative. Acceptable as a
demonstration; not safe as the headline GARCH estimate.

**Spot-check 2b — Variance Ratio asymptotic SE**. Notebook formula
`se = sqrt(2(k-1) / (3kT))` is the non-overlapping-returns SE under
homoscedasticity. The notebook computes VR using **overlapping**
returns, which under homoscedasticity has SE
`sqrt(2(2k-1)(k-1) / (3kT))` (Lo-MacKinlay 1988; Campbell-Lo-MacKinlay
1997, eq. 2.4.39). Concrete consequence on SPY 5y:

| lag | VR (both) | Notebook z | Notebook p | Textbook z | Textbook p |
|-----|-----------|-----------:|-----------:|-----------:|-----------:|
|   2 | 0.849 | −10.17 | 0.0000 | −5.85 | 0.0000 |
|   5 | 0.834 | −8.83  | 0.0000 | −2.90 | 0.0037 |
|  10 | 0.812 | −9.43  | 0.0000 | −2.11 | 0.0351 |
|  20 | 0.824 | −8.60  | 0.0000 | −1.29 | 0.1955 |

The VR estimates are correct; the *test* is over-rejecting random walk.

**Spot-check 3 (bonus) — Hurst on pure Gaussian random walks**.
20 trials, n=2500, white noise. Theory: E[H]=0.5. Measured: mean H =
**0.584** (sd 0.017, range 0.545-0.614). The R/S estimator has a known
finite-sample upward bias; the notebook does not apply the Anis-Lloyd
or Peters correction. Consequence: the cross-asset table's Hurst
column (every asset between 0.54 and 0.63) classifies all of them
"TRENDING" — which is what you would also get from pure noise.

---

## Findings

### [F01] `calculate_implied_correlation` is misnamed
- **Severity:** S0
- **Notebook:** correlation
- **Location:** `calculate_implied_correlation` (≈ lines 1154-1235)
- **Effort:** M
- **What's wrong:** The code inner-loops `var_synth += w_i * w_j * σ_i * σ_j * ρ_ij` using **historical** proxy correlations (`proxy_corr.loc[ri['proxy'], rj['proxy']]`), then returns `(var_synth − Σw_i²σ_i²) / (denominator)`. Algebra reduces to an IV-weighted average of historical correlations:
   numerator = Σ_{i≠j} w_i w_j σ_i^IV σ_j^IV ρ_ij^historical
   denominator = Σ_{i≠j} w_i w_j σ_i^IV σ_j^IV
  Verified with a hand-rolled 3-asset example: notebook output **identical** to that average. The "implied correlation" is not forward-looking and not implied.
   Additionally, every PORTFOLIO entry has `ticker == proxy`, so the entire `beta` machinery yields 1.00 in 18/18 cases — confirmed in our run. The proxy concept is dead code.
- **Proposed fix:** Either (a) remove the feature and explain in markdown why it cannot be computed without an INDEX/basket option, or (b) keep it under the renamed label "IV-weighted historical correlation" with an explicit caveat. A true implied-correlation analysis would require pulling the IV of a portfolio-equivalent index option (e.g. SPY IV for an S&P-like book) and back-solving ρ from `σ²_index_implied = Σ w_i²σ_i² + 2 Σ_{i<j} w_i w_j σ_i σ_j ρ`.
- **Risk if we skip it:** Publishing a feature called "forward-looking implied correlation" that does nothing of the kind is a credibility risk to the entire piece.

### [F02] yfinance options-chain IVs are unusable for this purpose
- **Severity:** S0
- **Notebook:** correlation
- **Location:** `get_constant_maturity_iv` (≈ lines 1074-1151), and any code consuming its output
- **Effort:** S (to remove); M (to migrate to a different source)
- **What's wrong:** A live probe today of `yf.Ticker('SPY').option_chain(...)` returns ATM call IVs of **0.000010 to 0.0078** for 0-3 DTE options at strike ~$737 (SPY at $737.62). SPY ATM IV should be 0.10-0.18. The notebook's run reported "Weighted Stock IV = 3.4%" — physically impossible for this portfolio. The downstream `dispersion_ratio = 1.000` only because numerator == denominator: every IV is its own proxy IV.
- **Proposed fix:** If you keep an IV-based feature, switch the source: pull VIX-style indices for the few liquid underliers (^VIX, ^VXN, ^GVZ for gold, ^OVX for oil) and document the rest as N/A. For the dispersion-ratio idea, you need each asset's IV separately from a *systematic-factor* IV — but most ETFs have no clean factor-IV mapping. Pragmatic option: delete the feature and reclaim the section for something else.
- **Risk if we skip it:** Same as F01.

### [F03] Variance Ratio test asymptotic SE is wrong
- **Severity:** S0
- **Notebook:** volatility
- **Location:** `variance_ratio_test` (≈ lines 566-596)
- **Effort:** S
- **What's wrong:** The notebook computes overlapping k-period sums (`ret_k = Σ ret[i:i+k]`) but uses the **non-overlapping** asymptotic SE `sqrt(2(k-1)/(3kT))`. The Lo-MacKinlay (1988) overlapping-returns SE under homoscedasticity is `sqrt(2(2k-1)(k-1)/(3kT))`. Concrete demonstration on SPY 5y at lag 20: same VR (0.824), notebook z = −8.6 (p ≈ 0) vs textbook z = −1.3 (p = 0.20). Over-rejection of the random-walk null is the systematic effect.
- **Proposed fix:** Replace SE with `np.sqrt(2 * (2 * k - 1) * (k - 1) / (3 * k * n))`. For full robustness against heteroscedasticity, switch to Lo-MacKinlay heteroscedasticity-robust SE (the closed form involves squared-return autocovariances). Or call `arch.unitroot.VarianceRatio` directly (since `arch` is already a useful dep for proper GARCH).
- **Risk if we skip it:** Every VR p-value in the cross-asset table is mis-stated. Multiple assets get "*** significant momentum/mean-reversion" labels that are noise.

### [F04] GARCH(1,1) parameters are hard-coded, not fitted
- **Severity:** S0
- **Notebook:** volatility
- **Location:** `garch_volatility`; config constants `GARCH_ALPHA=0.08`, `GARCH_BETA=0.90` (≈ lines 193-196, 411-430)
- **Effort:** M
- **What's wrong:** The recursion math is correct, but the constants are RiskMetrics-like guesses applied uniformly to every asset (precious metals, bonds, market-neutral funds, uranium miners). MLE fit on SPY 5y returns gave α=0.148, β=0.815 (persistence 0.96 vs 0.98). Cross-asset, persistence varies widely; hard-coded vols can be systematically wrong in level and reactivity. The docstring mentions "manual recursion (no MLE fitting)" but a casual reader will treat the output as a GARCH fit.
- **Proposed fix:** Per-asset MLE fit via `arch.arch_model(returns * 100, vol='Garch', p=1, q=1, mean='Zero')`. Pass `disp='off'`, catch convergence failures, report (α, β, ω, persistence) in the per-asset summary. Keep the manual recursion alongside as an educational sub-cell showing the formula explicitly. Add `arch` to `requirements.txt`.
- **Risk if we skip it:** The GARCH column in the cross-asset table is misleading. For a risk-management audience this is the single most-trusted vol estimator; serving it with default constants undercuts the whole notebook.

### [F05] Hurst exponent has +0.08 finite-sample bias
- **Severity:** S0
- **Notebook:** volatility
- **Location:** `calculate_hurst_exponent`, `rolling_hurst` (≈ lines 483-540)
- **Effort:** M
- **What's wrong:** R/S analysis without finite-sample correction systematically over-estimates H. Verified on 20 pure-Gaussian random walks of n=2500: mean H = 0.584, none below 0.545. The notebook's classifier flags H>0.55 as "TRENDING (momentum favored)" → every asset in the cross-asset table is "trending" but the input is essentially noise. The clip to [0,1] (line ≈530) silently hides any negative or >1 slope estimate, removing diagnostic information.
- **Proposed fix:** Use the Anis-Lloyd correction (subtract the expected R/S under null) or switch to detrended fluctuation analysis (DFA) via `nolds.dfa` / a small custom DFA helper. At minimum, add a "bias-corrected" H column alongside the raw one, and remove the [0,1] clip. Sanity-test by running on `rng.standard_normal(N)` in a markdown cell so a reader sees the bias.
- **Risk if we skip it:** The Hurst column tells the reader something false. The remediation cost is small relative to the credibility hit.

### [F06] Cumulative-return formula mixes log and simple returns
- **Severity:** S0
- **Notebook:** correlation
- **Location:** `plot_executive_dashboard` (line ≈ 1481-1494), `plot_drawdown_analysis` (line ≈ 2303-2330)
- **Effort:** S
- **What's wrong:** `port_r = (full_rets[avail] * wts).sum(axis=1)` where `full_rets` are LOG returns. Then `cum_port = (1 + port_r).cumprod()`. For LOG returns the correct level path is `np.exp(port_r.cumsum())`. Numerically: at a daily log return of +1%, `(1+log_r)=1.01` but `exp(log_r)=1.01005` — the relative under-statement compounds to ~1.3% per year, and is larger on volatile days. Combined with weighting-of-log-returns (which itself is an approximation to a true portfolio simple return), the drawdown panel mixes two distinct errors.
- **Proposed fix:** Either compute simple returns once at the top (`simple = prices.pct_change()`) and use `(1 + (simple * w).sum(1)).cumprod()` consistently, or stay in log space throughout (`level = port_log.cumsum()`; `dd = level - level.cummax()` in log units, then `expm1(dd)` for percent). Pick one convention and enforce it everywhere `cum*` appears.
- **Risk if we skip it:** Reported max drawdowns are off by single-percent-points; the underwater chart understates the drawdown on the deepest events.

### [F07] Fisher-z test for correlation stability is statistically meaningless
- **Severity:** S0
- **Notebook:** correlation
- **Location:** `run_statistical_tests`, "Correlation Stability (First Half vs Second Half)" block (≈ lines 724-756)
- **Effort:** M
- **What's wrong:** The code computes Avg ρ₁, Avg ρ₂ from upper-triangle correlations, then applies `np.arctanh(mean)` and a z-test with SE based on full-sample sizes. The Fisher-z transform is the variance-stabilizing transform of an individual sample correlation; transforming the *average* of pairwise correlations does not produce a test statistic with a known sampling distribution. The reported z-stat and p-value are not interpretable as a test of "did average correlation change."
- **Proposed fix:** Use one of: (a) a bootstrap test where each iteration resamples blocks of dates (preserving temporal dependency), recomputes the full correlation matrix on each half, and tabulates the empirical distribution of Δavg-ρ; (b) compute Fisher-z PER PAIR, paired-sample t-test on Δz; (c) use a structural-break test on a rolling-mean-correlation series. Pick (a) — it's intuitive for the audience and easy to write.
- **Risk if we skip it:** A test labeled "statistically significant" with an actual p-value that has no statistical meaning. Removes from the credibility column.

### [F08] Bootstrap CI for tail-vs-normal delta ignores pair dependency
- **Severity:** S1
- **Notebook:** correlation
- **Location:** `run_statistical_tests`, test 3 (≈ lines 682-722)
- **Effort:** M
- **What's wrong:** `rng.choice(tail_vals, size=k, replace=True)` resamples upper-triangle correlation values independently. Adjacent pairs share an asset, so observations are not i.i.d. — the resulting CI is wrong-width (typically too narrow). The 95% CI on the tail-normal delta is reported as [−0.111, +0.025]; this width is itself unreliable.
- **Proposed fix:** Bootstrap **dates** (block bootstrap with block length ≈ √n), recompute the full Pearson and Tail matrix on each resample, tabulate Δavg-ρ. This respects the dependency structure between pairs. Or report a simpler Wilcoxon signed-rank of `tail_vals − pearson_vals` on the matched pairs, which is what you actually want here.
- **Risk if we skip it:** "Not significant" is the right answer in our run (CI brackets zero), so the operational consequence is small. But the methodology should be defensible if anyone audits it.

### [F09] Hierarchical clustering uses non-metric distance
- **Severity:** S1
- **Notebook:** correlation
- **Location:** `run_clustering_analysis` (≈ lines 1047-1067)
- **Effort:** S
- **What's wrong:** `dist = 1 - corr` is a valid dissimilarity but not a proper distance metric for negative correlations: `d(A, B) = 2` when ρ=−1, which together with `d(A, A) = 0` violates the triangle inequality with Ward linkage. The standard fix in finance literature is Mantegna's `d = sqrt(0.5 * (1 - corr))`, which lies in [0, 1] and is a proper metric.
- **Proposed fix:** `dist = np.sqrt(np.clip(0.5 * (1 - corr.values), 0, 1))`. Document the choice in a markdown cell.
- **Risk if we skip it:** Cluster boundaries are still readable, but the dendrogram height axis is mis-scaled. Cosmetic for portfolios with mostly positive correlations; matters more if you add hedge ETFs.

### [F10] Volatility notebook never saves figures to disk
- **Severity:** S0
- **Notebook:** volatility
- **Location:** every `generate_*_dashboard` call to `plt.show()` (≈ lines 1042-1090)
- **Effort:** S
- **What's wrong:** The correlation notebook saves PNGs (`fig.savefig(filename)`), the volatility one doesn't. For a notebook intended to be published on GitHub, the figures need to be artifacted.
- **Proposed fix:** Add an `_save_and_show(fig, filename)` helper (mirror the correlation notebook's), drive filenames from `{ticker}_{dashboard_id}.png`, ensure output dir exists (`images/volatility/`). Make `SAVE_FIGURES = True` a constant.
- **Risk if we skip it:** Volatility README cannot embed sample images without manually screenshotting each.

### [F11] "Systematic risk" label is misleading
- **Severity:** S1
- **Notebook:** correlation
- **Location:** `calculate_portfolio_metrics` (≈ lines 832-840)
- **Effort:** S
- **What's wrong:** The code labels `Σ_{i≠j} w_i w_j σ_i σ_j ρ_ij` as `systematic_var` and the diagonal sum as `idio_var`. In CAPM terminology, systematic risk = β² σ²_market and idiosyncratic = residual variance after regression on a market factor. The notebook's quantity is the *co-movement share* of portfolio variance, which equals systematic only if the implicit single-factor model holds. Our run reports "Systematic Risk 86%" — that's the off-diagonal share, not market-factor exposure (which would compute against SPY: `(w'β)² σ²_SPY`).
- **Proposed fix:** Rename to "Cross-Asset Co-Movement Share" / "Diagonal Variance Share" in code AND in the dashboard text. If you want a real CAPM split, compute β-vector vs SPY, then `sys = (w·β)² · var(SPY)` annualized, `idio = total − sys`.
- **Risk if we skip it:** Sophisticated readers will quietly discount the analysis.

### [F12] Pairwise correlation significance reported without multiple-testing correction
- **Severity:** S1
- **Notebook:** correlation
- **Location:** `run_statistical_tests`, test 1 (≈ lines 629-655)
- **Effort:** S
- **What's wrong:** With 18 assets, n_pairs = 153. At α=0.05, expectation under H₀ is ~8 false positives. The run reports 147/153 significant; in this portfolio that's overwhelmingly real, but the test as written would also report ~5% significant under pure noise. The implication text ("Most correlations are real and not driven by noise…") trades on a comparison the test doesn't actually make.
- **Proposed fix:** Add Benjamini-Hochberg FDR adjustment (`from statsmodels.stats.multitest import multipletests`) and report `count significant at FDR α=0.05`. Or simply rephrase the implication to "X% pairs have |ρ| > critical at α=0.05 (no multiple-testing correction applied)."
- **Risk if we skip it:** Test is true-positive in our run, but the boilerplate text on a different portfolio could be misleading.

### [F13] Tail thresholds may produce unstable estimates
- **Severity:** S1
- **Notebook:** correlation
- **Location:** `_compute_tail_correlation`; `TAIL_PERCENTILE=0.05`, `MIN_TAIL_OBS=25` (≈ lines 174-176)
- **Effort:** S
- **What's wrong:** 5% tail of ~3300 trading days = 165 candidate days but in our run only 69 came through (presumably after alignment); the cap on tail correlation precision at n=69 is non-trivial. Reporting one number obscures sensitivity.
- **Proposed fix:** Compute tail correlation at three percentiles (5%, 10%, 15%) and show all three in the master table — gives the reader a stability signal. Or use a continuous "tail weight" (kernel-weighted) instead of a hard cut. Easy upgrade.
- **Risk if we skip it:** Tail conclusions hinge on a magic number with no displayed sensitivity.

### [F14] "Idiosyncratic Risk %" interpretation is wrong
- **Severity:** S1
- **Notebook:** correlation
- **Location:** `calculate_portfolio_metrics` (same block as F11)
- **Effort:** S
- **What's wrong:** `idio_var = Σ w_i² σ_i²` is only equal to idiosyncratic variance if all pairwise correlations are zero — which the notebook itself reports they are not (avg ρ = 0.40 in our run). Plus the per-asset σ is the *total* σ, not residual σ from a market regression. So "Idiosyncratic Risk 14%" is just `1 − cross_term_share`.
- **Proposed fix:** Same as F11 — relabel both halves. If a CAPM-style decomposition is desired, compute via regression vs SPY.
- **Risk if we skip it:** Compounds F11. Both halves of the donut are misnamed.

### [F15] Min-periods on rolling windows biases the early sample
- **Severity:** S2
- **Notebook:** volatility
- **Location:** every estimator (e.g. `realized_volatility`, `parkinson_volatility`, etc.) using `min_periods=max(window // 2, 5)`
- **Effort:** S
- **What's wrong:** For a 30-day window, computing a "30-day" vol from 5 observations and labeling it 30-day is misleading; the first ~15 days of every series have a different sampling distribution from later values. Plots show a smooth line all the way to the start of history; readers won't notice.
- **Proposed fix:** Set `min_periods=window` for vol estimators (so series starts honestly at index `window`) OR keep the relaxed `min_periods` but visually demarcate the warm-up region (shaded background, dashed line). The first option is the cleaner choice.
- **Risk if we skip it:** Reader implicitly compares warm-up vol to later vol as if they were the same quantity.

### [F16] Hurst clip to [0, 1] hides diagnostic information
- **Severity:** S1
- **Notebook:** volatility
- **Location:** `calculate_hurst_exponent` (last line, ≈ 530)
- **Effort:** S
- **What's wrong:** Independent of F05: silently clamping to [0,1] removes the signal that the regression went sideways (e.g., slope = −0.1 indicating R/S didn't grow, or 1.2 indicating super-trending — both flags for trouble or extreme persistence).
- **Proposed fix:** Drop the clip; let raw slope through. Add a warning if abs(H − 0.5) > 0.45 ("Estimate near boundary — check data length").
- **Risk if we skip it:** Real edge cases look like ordinary values.

### [F17] Vol notebook uses Close adjusted but Open/High/Low unadjusted
- **Severity:** S0 (data quality)
- **Notebook:** volatility
- **Location:** `fetch_ohlc_data`, `auto_adjust=False` plus the `'Adj_Close'` separate column (≈ lines 257, 274-285)
- **Effort:** S
- **What's wrong:** With `auto_adjust=False`, `Open`, `High`, `Low`, `Close` are RAW prices; `Adj_Close` is dividend/split-adjusted. The notebook then computes `Log_Return = log(Close / Close.shift(1))` from RAW close — fine, but inconsistent. The OHLC estimators (Parkinson, GK, RS, Yang-Zhang) use raw OHLC, which **does** correctly model intraday range. But on a split or large-dividend day, RAW Close jumps and `Log_Return` from raw close produces a spurious large move. This is the most plausible source of the BTAL kurt=344, MNA kurt=70 outliers.
- **Proposed fix:** Use `auto_adjust=True` (which adjusts O/H/L/C consistently for splits), or compute returns from `Adj Close` instead of `Close`. Crucially, OHLC range estimators want **split-adjusted** OHLC (range scales with price level, splits violate that). The correlation notebook already uses `auto_adjust=True` — make volatility match. Re-run and confirm BTAL/MNA kurtosis drop into normal range.
- **Risk if we skip it:** Data-quality contamination in every distribution test and every cross-asset summary row in the vol notebook.

### [F18] No pinned dependencies
- **Severity:** S2
- **Notebook:** both
- **Location:** repo root
- **Effort:** S
- **What's wrong:** yfinance changed its column return format three times in 2023-2025 (`Adj Close` removed/restored, MultiIndex level ordering flip). The DataEngine `_extract_prices` is itself a workaround. A `requirements.txt` documenting the versions you developed against is essential for reproducibility.
- **Proposed fix:** Lean `requirements.txt`: `yfinance>=0.2.40`, plus the science stack at major-version floors. Don't over-pin (the audience needs to use Colab's pre-installed wheels). Add a section in README naming the versions that were known to work.
- **Risk if we skip it:** A reader runs the notebook in 6 months, yfinance v0.2.55 changes column names again, the DataEngine's `_extract_prices` debug prints fire, results may or may not arrive.

### [F19] No on-disk price cache
- **Severity:** S2
- **Notebook:** both
- **Location:** the data-fetch path
- **Effort:** S
- **What's wrong:** Every notebook run re-downloads ~3300 trading days × 18 (or 29) tickers. Slow (~30 s), wastes Yahoo's bandwidth, and the developer experience is awful when iterating on plot code.
- **Proposed fix:** Add `data/cache/{tickers_hash}_{start}_{end}.parquet`. Check cache first, fetch only on miss. ~30 lines of code, big speedup. Keep the cache dir in `.gitignore`. Colab compatibility: the cache simply rebuilds in a fresh Colab session — no harm.
- **Risk if we skip it:** Iteration is painful; iterators will be lazy about visual polish.

### [F20] Forward-fill price gaps masks delisting / data issues
- **Severity:** S2
- **Notebook:** correlation
- **Location:** `DataEngine.fetch` (≈ line 385)
- **Effort:** S
- **What's wrong:** `prices = prices.ffill()` with no `limit`. If a ticker delists mid-sample, its last price is carried forward indefinitely → returns become zero on those days → average correlations and tail metrics get diluted by structural zeros.
- **Proposed fix:** `prices.ffill(limit=5)` (a week of tolerable gaps) and report the count of ffills per ticker. Drop tickers with > X% ffill.
- **Risk if we skip it:** Mostly fine for the current ETF roster (no delistings) but a latent bug.

### [F21] Volatility notebook drops failed tickers silently from N
- **Severity:** S2
- **Notebook:** volatility
- **Location:** `run_analysis` (≈ lines 1303-1352) and `generate_cross_asset_dashboard`
- **Effort:** S
- **What's wrong:** 27/29 in our run; the failed list is printed at the end but the cross-asset chart's x-axis silently has 27 ticks, not 29. Reader who skimmed the header thinking "29 assets" gets a 27-asset chart.
- **Proposed fix:** Include failed tickers in the cross-asset table with all-NaN cells, marked with a strikethrough or N/A badge. Or surface a one-line banner above the cross-asset chart: "Note: 2 of 29 assets failed (ILS, CERY.L)."
- **Risk if we skip it:** Minor but ugly for publication.

### [F22] DataEngine class is over-engineered for its job
- **Severity:** S3
- **Notebook:** correlation
- **Location:** `class DataEngine` (≈ lines 223-453)
- **Effort:** M
- **What's wrong:** ~230 lines of debug-printing column-shape-detection logic in a class whose state (`self.prices`, `self.returns`, `tickers_loaded`, `fetch_errors`) is read exactly once after `fetch()` returns. Half of `_extract_prices` is dead-code paths for yfinance MultiIndex permutations that no longer happen with current yfinance.
- **Proposed fix:** Collapse to `def fetch_prices_and_returns(tickers, start, end) -> Tuple[pd.DataFrame, pd.DataFrame]`. Keep the one MultiIndex case currently exercised (`raw['Close']`). Drop the debug prints. ~30 lines total. Don't try to handle every yfinance version; pin yfinance instead (F18).
- **Risk if we skip it:** Cognitive load and maintenance burden out of proportion to function.

### [F23] Helper duplication across notebooks
- **Severity:** S3
- **Notebook:** both
- **Location:** `apply_theme()`, `_header()`, `_subheader()`, color constants
- **Effort:** S
- **What's wrong:** Theme colors are defined twice with slight differences (`DARK_BG='#0e1117'` in correlation, `THEME['bg']='#0e1117'` in volatility). Header helpers exist in both. The Colab-paste constraint says local imports are off-limits, so duplication is OK — but the **specific values must match exactly** so the published notebooks share an identical visual language.
- **Proposed fix:** Pick the dict-of-constants style (volatility's `THEME`) and copy it identically into both notebooks. Same for helper functions. A simple `tests/test_theme_consistency.py` can `import ast; assert THEME == THEME` to keep them aligned.
- **Risk if we skip it:** Drift between notebooks; readers notice the colors changed.

### [F24] Excessive chart count with significant overlap
- **Severity:** S3
- **Notebook:** correlation
- **Location:** the 21 chart functions
- **Effort:** L (because of plot redesign work)
- **What's wrong:** Charts overlap heavily by what they show:
  - 09 (Rolling portfolio ρ to SPY) + 10 (Rolling per-asset to SPY) + 12 (Rolling avg pairwise) = three takes on rolling correlation
  - 03 (Tail vs Normal to SPY) + 05 (Stress coincidence) + 07 (Category to SPY) = three "behavior under stress" cuts
  - 02 (Master table, 6 columns of methods) ≈ heatmap of 01, 03, 08 contents
  - 04 (Beta vs ρ quadrant), 06 (Stability ranking) = two "diversifier quality" views
- **Proposed fix:** Consolidate to ~9 plots:
  1. Executive dashboard (keep, fix drawdown panel)
  2. Correlation methods comparison (was 02, cut from 6 to 3 columns)
  3. Tail-stress dashboard (consolidates 03+05; quadrant+coincidence one panel)
  4. Rolling correlation panel (consolidates 09+12; faceted by category)
  5. Beta-vs-correlation quadrant (was 04, keep)
  6. Correlation regime heatmap (was 11)
  7. Full clustered Pearson heatmap (was 13)
  8. PCA factor structure (was 19)
  9. Drawdown & cumulative returns (was 17, fixed math from F06)
- **Risk if we skip it:** Reader fatigue; the strong charts get lost in the redundant ones.

### [F25] Loop-based variance decomposition could be vectorized
- **Severity:** S3
- **Notebook:** correlation
- **Location:** `calculate_portfolio_metrics` (≈ lines 834-838) and `plot_risk_contribution` (≈ lines 2366-2371)
- **Effort:** S
- **What's wrong:** `for i in range(n): for j in range(n):` constructs a covariance matrix that already exists. Plus the manual quadratic form is `w @ cov @ w` in one line.
- **Proposed fix:** `vols_outer = np.outer(vols, vols); cov_mat = vols_outer * corr_mat.values; total_var = w @ cov_mat @ w; idio_var = np.sum(w**2 * vols**2); systematic_var = total_var - idio_var`. Clarity and 100x speed.
- **Risk if we skip it:** Performance only matters for large portfolios but readability improves immediately.

### [F26] Implementation imports inconsistent across notebooks
- **Severity:** S3
- **Notebook:** both
- **Location:** top-of-notebook imports
- **Effort:** S
- **What's wrong:** Vol uses `from scipy.stats import jarque_bera, kurtosis, skew` and also `from scipy import stats`. Correlation uses `from scipy import stats as sp_stats`. Random small differences make code harder to copy between cells.
- **Proposed fix:** Pick one alias and use it everywhere (`from scipy import stats as sps` is fine). Standardize across both notebooks.
- **Risk if we skip it:** Minor cosmetic.

### [F27] PNG output naming pollutes the working directory
- **Severity:** S3
- **Notebook:** correlation
- **Location:** `_save_and_show` (≈ lines 1244-1252) — writes `01_executive_dashboard.png` to CWD
- **Effort:** S
- **What's wrong:** Running the notebook in the repo root drops 22 PNGs next to the .ipynb. Bad git hygiene.
- **Proposed fix:** Constant `IMAGE_DIR = 'images/correlation'`, `Path(IMAGE_DIR).mkdir(parents=True, exist_ok=True)`, prefix all savefigs. Same change in vol notebook (when adding savefigs per F10).
- **Risk if we skip it:** Cluttered repo, accidental commits of PNGs.

### [F28] Debug-prints from DataEngine survive in production output
- **Severity:** S3
- **Notebook:** correlation
- **Location:** `_extract_prices`, many `print(f"  [debug] ...")` (≈ lines 244-309)
- **Effort:** S
- **What's wrong:** `[debug] MultiIndex with 2 levels: Level 0: [...]` appears in every run. Useful while developing, distracting in a published artifact.
- **Proposed fix:** Gate behind `DEBUG = False` constant or remove. Same for the various `[fallback]` prints.
- **Risk if we skip it:** Cosmetic; less polished.

### [F29] Bartlett's sphericity test on a near-singular matrix is unstable
- **Severity:** S2
- **Notebook:** correlation
- **Location:** `run_statistical_tests`, test 2 (≈ lines 657-680)
- **Effort:** S
- **What's wrong:** With determinant ≈ 0 (condition number 1975 in our run), `np.log(det_val)` is taken with `max(det, 1e-300)` floor. The χ² result is unreliable — Bartlett's test assumes the correlation matrix is not singular. The test "passes" trivially in this regime.
- **Proposed fix:** If `det < 1e-6`, skip the test and emit "Correlation matrix near-singular — Bartlett's test not applicable." Same diagnosis is already visible in the "high condition number" warning.
- **Risk if we skip it:** Reader sees a test "passing" that was structurally guaranteed to pass.

### [F30] Suspicious all-1.00 beta column in implied-correlation table
- **Severity:** S1 (data presentation)
- **Notebook:** correlation
- **Location:** `print_implied_correlation` table output (≈ lines 2705-2709)
- **Effort:** S
- **What's wrong:** Output shows every Beta as 1.00 for every asset — because ticker==proxy in 18/18 entries. This is suspicious to any reader and hints at the deeper F01 bug.
- **Proposed fix:** Either drop the Beta column entirely (it's not used) or, if you re-implement implied correlation correctly with a real index proxy (e.g. SPY for equities, AGG for bonds), populate beta meaningfully.
- **Risk if we skip it:** Visible to the reader; advertises F01.

### [F31] No automated tests / regression guard
- **Severity:** S2
- **Notebook:** repo
- **Effort:** M
- **What's wrong:** All correctness assurance is one-off (this review). Re-checking after refactor requires another full review.
- **Proposed fix:** Add `tests/test_estimators.py` codifying the spot-checks done here:
  - Yang-Zhang matches the textbook formula on a synthetic OHLC dataset
  - GARCH(1,1) recursion satisfies σ²_LR = ω / (1 − α − β) (mean reversion check)
  - Hurst on `rng.standard_normal(N)` is within [0.4, 0.7]
  - Variance-ratio SE matches `arch.unitroot.VarianceRatio` to within 1%
  Run via plain `pytest`. No CI required at MVP — local invocation is fine.
- **Risk if we skip it:** Next refactor reintroduces a quietly-wrong formula.

### [F32] No README, no license, no run instructions
- **Severity:** S6
- **Notebook:** repo root
- **Effort:** M
- **What's wrong:** A reader landing on the GitHub repo today sees three files (two notebooks and the review prompt) with no introduction.
- **Proposed fix:** Single `README.md` with:
  - Title + one-paragraph pitch
  - Two sample images (one from each notebook — pick the executive dashboard and the YZ term structure)
  - "How it works" section: 4-6 bullets of methodology
  - "How to run" — locally (`pip install -r requirements.txt && jupyter`), Colab badges
  - "What it computes" interpretation guide (table: metric → what it means → what's a good number)
  - "Limitations and known issues" (F01, F04 sit here — be honest)
  - License: **MIT** (permissive, friendly to retail audience and future contributors)
- **Risk if we skip it:** Repo looks unfinished. README is the single highest-leverage piece of polish.

### [F33] Proposed cell split — Correlation notebook
- **Severity:** S4
- **Notebook:** correlation
- **Effort:** L (one-time)
- **Proposed split** (titles + intent only, prose written separately):
  1. **markdown**: Title, abstract, what this notebook computes, intended audience
  2. **code**: `!pip install -q yfinance pandas numpy scipy scikit-learn statsmodels matplotlib seaborn`
  3. **code**: Imports + theme constants + `apply_theme()` + display helpers
  4. **markdown**: "Configuration — choose your portfolio"
  5. **code**: `PORTFOLIO` list, `START_DATE`, `END_DATE`, rolling windows, tail params
  6. **markdown**: "Step 1 — Fetch data"
  7. **code**: `fetch_prices_and_returns(...)`, run, sanity-check shapes
  8. **markdown**: "Step 2 — Correlation suite" (define Pearson, Spearman, EWMA, Tail in 1-2 lines each)
  9. **code**: `calculate_correlation_suite(...)`, print summary table
  10. **markdown**: "Step 3 — Portfolio risk decomposition"
  11. **code**: `calculate_portfolio_metrics(...)`, print metrics (with renamed labels per F11/F14)
  12. **markdown**: "Step 4 — Diversification structure: PCA, ENB, clustering"
  13. **code**: `run_pca_analysis`, `calculate_effective_n_bets`, `run_clustering_analysis`, scorecard
  14. **markdown**: "Step 5 — Statistical significance" (Pearson significance, Ljung-Box on squared returns, Jarque-Bera)
  15. **code**: `run_statistical_tests` (cleaned per F07, F08, F12, F29)
  16. **markdown**: "Step 6 — Visualization" (consolidated chart list per F24)
  17. **code**: 9 chart calls
  18. **markdown**: "Limitations and caveats" (data quality, multiple-testing, …)

### [F34] Proposed cell split — Volatility notebook
- **Severity:** S4
- **Notebook:** volatility
- **Effort:** M (one-time)
- **Proposed split**:
  1. **markdown**: Title, abstract, audience
  2. **code**: `!pip install -q yfinance pandas numpy scipy statsmodels arch matplotlib seaborn`
  3. **code**: Imports + theme + helpers
  4. **markdown**: "Configuration — asset universe, windows, GARCH approach"
  5. **code**: `TICKERS`, dates, windows, EWMA λ. Make GARCH `'mle' | 'manual'` a switch.
  6. **markdown**: "Volatility estimators — formulae"
  7. **code**: realized, Parkinson, GK, RS, Yang-Zhang, EWMA, GARCH definitions (with LaTeX in markdown above each)
  8. **markdown**: "Statistical tests and regime classification"
  9. **code**: downside dev, atr, hurst (bias-corrected), VR (fixed SE), distribution tests
  10. **markdown**: "Single-asset deep dive — choose one ticker to explore in detail"
  11. **code**: `SHOWCASE = 'GLD'`; full dashboard for that one ticker
  12. **markdown**: "Cross-asset comparison"
  13. **code**: loop over `TICKERS`, run analysis, build comparison df
  14. **code**: cross-asset dashboard (4-panel)
  15. **markdown**: "Reading the results — interpretation guide"
  16. **code**: pandas Styler summary table (replaces the current `print()` table)
  17. **markdown**: "Limitations" — hardcoded GARCH (if 'manual' selected), Hurst bias, yfinance data quality

### [F35] Suggested repo layout
- **Severity:** S6
- **Effort:** S
- **Layout:**
```
Analysis_securities/
├── README.md
├── LICENSE                       # MIT
├── requirements.txt              # lean: yfinance, pandas, numpy, scipy,
│                                 # scikit-learn, statsmodels, arch,
│                                 # matplotlib, seaborn
├── .gitignore                    # data/cache/, __pycache__/, .venv/,
│                                 # *.png at repo root
├── notebooks/
│   ├── Correlation_Analysis.ipynb
│   └── Volatility_Analysis.ipynb
├── images/
│   ├── correlation/              # 9 PNGs after consolidation
│   └── volatility/               # per-ticker dashboards
├── data/
│   └── cache/                    # parquet cache (gitignored)
└── tests/
    └── test_estimators.py        # codified spot-checks per F31
```
Each notebook still pastes to Colab as a single cell-or-multi-cell artifact with no local imports. The repo just gives it a polished home.

### [F36] Add `nbstripout` to keep output cells out of diffs
- **Severity:** S6
- **Effort:** S
- **What's wrong:** Committing notebooks with cell outputs (saved figures inline, hashable kernel state) makes diffs noisy and pulls binary data into git.
- **Proposed fix:** `pip install nbstripout && nbstripout --install`. Decide explicitly whether you want output cells preserved (the GitHub render is the user's first impression — output cells make the README mostly redundant) or stripped (then add a markdown cell pointing to images/). Strong recommendation: **keep** output cells but add a `.gitattributes` rule + nbstripout for incoming changes — single click for the next contributor.

### [F37] Dark theme — keep or change for a public GitHub piece
- **Severity:** S5
- **Effort:** S (no change recommended)
- **Argument for keeping**: distinctive, matches "institutional" branding, dark theme has become the default expectation for terminal-style quant work, the bright accent colors carry well on the panel background, file size of PNGs is lower with a dark backdrop.
- **Argument against**: GitHub's notebook renderer displays dark figures against the page's light background by default, creating a stark contrast strip. Accessibility audits sometimes flag low-contrast text (`#8a8d95` muted text on `#1a1d23` panel is borderline — WCAG AA needs ≥ 4.5:1 for normal text; this combination is ~5.0:1, just passing).
- **Recommendation**: KEEP, but bump the smallest font sizes (`fontsize=6.5` instances exist for label-dense charts) to 8+ minimum, and verify the muted-text color contrast on the panel background hits AAA on a colorimeter. The diverging colormap `[#1565c0, #42a5f5, #e3f2fd, #ffffff, #ffebee, #ef5350, #b71c1c]` is fine for red-green colorblindness (it's blue-white-red, not red-green) but pass it through `viscm` or Coblis to confirm.

### [F38] Use pandas Styler for numeric tables instead of plain `print`
- **Severity:** S4
- **Notebook:** both
- **Effort:** S per table
- **What's wrong:** Most console output is bare `print(f"...")` with manual column padding. In a published Jupyter notebook, a styled DataFrame is dramatically more readable than ASCII.
- **Proposed fix:** Wrap each "table" into a function returning a `pd.DataFrame` and apply `.style.format(...).background_gradient(cmap=CORR_CMAP, vmin=-1, vmax=1)`. Keep the ASCII tables in the "raw" prints for sanity but the styled version is what the reader engages with.

### [F39] Add Colab "Open in Colab" badge in README and notebook
- **Severity:** S6
- **Effort:** S
- **What's wrong:** No on-ramp for a casual reader.
- **Proposed fix:** A standard Colab badge at the top of each notebook and in README:
  `[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/<user>/<repo>/blob/main/notebooks/Correlation_Analysis.ipynb)`. Free to add.

---

## Recommended sequencing

If you only do five things, do these five — in order:

1. **F17** — Fix `auto_adjust=False` mismatch in volatility notebook. One-line change. Removes the BTAL/MNA kurt=344 / 70 outliers and a dozen downstream test-result distortions. Easiest win on the board.
2. **F01 + F02** — Either remove the implied-correlation feature or relabel it honestly. Cleanest fix is removal; this section is in the "Forward Looking" headline of the executive summary, so anything that's not actually forward-looking is a substantial credibility risk.
3. **F03 + F04 + F05** — The three statistical-method fixes in the volatility notebook. F03 is a one-line SE swap. F04 is wiring `arch.arch_model` into the GARCH path. F05 needs an Anis-Lloyd correction or a switch to DFA. These three together make the volatility notebook's claims defensible.
4. **F06 + F07** — Cumulative-return formula fix (line-level edit) and replace the Fisher-z stability test with a block bootstrap (or just delete the test and keep the visual stability ranking, which is more honest).
5. **F32 + F33 + F34 + F35** — README, repo layout, and the two cell-split refactors. This is the work that turns "scripts in a folder" into "published GitHub portfolio piece." Do this LAST so you only do the formatting work once on settled code.

After that, F24 (chart consolidation) is the single highest-leverage visual change. The remaining S2/S3 findings are mostly cleanup.

---

## Appendix A — Notes on what was NOT a finding

A few things looked like potential bugs on read-through but verified clean:

- Yang-Zhang weighting constant `k = 0.34 / (1.34 + (n+1)/(n-1))` is correct per Yang & Zhang (2000).
- EWMA `span = (2 / (1-λ)) - 1` correctly converts RiskMetrics λ to a pandas EWM span when `adjust=False`. The α-equivalent is `1-λ = 0.06`, span = `(2-α)/α = 32.33`, matches.
- Theoretical determinant `(1-ρ̄)^(n-1) (1 + (n-1)ρ̄)` is the correct closed form for a constant-correlation matrix.
- Effective number of bets (Meucci): `exp(entropy of normalized eigenvalues)` — correct.
- Bartlett's sphericity χ² formula `-((n-1) - (2k+5)/6) log(det)` is correct (modulo F29 caveat about near-singular matrices).
- Garman-Klass coefficient `0.5 (ln(H/L))² − (2 ln 2 − 1)(ln(C/O))²` matches the published estimator.
- Rogers-Satchell formula `ln(H/O) ln(H/C) + ln(L/O) ln(L/C)` matches Rogers & Satchell (1991).
- ATR via `tr.ewm(span=period, adjust=False).mean()` is the standard Wilder smoothing.

These pass.

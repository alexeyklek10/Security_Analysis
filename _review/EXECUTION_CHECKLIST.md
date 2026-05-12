# Execution Checklist — Securities Analysis Notebooks

Tick the boxes for the findings you want actioned, then re-invoke Claude
Code with this file. Each item links to the corresponding `F##` entry in
`REVIEW_FINDINGS.md` for the full reasoning, severity, effort estimate,
and proposed fix. Items are grouped by severity, then ordered to match
the **Recommended sequencing** in the findings doc — top-down execution
will leave the codebase consistent at every intermediate state.

Effort key: **S** ≤ 30min, **M** 1-3 hr, **L** > 3 hr.

---

## S0 — Correctness bugs (do these first)

- [ ] **F17**  Fix `auto_adjust` mismatch in volatility notebook (RAW OHLC + RAW Close → use adjusted everywhere). Removes BTAL/MNA kurt outliers. **(S)**
- [ ] **F01**  `calculate_implied_correlation` is an IV-weighted historical average, not implied. Decide: **remove** or **rename + caveat**. **(M)**
- [ ] **F02**  yfinance options-chain IVs unusable (SPY ATM IV reported as 0.0001-0.0078). Drop the feature or migrate to a working data source. **(S–M)**
- [ ] **F03**  Variance-ratio asymptotic SE uses non-overlapping formula on overlapping returns. Swap in `sqrt(2(2k-1)(k-1)/(3kT))` or call `arch.unitroot.VarianceRatio`. **(S)**
- [ ] **F04**  GARCH(1,1) α=0.08, β=0.90 hardcoded for all assets. Wire `arch.arch_model` MLE fit. **(M)**
- [ ] **F05**  Hurst R/S has +0.08 finite-sample bias confirmed on Gaussian noise. Add Anis-Lloyd correction or switch to DFA. **(M)**
- [ ] **F06**  `(1 + log_return).cumprod()` is wrong — fix `plot_executive_dashboard` & `plot_drawdown_analysis` to use `np.exp(log_r.cumsum())` or simple returns consistently. **(S)**
- [ ] **F07**  Fisher-z "correlation stability" test is statistically meaningless. Replace with block-bootstrap or paired Wilcoxon on per-pair Δz. **(M)**
- [ ] **F10**  Volatility notebook never saves figures. Add `_save_and_show()` mirror; write to `images/volatility/`. **(S)**

## S1 — Statistical methodology

- [ ] **F08**  Bootstrap CI on tail-vs-normal delta uses i.i.d. resample on dependent pairs. Switch to date-block bootstrap. **(M)**
- [ ] **F09**  Hierarchical clustering distance `1 - corr` is non-metric. Switch to Mantegna `sqrt(0.5 * (1 - corr))`. **(S)**
- [ ] **F11**  "Systematic risk %" mislabeled (it's the off-diagonal variance share). Rename or do a real CAPM split vs SPY. **(S)**
- [ ] **F12**  Add Benjamini-Hochberg FDR correction to pairwise-correlation significance count. **(S)**
- [ ] **F13**  Report tail correlation at 5/10/15% percentiles, not a single hard cut. **(S)**
- [ ] **F14**  "Idiosyncratic Risk %" is the complement of F11 and equally mislabeled. Fix together. **(S)**
- [ ] **F16**  Hurst clip to [0,1] hides bad estimates. Remove the clip; flag extreme values. **(S)**
- [ ] **F29**  Skip Bartlett's sphericity test when determinant < 1e-6 (matrix singular). **(S)**
- [ ] **F30**  Drop the constant-1.00 Beta column from the implied-correlation table (it carries no information). **(S)**

## S2 — Robustness & reproducibility

- [ ] **F15**  Set `min_periods=window` on vol estimators OR mark warm-up region visually. **(S)**
- [ ] **F18**  Add lean `requirements.txt` with yfinance pinned. **(S)**
- [ ] **F19**  Add parquet/pickle on-disk price cache keyed on `(tickers, start, end)`. **(S)**
- [ ] **F20**  `prices.ffill()` → `prices.ffill(limit=5)`, report ffill counts per ticker. **(S)**
- [ ] **F21**  Show failed tickers in cross-asset table with NaN/strikethrough rather than silent drop. **(S)**
- [ ] **F31**  Add `tests/test_estimators.py` codifying spot-checks (Yang-Zhang, GARCH mean reversion, Hurst on noise, VR SE). **(M)**

## S3 — Redundancy & structure

- [ ] **F22**  Collapse `DataEngine` class to a single `fetch_prices_and_returns()` function (~30 lines vs ~230). **(M)**
- [ ] **F23**  Align theme dicts and helper signatures between the two notebooks (duplication is fine; drift is not). **(S)**
- [ ] **F24**  Consolidate 21 correlation charts to ~9 (rolling correlations → 1, tail stress → 1, master table → cut to 3 columns). **(L)**
- [ ] **F25**  Vectorize `calculate_portfolio_metrics` quadratic form: `total_var = w @ (vols_outer * corr) @ w`. **(S)**
- [ ] **F26**  Standardize scipy.stats import alias across both notebooks. **(S)**
- [ ] **F27**  Write PNGs to `images/correlation/` not CWD. **(S)**
- [ ] **F28**  Gate `[debug]` prints behind a `DEBUG = False` constant or remove. **(S)**

## S4 — Presentation & narrative

- [ ] **F33**  Restructure correlation notebook to 17 cells (markdown + code alternating, per the proposed split in REVIEW_FINDINGS.md). **(L)**
- [ ] **F34**  Restructure volatility notebook to 17 cells. **(M)**
- [ ] **F38**  Replace ASCII `print(f"...")` tables with pandas Styler equivalents. **(S per table)**

## S5 — Visual redesign

- [ ] **F37**  Keep dark theme but raise minimum font sizes to 8+, verify diverging-colormap accessibility (Coblis / viscm pass). **(S)**

## S6 — README + repo polish

- [ ] **F32**  Write `README.md` (pitch + 2 sample images + methodology + run instructions + interpretation guide + limitations + license). **(M)**
- [ ] **F35**  Adopt proposed repo layout (`notebooks/`, `images/`, `data/cache/`, `tests/`, lean root). **(S)**
- [ ] **F36**  Install `nbstripout` (or decide explicitly to keep output cells — recommend keep + gitattributes). **(S)**
- [ ] **F39**  Add "Open In Colab" badge to README and both notebooks. **(S)**

---

## How to use this list

1. Skim `REVIEW_FINDINGS.md` for full reasoning on each F## item.
2. Tick the boxes you want actioned.
3. Re-invoke Claude Code in this folder with: "Execute the ticked items in EXECUTION_CHECKLIST.md."
4. Code changes will be made in execution order: top-down through this file, respecting severity, so the notebooks pass a `pytest` (once F31 is in) at every commit.

If you want a smaller MVP first pass: tick **F17, F01 (decide remove vs rename), F03, F06, F32, F35** — that's a half-day of focused work that flips the repo from "personal scripts" to "presentable portfolio piece."

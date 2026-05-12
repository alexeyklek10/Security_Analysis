# Pass 1 — Correctness Bugs Only

Paste this whole document into Claude Code as your first message, with the working directory set to `Analysis_securities/`. You have the full context of `REVIEW_FINDINGS.md` available — read it first if you didn't write it.

This is **Pass 1 of 3**. Scope is **S0 correctness only**. Resist scope creep — do not restructure cells, redesign plots, write a README, or refactor any function that isn't directly named in this prompt. Pass 2 and Pass 3 will handle that work.

## Owner decisions (binding)

- **F01/F02**: **Remove** the implied-correlation feature entirely. Delete `calculate_implied_correlation`, `get_constant_maturity_iv`, the related config (`TARGET_IV_DAYS`, the `proxy` field in PORTFOLIO entries if unused elsewhere), the related table-print function (`print_implied_correlation`), and any chart that consumes its output. Reclaim the section. Add a single markdown-style comment block near the top of the notebook noting that an "implied correlation" feature was previously here and was removed because yfinance ATM IVs are unreliable and the prior implementation reduced algebraically to an IV-weighted average of historical correlations (not implied). This auto-resolves F02 and F30.
- **F04**: Wire `arch.arch_model` for **per-asset MLE GARCH(1,1) fit**. Pattern: `arch_model(returns * 100, vol='Garch', p=1, q=1, mean='Zero', dist='normal').fit(disp='off')`. Catch convergence failures (set vol to NaN, log the asset). Report (α, β, ω, persistence = α+β, half-life = log(0.5)/log(α+β)) in the per-asset summary. **Keep the manual GARCH recursion function in the codebase** as an unused educational reference — leave a single-line comment above its definition saying "Reference implementation showing the GARCH(1,1) recursion; not called by the main analysis (which uses arch.arch_model MLE fit per asset)."

## Findings in scope for Pass 1

All S0 findings, ordered by recommended execution sequence. Each one's full reasoning is in `REVIEW_FINDINGS.md`:

| # | Notebook | Effort | Summary |
|---|----------|--------|---------|
| F17 | volatility | S | Use `auto_adjust=True` consistently. Compute returns from adjusted close, feed adjusted OHLC to range estimators. Delete the separate `Adj_Close` column path. |
| F01+F02+F30 | correlation | M | Remove implied-correlation feature per decision above. |
| F03 | volatility | S | Replace `variance_ratio_test` SE with Lo-MacKinlay overlapping-returns SE: `np.sqrt(2 * (2*k - 1) * (k - 1) / (3 * k * n))`. Keep the same return signature. |
| F04 | volatility | M | Wire `arch.arch_model` MLE per decision above. Add `arch` to the notebook's pip-install cell at top (the volatility notebook does not currently have one — add `!pip install -q arch` as the first line of the cell so Colab paste still works). |
| F05 + F16 | volatility | M | Bias-correct Hurst. Add Anis-Lloyd correction: subtract expected E[R/S] under null from the raw R/S series before fitting the slope. Reference: Anis & Lloyd (1976) E[R/S(n)] formula. Remove the `np.clip(hurst, 0, 1)` line; let raw slope through. Update `rolling_hurst` consistently. Update regime classification thresholds to operate on bias-corrected H (the +0.08 bias was pushing everything into "TRENDING"). |
| F06 | correlation | S | Fix cumulative-return formula in `plot_executive_dashboard` and `plot_drawdown_analysis`. Compute simple returns once near the top of the function from log returns: `simple_r = np.expm1(log_r)`, then `(1 + (simple_r * weights).sum(axis=1)).cumprod()`. Or stay in log space: `cum_log = (log_r * weights).sum(axis=1).cumsum(); level = np.exp(cum_log); drawdown = level / level.cummax() - 1`. Pick one convention, use it in both functions, document in a comment. |
| F07 | correlation | M | Delete the Fisher-z mean-correlation "stability" test from `run_statistical_tests`. Replace with a **paired Wilcoxon signed-rank** on per-pair Fisher-z differences between the two halves: for each upper-triangle pair, compute z₁ = arctanh(ρ_first_half) and z₂ = arctanh(ρ_second_half), then `scipy.stats.wilcoxon(z1 - z2)`. Report W-statistic and p. The visual stability ranking (chart 06) stays untouched. |
| F10 | volatility | S | Add `_save_and_show(fig, filename)` helper mirroring the one in the correlation notebook. Update every `generate_*_dashboard` call site. Save to `images/volatility/` relative to CWD; create the directory if it doesn't exist. Filenames: `{ticker}_dashboard.png` for per-asset, `cross_asset_dashboard.png` for the comparison panel. Add a `SAVE_FIGURES = True` constant near other config. The correlation notebook's PNGs continue going to CWD for now — that's Pass 2's `images/correlation/` work. |

**Out of scope for Pass 1**: every other F-number (F08, F09, F11, F12, F13, F14, F15, F18–F39). Do not touch them. If you encounter something tempting (e.g., the DataEngine debug prints from F28), leave a `# TODO Pass 2: F28` comment but do not change.

## Structural constraints (don't break Colab compatibility)

- Each notebook stays as a **single code cell** in this pass. Do not split into multiple cells; that's Pass 3 (F33, F34).
- All imports stay at the top of the single cell.
- New `arch` dependency: install via `!pip install -q arch` at the very top of the volatility notebook's code cell. The correlation notebook does not need it.
- Do not introduce any local `.py` module imports. All code stays in the notebook.

## After making changes — verification

Run both notebooks end-to-end via `jupyter nbconvert --to notebook --execute --inplace`. Then verify each correctness fix with a specific numerical check:

1. **F17 check**: Cross-asset kurtosis table should no longer show BTAL >100 or MNA >50. Specifically: BTAL excess kurtosis expected to drop into single-digit-to-low-double-digit range. Print the new BTAL and MNA kurtosis values and confirm they look plausible.
2. **F01/F02 check**: `grep -r 'implied' Correlation_Analysis.ipynb` returns nothing in code paths (the removal-note comment is OK). `grep -r 'proxy' Correlation_Analysis.ipynb` is similarly clean. The executive dashboard renders without errors.
3. **F03 check**: For SPY at lag 20, the new z-stat should be approximately −1.3 (with p ≈ 0.20). Print VR, z, p at lags 2, 5, 10, 20 for SPY and confirm against the table in the run report. Tolerance: |z| within 0.05 of textbook value.
4. **F04 check**: Print per-asset (α, β, persistence) for at least 5 representative tickers (SPY, GLD, TLT, QQQ, IWM if available). Persistence should be < 1 for all; for SPY specifically α ≈ 0.10–0.20, β ≈ 0.75–0.88 typical. Convergence should succeed for all named tickers.
5. **F05 check**: Add the Gaussian-noise sanity check as part of the new "Sanity checks" cell described below.
6. **F06 check**: Print max drawdown of the equal-weight portfolio with the new formula. Compare to the old formula's result. Document both numbers in the changelog.
7. **F07 check**: Print W-stat and p-value of the new Wilcoxon test. Should be in `[0, n*(n+1)/2]` range for W; p should be a valid p-value.
8. **F10 check**: `ls images/volatility/` shows one PNG per processed ticker plus the cross-asset PNG.

## Add a "Sanity checks" cell — both notebooks

Append a final code cell at the very end of each notebook (still inside the single existing cell, just as the last logical section, delimited with `# ===== SANITY CHECKS =====`) that runs these in-notebook regression checks. Skipping these does not block the analysis but produces visible reassurance for any reader.

**Volatility notebook sanity checks:**
- Yang-Zhang on synthetic geometric Brownian motion: run YZ on a 252-day simulated GBM with annual σ=20%; assert recovered σ is within 10% of 20%.
- Hurst on `np.random.default_rng(42).standard_normal(2500)`: assert recovered H is within [0.42, 0.58] (i.e., bias correction worked — without it the value would be ~0.58).
- GARCH(1,1) mean reversion: on the same GBM series, assert `ω / (1 − α − β)` (long-run variance from fitted params) is within 30% of sample variance.

**Correlation notebook sanity checks:**
- Equicorrelated synthetic 5-asset matrix with true ρ=0.4: assert average upper-triangle Pearson recovered is within ±0.05 of 0.4.
- Mantegna distance metric (preview for Pass 2 even though F09 is out of scope — just a one-line cell that defines the function and asserts it's a proper metric on a 3x3 test matrix). Skip this if it tempts you to also fix F09 — that's Pass 2.

Both notebooks should print a clearly-labeled `✓ Sanity check passed` (or fail with a loud message) per check.

## Deliverable: a changelog

Write `PASS1_CHANGELOG.md` in the working directory with these sections:

```
# Pass 1 Changelog — Correctness Bugs

## Summary
[2-3 sentence summary of what changed.]

## Files modified
- Correlation_Analysis.ipynb (Y lines added, Z lines removed)
- Volatility_Analysis.ipynb (Y lines added, Z lines removed)
- images/volatility/ (new directory, N PNGs)

## Per-finding outcomes

### F17 — auto_adjust fix
- What changed: [one paragraph]
- Before/after BTAL kurtosis: X → Y
- Before/after MNA kurtosis: X → Y

### F01/F02/F30 — implied-correlation removal
- What changed: [one paragraph]
- Functions removed: [list]
- Lines removed: ~N

### F03 — Variance ratio SE
- What changed: [one paragraph]
- SPY VR test, lag 20: old z=−8.6 / p=0.0000  →  new z=Y / p=Z

### F04 — GARCH MLE wiring
- What changed: [one paragraph]
- SPY fitted (α, β, persistence): (X, Y, Z)
- Tickers that failed to converge (if any): [list]

### F05+F16 — Hurst bias correction + remove clip
- What changed: [one paragraph]
- Gaussian noise sanity (n=2500, seed=42): H = X (bias-corrected); without correction would have been ~0.58
- Regime classification distribution: trending/mean-reverting/random-walk counts before vs after correction

### F06 — Cumulative return formula
- What changed: [one paragraph]
- Equal-weight portfolio max drawdown: old X% → new Y% (difference Z bp)

### F07 — Correlation stability test
- What changed: [one paragraph]
- New paired-Wilcoxon W = X, p = Y. Interpretation: [one sentence]

### F10 — Volatility figure saves
- What changed: [one paragraph]
- N PNGs written to images/volatility/

## Sanity checks
- Volatility: 3/3 passed | failed details
- Correlation: 2/2 passed | failed details

## Out of scope but flagged
[List any TODO Pass 2 comments added to the source code, with line ranges]

## Pass 2 readiness
[2-3 sentences: anything that surprised you, anything that complicates Pass 2 scope, anything the owner should know before commissioning Pass 2]
```

## Hard constraints

- Do not git-commit anything. The owner will review the diff and commit manually.
- Do not run `pip install` on the owner's main env — use the venv from the review pass.
- Do not modify `REVIEW_FINDINGS.md`, `EXECUTION_CHECKLIST.md`, or `DEEP_REVIEW_PROMPT.md` — they're the audit trail.
- If you discover during execution that a fix has a dependency on another finding that's out of scope for Pass 1, do the minimum required and add a `# TODO Pass 2: F##` comment. Do not silently expand scope.
- If a verification check fails, **stop and surface it in the changelog rather than papering over it**. A loud failure is more useful than a quiet broken fix.

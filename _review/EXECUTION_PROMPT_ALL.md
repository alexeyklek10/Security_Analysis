# Execution Prompt — Complete Refactor (Single Pass, Three Phases)

Paste this whole document into Claude Code as your first message, working directory `Analysis_securities/`. You have `REVIEW_FINDINGS.md` available for full per-finding reasoning — read it first.

**Goal**: Take both notebooks from S0-buggy single-cell scripts to a publishable GitHub portfolio piece in one wall-clock pass. ~6–10 hours.

**Method**: Three internal phases with **hard verification gates** between them. If gate fails, halt and write partial changelog rather than propagating broken numbers downstream.

## Default decisions baked in (binding unless overridden by the owner before this prompt runs)

- **F01**: Remove implied-correlation feature entirely. Delete `calculate_implied_correlation`, `get_constant_maturity_iv`, `print_implied_correlation`, `TARGET_IV_DAYS`, the `proxy` field everywhere it appears, any chart consuming the output. Leave one markdown-comment line near top of notebook noting the removal and why.
- **F04**: Wire `arch.arch_model` per-asset MLE GARCH(1,1). Keep manual GARCH function in codebase as commented reference implementation, not called.
- **F09**: `dist = sqrt(0.5 * (1 - corr))` Mantegna metric for hierarchical clustering.
- **F11/F14**: Rename `systematic_var`/`idio_var` to `co_movement_var`/`diagonal_var` throughout. Display labels: "Co-Movement Share" / "Diagonal Variance Share." Add a markdown note explaining the labels are NOT CAPM systematic/idiosyncratic.
- **F24**: Consolidate to the 9 charts the reviewer proposed. Delete the 12 obsolete plot functions.
- **F31**: In-notebook "Sanity checks" cell AND `tests/test_estimators.py` with thin reference implementations.
- **F36**: Strip notebook outputs at commit. Sample PNGs embedded in README. Install `nbstripout` locally.
- **F37**: Keep dark theme. Min font size 8 everywhere. Audit colormap for accessibility but no change recommended.
- **F35**: Repo layout per F35 proposal (`notebooks/`, `images/`, `data/cache/`, `tests/`, lean root).

Out of scope entirely (not in this pass): nothing — every numbered finding F01–F39 is actioned with the exceptions noted as "comment only" below.

---

## Phase A — Correctness (S0)

Execute in this order. Full per-finding details in `REVIEW_FINDINGS.md`.

1. **F17** (volatility): Switch `fetch_ohlc_data` to `auto_adjust=True`. Drop the separate `Adj_Close` column path. Returns and OHLC range estimators now use the same adjusted series.
2. **F01+F02+F30** (correlation): Remove implied-correlation feature per default above.
3. **F03** (volatility): Replace `variance_ratio_test` asymptotic SE with `np.sqrt(2 * (2*k - 1) * (k - 1) / (3 * k * n))`. Same return signature.
4. **F04** (volatility): Wire `arch.arch_model(returns * 100, vol='Garch', p=1, q=1, mean='Zero', dist='normal').fit(disp='off')`. Catch convergence failures → NaN + log. Report (α, β, ω, persistence=α+β, half-life=log(0.5)/log(α+β)) in per-asset summary. Add `!pip install -q arch` to top of vol notebook cell.
5. **F05+F16** (volatility): Bias-correct Hurst via Anis-Lloyd (subtract E[R/S(n)] under null before fitting slope). Reference: Anis & Lloyd (1976). Remove `np.clip(hurst, 0, 1)`. Update `rolling_hurst` consistently. Update regime classification thresholds to operate on bias-corrected H.
6. **F06** (correlation): Fix cumulative returns. Choose **simple-return convention**: compute `simple_r = np.expm1(log_r)` once near top of the relevant function, then `(1 + (simple_r * weights).sum(axis=1)).cumprod()`. Apply in `plot_executive_dashboard` and `plot_drawdown_analysis`. Add a comment documenting the convention.
7. **F07** (correlation): Delete Fisher-z mean-correlation test. Replace with paired Wilcoxon signed-rank on per-pair Fisher-z deltas between halves: `z1 = arctanh(rho_h1); z2 = arctanh(rho_h2); scipy.stats.wilcoxon(z1 - z2)`. Report W and p.
8. **F10** (volatility): Add `_save_and_show(fig, filename)` helper mirroring correlation notebook's. Save to `images/volatility/` (create dir). Filenames: `{ticker}_dashboard.png`, `cross_asset_dashboard.png`. Add `SAVE_FIGURES = True` constant.

### GATE A — verification (HARD)

Run both notebooks via `jupyter nbconvert --to notebook --execute --inplace`. Then verify each:

| Check | Expectation |
|---|---|
| F17: BTAL cross-asset excess kurtosis | drops below 50 (was 344) |
| F17: MNA cross-asset excess kurtosis | drops below 30 (was 70) |
| F01: `grep 'implied\\|proxy\\|TARGET_IV_DAYS' Correlation_Analysis.ipynb` | returns nothing in code paths (removal-note comment OK) |
| F03: SPY VR z-stat at lag 20 | within ±0.15 of −1.29 |
| F04: SPY GARCH (α, β, persistence) | α ∈ [0.08, 0.25], β ∈ [0.72, 0.92], α+β < 1 |
| F05: In-notebook Gaussian-noise Hurst sanity (n=2500, seed=42) | within [0.42, 0.58] |
| F06: Equal-weight max DD reported value present and finite | non-trivial, within ±1.5pp of pre-fix value (sanity, not strict) |
| F07: Wilcoxon W-stat and p-value present in test output | values are finite, p ∈ [0,1] |
| F10: `images/volatility/*.png` | ≥27 PNGs present (one per processed ticker + cross-asset) |

**If any GATE A check fails: write `PARTIAL_CHANGELOG.md` documenting what passed and what failed. Halt. Do not begin Phase B.**

---

## Phase B — Cleanup (S1, S2, S3)

After Phase A's gate is clean, proceed. Execute in this order; each fix is small.

### Methodology fixes (S1)

9. **F08** (correlation): Replace i.i.d. bootstrap in tail-vs-normal test with block bootstrap on dates. Block length ≈ √n. On each resample, recompute full Pearson and Tail matrices, tabulate Δavg-ρ. Or: replace with paired Wilcoxon on `tail_vals − pearson_vals` (matched pairs) — simpler, defensible. Prefer Wilcoxon.
10. **F09** (correlation): `run_clustering_analysis` — `dist = np.sqrt(np.clip(0.5 * (1 - corr.values), 0, 1))`. Note in markdown comment that this is Mantegna's metric.
11. **F11+F14** (correlation): Rename `systematic_var` → `co_movement_var`, `idio_var` → `diagonal_var` in `calculate_portfolio_metrics`. Update all consumers (printouts, dashboard text, donut labels). Add explanation cell/comment: "These quantities partition portfolio variance into 'covariance contribution from pairs' vs 'individual asset variance contribution'. They are NOT a CAPM systematic-vs-idiosyncratic split — that would require regression against a market factor."
12. **F12** (correlation): Pairwise correlation significance count — add Benjamini-Hochberg FDR (`statsmodels.stats.multitest.multipletests(pvals, alpha=0.05, method='fdr_bh')`). Report `count significant at FDR α=0.05`.
13. **F13** (correlation): Report tail correlation at three percentiles: 5%, 10%, 15%. Master table gets 3 columns.
14. **F16** (volatility): Already done in Phase A as part of F05+F16.
15. **F29** (correlation): In Bartlett's sphericity test: `if det_val < 1e-6: skip and emit "Correlation matrix near-singular — Bartlett's test not applicable."` Otherwise compute normally.

### Robustness fixes (S2)

16. **F15** (volatility): `min_periods=window` on every rolling vol estimator. Series start honestly at index `window`. Document in comment.
17. **F18**: Write lean `requirements.txt` in repo root: `yfinance>=0.2.40`, `pandas>=2.0`, `numpy>=1.24`, `scipy>=1.10`, `scikit-learn>=1.3`, `statsmodels>=0.14`, `arch>=6.0`, `matplotlib>=3.7`, `seaborn>=0.12`, `pyarrow>=14` (for parquet cache).
18. **F19** (both): Add lazy parquet cache. Helper function `_get_cached_prices(tickers, start, end, cache_dir='data/cache')` — hashes (tickers tuple, start, end) → filename → load if exists, else fetch+save. ~25 lines. Plumb into the data-fetch paths in both notebooks. The exact same helper code goes in both notebooks (Colab-paste constraint). Add `data/cache/` to `.gitignore`.
19. **F20** (correlation): `prices.ffill()` → `prices.ffill(limit=5)`. Print ffill counts per ticker after fetch.
20. **F21** (volatility): Failed tickers — include in cross-asset table with NaN cells. Surface one-line banner above cross-asset chart: "Note: N of M assets failed: [list]."

### Redundancy & structure (S3)

21. **F22** (correlation): Collapse `DataEngine` class to `def fetch_prices_and_returns(tickers, start, end) -> Tuple[pd.DataFrame, pd.DataFrame]`. Keep only the `raw['Close']` MultiIndex path currently exercised. Delete debug prints and dead fallback paths. Target ~30 lines.
22. **F23** (both): Pick the volatility notebook's `THEME = {...}` dict style. Copy identically into both notebooks (every color, every font size). Same for `_header`, `_subheader` helpers. The two notebooks must now share *byte-identical* theme code blocks where applicable.
23. **F24** (correlation): Consolidate 21 charts → 9. Delete the 12 plot functions that become obsolete (`plot_spy_correlation_master`, `plot_category_spy_bars`, `plot_correlation_change`, `plot_rolling_avg_pairwise`, `plot_correlation_distribution`, `plot_asset_volatilities`, and others per reviewer's mapping). Keep: executive dashboard (fixed per F06), correlation methods comparison (was 02, trimmed to 3 columns), tail-stress dashboard (consolidates 03+05), rolling correlation panel (consolidates 09+12 faceted by category), beta-vs-correlation quadrant (04), correlation regime heatmap (11), full clustered Pearson heatmap (13), PCA factor structure (19), drawdown & cumulative returns (17 with F06 fix).
24. **F25** (correlation): Vectorize variance decomp in `calculate_portfolio_metrics` — `vols_outer = np.outer(vols, vols); cov_mat = vols_outer * corr_mat.values; total_var = w @ cov_mat @ w; diagonal_var = np.sum(w**2 * vols**2); co_movement_var = total_var - diagonal_var`. Same in `plot_risk_contribution`.
25. **F26** (both): Standardize `from scipy import stats as sps` everywhere; remove other aliases.
26. **F27** (correlation): Save figures to `images/correlation/` not CWD. Mirror F10's pattern.
27. **F28** (correlation): Remove all `print(f"  [debug] ...")` lines. Gate any remaining diagnostic prints behind `VERBOSE = False` constant.

### GATE B — verification (HARD)

Re-run both notebooks fully. Verify:

- Both notebooks execute end-to-end with no errors.
- Sanity-check cells still pass (Hurst on noise, GARCH mean reversion, YZ on GBM, equicorrelated recovery).
- Correlation notebook produces exactly 9 PNGs in `images/correlation/`.
- Volatility notebook produces ≥28 PNGs in `images/volatility/`.
- `grep -i 'systematic\\|idiosyncratic' Correlation_Analysis.ipynb` returns nothing (rename complete).
- `grep '\\[debug\\]' Correlation_Analysis.ipynb` returns nothing.
- `data/cache/` exists and contains parquet files after first run.

**If any GATE B check fails: write changelog through Phase B, document failures, halt. Do not begin Phase C.**

---

## Phase C — Presentation (S4, S5, S6)

This is the format/polish layer. Code should be settled by now.

### Cell splits

28. **F33** (correlation): Split notebook into the 18-cell sequence proposed in `REVIEW_FINDINGS.md` F33. For each markdown cell, write ~2-4 sentences of clear narrative (not lorem ipsum). Title, abstract, audience targeting (split: rigorous methods for quant readers, plain-language interpretations for learners). For "Step 2 — Correlation suite," the markdown cell should briefly define Pearson / Spearman / Kendall / EWMA / Tail in 1–2 sentences each.
29. **F34** (volatility): Split per F34's 17-cell sequence. LaTeX formulae above each estimator definition (use `$$...$$` blocks). Single-asset deep dive uses `SHOWCASE = 'GLD'`. Make GARCH approach an explicit `'mle'` default with a one-line comment about how to swap to `'manual'` for pedagogical interest.

### Tables → Styler

30. **F38** (both): Wrap every "print numeric table" in a function returning a `pd.DataFrame.style.format(...).background_gradient(...)`. Keep raw `print()` versions as fallback printed first; styled versions render second. Target: per-asset GARCH params, correlation methods comparison, vol-estimator comparison, statistical test results.

### Visual polish

31. **F37** (both): Audit every `fontsize=` instance. Anything below 8 → set to 8 (axis ticklabels, annotations, table cells). Verify the diverging colormap `[#1565c0, #42a5f5, #e3f2fd, #ffffff, #ffebee, #ef5350, #b71c1c]` text/background pairs all hit WCAG AA (4.5:1 normal text). Print contrast ratios in a comment.

### Repo layout, README, tests

32. **F35** — Move files into target layout:
    ```
    Analysis_securities/
    ├── README.md
    ├── LICENSE                    (MIT)
    ├── requirements.txt           (from F18)
    ├── .gitignore                 (covers data/cache/, __pycache__/, .venv/, *.pyc, images/*.png ONLY at repo root)
    ├── .gitattributes             (notebook merge driver)
    ├── notebooks/
    │   ├── Correlation_Analysis.ipynb
    │   └── Volatility_Analysis.ipynb
    ├── images/
    │   ├── correlation/           (9 PNGs)
    │   └── volatility/            (per-ticker dashboards)
    ├── data/
    │   └── cache/                 (parquet, gitignored)
    └── tests/
        └── test_estimators.py
    ```
    Move `REVIEW_FINDINGS.md`, `EXECUTION_CHECKLIST.md`, `EXECUTION_PROMPT_ALL.md`, `DEEP_REVIEW_PROMPT.md`, `EXECUTION_PROMPT_PASS1.md`, `COMPLETE_CHANGELOG.md` into a top-level `_review/` directory (or delete the prompts that are now historical artifacts; keep `REVIEW_FINDINGS.md` for audit).

33. **F32** — Write `README.md`:
    - Title: "Securities Analysis — Correlation & Volatility"
    - One-paragraph pitch (3-4 sentences): what these notebooks compute, who they're for, why they exist.
    - Two embedded sample images (one per notebook) — pick the correlation executive dashboard and the volatility Yang-Zhang term structure (or whichever single image best represents each notebook visually).
    - **Methodology** section: 5-7 bullets summarizing the techniques (Pearson/Spearman/Kendall/EWMA/Tail correlations; PCA + ENB diversification scorecard; hierarchical clustering with Mantegna metric; OHLC vol estimators including Yang-Zhang and Garman-Klass; GARCH(1,1) MLE via `arch`; bias-corrected Hurst; Lo-MacKinlay variance ratio).
    - **How to run** — locally and Colab. Provide Colab badge URLs (placeholder if repo not yet on GitHub).
    - **Interpretation guide** — a table: `metric → what it means → what's a typical / good value` for headline outputs.
    - **Limitations and known caveats** — short, honest paragraph (≤5 bullets): tail metrics noisy at small n; GARCH(1,1) is single-regime; rolling windows are convention-dependent; no transaction costs; survivorship bias risk in ticker selection.
    - **License**: MIT.
    - Audience note: aim the README at both quant readers and intermediate retail traders — be technically precise but unpack jargon.

34. **F36** — Add `.gitattributes` and run `nbstripout --install`:
    - `.gitattributes` content: `*.ipynb filter=nbstripout`
    - Run `nbstripout --install` in the repo (local-only one-time setup; document this in README's "How to run" section under a "Development" subheading).
    - Verify by re-saving a notebook and `git diff` showing no output-cell churn.

35. **F39** — Add "Open in Colab" badges (with placeholder GitHub user/repo paths the owner can replace) at the top of each notebook (first markdown cell, after title) AND in README.

36. **F31** — `tests/test_estimators.py`:
    - Thin reference implementations of YZ, GK, GARCH mean-reversion, bias-corrected Hurst, Lo-MacKinlay VR SE.
    - Each test imports nothing from notebooks (the notebooks remain Colab-pasteable). Tests run via plain `pytest tests/`.
    - No CI setup — local-run only at this stage. Document `pytest tests/` invocation in README under "Development."
    - Each test should match the in-notebook sanity check on the same input, but lives outside the notebook so a refactor can break the regression guard before touching production code.

### GATE C — verification (HARD)

Fresh end-to-end test:

1. Delete `.venv/`, `data/cache/`, `images/correlation/`, `images/volatility/`.
2. Create new venv. `pip install -r requirements.txt`.
3. `jupyter nbconvert --to notebook --execute notebooks/Correlation_Analysis.ipynb --inplace --output-dir notebooks/`
4. `jupyter nbconvert --to notebook --execute notebooks/Volatility_Analysis.ipynb --inplace --output-dir notebooks/`
5. Both must complete without errors. All sanity-check cells must pass.
6. `pytest tests/` — all green.
7. `git diff` after `nbstripout` filter — should show no output-cell churn between fresh-run notebook and committed notebook.
8. README renders correctly when previewed (check `images/` paths resolve).

---

## Final deliverable: `COMPLETE_CHANGELOG.md`

Replace any Phase-specific changelog files. Structure:

```
# Complete Refactor Changelog

## Summary
[3-5 sentences: scope, biggest changes, what improved, what's now true that wasn't before.]

## Files added / moved / deleted
[Bulleted list of all file-system changes.]

## Phase A — Correctness (per-finding outcomes with before/after numbers)
[Same structure as Pass 1 changelog spec.]

## Phase B — Cleanup (per-finding summary)
[One paragraph per finding.]

## Phase C — Presentation (per-finding summary)
[One paragraph per finding.]

## Verification results
- GATE A: PASSED [or specific failures]
- GATE B: PASSED [or specific failures]
- GATE C: PASSED [or specific failures]
- pytest: N tests, all passing
- Cross-asset kurtosis sanity: BTAL X → Y, MNA X → Y
- SPY VR test lag 20: old z=−8.6 → new z=Y
- SPY GARCH: α=X, β=Y, persistence=Z
- Gaussian-noise Hurst sanity: X (bias-corrected)
- Equal-weight max DD before vs after F06: X% → Y%

## Anything surprising
[Honest note on anything unexpected encountered. If everything went smooth, say so.]

## Ready-to-publish checklist
- [ ] Owner has reviewed COMPLETE_CHANGELOG.md
- [ ] Owner has done a manual eyeball of one chart per notebook
- [ ] Owner has replaced `<user>/<repo>` placeholders in Colab badges
- [ ] Owner has run `pytest tests/` themselves to confirm
- [ ] `git init && git add . && git commit -m "Initial publishable version"` ready to invoke
```

## Hard constraints

- **Do not** git-commit anything. Owner reviews diff and commits manually.
- **Do not** run pip install on owner's system Python; use venv from review pass (or create new venv if it doesn't exist).
- **Phase ordering is binding.** Gate failures stop progression. The point of gates is to catch broken numbers before the presentation layer is built on top of them.
- **Don't** introduce local module imports. Both notebooks must remain copy-pasteable into a single Colab cell (with one initial `!pip install` line each).
- **Don't** preserve cell outputs in the committed notebooks (F36) — `nbstripout` filter handles this, but verify before declaring Phase C complete.
- **Don't** silently fix things outside the 39 numbered findings. If you spot a 40th issue, add it to a `POSTPASS_FINDINGS.md` for the owner's review — don't paper over it.
- **Do** halt loudly on any gate failure. A halted-with-clear-changelog state is more valuable than a finished-but-broken state.

# Deep Review Prompt — Securities Analysis Notebooks

Paste this whole document into Claude Code as your first message, with the working directory set to this folder (`Analysis_securities/`). The reviewer should be in "senior quant + technical-writing editor" mode — rigorous on the math, opinionated on presentation, allergic to redundancy.

---

## Context you're walking into

Two Jupyter notebooks live in this folder:

- **`Correlation_Analysis.ipynb`** — ~3,000 lines crammed into a single Colab cell. A `DataEngine` class plus 50+ functions covering portfolio correlation, rolling/EWMA/tail correlations, PCA, hierarchical clustering, implied correlation from options chains (via yfinance), beta vs correlation, stress coincidence, plus ~20 named dashboard plots.
- **`Volatility_Analysis.ipynb`** — ~1,360 lines, also a single Colab cell. Seven volatility estimators (realized, Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang, EWMA, manual GARCH(1,1)), downside deviation, vol-of-vol, ATR + percentile, Hurst exponent (and rolling), market efficiency ratio, rolling VaR / CVaR, variance ratio test, return distribution tests (Jarque-Bera, skew, kurt, Ljung-Box), regime classification, per-asset and cross-asset dashboards.

Both currently look like working Colab scripts dumped into single cells. The owner wants to publish them on GitHub as clean, professional analyses — while keeping them Colab-paste-runnable.

## Target end state (informs your recommendations)

- Each notebook split into properly sectioned multi-cell `.ipynb` files with markdown narrative between code cells.
- **Each notebook must remain self-contained.** A user must be able to copy-paste the whole notebook body into a single Colab cell and have it work. So: **no local module imports** — only pip-installable packages. Some code duplication between the two notebooks is acceptable; that's the cost of Colab-paste compatibility.
- Audience is split: serious quant readers + retail learners. The code must be rigorous; the narrative and plots must be accessible. README will do heavy lifting.
- Visual layer is **fully in-scope**. Propose redesigns where warranted.

## Your job in this pass

**Do NOT modify the source notebooks.** This is discovery + proposal only. The owner will triage your findings, then commission execution in a separate pass.

Produce two deliverables in this folder:

1. **`REVIEW_FINDINGS.md`** — structured, triaged list of every improvement proposal.
2. **`EXECUTION_CHECKLIST.md`** — same findings reduced to a ticklist with `[ ]` checkboxes, grouped by recommended execution order, so the owner can tick which ones to action.

## How to run the review

1. Read both notebooks fully. Don't skim. The `DataEngine` class, the manual `garch_volatility` calibration, the `calculate_implied_correlation` function (pulls options-chain IVs from yfinance), the `calculate_hurst_exponent`, and the cross-asset dashboards are the densest parts — read them line by line.
2. Set up a Python venv. Install: `yfinance pandas numpy scipy scikit-learn statsmodels matplotlib seaborn`. Execute each notebook end-to-end via `jupyter nbconvert --to notebook --execute` or `papermill`. Capture: total runtime, every warning, every error, every figure produced. Note any silently wrong numbers (e.g., correlations outside [-1, 1], negative variances, p-values that look impossibly small/large).
3. Spot-check at least **two** calculations with independent reimplementations:
   - **One volatility estimator** — strongly suggest Yang-Zhang or Garman-Klass. Implement it fresh from the textbook formula and confirm the notebook's numbers match.
   - **One statistical test** — strongly suggest the manual GARCH(1,1) recursion (verify the variance update equation, verify α + β < 1, verify it converges to the unconditional variance σ² = ω / (1 − α − β)) OR the variance ratio test against `arch.unitroot.VarianceRatio` or a textbook implementation.

## What to look for (in priority order)

**S0 — Correctness bugs.** Math that's wrong or subtly wrong. Annualization-factor mistakes (252 vs 365, daily vs weekly). Look-ahead bias in rolling windows. Log-return vs simple-return mixing. NaN propagation that silently zeros downstream results. Survivorship bias in the ticker list. The manual GARCH(1,1) is the highest-risk function — verify the recursion, the unconditional-variance initialization, and the alpha+beta<1 constraint. The implied-correlation-from-options-chains code is the second-highest risk — verify the constant-maturity interpolation across expiries, and verify the formula relating portfolio IV to component IVs and pairwise implied correlations.

**S1 — Statistical methodology.** Are p-values reported with multiple-testing context where the user might draw a "found a signal" conclusion from a sweep? Does the Hurst exponent's `max_lag` choice respect the sample-size rule of thumb? Are the 5% / 95% tail-correlation thresholds defensible given sample size, or are they too noisy? Are rolling-window choices (e.g., 252 days) justified or arbitrary? Are confidence intervals shown anywhere — bootstrap CIs on the correlation matrix? on the vol estimates? Are regime-classification cutoffs principled (e.g., based on full-sample distribution quantiles) or hand-tuned?

**S2 — Robustness & reproducibility.** What happens when a ticker has shorter history than others? When yfinance returns partial data or fails entirely for one ticker? Should there be a random seed anywhere? Are package versions pinned? Should a simple on-disk cache (pickle / parquet) be added so re-running doesn't re-download? Are there silent exception swallows that mask bad data?

**S3 — Redundancy & structure.** Which functions duplicate work *across* the two notebooks (theme application, header helpers, return calculations, plot styling)? Which plots in the correlation notebook show essentially the same information? Are the 20+ correlation plots earning their keep, or could they consolidate into 6–8 sharper ones? Is the `DataEngine` class actually pulling its weight, or could it be a couple of functions? Inside each notebook, which functions are dead code?

**S4 — Presentation & narrative.** Propose a concrete cell-by-cell split for each notebook with the markdown narrative outlines (you don't need to write the prose — just the section titles, intent of each markdown cell, and which code goes in which cell). Propose a README structure: title, what-it-does in 2 sentences, methodology bullets, sample images, how-to-run (locally + Colab badge), interpretation guide. Identify numeric outputs that should be styled tables (pandas Styler) rather than `print()` statements.

**S5 — Visual redesign opportunities.** Open season. For each plot you'd change, state: plot name, what's wrong / suboptimal, what's better. Be specific. Cite a principle (Cleveland's preattentive attributes, Tufte's data-ink, Cairo's truthful-vs-functional) when relevant. Explicitly evaluate whether the dark institutional theme is the right choice for a public GitHub portfolio piece — argue both sides honestly.

**S6 — README + repo polish.** What goes in the README. Whether to include rendered sample images. Suggested repo name. Suggested folder structure (e.g., `notebooks/`, `images/`, `data/cache/`, no top-level clutter). License choice and rationale. `requirements.txt` vs `pyproject.toml` (lean toward the simpler choice given the Colab constraint). CI? Pre-commit? `nbstripout`? — propose only what serves the goal; resist over-engineering.

## Output format for `REVIEW_FINDINGS.md`

```
# Review Findings — Securities Analysis Notebooks

## Executive summary
[3–5 sentences. Overall shape of the work, biggest lift, what's already strong, what's most at risk.]

## Run report
- Correlation notebook: ran in X seconds, N warnings (list them), produced N figures. Issues observed: ...
- Volatility notebook: ran in X seconds, N warnings, N figures. Issues observed: ...
- Spot-check 1 — [estimator name]: independent reimplementation matched / differed by X%. Details.
- Spot-check 2 — [test/function name]: matched / differed. Details.

## Findings

### [F01] [Concise title]
- **Severity:** S0 / S1 / S2 / S3 / S4 / S5 / S6
- **Notebook:** correlation / volatility / both
- **Location:** function name, approx line range
- **Effort:** S (<30min) / M (1–3hr) / L (>3hr)
- **What's wrong / what could be better:** 2–4 sentences. Concrete.
- **Proposed fix:** 2–4 sentences. Concrete. Cite the formula / approach.
- **Risk if we skip it:** 1 sentence.

[Continue F02, F03, ... — number sequentially. Expect 25–50 findings if you're thorough.]

## Recommended sequencing
[The "if you only do 5 things, do these" list, in execution order, with a one-line why for each.]
```

## Output format for `EXECUTION_CHECKLIST.md`

Group by severity. Each line: `- [ ] F##  [S0]  short title  (effort)`. Add a brief header explaining the owner ticks what they want and re-invokes Claude Code with the ticked list.

## Hard constraints

- Don't modify the source `.ipynb` files in this pass.
- Don't ask the owner clarifying questions — make defensible judgment calls and surface the assumption in the relevant finding.
- Don't include aesthetic-only findings without a stated rationale or principle.
- Don't recommend anything that breaks Colab-paste compatibility (no local `.py` module imports at runtime, no project-rooted relative imports).
- Don't pad. A 30-finding doc that's all sharp beats a 60-finding doc that's half generic.

Take your time. This is the slowest, most thorough pass — execution comes later.

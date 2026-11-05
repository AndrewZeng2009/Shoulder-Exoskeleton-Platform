"""
Reproduces every statistic, table, and figure reported in
"Open-Source Cable-Driven Shoulder Exoskeleton Research Platform: Design and Evaluation"
from the trial-level dataset Data/trial_level_data.csv.

Usage (from the repository root):
    pip install -r Analysis/requirements.txt
    python Analysis/analyze.py

Outputs: Results/*.csv (all statistics), Results/latex_tables.tex (Tables 2-5), Figures/*.pdf and *.png (Figures 6-9).
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data" / "trial_level_data.csv"
RES = ROOT / "Results"; FIG = ROOT / "Figures"
RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)

COND = ["Baseline", "Harness-only", "Passive-only", "Active-only", "Active+passive"]
TCOND = ["Passive-only", "Active-only", "Active+passive"]
MOTIONS = ["Flexion", "Abduction"]; LOADS = [0, 3, 5]
ROM_MOTIONS = ["Flexion", "Abduction", "Horizontal adduction"]; AXES = ["pitch", "roll", "yaw"]

df = pd.read_csv(DATA)
emg = df[df.test_type == "EMG"].copy(); emg["load_lb"] = emg.load_lb.astype(int)
tor = df[df.test_type.isin(["Bench torque", "In vivo torque"])].copy()
rom = df[df.test_type == "ROM"].copy()
tor["setup"] = np.where(tor.test_type == "Bench torque", "Bench", "In vivo " + tor.motion.str.lower())

def msd(x):
    x = np.asarray(x, float); return x.mean(), x.std(ddof=1)

def welch_ci(groups, signs, alpha=0.05):
    """Linear contrast sum(sign*mean) with Welch-Satterthwaite df and t-based CI."""
    est = sum(s * np.mean(g) for g, s in zip(groups, signs))
    v = [np.var(g, ddof=1) / len(g) for g in groups]
    se = np.sqrt(sum(v)); dof = sum(v) ** 2 / sum(vi ** 2 / (len(g) - 1) for vi, g in zip(v, groups))
    t = stats.t.ppf(1 - alpha / 2, dof)
    return est, se, dof, est - t * se, est + t * se

def icc31(x):
    """ICC(3,1): two-way mixed effects, consistency, single measurement (Shrout & Fleiss 1979)."""
    x = np.asarray(x, float); n, k = x.shape; gm = x.mean()
    ssr = k * ((x.mean(1) - gm) ** 2).sum(); ssc = n * ((x.mean(0) - gm) ** 2).sum()
    sse = ((x - gm) ** 2).sum() - ssr - ssc
    msr = ssr / (n - 1); mse = sse / ((n - 1) * (k - 1))
    return (msr - mse) / (msr + (k - 1) * mse)

def cell(m, L, c, metric):
    return emg[(emg.motion == m) & (emg.load_lb == L) & (emg.condition == c)][metric].to_numpy()

# ---------------- 1. EMG summary (Tables 2-3) ----------------
rows = []
for m in MOTIONS:
    for L in LOADS:
        bm, bp = cell(m, L, "Baseline", "emg_mean_counts").mean(), cell(m, L, "Baseline", "emg_peak_counts").mean()
        hm, hp = cell(m, L, "Harness-only", "emg_mean_counts").mean(), cell(m, L, "Harness-only", "emg_peak_counts").mean()
        for c in COND:
            mm, ms = msd(cell(m, L, c, "emg_mean_counts")); pm, ps = msd(cell(m, L, c, "emg_peak_counts"))
            rows.append(dict(motion=m, load_lb=L, condition=c, n=len(cell(m, L, c, "emg_mean_counts")),
                             mean_emg=mm, mean_sd=ms, mean_cv_pct=100 * ms / mm, peak_emg=pm, peak_sd=ps, peak_cv_pct=100 * ps / pm,
                             pct_reduction_mean_vs_baseline=100 * (bm - mm) / bm, pct_reduction_peak_vs_baseline=100 * (bp - pm) / bp,
                             pct_change_mean_vs_harness=100 * (mm - hm) / hm, pct_change_peak_vs_harness=100 * (pm - hp) / hp))
emg_sum = pd.DataFrame(rows); emg_sum.round(3).to_csv(RES / "emg_summary.csv", index=False)

# ---------------- 2. Condition minus baseline, Welch CIs (device burden etc.) ----------------
rows = []
for m in MOTIONS:
    for L in LOADS:
        for c in COND[1:]:
            for met in ["emg_mean_counts", "emg_peak_counts"]:
                e, se, d, lo, hi = welch_ci([cell(m, L, c, met), cell(m, L, "Baseline", met)], [1, -1])
                rows.append(dict(motion=m, load_lb=L, condition=c, metric=met, diff_vs_baseline=e, se=se, df=d, ci_low=lo, ci_high=hi,
                                 ci_excludes_zero=(lo > 0) or (hi < 0)))
pd.DataFrame(rows).round(3).to_csv(RES / "effects_vs_baseline_welch.csv", index=False)

# ---------------- 3. Passive x Active interaction (Table 4) ----------------
rows = []
for m in MOTIONS:
    for L in LOADS:
        for met, lab in [("emg_mean_counts", "Mean"), ("emg_peak_counts", "Peak")]:
            H, P, A, AP = [cell(m, L, c, met) for c in COND[1:]]
            I, se, d, lo, hi = welch_ci([AP, A, P, H], [1, -1, -1, 1])
            rows.append(dict(motion=m, load_lb=L, metric=lab, I_counts=I, I_pct_of_harness=100 * I / H.mean(), se=se, df=d,
                             ci_low=lo, ci_high=hi, ci_excludes_zero=(lo > 0) or (hi < 0),
                             passive_vs_harness_pct=100 * (P.mean() - H.mean()) / H.mean(),
                             active_vs_harness_pct=100 * (A.mean() - H.mean()) / H.mean(),
                             combined_vs_harness_pct=100 * (AP.mean() - H.mean()) / H.mean()))
inter = pd.DataFrame(rows); inter.round(3).to_csv(RES / "interaction_emg.csv", index=False)

# ---------------- 4. Torque summary and interaction ----------------
rows = []
for setup in ["Bench", "In vivo flexion", "In vivo abduction", "In vivo pooled"]:
    for c in TCOND:
        sel = tor[(tor.condition == c) & ((tor.setup == setup) if setup != "In vivo pooled" else (tor.test_type == "In vivo torque"))]
        mu, sd = msd(sel.torque_nm); rows.append(dict(setup=setup, condition=c, n=len(sel), mean_nm=mu, sd_nm=sd, cv_pct=100 * sd / mu))
pd.DataFrame(rows).round(3).to_csv(RES / "torque_summary.csv", index=False)
rows = []
for setup in ["Bench", "In vivo flexion", "In vivo abduction", "In vivo pooled"]:
    g = lambda c: tor[(tor.condition == c) & ((tor.setup == setup) if setup != "In vivo pooled" else (tor.test_type == "In vivo torque"))].torque_nm.to_numpy()
    I, se, d, lo, hi = welch_ci([g("Active+passive"), g("Active-only"), g("Passive-only")], [1, -1, -1])
    rows.append(dict(setup=setup, sum_of_parts_nm=g("Passive-only").mean() + g("Active-only").mean(), combined_nm=g("Active+passive").mean(),
                     I_nm=I, se=se, df=d, ci_low=lo, ci_high=hi, ci_excludes_zero=(lo > 0) or (hi < 0)))
pd.DataFrame(rows).round(3).to_csv(RES / "interaction_torque.csv", index=False)

# ---------------- 5. ROM summary ----------------
rows = []
for m in ROM_MOTIONS:
    for a in AXES:
        mu, sd = msd(rom[rom.motion == m][f"{a}_deg"]); rows.append(dict(motion=m, axis=a, n=10, mean_deg=mu, sd_deg=sd, cv_pct=100 * sd / mu))
rom_sum = pd.DataFrame(rows); rom_sum.round(3).to_csv(RES / "rom_summary.csv", index=False)

# ---------------- 6. Test-retest (Table 5, Figure 9, Supplementary Table S1) ----------------
pairs = []
for m in MOTIONS:
    for L in LOADS:
        for c in COND:
            sub = emg[(emg.motion == m) & (emg.load_lb == L) & (emg.condition == c)]
            for met, lab in [("emg_mean_counts", "Mean EMG (counts)"), ("emg_peak_counts", "Peak EMG (counts)")]:
                s1, s2 = sub[sub.session == 1][met].mean(), sub[sub.session == 2][met].mean()
                pairs.append(dict(measure=lab, motion=m, load_lb=L, condition=c, s1=s1, s2=s2))
for setup in ["Bench", "In vivo flexion", "In vivo abduction"]:
    for c in TCOND:
        sub = tor[(tor.setup == setup) & (tor.condition == c)]
        pairs.append(dict(measure="Torque (Nm)", motion=setup, load_lb="" if setup == "Bench" else 5, condition=c,
                          s1=sub[sub.session == 1].torque_nm.mean(), s2=sub[sub.session == 2].torque_nm.mean()))
for m in ROM_MOTIONS:
    for a in AXES:
        sub = rom[rom.motion == m]
        pairs.append(dict(measure="ROM (deg)", motion=m, load_lb="", condition=a,
                          s1=sub[sub.session == 1][f"{a}_deg"].mean(), s2=sub[sub.session == 2][f"{a}_deg"].mean()))
pairs = pd.DataFrame(pairs); pairs["diff_s2_minus_s1"] = pairs.s2 - pairs.s1
pairs["pct_diff_of_pair_mean"] = 100 * pairs.diff_s2_minus_s1 / ((pairs.s1 + pairs.s2) / 2)
pairs.rename(columns={"s1": "session1_mean", "s2": "session2_mean"}).round(3).to_csv(RES / "session_means_S1_vs_S2.csv", index=False)
tr_rows = []
for meas in ["Mean EMG (counts)", "Peak EMG (counts)", "Torque (Nm)", "ROM (deg)"]:
    p = pairs[pairs.measure == meas]; d = p.diff_s2_minus_s1.to_numpy(); pc = p.pct_diff_of_pair_mean.to_numpy()
    bias, sdd = d.mean(), d.std(ddof=1); pb, psd = pc.mean(), pc.std(ddof=1)
    tr_rows.append(dict(measure=meas, pairs=len(p), bias=bias, sd_diff=sdd, loa_low=bias - 1.96 * sdd, loa_high=bias + 1.96 * sdd,
                        bias_pct=pb, loa_low_pct=pb - 1.96 * psd, loa_high_pct=pb + 1.96 * psd,
                        pearson_r=np.corrcoef(p.s1, p.s2)[0, 1],
                        icc_3_1=icc31(p[["s1", "s2"]].to_numpy()), sem=sdd / np.sqrt(2), mdc95=1.96 * sdd))
tr = pd.DataFrame(tr_rows); tr.round(4).to_csv(RES / "test_retest_summary.csv", index=False)

# % reduction vs same-session baseline, replicated across sessions
rows = []
for m in MOTIONS:
    for L in LOADS:
        for c in COND[1:]:
            r = dict(motion=m, load_lb=L, condition=c)
            for met, lab in [("emg_mean_counts", "mean"), ("emg_peak_counts", "peak")]:
                for s in (1, 2):
                    b = emg[(emg.motion == m) & (emg.load_lb == L) & (emg.condition == "Baseline") & (emg.session == s)][met].mean()
                    x = emg[(emg.motion == m) & (emg.load_lb == L) & (emg.condition == c) & (emg.session == s)][met].mean()
                    r[f"{lab}_reduction_S{s}_pct"] = 100 * (b - x) / b
                r[f"{lab}_S2_minus_S1_pts"] = r[f"{lab}_reduction_S2_pct"] - r[f"{lab}_reduction_S1_pct"]
            rows.append(r)
rep = pd.DataFrame(rows); rep.round(2).to_csv(RES / "pct_reduction_replication.csv", index=False)

# ---------------- 7. Battery voltage ----------------
rows = []
for s in (1, 2):
    v = df[df.session == s].battery_v_after_trial
    rows.append(dict(session=s, n_readings=len(v), v_first=v.iloc[0], v_last=v.iloc[-1], v_max=v.max(), v_min=v.min()))
pd.DataFrame(rows).to_csv(RES / "battery_voltage_summary.csv", index=False)
rows = []
for setup in ["Bench", "In vivo flexion", "In vivo abduction"]:
    for c in TCOND:
        sub = tor[(tor.setup == setup) & (tor.condition == c)]
        lr = stats.linregress(sub.battery_v_after_trial, sub.torque_nm); t = stats.t.ppf(.975, len(sub) - 2)
        rows.append(dict(setup=setup, condition=c, n=len(sub), slope_nm_per_v=lr.slope, slope_ci_low=lr.slope - t * lr.stderr,
                         slope_ci_high=lr.slope + t * lr.stderr, r=lr.rvalue, p=lr.pvalue))
pd.DataFrame(rows).round(4).to_csv(RES / "torque_vs_battery_voltage.csv", index=False)

# ---------------- 8. LaTeX tables ----------------
def f1(x): return f"{x:.1f}"
L = ["% Generated by Analysis/analyze.py"]
for m, lab in [("Flexion", "tab:emg-flexion"), ("Abduction", "tab:emg-abduction")]:
    L.append(f"% ---- rows for Table {'2' if m=='Flexion' else '3'} ({lab}) ----")
    for Ld in LOADS:
        L.append(f"\\multirow{{5}}{{*}}{{{Ld}}}")
        for _, r in emg_sum[(emg_sum.motion == m) & (emg_sum.load_lb == Ld)].iterrows():
            rm = "---" if r.condition == "Baseline" else f1(r.pct_reduction_mean_vs_baseline)
            rp = "---" if r.condition == "Baseline" else f1(r.pct_reduction_peak_vs_baseline)
            name = r.condition.replace("-only", "-Only").replace("Active+passive", "Active+Passive")
            L.append(f" & {name:<14s} & {r.mean_emg:.0f}$\\pm${r.mean_sd:.0f} & {f1(r.mean_cv_pct)} & {r.peak_emg:.0f}$\\pm${r.peak_sd:.0f} & {f1(r.peak_cv_pct)} & {rm} & {rp} \\\\")
        L.append("\\hline")
L.append(r"""
% ---- Table 4 ----
\begin{table}[H]
\centering
\caption{Passive and active effects and the Passive $\times$ Active interaction with harness-only ($H$) as the factorial reference. Effects are percent change in EMG relative to $Y_H$ (negative = less muscle activity). $I = Y_{A+P} - Y_{A} - Y_{P} + Y_{H}$ in EMG counts with a 95\% Welch confidence interval ($n = 10$ trials per cell); $I = 0$ indicates additive effects and $I > 0$ indicates less reduction than the sum of the individual effects.}
\label{tab:interaction}
\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{l c l r r r r r c}
\hline
Motion & Load (lb) & Metric & $P$ vs $H$ (\%) & $A$ vs $H$ (\%) & $A{+}P$ vs $H$ (\%) & $I$ & $I$ (\% of $Y_H$) & 95\% CI of $I$ \\
\hline""")
for _, r in inter.iterrows():
    star = "$^*$" if r.ci_excludes_zero else ""
    L.append(f"{r.motion} & {r.load_lb} & {r.metric} & {r.passive_vs_harness_pct:.1f} & {r.active_vs_harness_pct:.1f} & {r.combined_vs_harness_pct:.1f} & {r.I_counts:+.1f} & {r.I_pct_of_harness:+.1f} & [{r.ci_low:.1f}, {r.ci_high:.1f}]{star} \\\\")
L.append(r"""\hline
\multicolumn{9}{l}{$^*$95\% CI excludes zero.}\\
\end{tabular}
\end{table}

% ---- Table 5 ----
\begin{table}[H]
\centering
\caption{Test-retest agreement between Session 1 (trials 1--5) and Session 2 (trials 6--10). Bias and limits of agreement (LoA) are Session 2 minus Session 1; percentage values use each pair's difference as a percentage of the pair mean. SEM = SD of differences$/\sqrt{2}$; MDC$_{95}$ = $1.96\sqrt{2}\,$SEM.}
\label{tab:test-retest}
\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{l c c c c c c c}
\hline
Measure & Pairs & Bias & 95\% LoA & 95\% LoA (\%) & Pearson $r$ & ICC(3,1) & SEM / MDC$_{95}$ \\
\hline""")
fmt = {"Mean EMG (counts)": "{:.1f}", "Peak EMG (counts)": "{:.1f}", "Torque (Nm)": "{:.3f}", "ROM (deg)": "{:.2f}"}
for _, r in tr.iterrows():
    f = fmt[r.measure].format; nm = r.measure.replace("(deg)", "(\\textdegree{})")
    r4 = lambda x: f"{x:.4f}" if x > 0.9995 else f"{x:.3f}"
    L.append(f"{nm} & {r.pairs} & {'+' if r.bias >= 0 else ''}{f(r.bias)} & [{f(r.loa_low)}, {f(r.loa_high)}] & [{r.loa_low_pct:.1f}, {r.loa_high_pct:+.1f}] & {r4(r.pearson_r)} & {r4(r.icc_3_1)} & {f(r["sem"])} / {f(r["mdc95"])} \\\\")
L.append("\\hline\n\\end{tabular}\n\\end{table}\n")
(RES / "latex_tables.tex").write_text("\n".join(L))

# ---------------- 9. Figures ----------------
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]; INK = "#0b0b0b"; INK2 = "#52514e"; GRID = "#e4e3df"
plt.rcParams.update({"font.family": "serif", "font.serif": ["Nimbus Roman", "Times New Roman", "DejaVu Serif"], "font.size": 10,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False,
                     "pdf.fonttype": 42, "savefig.dpi": 300})
ERR = dict(ecolor=INK, elinewidth=0.8, capsize=2.5, capthick=0.8)
rng = np.random.default_rng(0)
def save(fig, name):
    # PNG for the repository; PDF (vector) for the manuscript
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight"); plt.close(fig)
def jitter(ax, x, vals, w):
    ax.scatter(x + rng.uniform(-w, w, len(vals)), vals, s=7, color=INK, alpha=0.55, linewidths=0, zorder=4)

# Figure 6: torque
fig, ax = plt.subplots(figsize=(6.5, 3.6)); x = np.arange(3); w = 0.36
for off, sel, col, lab in [(-w / 2, tor.test_type == "Bench torque", C[0], "Bench (n = 10)"),
                           (w / 2, tor.test_type == "In vivo torque", C[1], "In vivo, flexion + abduction (n = 20)")]:
    data = [tor[sel & (tor.condition == c)].torque_nm.to_numpy() for c in TCOND]
    m = [d.mean() for d in data]; s = [d.std(ddof=1) for d in data]
    ax.bar(x + off, m, w * 0.94, color=col, yerr=s, error_kw=ERR, label=lab, edgecolor="white", linewidth=1)
    for xi, d, mi in zip(x + off, data, m):
        jitter(ax, xi, d, w * 0.25); ax.text(xi, max(mi + d.std(ddof=1), d.max()) + 0.06, f"{mi:.2f}", ha="center", va="bottom", fontsize=8, color=INK)
ax.set_xticks(x, ["Passive-Only", "Active-Only", "Active+Passive"]); ax.set_ylabel("Torque (Nm)"); ax.set_xlabel("Assistance condition")
ax.set_ylim(0, 3.8); ax.legend(loc="upper left"); save(fig, "Torque Data")

# Figure 7: ROM Euler angles
fig, ax = plt.subplots(figsize=(6.5, 3.6)); x = np.arange(3); w = 0.27
for k, a in enumerate(AXES):
    data = [rom[rom.motion == m][f"{a}_deg"].to_numpy() for m in ROM_MOTIONS]; m_ = [d.mean() for d in data]; s_ = [d.std(ddof=1) for d in data]
    xs = x + (k - 1) * w
    ax.bar(xs, m_, w * 0.94, color=C[k], yerr=s_, error_kw=ERR, label=f"{a.capitalize()} (°)", edgecolor="white", linewidth=1)
    for xi, d, mi in zip(xs, data, m_):
        jitter(ax, xi, d, w * 0.22); ax.text(xi, max(mi + d.std(ddof=1), d.max()) + 2, f"{mi:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
ax.set_xticks(x, ["Flexion", "Abduction", "Horizontal Adduction"]); ax.set_ylabel("Maximum Euler angle (°)"); ax.set_xlabel("Motion")
ax.set_ylim(0, 215); ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.12)); save(fig, "Euler Angles")

# Figure 8: EMG
order = ["Baseline", "Harness-only", "Passive-only", "Active-only", "Active+passive"]
fig, axs = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True)
groups = [(Ld, kind) for Ld in LOADS for kind in ("Mean", "Peak")]; w = 0.16
for ax, m, lab in zip(axs, MOTIONS, ["a) Flexion", "b) Abduction"]):
    x = np.arange(len(groups))
    for k, c in enumerate(order):
        r = [emg_sum[(emg_sum.motion == m) & (emg_sum.load_lb == Ld) & (emg_sum.condition == c)].iloc[0] for Ld, _ in groups]
        mv = [ri.mean_emg if kind == "Mean" else ri.peak_emg for ri, (_, kind) in zip(r, groups)]
        sv = [ri.mean_sd if kind == "Mean" else ri.peak_sd for ri, (_, kind) in zip(r, groups)]
        ax.bar(x + (k - 2) * w, mv, w * 0.92, yerr=sv, error_kw=dict(ERR, capsize=1.5, elinewidth=0.6, capthick=0.6), color=C[k],
               label=c.replace("-only", "-Only").replace("Active+passive", "Active+Passive"), edgecolor="white", linewidth=0.6)
    ax.set_xticks(x, [f"{Ld} lb {kind}" for Ld, kind in groups], fontsize=9); ax.set_title(lab, loc="left", fontsize=11, color=INK)
    ax.set_xlabel("Load and EMG metric")
axs[0].set_ylabel("EMG (MyoWare envelope, ADC counts)"); axs[0].set_ylim(0, 720)
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.06))
fig.tight_layout(); save(fig, "EMG Data")

# Figure 9: Bland-Altman
fig, axs = plt.subplots(2, 2, figsize=(8, 6.2))
for ax, (meas, title, xl) in zip(axs.flat, [("Mean EMG (counts)", "Mean EMG (30 trial types)", "Mean of sessions (counts)"),
                                           ("Peak EMG (counts)", "Peak EMG (30 trial types)", "Mean of sessions (counts)"),
                                           ("Torque (Nm)", "Torque (9 trial types)", "Mean of sessions (Nm)"),
                                           ("ROM (deg)", "ROM (9 measures)", "Mean of sessions (°)")]):
    p = pairs[pairs.measure == meas]; r = tr[tr.measure == meas].iloc[0]
    ax.scatter((p.s1 + p.s2) / 2, p.pct_diff_of_pair_mean, s=18, color=C[0], edgecolors="white", linewidths=0.8, zorder=6)
    ax.axhline(0, color=GRID, lw=0.8); ax.axhline(r.bias_pct, color=INK, lw=1.2)
    ax.axhline(r.loa_low_pct, color=INK2, lw=1, ls="--"); ax.axhline(r.loa_high_pct, color=INK2, lw=1, ls="--")
    xmax = ax.get_xlim()[1]
    for yv, t in [(r.bias_pct, f"Bias {r.bias_pct:+.1f}%"), (r.loa_high_pct, f"Upper LoA {r.loa_high_pct:+.1f}%"), (r.loa_low_pct, f"Lower LoA {r.loa_low_pct:+.1f}%")]:
        ax.text(xmax, yv, t.replace("-", "\u2212"), ha="right", va="bottom", fontsize=8, color=INK, bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.85), zorder=5)
    icc = f"{r.icc_3_1:.4f}" if r.icc_3_1 > 0.9995 else f"{r.icc_3_1:.3f}"
    ax.set_title(f"{title}   ICC(3,1) = {icc}", loc="left", fontsize=9.5, color=INK)
    ax.set_xlabel(xl, fontsize=9); ax.set_ylabel("Session 2 − Session 1 (% of mean)", fontsize=9)
    lim = max(abs(p.pct_diff_of_pair_mean).max(), abs(r.loa_low_pct), abs(r.loa_high_pct)) * 1.25; ax.set_ylim(-lim, lim)
fig.tight_layout(); save(fig, "Test-Retest Bland-Altman")
print("Done. Results ->", RES, " Figures ->", FIG)

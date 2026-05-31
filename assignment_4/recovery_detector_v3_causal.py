# -*- coding: utf-8 -*-
"""
Recovery Detector v3 - VERSIONE COMPLETAMENTE CAUSALE
======================================================
Differenza chiave rispetto al v2: TUTTE le soglie sono calcolate in modo expanding,
cioe' per ogni settimana t la soglia qX e' il quantile sui soli score osservati
fino a t-1. Nessun look-ahead nelle decisioni operative.

Cosi' i numeri sono direttamente confrontabili con quelli del notebook centrale
e valgono per una versione deployment-ready.

Test ridotto a 4 configurazioni candidate (le migliori del v2).
"""

import time
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score

t0 = time.time()

# =============================================================
# 1-3. Stesso setup del v2 (omesso dettagli per brevita')
# =============================================================
XLSX = 'Dataset4_EWS.xlsx'
data_df = pd.read_excel(XLSX, sheet_name='Markets')
date_col = data_df.columns[0]
data_df[date_col] = pd.to_datetime(data_df[date_col], dayfirst=True)
data_df = data_df.set_index(date_col)
y_full = data_df['Y'].values
X_df = data_df.drop('Y', axis=1)

indices_currencies = ['XAUBGNL', 'BDIY', 'CRY', 'Cl1', 'DXY', 'EMUSTRUU', 'GBP', 'JPY',
                     'LF94TRUU', 'LF98TRUU', 'LG30TRUU', 'LMBITR', 'LP01TREU', 'LUACTRUU',
                     'LUMSTRUU', 'MXBR', 'MXCN', 'MXEU', 'MXIN', 'MXJP', 'MXRU', 'MXUS', 'VIX']
interest_rates = ['EONIA', 'GTDEM10Y', 'GTDEM2Y', 'GTDEM30Y', 'GTGBP20Y', 'GTGBP2Y',
                  'GTGBP30Y', 'GTITL10YR', 'GTITL2YR', 'GTITL30YR', 'GTJPY10YR',
                  'GTJPY2YR', 'GTJPY30YR', 'US0001M', 'USGG3M', 'USGG2YR', 'GT10', 'USGG30YR']
stationary_df = pd.DataFrame(index=X_df.index[1:])
for col in indices_currencies:
    if col in X_df.columns:
        stationary_df[col] = np.diff(np.log(X_df[col]))
for col in interest_rates:
    if col in X_df.columns:
        stationary_df[col] = np.diff(X_df[col])
if 'ECSURPUS' in X_df.columns:
    stationary_df['ECSURPUS'] = X_df['ECSURPUS'].values[1:]
y_stationary = y_full[1:]

H = 4
idx = stationary_df.index
y_now = pd.Series(np.asarray(y_stationary), index=idx)
yv = y_now.values
y_ahead_full = np.array([1 if yv[t+1:t+1+H].any() else 0 for t in range(len(yv))])

eq_cols = [c for c in ['MXUS','MXEU','MXJP','MXBR','MXCN','MXIN','MXRU'] if c in stationary_df.columns]
P_crisis = pd.DataFrame(index=idx)
P_crisis['accel_volatilita'] = stationary_df['MXUS'].rolling(4).std() - stationary_df['MXUS'].rolling(12).std()
W = 13
eqr = stationary_df[eq_cols].values
avg_corr = np.full(len(idx), np.nan)
for t in range(W, len(idx)):
    C = np.corrcoef(eqr[t-W:t], rowvar=False)
    iu = np.triu_indices_from(C, 1)
    avg_corr[t] = np.nanmean(C[iu])
P_crisis['correlazione_media'] = avg_corr
P_crisis['tensione_credito'] = -stationary_df['LF98TRUU'].rolling(4).mean()
P_crisis['slancio_vix']      = stationary_df['VIX'].rolling(4).mean()
P_crisis['livello_vix']      = X_df['VIX'].reindex(idx)
P_crisis['pendenza_tassi']   = (X_df['GT10'] - X_df['USGG3M']).reindex(idx)
lvl = X_df['MXUS'].reindex(idx)
drawdown = lvl / lvl.cummax() - 1
P_crisis['velocita_drawdown'] = drawdown.diff(4)
P_crisis['slancio_baltic']   = -stationary_df['BDIY'].rolling(8).mean()
P_crisis['sorpresa_econ']    = -X_df['ECSURPUS'].reindex(idx).rolling(4).mean()

# Feature extra per recovery
P_rec_only = pd.DataFrame(index=idx)
P_rec_only['dd_level'] = drawdown
in_dd = (drawdown < -0.10).astype(int).values
streak = np.zeros(len(idx))
for t in range(len(idx)):
    streak[t] = streak[t-1] + 1 if t > 0 and in_dd[t] == 1 else (1 if in_dd[t] == 1 else 0)
P_rec_only['weeks_in_dd'] = streak
vix = X_df['VIX'].reindex(idx)
vix_max12 = vix.rolling(12).max()
P_rec_only['vix_off_peak'] = (vix_max12 - vix) / (vix_max12 + 1e-9)
P_rec_only['momentum_4w'] = stationary_df['MXUS'].rolling(4).sum()
P_rec_only['vol_declining'] = stationary_df['MXUS'].rolling(4).std() - stationary_df['MXUS'].rolling(12).std()
P_rec_only['credit_recovery'] = stationary_df['LF98TRUU'].rolling(4).mean()

# =============================================================
# 4. Walk-forward + helper causali
# =============================================================
START, STEP = 200, 12

P_extended = P_crisis.join(P_rec_only, how='inner').dropna()
MAX_H = 12
P_extended_full = P_extended.iloc[:-MAX_H].copy()
y_ahead_aligned = pd.Series(y_ahead_full, index=idx).reindex(P_extended_full.index).values
P_crisis_aligned = P_crisis.reindex(P_extended_full.index).dropna()
P_extended_full = P_extended_full.loc[P_crisis_aligned.index]
y_ahead_aligned = pd.Series(y_ahead_full, index=idx).reindex(P_crisis_aligned.index).values.astype(int)

mxus_ret = X_df['MXUS'].reindex(P_crisis_aligned.index).pct_change().fillna(0).values
log_lvl = np.log(X_df['MXUS'].reindex(P_crisis_aligned.index).values)

def walk_forward(P_data, y_target, start=START, step=STEP):
    Xv = P_data.values
    s = np.full(len(P_data), np.nan); m = None
    for t in range(start, len(P_data)):
        if (t - start) % step == 0:
            m = make_pipeline(StandardScaler(),
                              LogisticRegression(class_weight='balanced', max_iter=1000))
            m.fit(Xv[:t], y_target[:t])
        s[t] = m.predict_proba(Xv[t:t+1])[:, 1][0]
    return s

def make_y_recovery_aligned(H_rec, thr_rec):
    """y_recovery sull'index di P_crisis_aligned."""
    y = np.full(len(P_crisis_aligned), np.nan)
    for t in range(len(P_crisis_aligned) - H_rec):
        y[t] = 1.0 if (log_lvl[t + H_rec] - log_lvl[t]) > thr_rec else 0.0
    return y

def stats(r, ppy=52):
    if len(r) < 2 or r.std() < 1e-12:
        return dict(CAGR=0.0, Vol=0.0, Sharpe=np.nan, MaxDD=0.0, Calmar=np.nan)
    eq = np.cumprod(1 + r)
    cagr = float(eq[-1]**(ppy/len(r)) - 1) if eq[-1] > 0 else -1.0
    vol = float(r.std() * np.sqrt(ppy))
    sh = float(r.mean()*ppy / (r.std()*np.sqrt(ppy) + 1e-9))
    mdd = float((eq / np.maximum.accumulate(eq) - 1).min())
    calmar = cagr / abs(mdd) if abs(mdd) > 1e-9 else np.nan
    return dict(CAGR=cagr, Vol=vol, Sharpe=sh, MaxDD=mdd, Calmar=calmar)

# =============================================================
# 5. *** CRUCIALE: Double Confirm CAUSALE ***
#    Per ogni settimana t, le soglie sono il quantile dei soli score
#    osservati FINO A t-1 (escluso lo score di t stesso).
# =============================================================
def double_confirm_causal(score_A, score_B, qA_out=0.70, qB_in=0.60,
                           qA_in=0.60, qB_out=0.40, warmup=50):
    """
    Soglie EXPANDING CAUSALI: per ogni t, quantile sugli score validi fino a t-1.
    Warmup di 50 punti (prima dello startup non e' possibile stimare quantili
    affidabili -> resti nello stato iniziale).
    """
    n = len(score_A)
    pos = np.full(n, 1.0)
    state = 1
    sA_valid_so_far = []
    sB_valid_so_far = []
    for t in range(n):
        # Accumula gli score validi PRIMA di t (causale stretto)
        # NB: l'aggiornamento avviene DOPO la decisione su t
        if np.isnan(score_A[t]) or np.isnan(score_B[t]):
            pos[t] = state
            continue
        if len(sA_valid_so_far) < warmup:
            # Warmup: aggiungi senza decidere
            sA_valid_so_far.append(score_A[t])
            sB_valid_so_far.append(score_B[t])
            pos[t] = state
            continue
        # Quantili sugli score osservati FINO A t-1 (= sA_valid_so_far, prima dell'append)
        sA_arr = np.array(sA_valid_so_far)
        sB_arr = np.array(sB_valid_so_far)
        qA_out_v = np.quantile(sA_arr, qA_out)
        qA_in_v  = np.quantile(sA_arr, qA_in)
        qB_in_v  = np.quantile(sB_arr, qB_in)
        qB_out_v = np.quantile(sB_arr, qB_out)
        if state == 1:
            if score_A[t] > qA_out_v and score_B[t] < qB_out_v:
                state = 0
        else:
            if score_B[t] > qB_in_v and score_A[t] < qA_in_v:
                state = 1
        pos[t] = state
        # Ora aggiorna lo storico per t+1
        sA_valid_so_far.append(score_A[t])
        sB_valid_so_far.append(score_B[t])
    return pos

def single_threshold_causal(score, q_out=0.70, warmup=50):
    """Strategia A-only con soglia expanding (per riferimento)."""
    n = len(score)
    pos = np.full(n, 1.0)
    s_valid = []
    state = 1
    for t in range(n):
        if np.isnan(score[t]):
            pos[t] = state; continue
        if len(s_valid) < warmup:
            s_valid.append(score[t]); pos[t] = state; continue
        q_v = np.quantile(np.array(s_valid), q_out)
        state = 0 if score[t] > q_v else 1
        pos[t] = state
        s_valid.append(score[t])
    return pos

def backtest(pos, mask):
    pos_lag = np.concatenate([[1.0], pos[:-1]])
    ret = mxus_ret * pos_lag
    rv = ret[mask]
    pv = pos_lag[mask]
    s = stats(rv)
    n_switch = int((np.abs(np.diff(pv)) > 1e-6).sum())
    pct_cash = float((1 - pv).mean() * 100)
    return s, n_switch, pct_cash

# =============================================================
# 6. Train Modello A (1 volta) + 4 config di B
# =============================================================
print(f"[{time.time()-t0:5.1f}s] Train Modello A (crisi)...")
score_A = walk_forward(P_crisis_aligned, y_ahead_aligned)
mask_A = ~np.isnan(score_A)
pr_A = average_precision_score(y_ahead_aligned[mask_A], score_A[mask_A])
print(f"            PR-AUC Modello A = {pr_A:.4f}\n")

CONFIGS = [
    (6, 0.04, 'extended'),    # best CAGR in v2 in-sample
    (6, 0.05, 'extended'),    # secondo
    (4, 0.03, 'original'),    # best Calmar in v2 in-sample
    (8, 0.04, 'extended'),    # alta PR-AUC modello B
]

print(f"[{time.time()-t0:5.1f}s] Confronto causale (soglie expanding):")
print(f"  Riferimenti causali:")
s_bh = stats(mxus_ret[mask_A])
print(f"    Buy & Hold:           CAGR {s_bh['CAGR']*100:>5.2f}%  MaxDD {s_bh['MaxDD']*100:>6.2f}%  Calmar {s_bh['Calmar']:>5.3f}")
pos_A_only = single_threshold_causal(score_A, q_out=0.70, warmup=50)
s_A, n_A, c_A = backtest(pos_A_only, mask_A)
print(f"    S1 A-only (q70 caus): CAGR {s_A['CAGR']*100:>5.2f}%  MaxDD {s_A['MaxDD']*100:>6.2f}%  Calmar {s_A['Calmar']:>5.3f}  Cash {c_A:.1f}%  Switch {n_A}")

print(f"\n{'Config (H, THR, feat)':<30s} {'PR-B':>6s}  | {'CAGR':>5s}  {'MaxDD':>6s}  {'Calmar':>6s}  {'Cash':>5s}  {'Switch':>5s}")
results = []
for H_rec, thr_rec, feat_set in CONFIGS:
    # Target
    y_rec = make_y_recovery_aligned(H_rec, thr_rec)
    y_rec_clean = np.where(np.isnan(y_rec), 0, y_rec).astype(int)
    # Feature set
    P_B = P_extended_full if feat_set == 'extended' else P_crisis_aligned
    # Train B
    score_B = walk_forward(P_B, y_rec_clean)
    # PR-AUC
    mask_pr = ~np.isnan(score_B) & ~np.isnan(y_rec)
    pr_B = average_precision_score(y_rec[mask_pr].astype(int), score_B[mask_pr])
    # Strategy CAUSALE
    pos = double_confirm_causal(score_A, score_B, warmup=50)
    s, n_sw, pct_cash = backtest(pos, mask_A)
    results.append((H_rec, thr_rec, feat_set, pr_B, s, n_sw, pct_cash, pos, score_B))
    print(f"{'H='+str(H_rec)+', THR='+str(thr_rec)+', '+feat_set:<30s} {pr_B:>6.4f}  | "
          f"{s['CAGR']*100:>5.2f}%  {s['MaxDD']*100:>6.2f}%  {s['Calmar']:>6.3f}  "
          f"{pct_cash:>4.1f}%  {n_sw:>5d}")

# =============================================================
# 7. Diagnostica delle 3 crisi col vincitore CAGR
# =============================================================
best = max(results, key=lambda r: r[4]['CAGR'])
H_w, THR_w, feat_w, pr_B_w, s_w, n_sw_w, c_w, pos_w, _ = best
print(f"\n[{time.time()-t0:5.1f}s] Vincitore CAGR causale: H={H_w}, THR={THR_w}, feat={feat_w}")
print(f"  CAGR {s_w['CAGR']*100:.2f}% vs B&H {s_bh['CAGR']*100:.2f}%  (delta {(s_w['CAGR']-s_bh['CAGR'])*100:+.2f} pti)")
print(f"  MaxDD {s_w['MaxDD']*100:.2f}% vs B&H {s_bh['MaxDD']*100:.2f}%  (riduzione {-(s_w['MaxDD']-s_bh['MaxDD'])*100:.1f} pti)")
print(f"  Calmar {s_w['Calmar']:.3f} vs B&H {s_bh['Calmar']:.3f}  ({s_w['Calmar']/s_bh['Calmar']:.2f}x)")

crises = {
    '2008': ('2007-06-01', '2009-06-30'),
    '2011': ('2011-01-01', '2012-09-30'),
    '2020': ('2020-01-01', '2020-08-31'),
}
print(f"\nDiagnostica 3 crisi (causale):")
for label, (a, b) in crises.items():
    win = (P_crisis_aligned.index >= pd.Timestamp(a)) & (P_crisis_aligned.index <= pd.Timestamp(b))
    if not win.any(): continue
    ret_w_ = mxus_ret[win]
    pl = np.concatenate([[1.0], pos_w[:-1]])[win]
    r_strategy = ret_w_ * pl
    print(f"  {label}: B&H rend={np.prod(1+ret_w_)-1:+7.2%} DD={stats(ret_w_)['MaxDD']:+7.2%}  | "
          f"Strategy rend={np.prod(1+r_strategy)-1:+7.2%} DD={stats(r_strategy)['MaxDD']:+7.2%}  "
          f"Cash={(1-pl).mean()*100:.1f}%")

# =============================================================
# 8. Costi di transazione 10 bp
# =============================================================
print(f"\n[{time.time()-t0:5.1f}s] Con TC 10bp/switch:")
for H_rec, thr_rec, feat_set, pr_B, s, n_sw, _, pos, _ in results:
    pos_lag = np.concatenate([[1.0], pos[:-1]])
    changes = np.concatenate([[0.0], np.abs(np.diff(pos_lag))])
    ret_tc = mxus_ret * pos_lag - changes * 10 / 10000.0
    s_tc = stats(ret_tc[mask_A])
    print(f"  H={H_rec}, THR={thr_rec}, {feat_set:<10s}: CAGR {s_tc['CAGR']*100:>5.2f}% (delta vs no-TC {(s_tc['CAGR']-s['CAGR'])*100:+.2f})  MaxDD {s_tc['MaxDD']*100:>6.2f}%  Calmar {s_tc['Calmar']:>5.3f}")

print(f"\n[{time.time()-t0:5.1f}s] Fine.")

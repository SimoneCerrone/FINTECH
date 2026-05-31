# -*- coding: utf-8 -*-
"""
Recovery Detector v2 — Grid search target + feature dedicate
============================================================
Hp di lavoro: il problema del v1 e' che le 9 feature di Vitto sono ottimizzate
per "crisi in arrivo", quindi al fondo di un crash dicono "crisi grave" e il
recovery detector usa quei segnali ribaltati - male.

In questa versione:
  1. Grid search su (H_REC, THR_REC) per trovare il target migliore
  2. Aggiungiamo feature dedicate al recovery (P_extended):
     - dd_level         : drawdown corrente (gia' rolling, livello assoluto)
     - weeks_in_dd      : settimane consecutive con drawdown < -10%
     - vix_off_peak     : (VIX recent peak - VIX current) / peak
     - momentum_4w      : log-return MXUS rolling 4 settimane
     - vol_declining    : indicator se la vol e' in calo
  3. Backtest S3 Double Confirm per ogni combinazione
"""

import time, itertools
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score

t0 = time.time()

# =============================================================
# 1-3. (Identico al v1) Caricamento, stationarity, 9 precursori
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

# =============================================================
# 4. NUOVE feature dedicate al recovery
# =============================================================
P_rec_only = pd.DataFrame(index=idx)

# dd_level: profondita' del drawdown corrente (negativo, piu' negativo = piu' giu')
P_rec_only['dd_level'] = drawdown

# weeks_in_dd: numero di settimane consecutive con drawdown < -10%
in_dd = (drawdown < -0.10).astype(int).values
streak = np.zeros(len(idx))
for t in range(len(idx)):
    streak[t] = streak[t-1] + 1 if t > 0 and in_dd[t] == 1 else (1 if in_dd[t] == 1 else 0)
P_rec_only['weeks_in_dd'] = streak

# vix_off_peak: quanto siamo lontani dal picco recente di VIX (12 settimane)
vix = X_df['VIX'].reindex(idx)
vix_max12 = vix.rolling(12).max()
P_rec_only['vix_off_peak'] = (vix_max12 - vix) / (vix_max12 + 1e-9)

# momentum_4w: log-return MXUS 4 settimane (segnale di bottom)
P_rec_only['momentum_4w'] = stationary_df['MXUS'].rolling(4).sum()

# vol_declining: vol 4-sett MENO vol 12-sett (negativo = vol in calo = stabilizzazione)
P_rec_only['vol_declining'] = stationary_df['MXUS'].rolling(4).std() - stationary_df['MXUS'].rolling(12).std()
# = -accel_volatilita (e' la stessa di P_crisis con segno flippato per renderla pos-recovery)
# OK lasciamo, e' ridondante ma non fa male

# credit_spread_decline: high yield in ripresa (segno opposto a tensione_credito)
P_rec_only['credit_recovery'] = stationary_df['LF98TRUU'].rolling(4).mean()

# =============================================================
# 5. Setup walk-forward comune
# =============================================================
START, STEP = 200, 12
mxus_ret = X_df['MXUS'].reindex(idx).pct_change().fillna(0).values
log_lvl = np.log(X_df['MXUS'].reindex(idx).values)

def make_y_recovery(H_rec, thr_rec):
    """Costruisce y_recovery con orizzonte H_rec e soglia THR_rec (log-return forward)."""
    y = np.full(len(idx), np.nan)
    for t in range(len(idx) - H_rec):
        y[t] = 1.0 if (log_lvl[t + H_rec] - log_lvl[t]) > thr_rec else 0.0
    return y

def walk_forward(P_data, y_target, start=START, step=STEP):
    """Walk-forward Logistica."""
    Xv = P_data.values
    s = np.full(len(P_data), np.nan); m = None
    for t in range(start, len(P_data)):
        if (t - start) % step == 0:
            m = make_pipeline(StandardScaler(),
                              LogisticRegression(class_weight='balanced', max_iter=1000))
            m.fit(Xv[:t], y_target[:t])
        s[t] = m.predict_proba(Xv[t:t+1])[:, 1][0]
    return s

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

def double_confirm(score_A, score_B, qA_out=0.70, qB_in=0.60, qA_in=0.60, qB_out=0.40):
    """Strategia Double Confirm con soglie parametriche."""
    qA_out_v = np.nanquantile(score_A, qA_out)
    qA_in_v  = np.nanquantile(score_A, qA_in)
    qB_in_v  = np.nanquantile(score_B, qB_in)
    qB_out_v = np.nanquantile(score_B, qB_out)
    pos = np.full(len(score_A), 1.0)
    state = 1
    for t in range(len(score_A)):
        if np.isnan(score_A[t]) or np.isnan(score_B[t]):
            pos[t] = state; continue
        if state == 1:
            if score_A[t] > qA_out_v and score_B[t] < qB_out_v:
                state = 0
        else:
            if score_B[t] > qB_in_v and score_A[t] < qA_in_v:
                state = 1
        pos[t] = state
    return pos

def backtest(pos, score_A, score_B, mxus_ret):
    pos_lag = np.concatenate([[1.0], pos[:-1]])
    ret = mxus_ret * pos_lag
    mask = ~np.isnan(score_A) & ~np.isnan(score_B)
    rv = ret[mask]
    pv = pos_lag[mask]
    s = stats(rv)
    n_switch = int((np.abs(np.diff(pv)) > 1e-6).sum())
    pct_cash = float((1 - pv).mean() * 100)
    return s, n_switch, pct_cash

# =============================================================
# 6. Allineamento (P_crisis + P_rec_only -> P_extended)
# =============================================================
# y_recovery dipende da H_REC, lo costruiremo nel loop. Per ora alligno P
P_extended = P_crisis.join(P_rec_only, how='inner').dropna()

# Allineamento finale con un last_full ampio per safety
y_ahead = pd.Series(y_ahead_full, index=idx).reindex(P_extended.index).values

# Trimming per il piu' grande H tra ahead e recovery
MAX_H = 12   # massimo H_REC che testeremo
P_extended_full = P_extended.iloc[:-MAX_H].copy()
y_ahead_full_aligned = y_ahead[:-MAX_H].astype(int)

print(f"[{time.time()-t0:5.1f}s] Setup pronto. P_extended: {P_extended_full.shape}")
print(f"            Colonne extra recovery: {list(P_rec_only.columns)}\n")

# =============================================================
# 7. Train Modello A (crisi) UNA SOLA VOLTA (non dipende dal grid)
# =============================================================
# Modello A sui 9 precursori originali (per coerenza col notebook centrale)
P_crisis_aligned = P_crisis.reindex(P_extended_full.index).dropna()
# Ri-allineo y_ahead a P_crisis_aligned
y_ahead_A = pd.Series(y_ahead_full_aligned, index=P_extended_full.index).reindex(P_crisis_aligned.index).values
# P_extended_full e P_crisis_aligned devono avere stesso index
P_extended_full = P_extended_full.loc[P_crisis_aligned.index]
y_ahead_full_aligned = y_ahead_A

# Allineiamo mxus_ret a P_crisis_aligned.index (usato sia dal grid che dalla diagnostica)
mxus_ret_aligned = X_df['MXUS'].reindex(P_crisis_aligned.index).pct_change().fillna(0).values

print(f"[{time.time()-t0:5.1f}s] Train Modello A (crisi, 9 precursori)...")
score_A = walk_forward(P_crisis_aligned, y_ahead_full_aligned)
pr_A = average_precision_score(y_ahead_full_aligned[~np.isnan(score_A)],
                                score_A[~np.isnan(score_A)])
print(f"            PR-AUC Modello A = {pr_A:.4f}")

# =============================================================
# 8. Grid search su Modello B (recovery)
# =============================================================
print(f"\n[{time.time()-t0:5.1f}s] Grid search Modello B (recovery target):")
print(f"{'H_rec':>5}  {'THR':>5}  {'feat_set':>10}  {'PR-AUC':>7}  {'prev':>5}  | "
      f"{'CAGR':>6}  {'MaxDD':>7}  {'Calmar':>6}  {'Cash':>5}  {'Switch':>5}")

H_REC_GRID = [4, 6, 8]
THR_GRID   = [0.03, 0.04, 0.05]
FEATS_GRID = ['original', 'extended']

results = []
for H_rec, thr_rec, feat_set in itertools.product(H_REC_GRID, THR_GRID, FEATS_GRID):
    # Costruisci target
    y_rec_full = make_y_recovery(H_rec, thr_rec)
    y_rec = pd.Series(y_rec_full, index=idx).reindex(P_extended_full.index).values
    if np.isnan(y_rec).any():
        # Trimmo settimane finali dove target non e' definito
        valid_y = ~np.isnan(y_rec)
        if valid_y.sum() < 500:
            continue
    y_rec_clean = y_rec.copy()
    # Per il walk_forward serve un target finito ovunque -> riempio NaN con 0 (al training non li usa comunque oltre t)
    y_rec_clean = np.where(np.isnan(y_rec_clean), 0, y_rec_clean).astype(int)

    # Scegli feature set
    if feat_set == 'original':
        P_B = P_crisis_aligned
    else:
        P_B = P_extended_full

    # Train B
    score_B = walk_forward(P_B, y_rec_clean)

    # Metriche
    mask = ~np.isnan(score_A) & ~np.isnan(score_B) & ~np.isnan(y_rec_full[:len(score_B)] if False else y_rec)
    # Piu' semplice: maschera per PR-AUC -> dove sia y_rec sia score_B sono validi
    mask_pr = ~np.isnan(score_B) & ~np.isnan(y_rec)
    pr_B = average_precision_score(y_rec[mask_pr].astype(int), score_B[mask_pr])
    prev = y_rec[mask_pr].mean()

    # Backtest S3 Double Confirm
    pos = double_confirm(score_A, score_B)
    s, n_sw, pct_cash = backtest(pos, score_A, score_B, mxus_ret_aligned)
    results.append((H_rec, thr_rec, feat_set, pr_B, prev, s, n_sw, pct_cash))

    print(f"{H_rec:>5}  {thr_rec:>5.2f}  {feat_set:>10}  {pr_B:>7.4f}  {prev:>5.3f}  | "
          f"{s['CAGR']*100:>5.2f}%  {s['MaxDD']*100:>6.2f}%  {s['Calmar']:>6.3f}  "
          f"{pct_cash:>4.1f}%  {n_sw:>5d}")

# =============================================================
# 9. Identifica vincitore + B&H come riferimento
# =============================================================
print(f"\n[{time.time()-t0:5.1f}s] Riferimenti:")
mask_global = ~np.isnan(score_A)
s_bh = stats(mxus_ret_aligned[mask_global])
print(f"  Buy & Hold: CAGR={s_bh['CAGR']*100:.2f}%  "
      f"MaxDD={s_bh['MaxDD']*100:.2f}%  "
      f"Calmar={s_bh['Calmar']:.3f}")
print(f"  S1 Original baseline (no recovery detector): ~CAGR 3.15% MaxDD -19.75% Calmar 0.160")

# Trova migliore per CAGR e per Calmar
best_cagr = max(results, key=lambda r: r[5]['CAGR'])
best_calm = max(results, key=lambda r: r[5]['Calmar'] if not np.isnan(r[5]['Calmar']) else -np.inf)
print(f"\nMigliore per CAGR:   H_rec={best_cagr[0]}, THR={best_cagr[1]:.2f}, feat={best_cagr[2]}  "
      f"-> CAGR={best_cagr[5]['CAGR']*100:.2f}%, MaxDD={best_cagr[5]['MaxDD']*100:.2f}%, "
      f"Calmar={best_cagr[5]['Calmar']:.3f}")
print(f"Migliore per Calmar: H_rec={best_calm[0]}, THR={best_calm[1]:.2f}, feat={best_calm[2]}  "
      f"-> CAGR={best_calm[5]['CAGR']*100:.2f}%, MaxDD={best_calm[5]['MaxDD']*100:.2f}%, "
      f"Calmar={best_calm[5]['Calmar']:.3f}")

# =============================================================
# 10. Diagnostica delle 3 crisi col vincitore Calmar
# =============================================================
H_w, THR_w, feat_w, _, _, _, _, _ = best_calm
print(f"\n[{time.time()-t0:5.1f}s] Diagnostica col config vincente (Calmar): "
      f"H={H_w}, THR={THR_w}, feat={feat_w}")
y_rec_full_w = make_y_recovery(H_w, THR_w)
y_rec_w = pd.Series(y_rec_full_w, index=idx).reindex(P_extended_full.index).values
y_rec_w_clean = np.where(np.isnan(y_rec_w), 0, y_rec_w).astype(int)
P_B_w = P_extended_full if feat_w == 'extended' else P_crisis_aligned
score_B_w = walk_forward(P_B_w, y_rec_w_clean)
pos_w = double_confirm(score_A, score_B_w)

crises = {
    '2008': ('2007-06-01', '2009-06-30'),
    '2011': ('2011-01-01', '2012-09-30'),
    '2020': ('2020-01-01', '2020-08-31'),
}
for label, (a, b) in crises.items():
    win = (P_crisis_aligned.index >= pd.Timestamp(a)) & (P_crisis_aligned.index <= pd.Timestamp(b))
    if not win.any(): continue
    ret_w_ = mxus_ret_aligned[win]
    pl = np.concatenate([[1.0], pos_w[:-1]])[win]
    r_strategy = ret_w_ * pl
    print(f"  {label}: B&H rend={np.prod(1+ret_w_)-1:+7.2%}  DD={stats(ret_w_)['MaxDD']:+7.2%}  | "
          f"Strategy rend={np.prod(1+r_strategy)-1:+7.2%}  DD={stats(r_strategy)['MaxDD']:+7.2%}  "
          f"Cash={(1-pl).mean()*100:.1f}%")

print(f"\n[{time.time()-t0:5.1f}s] Fine.")

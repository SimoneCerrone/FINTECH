# -*- coding: utf-8 -*-
"""
Recovery Detector — Proof of Concept
=====================================
Test rapido dell'idea "Modello A (crisi) + Modello B (recovery) con double confirmation".

Strategia testate:
  S0. Buy & Hold (benchmark)
  S1. Original — Modello A binary q70 (replica baseline post-fix)
  S2. Hysteresis — Modello A con soglie asimmetriche q70/q40
  S3. Double Confirm — Modello A + Modello B, decisione combinata
  S4. Position sizing continuo basato su (A − B)

Replica il minimo indispensabile: stationarity, 9 precursori, walk-forward Logistica
solo (nessun tuning, nessun LSTM-AE). Tempo previsto: ~30 sec.
"""

import time
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score

t_start = time.time()

# =============================================================
# 1. Caricamento dati (stesso path del notebook)
# =============================================================
XLSX = 'Dataset4_EWS.xlsx'
data_df = pd.read_excel(XLSX, sheet_name='Markets')
date_col = data_df.columns[0]
data_df[date_col] = pd.to_datetime(data_df[date_col], dayfirst=True)
data_df = data_df.set_index(date_col)
y_full = data_df['Y'].values
X_df = data_df.drop('Y', axis=1)
print(f"[{time.time()-t_start:5.1f}s] Dati caricati: {X_df.shape}")

# =============================================================
# 2. Stationarity (replica cell 27)
# =============================================================
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

# =============================================================
# 3. Costruzione 9 precursori (replica cell 75)
# =============================================================
H = 4  # orizzonte y_ahead
idx = stationary_df.index
y_now = pd.Series(np.asarray(y_stationary), index=idx)
yv = y_now.values
y_ahead_full = np.array([1 if yv[t+1:t+1+H].any() else 0 for t in range(len(yv))])

eq_cols = [c for c in ['MXUS','MXEU','MXJP','MXBR','MXCN','MXIN','MXRU'] if c in stationary_df.columns]
P = pd.DataFrame(index=idx)
P['accel_volatilita'] = stationary_df['MXUS'].rolling(4).std() - stationary_df['MXUS'].rolling(12).std()

W = 13
eqr = stationary_df[eq_cols].values
avg_corr = np.full(len(idx), np.nan)
for t in range(W, len(idx)):
    C = np.corrcoef(eqr[t-W:t], rowvar=False)
    iu = np.triu_indices_from(C, 1)
    avg_corr[t] = np.nanmean(C[iu])
P['correlazione_media'] = avg_corr

P['tensione_credito'] = -stationary_df['LF98TRUU'].rolling(4).mean()
P['slancio_vix']      = stationary_df['VIX'].rolling(4).mean()
P['livello_vix']      = X_df['VIX'].reindex(idx)
P['pendenza_tassi']   = (X_df['GT10'] - X_df['USGG3M']).reindex(idx)

lvl = X_df['MXUS'].reindex(idx)
drawdown = lvl / lvl.cummax() - 1
P['velocita_drawdown'] = drawdown.diff(4)

P['slancio_baltic']   = -stationary_df['BDIY'].rolling(8).mean()
P['sorpresa_econ']    = -X_df['ECSURPUS'].reindex(idx).rolling(4).mean()

# =============================================================
# 4. Costruzione del NUOVO target y_recovery
# =============================================================
# Definizione: y_recovery[t] = 1 se il forward return log a 8 settimane > +5%
# (cioe' "vero rimbalzo sostenuto"). Usiamo log-returns per coerenza con la pipeline.
H_REC = 8
THR_REC = 0.05
mxus = X_df['MXUS'].reindex(idx).values
log_lvl = np.log(mxus)
y_recovery_full = np.full(len(idx), np.nan)
for t in range(len(idx) - H_REC):
    y_recovery_full[t] = 1.0 if (log_lvl[t + H_REC] - log_lvl[t]) > THR_REC else 0.0

# Allineamento P / y_ahead / y_recovery
P = P.dropna()
y_ahead    = pd.Series(y_ahead_full, index=idx).reindex(P.index).values
y_recovery = pd.Series(y_recovery_full, index=idx).reindex(P.index).values
# Tengo la riga solo se entrambi target sono definiti
last_full = max(H, H_REC)
P          = P.iloc[:-last_full]
y_ahead    = y_ahead[:-last_full].astype(int)
y_recovery = y_recovery[:-last_full].astype(int)

print(f"[{time.time()-t_start:5.1f}s] Precursori pronti: {P.shape}")
print(f"            Prevalenza y_ahead (crisi):    {y_ahead.mean():.3f}")
print(f"            Prevalenza y_recovery (rally): {y_recovery.mean():.3f}")

# =============================================================
# 5. Walk-forward Logistica per entrambi i target
# =============================================================
START, STEP = 200, 12
Xv = P.values

def walk_forward(y_target):
    s = np.full(len(P), np.nan)
    m = None
    for t in range(START, len(P)):
        if (t - START) % STEP == 0:
            m = make_pipeline(StandardScaler(),
                              LogisticRegression(class_weight='balanced', max_iter=1000))
            m.fit(Xv[:t], y_target[:t])
        s[t] = m.predict_proba(Xv[t:t+1])[:, 1][0]
    return s

print(f"[{time.time()-t_start:5.1f}s] Train Modello A (crisi)...")
score_A = walk_forward(y_ahead)
print(f"[{time.time()-t_start:5.1f}s] Train Modello B (recovery)...")
score_B = walk_forward(y_recovery)

mask = ~np.isnan(score_A) & ~np.isnan(score_B)
pr_A = average_precision_score(y_ahead[mask], score_A[mask])
pr_B = average_precision_score(y_recovery[mask], score_B[mask])
print(f"[{time.time()-t_start:5.1f}s] PR-AUC Modello A (crisi):    {pr_A:.4f}  (baseline = {y_ahead[mask].mean():.3f})")
print(f"            PR-AUC Modello B (recovery): {pr_B:.4f}  (baseline = {y_recovery[mask].mean():.3f})")

# =============================================================
# 6. Funzioni helper backtest
# =============================================================
mxus_ret = X_df['MXUS'].reindex(P.index).pct_change().fillna(0).values

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

def report(name, positions):
    """positions: array di 0.0-1.0 (frazione investita), allineato a P.index."""
    # lag-1 (decisione si applica la settimana dopo)
    pos_lag = np.concatenate([[1.0], positions[:-1]])
    ret = mxus_ret * pos_lag
    rv = ret[mask]
    pv = pos_lag[mask]
    s = stats(rv)
    n_switch = int(np.abs(np.diff(pv)).sum() > 0)  # rough
    # piu' preciso: n cambi di stato tra t e t+1
    n_switch = int((np.abs(np.diff(pv)) > 1e-6).sum())
    pct_cash = float((1 - pv).mean() * 100)
    print(f"{name:<35s} CAGR={s['CAGR']*100:>6.2f}%  Vol={s['Vol']*100:>5.2f}%  "
          f"Sharpe={s['Sharpe']:>5.2f}  MaxDD={s['MaxDD']*100:>6.2f}%  "
          f"Calmar={s['Calmar']:>5.3f}  Cash={pct_cash:>5.1f}%  Switch={n_switch:>3d}")
    return s

# =============================================================
# 7. Strategie a confronto
# =============================================================
print(f"\n[{time.time()-t_start:5.1f}s] Backtest 5 strategie a confronto:\n")
print(f"{'Strategia':<35s} {'CAGR':>10s}  {'Vol':>5s}    {'Sharpe':>5s}  {'MaxDD':>7s}    {'Calmar':>5s}    {'Cash':>4s}    {'Switch':>3s}")

# --- S0. Buy & Hold ---
pos_bh = np.ones(len(P))
s0 = report("S0. Buy & Hold (benchmark)", pos_bh)

# Quantili IN-SAMPLE (questo e' POC veloce; in versione finale serviranno expanding)
qA_70 = np.nanquantile(score_A, 0.70)
qA_60 = np.nanquantile(score_A, 0.60)
qA_50 = np.nanquantile(score_A, 0.50)
qA_40 = np.nanquantile(score_A, 0.40)
qB_60 = np.nanquantile(score_B, 0.60)
qB_50 = np.nanquantile(score_B, 0.50)
qB_40 = np.nanquantile(score_B, 0.40)

# --- S1. Original baseline (A binary q70) ---
pos_S1 = np.where(np.nan_to_num(score_A) > qA_70, 0.0, 1.0)
s1 = report("S1. Original (A > q70 -> cash)", pos_S1)

# --- S2. Hysteresis (A con q70 esci / q40 rientra) ---
pos_S2 = np.full(len(P), 1.0)
state = 1
for t in range(len(P)):
    if np.isnan(score_A[t]):
        pos_S2[t] = state; continue
    if state == 1 and score_A[t] > qA_70:
        state = 0
    elif state == 0 and score_A[t] < qA_40:
        state = 1
    pos_S2[t] = state
s2 = report("S2. Hysteresis A (q70 out / q40 in)", pos_S2)

# --- S3. Double Confirmation (A + B) ---
# Esci quando A urla forte E B non vede recovery
# Rientra quando B segnala recovery E A non urla
pos_S3 = np.full(len(P), 1.0)
state = 1
for t in range(len(P)):
    if np.isnan(score_A[t]) or np.isnan(score_B[t]):
        pos_S3[t] = state; continue
    if state == 1:
        if score_A[t] > qA_70 and score_B[t] < qB_40:
            state = 0
    else:
        if score_B[t] > qB_60 and score_A[t] < qA_60:
            state = 1
    pos_S3[t] = state
s3 = report("S3. Double Confirm (A+B)", pos_S3)

# --- S4. Position sizing continuo: peso_equity = sigmoid(B - A) ---
# Quando A >> B -> tendi a cash. Quando B >> A -> tendi a equity.
# Mappiamo (B - A) in [0,1] tramite sigmoid scalata.
from scipy.special import expit
diff = score_B - score_A   # positivo = recovery vince, negativo = crisi vince
diff_filled = np.where(np.isnan(diff), 0.0, diff)
# Scalatura: usiamo mediana e IQR dei diff per normalizzare
med = np.nanmedian(diff_filled[mask])
iqr = np.nanpercentile(diff_filled[mask], 75) - np.nanpercentile(diff_filled[mask], 25)
z = (diff_filled - med) / (iqr / 1.349 + 1e-9)  # 1.349 ~ z corrispondente a IQR
pos_S4 = np.clip(expit(z), 0.0, 1.0)
s4 = report("S4. Position sizing continuo", pos_S4)

# --- S5. Hysteresis con isteresi piu' larga (per confronto)
pos_S5 = np.full(len(P), 1.0)
state = 1
for t in range(len(P)):
    if np.isnan(score_A[t]):
        pos_S5[t] = state; continue
    if state == 1 and score_A[t] > qA_70:
        state = 0
    elif state == 0 and score_A[t] < qA_50:
        state = 1
    pos_S5[t] = state
s5 = report("S5. Hysteresis loose (q70 / q50)", pos_S5)

# --- Costi di transazione: ricalcolo S3 con TC 10bp
print(f"\n[{time.time()-t_start:5.1f}s] Con costi transazione 10bp/switch (S3 Double Confirm):")
def report_with_tc(name, positions, tc_bp=10):
    pos_lag = np.concatenate([[1.0], positions[:-1]])
    changes = np.concatenate([[0.0], np.abs(np.diff(pos_lag))])
    ret = mxus_ret * pos_lag - changes * tc_bp / 10000.0
    rv = ret[mask]
    s = stats(rv)
    print(f"{name:<35s} CAGR={s['CAGR']*100:>6.2f}%  MaxDD={s['MaxDD']*100:>6.2f}%  Calmar={s['Calmar']:>5.3f}")
    return s

report_with_tc("S3 Double Confirm + TC 10bp", pos_S3)
report_with_tc("S4 Position sizing + TC 10bp", pos_S4)

# =============================================================
# 8. Diagnostica: cosa fa ciascuna strategia nelle 3 crisi
# =============================================================
print(f"\n[{time.time()-t_start:5.1f}s] Comportamento nelle 3 crisi storiche:")
crises = {
    '2008': ('2007-06-01', '2009-06-30'),
    '2011': ('2011-01-01', '2012-09-30'),
    '2020': ('2020-01-01', '2020-08-31'),
}
for label, (a, b) in crises.items():
    win = (P.index >= pd.Timestamp(a)) & (P.index <= pd.Timestamp(b))
    if not win.any(): continue
    print(f"\n  Crisi {label}:")
    ret_w = mxus_ret[win]
    print(f"    Buy & Hold        : rend={np.prod(1+ret_w)-1:>+7.2%}  MaxDD={stats(ret_w)['MaxDD']:>+7.2%}")
    for nm, p in [('S1 Original', pos_S1), ('S2 Hysteresis', pos_S2),
                  ('S3 DoubleConfirm', pos_S3), ('S4 PositionSize', pos_S4)]:
        pl = np.concatenate([[1.0], p[:-1]])[win]
        r = mxus_ret[win] * pl
        print(f"    {nm:<18s}: rend={np.prod(1+r)-1:>+7.2%}  MaxDD={stats(r)['MaxDD']:>+7.2%}  Cash={(1-pl).mean()*100:>5.1f}%")

print(f"\n[{time.time()-t_start:5.1f}s] Fine.")

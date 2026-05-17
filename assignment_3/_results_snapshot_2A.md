# Snapshot risultati forward-looking — chosen_model = 2A (B ⊕ Fully-invested NNLS)

Estratti dal notebook dopo l'esecuzione di celle 87–100.
Setup: `chosen_model = adapt_fi_nnls_result`, `chosen_factory = fully_invested_nnls_factory`.

## Cell 88 — selettore
- TE annualizzato (net): **2.76%**
- Ultimi pesi:
  - DU1: 0.4226  (bond 2y Schatz — il peso più grande)
  - ES1: 0.3098  (S&P 500)
  - TY1: 0.1063  (UST 10y)
  - RX1: 0.0958  (Bund 10y)
  - VG1: 0.0306  (Eurostoxx)
  - TP1: 0.0208  (Topix)
  - GC1: 0.0141  (Gold)
  - CO1, NQ1, LLL1, TU2: 0.0
- Σw = 1.00 (rispetta il vincolo FI)

## Idea 8 — Inverse stress test (copula t-Student)
- Copula fitted: **ν = 30** (vicino a Gaussian, tail dependence debole)
- det(Corr) = 0.0011
- Unconditional replica P&L (10 000 scenari):
  - mean +0.0007, vol 0.0078
  - **VaR 1% = −2.34%, CVaR 1% = −3.39%**
- VaR/CVaR condizionati per scenario:

| Scenario | N | VaR 5% | CVaR 5% | Median |
|---|---|---|---|---|
| Equity crash (<-10%) | 15 | −4.85% | −4.97% | −4.50% |
| Oil crash (<-15%) | 88 | −2.65% | −3.47% | −0.74% |
| Risk-off (eq<-5%, bd>+1%) | 25 | −4.07% | −4.27% | −1.75% |
| Corr. sell-off (all<-3%) | 1 | — insufficient — | | |
| EM crisis (LLL1<-15%) | 29 | −4.50% | −4.64% | −1.73% |
| Gold spike (GC1>+5%) | 252 | −1.13% | −2.09% | +0.35% |

## Idea D — Conformal prediction
**Standard conformal:**
- 90%: coverage empirica = **90.5%** (target ≥90%, OK)
- 95%: coverage empirica = **95.1%** (target ≥95%, OK)
- Historical TE backtest: **2.76%**
- Conformal TE 90% annualised: **4.18%**
- Conformal TE 95% annualised: **6.33%**

**Regime-conditioned (D2):**
- Overall coverage: 88.7%
- Calm coverage: 90.7%
- Stress coverage: 85.8%
- Mean half-width calm: **±0.572%**
- Mean half-width stress: **±0.770%**
- Standard 90% width: ±0.580%

**Calibration check multi-α:**
| α | nominal | empirical |
|---|---|---|
| 0.20 | 80% | 79.4% |
| 0.15 | 85% | 84.9% |
| 0.10 | 90% | 90.5% |
| 0.07 | 93% | 93.1% |
| 0.05 | 95% | 95.1% |

→ La curva di calibrazione è praticamente sulla diagonale: il conformal funziona benissimo su 2A.

## Idea E — RL rebalancing

| Policy | RMSE TE | Cost (bps) | Rebal % | Reward |
|---|---|---|---|---|
| Weekly (1w) | 0.003960 | 17.21 | 100.0% | −0.0103 |
| Bi-weekly (2w) | 0.003990 | 13.49 | 50.0% | −0.0101 |
| Monthly (4w) | 0.003996 | 10.05 | 25.0% | −0.0098 |
| **RL (history only)** | **0.003943** | **9.65** | **69.5%** | **−0.0095** |
| **RL (copula-augm.)** | **0.003949** | **8.33** | **30.3%** | **−0.0094** |

→ Entrambi gli agenti RL dominano i calendari fissi. Copula-augmented riduce il costo del 14% rispetto a history-only mantenendo la stessa RMSE TE.

## Idea 8b — Historical scenario replay (6 crisi)

| Crisi | Target | Replica | MaxDiv | Beta | Corr |
|---|---|---|---|---|---|
| 2008 GFC (Sep-Nov 08) | −18.65% | −10.69% | 0.0274 | 0.718 | 0.820 |
| 2010 Flash Crash (May 10) | −3.84% | −1.20% | 0.0120 | 0.667 | 0.892 |
| 2011 EU Debt Crisis | −3.82% | −0.07% | 0.0143 | 0.780 | 0.931 |
| 2015 China Sell-off | −1.83% | +0.19% | 0.0113 | 1.451 | 0.957 |
| 2018 Q4 Sell-off | −7.83% | −6.66% | 0.0065 | 1.082 | 0.898 |
| 2020 COVID Crash | −7.82% | −5.15% | 0.0242 | 0.859 | 0.937 |

→ La replica sotto-replica i drawdown peggiori (2008 GFC: -10.7% vs target -18.7%), ma con Beta < 1 per le crisi più importanti. Nel 2015 e 2018 Beta supera 1 (1.45 e 1.08) — la replica amplifica leggermente. Correlation sempre >= 0.82.

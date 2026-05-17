# Snapshot forward-looking — chosen_model = composite_result (Stefano)

`chosen_model = composite_result`, `chosen_factory = nnls_factory` (branch stress).

## Cell 88
- TE annualizzato (net): **2.73%**
- Ultimi pesi (settimana finale in regime CALM → Liquidity-aware attiva):
  - ES1: 0.4309
  - TY1: 0.1851
  - DU1: −0.2375 (SHORT)
  - RX1: 0.1128
  - NQ1: −0.0933 (SHORT)
  - LLL1: 0.0322
  - GC1: 0.0157, VG1: 0.0136, TP1: 0.013, CO1: 0.0012
  - TU2: −0.0156
- Σw ≠ 1, contiene shorts (no FI constraint)

## Idea 8 — copula stress (ν=30)
- Replica P&L: mean 0.0006, vol **0.0084** (vs 2A 0.0078)
- VaR 1%: **−2.59%** | CVaR 1%: **−3.82%**

| Scenario | VaR 5% | CVaR 5% | Median |
|---|---|---|---|
| Equity crash <-10% (n=15) | −5.84% | −6.28% | −4.66% |
| Oil crash <-15% (n=88) | −3.17% | −3.83% | −0.86% |
| Risk-off (n=25) | −4.83% | −5.11% | −2.03% |
| EM crisis (n=29) | −4.81% | −5.02% | −2.56% |
| Gold spike (n=252) | −1.30% | −2.30% | +0.41% |

## Idea D — Conformal
- 90%: empirical **91.4%** | 95%: 95.1%
- Historical TE: 2.73% | Conformal TE 90% **4.30%** | 95% **5.63%**
- D2 calm: ±0.565% | stress: ±0.732% | standard: ±0.596%
- Calibration multi-α: 80.8 / 85.8 / 91.4 / 94.2 / 95.1

## Idea E — RL
| Policy | RMSE TE | Cost (bps) | Rebal % | Reward |
|---|---|---|---|---|
| Weekly | 0.003929 | 38.88 | 100% | −0.0123 |
| Bi-weekly | 0.003944 | 30.08 | 50% | −0.0115 |
| Monthly | 0.003956 | 22.93 | 25% | −0.0109 |
| RL (history) | 0.003909 | 27.11 | 81.4% | −0.0111 |
| RL (copula-augm) | 0.003922 | **14.11** | 10.9% | −0.0098 |

## Idea 8b — Crisis replay
| Crisi | Target | Replica | MaxDiv | Beta | Corr |
|---|---|---|---|---|---|
| 2008 GFC | −18.65% | −13.17% | 0.0247 | 0.913 | 0.848 |
| 2010 Flash | −3.84% | −1.46% | 0.0101 | 0.765 | 0.846 |
| 2011 EU | −3.82% | −1.18% | 0.0131 | 0.812 | 0.936 |
| 2015 China | −1.83% | +0.00% | 0.0107 | 1.395 | 0.952 |
| 2018 Q4 | −7.83% | −6.49% | 0.0065 | 1.041 | 0.884 |
| 2020 COVID | −7.82% | −5.41% | 0.0213 | 0.911 | 0.952 |

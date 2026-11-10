# REMIX V8 — Informe de investigación (lotes A y B, más verificación C)

Alcance: Exness-MT5Trial11 (demo, aislada en `C:\REMIX_MT5_LAB\terminal`), 3.000 USD, solo Strategy Tester y análisis de históricos. Datos: M15 reales 2024-01→2026-10-31 remuestreados (`data/raw/v7`, no se sube). **Reserva prospectiva ≥ 2026-11-01: no se usó** (un test comprueba que ningún dato posterior entra en los estudios). Rama `feature/remix-v8-institutional-edge`; ramas previas intactas.

## Fase 0 — estado recuperado
Repo `jeiners397-alt/exness-quant-bot`; HEAD V7 = `ddc2760`; 133 pruebas previas pasan (ahora 142). Terminal principal PID 34572 vivo y sin tocar. Un terminal de la instancia aislada (PID 29128, ocioso desde una ejecución anterior) impedía lanzar nuevos tests (la 2.ª instancia se cierra al instante, `SIN_INFORME`): se detuvo **solo ese proceso**, verificando que su ruta estaba bajo `C:\REMIX_MT5_LAB`. Error técnico pendiente: el log del probador (≈229 MB) se copia a cada run (`tester_log.txt`); está excluido de Drive/GitHub (>30 MB).

## Lote A — XAUUSDm H1 (ver `V8_XAU_H1_AUDIT.md`)
1. Se recuperó del código la definición exacta de V7 y se **corrigió su descripción**: es un pico que cierra *dentro* operado a favor del pico, no una ruptura con cierre fuera.
2. Referencia Python reproduce V7 al decimal (n 161/159, expectativa +0,2152/+0,1446 R, t 2,18/1,46).
3. EA compilado y ejecutado: paridad 97,8 % (H1) y 99,6 % (H4); causas de cada discrepancia identificadas (mercado cerrado a las 22–23 UTC, SL de cortos por ASK, velas parciales H4).
4. Resultado oficial H1: TP 1,5R +395,57 USD (PF 1,17), TP 3R +877,28 USD (PF 1,31); DD 7 %.

## Lote B — H4 y D1 (`V8_H4_D1_EVENT_STUDY.csv`)
5 mercados (XAUUSDm, USTECm, BTCUSDm, ETHUSDm, EURUSDm) × 2 TF × 9 conjuntos de reglas (familias A–H, la A con ventanas 20 y 55) × primario/invertido × 5 RR = **890 pruebas registradas**. Misma metodología que V7 (entrada en la apertura siguiente, spread real, SL 1 ATR, control aleatorio por hora y tercil de ER). Regla de candidato fijada de antemano (n_IS≥30, t_IS≥2, confirmación OOS n≥15 t≥1,65; clase B exige además t_IS ≥ √(2 ln N) = 3,69, robustez a coste ×1,5 e IC95 OOS que excluya 0).

Resultado: **D 466, F 270 (muestra < 30), C 151, G 3, B 0, A 0.**
- Media de la expectativa por familia: H4 entre −0,03 y −0,08 R (negativa en todas); D1 entre −0,07 y +0,09 R (ruido).
- Costes: coste/ATR baja de 0,16 (M15 EURUSD) a 0,039 (H4) y 0,018 (D1); aun así **ningún mercado distinto del oro** produce candidatas con t ≥ 2 sostenido: de 37 pruebas con t_all ≥ 2, 21 son XAUUSDm y las otras 16 son 13 de clase F (muestras de 3 a 25 operaciones, mediana 22) y 3 de clase C débiles.
- En XAUUSDm aparecen 45 celdas C (H4 32, D1 13); las más claras: **H4 `A1_BREAKOUT20` continuación** (primera vela que cierra fuera del rango de 20 velas): n=243, expectativa +0,25 R (TP 2R) / +0,35 R (TP 3R), t 2,6/2,9; positiva cada año (en las ejecuciones oficiales a 2R: 2024 +0,15, 2025 +0,18, 2026 +0,33 R), en largos (+0,19 R a 1,5R) y en cortos (+0,07 R, débil), y supera por poco al control aleatorio con la misma mezcla direccional largos/cortos (p = 0,04 con 500 sorteos; ese control separa el efecto de la tendencia alcista del oro, que aporta +0,07 R a largos aleatorios). H4 `D_EXTREME_REVERSION` invertido (continuación tras movimiento extremo): t_all 3,33 pero **concentrado en largos y débil en 2026** (+0,48 → +0,59 → +0,12 R por año a 1,5R). D1 `B_MOMENTUM`: n=63 (poca potencia).
- Sensibilidad de A1 en 54 celdas (ventana 10–55 × SL 0,75–1,5 ATR × RR 1,5–3): **54/54 con expectativa positiva** y 69 % con t ≥ 2; la referencia prefijada (20, 1 ATR) no es la mejor celda (`V8_H4_SENSITIVITY.csv`).
- Entradas/salidas alternativas (`V8_EXIT_ANALYSIS.csv`): ninguna mejora robusta. La mejor por IS en H4 (límite −0,6 ATR, TP3) pasa de +0,34 (IS) a +0,05 R (OOS); en H1 la mejor por IS es la referencia TP3. Break-even, trailing, cierre parcial y salida temporal quedan por debajo o dentro del ruido de la referencia.

## Lote C (verificación de la pista XAU H4)
Sin candidatas B no se justifica optimizar. Sí se ejecutaron, por ser baratas y para auditar, 2 backtests oficiales de la regla H4 prefijada (TP 2R y 3R): **+1.622,79 USD (PF 1,49, DD 8,1 %) y +2.172,77 USD (PF 1,57, DD 8,4 %)** en 248 operaciones. Es **reproducción in-sample** de un hallazgo seleccionado entre 3.174 pruebas acumuladas.

## Qué no se hizo
Optimización completa/genética/forward de MT5 (ver razón arriba), ML, cartera unificada (solo hay una candidata de clase C en un solo mercado), calendario macro, order flow, tests de estrés con spreads reales ampliados (se modelaron), M5, ticks reales completos (9 % de cobertura), nuevos símbolos distintos de los 5 prioritarios (los 5 alternativos solo en perfil de costes).


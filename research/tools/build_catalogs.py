"""Construye el catalogo canonico a partir de las fuentes A, B, C (+extras/web) y las estrategias LAB.

Entradas (staging):
  research/_staging/REMIX_strategies_staging.csv, REMIX_indicators_staging.csv   (Fuente A, parseadas del XLSX)
  research/_staging/C_strategies_raw.json                                        (Fuente C, lectura del conector)
  research/_staging/B_strategies.txt, B_indicators.txt, C_indicators.txt, C_extras_web.txt (transcripcion compacta)
Salidas: research/CATALOG_STRATEGIES.csv, CATALOG_INDICATORS.csv, EXNESS_COMPATIBILITY_MATRIX.csv, build_stats.json

LIMITE METODOLOGICO: la deduplicacion es por CONCEPTO segun nombre/definicion declarada (reglas regex revisables).
No demuestra equivalencia matematica; los grupos marcados EQUIV_MATEMATICA son los unicos con identidad
conocida (p.ej. SMMA == media de Wilder/RMA). Todo lo demas es VARIANTE o CANDIDATO_DUPLICADO a revisar.
Los winrates/rendimientos de las fuentes NO se importan como evidencia.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

R = Path(__file__).resolve().parent.parent
ST = R / "_staging"


def unesc(s):
    return re.sub(r"\\([_\[\]<>*#`~|!()+.\-\\])", r"\1", s)


def read_pipe(p, ncols):
    rows = []
    for ln in (ST / p).read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = ln.split("|")
        parts += [""] * (ncols - len(parts))
        rows.append(parts[:ncols])
    return rows


# ------------------------------------------------------------------ carga
strat, ind = [], []   # dicts: id, name, source, src_ref, desc, status_src, extra

# Fuente A
for r in csv.DictReader(open(ST / "REMIX_strategies_staging.csv", encoding="utf-8-sig")):
    strat.append(dict(id=f"REMIX_S{int(r['N°']):03d}", name=r["Nombre literal del usuario"], source="A_REMIX",
                      desc=r["Descripción original"], cat=r["Categoría"], status_src=r["Viabilidad para Exness MT5"],
                      prio=r["Prioridad de diseño"], note=r["Motivo / limitación"], orig_id=r["N°"]))
for r in csv.DictReader(open(ST / "REMIX_indicators_staging.csv", encoding="utf-8-sig")):
    ind.append(dict(id=f"REMIX_I{int(r['N°']):03d}", name=r["Nombre literal del usuario"], source="A_REMIX",
                    desc=r["Descripción original"], cat=r["Categoría"], status_src=r["Viabilidad para Exness MT5"],
                    prio=r["Prioridad de diseño"], note=r["Motivo / limitación"], orig_id=r["N°"]))
# Fuente B
for i, n, s, note in read_pipe("B_strategies.txt", 4):
    strat.append(dict(id=f"FUT_S{int(i):03d}", name=n, source="B_FUTURES_Z24", desc="", cat="", note=note,
                      status_src={"P": "PROXY_EXPERIMENTAL_NO_IDENTICO", "R": "REGLA_CAUSAL_OPERATIVA_V1",
                                  "N": "NO_EVALUABLE_AUN"}[s], orig_id=i))
RISK_B = {"E": "ESTANDAR", "V": "VERIFICAR", "P": "REPINTADO_O_CONFIRMACION_TARDIA"}
STAT_B = {"SB": "SERIE_BASE_RELACIONADA_EN_MOTOR", "LIB": "LIBRERIA_OPCIONAL_SIN_PARIDAD_GARANTIZADA",
          "Z24": "IMPLEMENTADO_Z24_FORMULA_PUBLICA", "NOP": "FUENTE_O_ALGORITMO_NO_PUBLICADO",
          "REQ": "REQUIERE_IMPLEMENTACION", "EXT": "REQUIERE_DATOS_EXTERNOS"}
for i, n, cat, s, rk in read_pipe("B_indicators.txt", 5):
    ind.append(dict(id=f"FUT_I{int(i):03d}", name=n, source="B_FUTURES_Z24", desc="", cat=cat, status_src=STAT_B[s],
                    risk_src=RISK_B[rk], note="", orig_id=i))
# Fuente C estrategias (JSON de lectura del conector, escapes Markdown)
raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["fileContent"] if len(sys.argv) > 1 else None
if raw is not None:
    (ST / "C_strategies_raw.json").write_text(json.dumps({"fileContent": raw}, ensure_ascii=False), encoding="utf-8")
raw = json.loads((ST / "C_strategies_raw.json").read_text(encoding="utf-8"))["fileContent"]
raw = unesc(raw)
pat = re.compile(r'"id":\s*(\d+),\s*"name":\s*"(.*?)",\s*"user_description":\s*"(.*?)",\s*"user_estimated_win_rate":\s*"(.*?)",'
                 r'\s*"user_estimated_daily_profit":\s*"(.*?)",\s*"status":\s*"(.*?)"', re.S)
cs = pat.findall(raw)
assert len(cs) == 200, f"C estrategias parseadas: {len(cs)}"
for i, n, d, wr, dp, stt in cs:
    ub = re.findall(r"\d+", wr)
    strat.append(dict(id=f"SPOT_S{int(i):03d}", name=n.replace('\\"', '"'), source="C_SPOT_S1", desc=d.replace('\\"', '"'),
                      cat="", status_src=stt, note="", orig_id=i, wr_upper=int(ub[-1]) if ub else None))
for i, n in read_pipe("C_indicators.txt", 2):
    ind.append(dict(id=f"SPOT_I{int(i):03d}", name=n, source="C_SPOT_S1", desc="", cat="", status_src="PENDING_VERIFICATION",
                    note="", orig_id=i))
ex = read_pipe("C_extras_web.txt", 4)
assert sum(1 for e in ex if e[0].startswith("EXTRA_")) == 36 and sum(1 for e in ex if e[0].startswith("WEB_")) == 12
for i, n, fam, dat in ex:
    strat.append(dict(id=i, name=n, source="C_EXTRA" if i.startswith("EXTRA") else "C_WEB", desc=fam, cat=fam,
                      status_src="HIPOTESIS_REQUIERE_PRUEBA" if i.startswith("EXTRA") else "NUEVA_HIPOTESIS_NO_PROBADA",
                      note=dat, orig_id=i))
n_src_strat, n_src_ind = len(strat), len(ind)
# Estrategias del laboratorio (no pertenecen a las fuentes; origen: especificacion del usuario)
LAB = [("LAB_S01", "London Breakout", "Rango asiatico 00-07h servidor; ruptura 07-10h; SL=rango; TP=1.5R; cierre 17h"),
       ("LAB_S02", "Donchian Channel + ATR", "Ruptura Donchian(20) previo; SL 2 ATR; TP 3 ATR"),
       ("LAB_S03", "EMA + ADX Pullback", "EMA50>EMA200, ADX>25, +DI>-DI; cierre cruza EMA20; SL 1.5 ATR; TP 3 ATR"),
       ("LAB_S04", "Bollinger Squeeze + Momentum", "BW<0.75*SMA(BW,100) en i-1; cierre fuera de banda con momentum 10; SL 2 ATR; TP 3 ATR")]
for i, n, d in LAB:
    strat.append(dict(id=i, name=n, source="LAB_USER_SPEC", desc=d, cat="", status_src="IMPLEMENTADO_EN_LAB", note="", orig_id=i[-3:]))

# ------------------------------------------------------------------ conceptos (dedup por nombre/definicion)
IND_RULES = [
    ("SMMA_RMA_WILDER", r"smma|smoothed moving average|wilder.s smoothing", "EQUIV_MATEMATICA"),
    ("EMA", r"^ema \(exponential", ""), ("SMA", r"^sma \(simple", ""), ("WMA", r"^wma", ""),
    ("HMA", r"\bhma\b|hull moving", ""), ("ALMA", r"\balma\b|arnaud legoux", ""), ("KAMA", r"\bkama\b|kaufman adaptive", ""),
    ("VWMA", r"vwma", ""), ("DEMA_TEMA", r"\bdema\b|\btema\b|double ema|triple ema \(", ""),
    ("MA_RIBBON", r"ribbon|rainbow|guppy|gmma", ""), ("SUPERTREND", r"supertrend", ""), ("ICHIMOKU", r"ichimoku", ""),
    ("PSAR", r"parabolic sar", ""), ("ADX_DMI", r"^adx|adx & di|^dmi \(directional movement", ""),
    ("AROON", r"aroon", ""), ("VORTEX", r"vortex", ""), ("ZIGZAG", r"zigzag", ""), ("MCGINLEY", r"mcginley", ""),
    ("LINREG", r"linear regression (trendline|slope)|regression slope|polynomial regression|cuadr", ""),
    ("DONCHIAN", r"donchian|turtle trade", ""), ("KELTNER", r"keltner", ""), ("T3", r"\bt3\b|tillson", ""),
    ("ZLEMA", r"zlema|zero lag ema|zero lag exponential", ""), ("CHOP", r"choppiness index", ""),
    ("STOCHRSI", r"stoch.*rsi", ""), ("RSI", r"^rsi \(relative|relative strength index \(rsi\)|rsi \(relative", ""),
    ("RSI_DIVERGENCE", r"rsi divergence", ""), ("CONNORS_RSI", r"connors", ""), ("RSI_TREND_MAGIC", r"rsi trend magic", ""),
    ("STOCHASTIC", r"^stochastic oscillator|stochastic fast", ""), ("MACD", r"macd", ""), ("CCI", r"\bcci\b|commodity channel", ""),
    ("WILLIAMS_R", r"williams %r", ""), ("ROC", r"^roc|rate of change \(roc\)", ""),
    ("MOMENTUM", r"momentum indicator|linear momentum", ""), ("ULTIMATE_OSC", r"ultimate oscillator", ""),
    ("TRIX", r"trix|triple exponential average", ""), ("DPO", r"detrended price oscillator|\bdpo\b", ""),
    ("CMO", r"chande momentum|\bcmo\b", ""), ("AWESOME_AC", r"awesome oscillator|accelerator oscillator", ""),
    ("KST", r"know sure thing|\bkst\b", ""), ("COPPOCK", r"coppock", ""), ("FISHER", r"fisher transform", ""),
    ("RVI", r"relative volatility index|rvi oscillator", ""), ("SQUEEZE_MOMENTUM", r"squeeze momentum", ""),
    ("WADDAH", r"waddah", ""), ("PPO", r"^ppo|percentage price oscillator", ""), ("TSI", r"true strength", ""),
    ("CENTER_GRAVITY", r"center of gravity", ""), ("STC", r"schaff", ""), ("QQE", r"\bqqe\b", ""),
    ("WAVETREND", r"wavetrend|market cipher b|vumanchu", ""), ("KLINGER", r"klinger", ""),
    ("FORCE_INDEX", r"force index|\befi\b", ""), ("ELDER_RAY", r"bull bear power|elder ray", ""),
    ("DISPARITY", r"disparity index|distance to ema", ""), ("SMI_STOCH", r"stochastic momentum index", ""),
    ("SMI_ERGODIC", r"smi ergodic", ""), ("SMART_MONEY_INDEX", r"smart money index", ""),
    ("DYNAMIC_MOMENTUM_INDEX", r"dynamic momentum index", ""), ("BOP", r"balance of power", ""),
    ("PGO", r"pretty good", ""), ("MASS_INDEX", r"mass index", ""),
    ("VOLUME_PROFILE", r"volume profil|vpvr|\bfrvp\b|\bsvp\b|\bavp\b|point of control|\bpoc\b|\bhvn\b|\blvn\b|volume density", ""),
    ("VWAP", r"vwap", ""), ("OBV", r"on-balance|\bobv\b", ""), ("CMF", r"chaikin money flow", ""),
    ("AD_LINE", r"accumulation/distribution", ""), ("VFI", r"volume flow indicator|^vfi", ""),
    ("VOLUME_OSC", r"volume oscil|percentage volume oscillator|\bpvo\b", ""), ("VROC", r"volume rate of change|\bvroc\b", ""),
    ("EOM", r"ease of movement", ""), ("MFI", r"money flow index", ""), ("PVI_NVI", r"positive volume index|negative volume index|\bpvi\b|\bnvi\b", ""),
    ("CVD_DELTA", r"delta|\bcvd\b|net volume|net buyer", ""), ("OPEN_INTEREST", r"open interest", ""),
    ("LONG_SHORT_RATIO", r"long/short ratio|binance smart signal", ""), ("FUNDING", r"funding rate", ""),
    ("TAKER_RATIO", r"taker", ""), ("LIQUIDATION", r"liquidation", ""), ("ORDER_BOOK", r"order book|depth", ""),
    ("TRADE_SIZE", r"trade size|large orders", ""), ("WEIS_WAVE", r"weis wave", ""), ("MARKET_FACILITATION", r"market facilitation", ""),
    ("VOLUME_CLIMAX", r"volume climax", ""), ("VZO", r"volume zone", ""), ("VWRSI", r"volume weighted rsi|vwrsi", ""),
    ("BOLLINGER", r"bollinger", ""), ("ATR", r"^atr \(|normalized atr|atr bands|atr trailing|atr volatility stop|volatility ratio", ""),
    ("STDDEV_HV", r"standard deviation|historical volatility|mean absolute deviation", ""),
    ("CHAIKIN_VOLATILITY", r"chaikin volatility", ""), ("GARCH", r"garch", ""), ("ULCER", r"ulcer", ""),
    ("ENVELOPE_STARC", r"envelope bands|starc", ""), ("BETA", r"\bbeta\b", ""), ("VWAP", r"vwap", ""),
    ("MARKET_STRUCTURE_SMC", r"market structure|change of character|choch|\bmsb\b|smart money concepts", ""),
    ("FVG", r"fair value gap|imbalance", ""), ("ORDER_BLOCK", r"order block|breaker|mitigation", ""),
    ("LIQUIDITY_POOLS", r"liquidity pool|equal highs", ""), ("FIBONACCI", r"fibonacci|optimal trade entry|\bote\b", ""),
    ("PIVOTS", r"pivot points|camarilla|woodie|demark pivots", ""), ("TD_SEQUENTIAL", r"td sequential|demark sequential", ""),
    ("SUPPLY_DEMAND", r"supply (and|&) demand", ""), ("SESSION_HL", r"session high|previous day", ""),
    ("FRACTALS", r"fractals", ""), ("TRENDLINES_AUTO", r"trendlines", ""), ("PITCHFORK", r"pitchfork", ""),
    ("GANN", r"gann", ""), ("HARMONIC", r"harmonic", ""), ("CLASSIC_PATTERNS", r"head and shoulders|double top|triangle|wedge|flag", ""),
    ("RENKO_KAGI_PF", r"kagi|renko|three line break|point & figure", ""), ("HEIKIN_ASHI", r"heikin", ""),
    ("HALFTREND", r"halftrend", ""), ("UT_BOT", r"ut bot", ""), ("NADARAYA_WATSON", r"nadaraya", ""),
    ("LORENTZIAN_KNN", r"lorentzian|knn", ""), ("ALPHATREND", r"alpha ?trend", ""), ("SSL", r"\bssl\b", ""),
    ("CORAL", r"coral trend", ""), ("MCDX", r"mcdx", ""), ("MARKET_CIPHER_A", r"cipher a", ""),
    ("RANGE_IDENTIFIER", r"range (identifier|filter)", ""), ("MTF_DASHBOARD", r"multi-?timeframe|trend meter|trend dashboard", ""),
    ("EHLERS_FILTERS", r"ehlers|supersmoother|roofing|\bmama\b|\bfama\b|cyber cycle|sine wave", ""),
    ("HURST_ENTROPY_FRACTAL", r"hurst|entropy|fractal dimension|variance ratio|efficiency ratio", ""),
    ("KALMAN_ARIMA_FFT", r"kalman|arima|fourier|\bfft\b|empirical mode", ""),
    ("ZSCORE_MEANREV", r"z-score|half-life|mean reversion|co-integration|cointegration|adf", ""),
    ("PERF_RATIOS", r"sharpe|sortino|treynor|information ratio|jensen|skewness|markov", ""),
    ("CORRELATION", r"correlation|beta relative", ""), ("WYCKOFF_VSA", r"wyckoff|volume spread|effort vs|absorption candle", ""),
    ("TREND_FILTERS_MISC", r"trend magic|trend trader|trend mystery|vidya|tii|trend intensity", ""),
    ("OSC_MISC", r"normalizada|detrended momentum|detrended synthetic|oscilador", ""),
]
STR_RULES = [
    ("ORDERBLOCK_FVG_ICT", r"order block|fair value gap|\bfvg\b|ict\b|breaker|smc|smart money concepts|wick|mitigation"),
    ("VOLUME_PROFILE_POC", r"volume profile|\bpoc\b|\bhvn\b|\blvn\b|nodos|vacio|void"), ("CVD_ORDERFLOW", r"cvd|delta|order.?flow|absorci|aggtrade|footprint|taker"),
    ("LIQUIDATION_OI_FUNDING", r"liquidation|open interest|funding|long/short"), ("ANCHORED_VWAP", r"vwap"),
    ("SUPERTREND", r"supertrend"), ("SQUEEZE_BREAKOUT", r"squeeze|bb squeeze|volatility contraction|compression|coil"),
    ("DONCHIAN_BREAKOUT", r"donchian|turtle"), ("ATR_EXPANSION_BREAKOUT", r"atr expansion|range expansion"),
    ("ICHIMOKU", r"ichimoku|kumo"), ("EMA_ADX_TREND", r"ema cross|golden cross|ema50|ema 50|adx|dmi|three timeframes|sma200|sma 5/20|ema.*pullback|pullback ema"),
    ("SESSION_OPENING_RANGE", r"session open|opening range|london|ny/london|00utc|pre-breakout|rollover"),
    ("PREV_DAY_SWEEP", r"previous day|previous-day|weekly-low sweep|sweep|reclaim|false.?break|failed breakdown"),
    ("FIBONACCI_OTE", r"fibonacci|\bote\b|optimal trade"), ("PIVOTS", r"pivot|camarilla|woodie"),
    ("WYCKOFF", r"wyckoff|spring|accumulation"), ("RSI_DIVERGENCE", r"divergen"), ("RSI_LEVELS", r"rsi 14 re-entry|rsi multi|stochrsi"),
    ("MEAN_REVERSION_BANDS", r"keltner|bollinger bands counter|envelope|linear regression channel|nadaraya|reversion|z-score|kalman|dca"),
    ("OSC_ZERO_CROSS", r"zero|cross|crossover|signal line|oscillator"), ("ML_KNN", r"lorentzian|machine learning|knn"),
    ("PATTERN_DETECTION", r"armonic|gartley|double bottom|double top|head and shoulders|triangle|wedge|flag|gann|fractal|zigzag|td sequential|demark"),
    ("MOMENTUM_RELATIVE_STRENGTH", r"momentum|relative strength|btc|lead lag|breadth|cross-sectional|top-gainer|gainer|mover"),
    ("NEWS_EVENT", r"noticias|news|ipc|cpi|fomc|nfp"), ("MANAGEMENT_NOT_SIGNAL", r"martingal|grid|hedg|125x|apalanc"),
    ("RANDOM_CONTROL", r"aleatori|random|sin plan|telegram|catch the falling|signals de"),
    ("HEIKIN_TREND", r"heikin"), ("HALFTREND_RANGEFILTER", r"halftrend|range filter|ut bot|ssl|qqe|waddah|wavetrend|vortex"),
]
INDRX = [(c, re.compile(p, re.I), t) for c, p, t in IND_RULES]
STRRX = [(c, re.compile(p, re.I)) for c, p in STR_RULES]


def concept_ind(name):
    for c, rx, t in INDRX:
        if rx.search(name):
            return c, t
    return "UNIQ_" + re.sub(r"\W+", "_", name.upper())[:30], ""


def concept_str(name, desc):
    for c, rx in STRRX:
        if rx.search(name):
            return c
    for c, rx in STRRX:
        if rx.search(desc):
            return c
    return "UNIQ_" + re.sub(r"\W+", "_", name.upper())[:30]


# ------------------------------------------------------------------ clasificacion Exness
EXT_RX = re.compile(r"order.?flow|footprint|\bcvd\b|delta|aggtrade|order book|depth|\bdom\b|open interest|\boi\b|funding|liquidation|"
                    r"long/short|taker|gamma|\bgex\b|opciones|options|\bcme\b|dark pool|whale|on-?chain|inflow|binance|put/call|"
                    r"implied vol|volatilidad implicita|\bvix\b|cvi|net volume|net buyer|flujo de .rdenes", re.I)
NEG_RX = re.compile(r"aleatori|random|martingal|grid trading|125x|sin stop loss|telegram|catch the falling|hedging arbitrario|"
                    r"sin plan|signals de", re.I)
PATTERN_RX = re.compile(r"armonic|harmonic|gartley|head and shoulders|double (top|bottom)|triangle|wedge|flag|pennant|pitchfork|gann|"
                        r"zigzag|fractals|trendlines|kagi|renko|point & figure|three line", re.I)
SMC_RX = re.compile(r"order block|fair value|\bfvg\b|breaker|mitigation|choch|change of character|market structure|liquidity pool|"
                    r"smart money concepts|\bote\b|optimal trade|wyckoff|supply (and|&) demand|spring|\bsmc\b|ict", re.I)
CROSS_RX = re.compile(r"btc|breadth|cross-sectional|top-gainer|lead lag|altcoin|top gainers|mover|sector|pares", re.I)
REPAINT_RX = re.compile(r"zigzag|fractals|trendlines|pitchfork|gann|harmonic|head and shoulders|double (top|bottom)|triangle|wedge|flag|"
                        r"kagi|renko|fibonacci|nadaraya|fft|fourier|empirical mode|divergence|divergencia|liquidity pool|breaker|mitigation|"
                        r"order block|pivot|point & figure|three line|supply", re.I)
HF_RX = re.compile(r"scalp|micro|\b1m\b|\b5m\b|1 minuto|en 1m|segundos|ultra-rápido|ultra-rapido", re.I)


def classify(e, kind):
    text = f"{e['name']} {e.get('desc','')} {e.get('note','')}"
    tags = []
    # etiquetas de datos
    if EXT_RX.search(text):
        tags.append("EXTERNAL_MICROSTRUCTURE_OR_DERIVS")
    if re.search(r"volume|volumen|\bvwap\b|obv|cmf|mfi|vfi|klinger|a/d|eom|vroc|poc", text, re.I):
        tags.append("TICK_VOLUME_PROXY")
    if CROSS_RX.search(text):
        tags.append("CRYPTO_UNIVERSE_OR_BTC_REFERENCE")
    if re.search(r"noticias|news|ipc|calendario", text, re.I):
        tags.append("NEWS_CALENDAR")
    if re.search(r"machine learning|knn|lorentzian|arima|garch|kalman|markov|train", text, re.I):
        tags.append("MODEL_FITTING")
    if not tags:
        tags.append("OHLC_MT5")
    # clase
    src = e["status_src"]
    if e["source"] == "A_REMIX":
        cls = {"Nativo MT5/OHLC": "IMPLEMENTABLE_CON_DATOS_MT5", "Condicional": "IMPLEMENTABLE_CON_CONDICIONES",
               "Proxy limitado": "IMPLEMENTABLE_CON_CONDICIONES", "Externo verificable": "REQUIERE_DATOS_EXTERNOS",
               "Excluir MVP": "NO_EVALUABLE_ACTUALMENTE"}[src]
        why = f"Clasificacion de la propia fuente A ({src}): {e.get('note','')}"
        if NEG_RX.search(text):
            cls, why = "CONTROL_NEGATIVO_O_RIESGO_INCOMPATIBLE", "Patron de riesgo/azar en el texto"
        return cls, why, tags
    if NEG_RX.search(text) or (e.get("wr_upper") is not None and e["wr_upper"] <= 30):
        return "CONTROL_NEGATIVO_O_RIESGO_INCOMPATIBLE", "Descrita por la fuente como estrategia de azar/riesgo extremo o de resultado esperado negativo (estimacion NO verificada; solo sirve para marcar candidato a control)", tags
    if "EXTERNAL_MICROSTRUCTURE_OR_DERIVS" in tags and not re.search(r"proxy|ohlcv_15m", src, re.I) or src == "REQUIERE_DATOS_EXTERNOS":
        return "REQUIERE_DATOS_EXTERNOS", "Necesita microestructura/derivados/opciones no provistos por MT5 CFD (no se sustituye por tick-volume)", tags
    if src == "NO_EVALUABLE_AUN" or "MODEL_FITTING" in tags and kind == "strategy" and src != "REGLA_CAUSAL_OPERATIVA_V1":
        return "NO_EVALUABLE_ACTUALMENTE", f"Definicion/datos insuficientes: {e.get('note','') or 'modelo o regla no especificados'}", tags
    if "NEWS_CALENDAR" in tags:
        return "REQUIERE_DATOS_EXTERNOS", "Requiere calendario de noticias verificable (el archivo exness_news_events.csv esta vacio)", tags
    reasons = []
    if "CRYPTO_UNIVERSE_OR_BTC_REFERENCE" in tags:
        reasons.append("referencia BTC/universo cripto: requiere rediseno para universo FX/metales (p.ej. fuerza relativa entre majors)")
    if SMC_RX.search(text):
        reasons.append("concepto discrecional (SMC/Wyckoff/OTE): exige definicion operativa causal y sin repintado")
    if PATTERN_RX.search(text):
        reasons.append("deteccion de patron/pivote: requiere retardo de confirmacion explicito")
    if "TICK_VOLUME_PROXY" in tags:
        reasons.append("volumen = tick-volume CFD (proxy, no volumen transado)")
    if src in ("PENDING_VERIFICATION", "FUENTE_O_ALGORITMO_NO_PUBLICADO"):
        reasons.append("formula no verificada/no publicada")
    if reasons:
        return "IMPLEMENTABLE_CON_CONDICIONES", "; ".join(reasons), tags
    return "IMPLEMENTABLE_CON_DATOS_MT5", "Reglas computables con OHLC/spread de MT5", tags


def causal_risk(e):
    t = f"{e['name']} {e.get('desc','')}"
    if e.get("risk_src") == "REPINTADO_O_CONFIRMACION_TARDIA" or REPAINT_RX.search(t):
        return "ALTO_REPINTADO_O_CONFIRMACION_TARDIA"
    if e.get("risk_src") == "VERIFICAR" or "no publicado" in e["status_src"].lower() or "NOPUB" in e["status_src"]:
        return "MEDIO_VERIFICAR_FORMULA"
    if re.search(r"multi-?timeframe|\bmtf\b|4h|1d|daily|diario|semanal|weekly", t, re.I):
        return "MEDIO_MTF_USAR_SOLO_BARRA_CERRADA"
    return "BAJO"


MARKET = {"A_REMIX": "Lista usuario (mixto FX/CFD; viabilidad Exness evaluada por la fuente)",
          "B_FUTURES_Z24": "Binance USDT-M Futures (perpetuos cripto)", "C_SPOT_S1": "Binance Spot / TradingView (cripto, tipicamente LONG-only)",
          "C_EXTRA": "Binance Spot (cripto, hipotesis nuevas)", "C_WEB": "Binance Spot (cripto, hipotesis web)",
          "LAB_USER_SPEC": "FX/CFD Exness (especificacion REMIX LAB)"}

rows_s, rows_i, rows_c = [], [], []
cs_group = defaultdict(list)
ci_group = defaultdict(list)
for e in strat:
    e["concept"] = concept_str(e["name"], e.get("desc", ""))
    cs_group[e["concept"]].append(e["id"])
for e in ind:
    e["concept"], e["equiv"] = concept_ind(e["name"])
    ci_group[e["concept"]].append(e["id"])


def vstate(e):
    return ("IMPLEMENTADO_EN_LAB_SIN_VALIDACION_OOS" if e["source"] == "LAB_USER_SPEC" else "HIPOTESIS_SIN_BACKTEST_EXNESS")


for e in strat:
    cls, why, tags = classify(e, "strategy")
    grp = cs_group[e["concept"]]
    srcs = sorted({g.split("_")[0] for g in grp})
    e.update(cls=cls, why=why, tags=tags)
    long_only = e["source"] in ("C_SPOT_S1", "C_EXTRA", "C_WEB")
    rows_s.append(dict(
        canonical_id=e["id"], original_id=e["orig_id"], source=e["source"], name=e["name"],
        market_original=MARKET[e["source"]], concept_group=e["concept"], group_size=len(grp),
        group_sources="+".join(srcs), is_cross_source_candidate_dup=int(len(srcs) > 1),
        entry_exit_logic=(e.get("desc") or e.get("note") or "")[:300], family=e.get("cat", ""),
        data_requirements="|".join(tags), source_status=e["status_src"], exness_class=cls,
        long_only_spot_redesign_needed=int(long_only), cost_sensitivity=("ALTA" if HF_RX.search(e["name"] + e.get("desc", "")) else "NORMAL"),
        validation_state=vstate(e), evidence_note="Winrate/rendimiento de la fuente NO verificados y NO importados"))
    rows_c.append(dict(canonical_id=e["id"], name=e["name"], exness_class=cls, reason=why, data_tags="|".join(tags),
                       causal_risk=causal_risk(e), negative_control_candidate=int(cls == "CONTROL_NEGATIVO_O_RIESGO_INCOMPATIBLE"),
                       min_lot_risk_note="Con 100 USD/0.5% el lote minimo puede exceder el riesgo: evaluar viabilidad por SL (ver LAB T001)"))

for e in ind:
    cls, why, tags = classify(e, "indicator")
    grp = ci_group[e["concept"]]
    srcs = sorted({g.split("_")[0] for g in grp})
    rows_i.append(dict(
        canonical_id=e["id"], original_id=e["orig_id"], source=e["source"], name=e["name"], category=e.get("cat", ""),
        concept_group=e["concept"], group_size=len(grp), group_sources="+".join(srcs),
        is_cross_source_candidate_dup=int(len(srcs) > 1), equivalence_note=("EQUIV_MATEMATICA_CONOCIDA" if e.get("equiv") else
                                                                             ("VARIANTE_O_DUPLICADO_POR_NOMBRE" if len(grp) > 1 else "")),
        formula_status=("NO_VERIFICADA" if e["source"] == "C_SPOT_S1" else "VER_ESTADO_FUENTE:" + e["status_src"]),
        data_requirements="|".join(tags), repaint_or_lookahead_risk=causal_risk({**e, "desc": ""}),
        exness_class=cls, limitation=why, source_status=e["status_src"]))
    rows_c.append(dict(canonical_id=e["id"], name=e["name"], exness_class=cls, reason=why, data_tags="|".join(tags),
                       causal_risk=causal_risk(e), negative_control_candidate=0, min_lot_risk_note=""))


def dump(path, rows):
    with open(R / path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


dump("CATALOG_STRATEGIES.csv", rows_s)
dump("CATALOG_INDICATORS.csv", rows_i)
dump("EXNESS_COMPATIBILITY_MATRIX.csv", rows_c)

# ------------------------------------------------------------------ estadisticas
fuentes = [e for e in strat if e["source"] != "LAB_USER_SPEC"]
stats = dict(
    strategies_raw=len(fuentes), indicators_raw=len(ind), lab_strategies=len(strat) - len(fuentes),
    by_source_strat=dict(Counter(e["source"] for e in fuentes)), by_source_ind=dict(Counter(e["source"] for e in ind)),
    strat_concepts_unique=len({e["concept"] for e in fuentes}), ind_concepts_unique=len({e["concept"] for e in ind}),
    strat_cross_source_groups=sum(1 for c, g in cs_group.items() if len({x.split('_')[0] for x in g}) > 1),
    ind_cross_source_groups=sum(1 for c, g in ci_group.items() if len({x.split('_')[0] for x in g}) > 1),
    class_strat=dict(Counter(r["exness_class"] for r in rows_s if not r["canonical_id"].startswith("LAB"))),
    class_ind=dict(Counter(r["exness_class"] for r in rows_i)),
    class_strat_by_source={s: dict(Counter(r["exness_class"] for r in rows_s if r["source"] == s)) for s in MARKET},
    class_ind_by_source={s: dict(Counter(r["exness_class"] for r in rows_i if r["source"] == s)) for s in ("A_REMIX", "B_FUTURES_Z24", "C_SPOT_S1")},
    top_cross_source_strat_groups=sorted(((c, len(g), sorted({x.split('_')[0] for x in g})) for c, g in cs_group.items()
                                          if len({x.split('_')[0] for x in g}) > 1), key=lambda x: -x[1])[:25],
    ind_equiv=[(c, g) for c, g in ci_group.items() if c == "SMMA_RMA_WILDER"],
    ind_top_groups=sorted(((c, len(g)) for c, g in ci_group.items()), key=lambda x: -x[1])[:15],
)
(R / "build_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: v for k, v in stats.items() if not k.startswith("top_") and k != "ind_equiv" and k != "ind_top_groups"},
                 indent=1, ensure_ascii=False))

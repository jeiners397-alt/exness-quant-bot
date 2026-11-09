"""SOURCE_MANIFEST.csv: inventario de documentos de trading en Drive. Solo registra lo observado en listados y lecturas de esta sesion.

read_status: LEIDO_COMPLETO | SOLO_METADATOS | NO_PROCESABLE_ZIP | NO_DESCARGADO_GRANDE | CARPETA_NO_ENUMERADA | CARPETA_ENUMERADA
relevance: ALTA (alimenta el catalogo/datos), MEDIA, BAJA, NULA_PARA_EXNESS
"""
import csv
from pathlib import Path

R = Path(__file__).resolve().parent.parent
URL_F = "https://drive.google.com/file/d/{}/view"
URL_D = "https://drive.google.com/drive/folders/{}"
ROOT = "REMIX FOREX V1 — Adaptive Quantitative Trading System"
B = "bot binance reversiones y estrategias. "
C = B + "/09_SPOT_EDGE_S1_INVESTIGACION"
D = "Bot_Trading_Binance_Data/Exness data"

# (nombre, id, ruta, tipo, tamano_bytes, creado, fuente, estado_lectura, relevancia, nota)
F = []
def f(*a): F.append(a)
def fo(name, id_, path, src, st="CARPETA_ENUMERADA", rel="MEDIA", note=""):
    F.append((name, id_, path, "carpeta", "", "", src, st, rel, note))

# ---- Fuente A
fo(ROOT, "10iMMgFDjMbk1CYpyMvC4dxrdyz7cBj5P", "(raiz)", "A", rel="ALTA")
for n, i in [("01_Documentación y planificación", "1TqZ_mY589qK_E6EKl1jqSsHdcO-RGM7d"), ("02_Código Python y MQL5", "16oIZrN_VNxrsHSrkQ72GvCwKrs3QT2QN"),
             ("05_Informes y auditorías", "1Z-AplyTcSmEiGqUu09GSRD6Rtf4qIIkf")]:
    fo(n, i, ROOT, "A")
fo("03_Datos históricos", "1PuMyX9DJ0HDnd9g_zndUD7vdj1F4AYCt", ROOT, "A", note="vacia al momento del listado")
fo("04_Backtests y resultados", "1bhDJMGeJleKxqBbmrwO328bTDxGCjoaX", ROOT, "A", note="vacia al momento del listado")
p1 = ROOT + "/01_Documentación y planificación"
for n, i, sz in [("01_REMIX_MASTER_PROMPT.md", "153ftS1mVeYgPL2JsEHXEOxX2UrmXp-uH", 8425), ("02_REMIX_DATA_PROTOCOL.md", "1XpaJ18LngyvECaCV8PgiHAYYd8ciRgkV", 8735),
                 ("03_REMIX_STRATEGY_LIBRARY.md", "1ITW3TyweZ1x7qwC4jmltjaHDHZmLnRyc", 9481), ("04_REMIX_BACKTEST_PROTOCOL.md", "10ADbQOcafUj2h5Gv99MHuYmOKbr8boLP", 8984),
                 ("05_REMIX_RISK_ENGINE.md", "1fwGG1SfuDcX7zGovWX17e9W4jowkeUkr", 6265), ("06_REMIX_REGIME_ENGINE.md", "1InKEhaJvTjo1JMEdWtIx4bE1w5DyAEW3", 5205),
                 ("07_REMIX_MQL5_ARCHITECTURE.md", "1W7479la3ioLr8UCnHjzRA4HDJGvGKRS2", 6771)]:
    f(n, i, p1, "md", sz, "2026-11-08", "A", "SOLO_METADATOS", "ALTA", "especificacion 1-7 de 8; pendiente de lectura selectiva")
f("AUDITORIA_FUENTES_DRIVE_REMIX_2026-11-09.md", "1W4iSR4UNbRmdj0T3Tr7nmfWAai9Zs8_6", p1, "md", 7429, "2026-11-09", "A", "LEIDO_COMPLETO", "ALTA", "auditoria exploratoria previa (ChatGPT)")
f("INFORME_DISENO_Y_RESEARCH_V1.md", "13ZxrXW8Rj4lo9MOJEzCWUjKd01Z2FGXb", p1, "md", 25698, "2026-11-08", "A", "SOLO_METADATOS", "ALTA", "12 familias preliminares")
f("README_FASE0.md", "1zNyj_d6lG_qXyDuLuEjj-NQwJN69xcyZ", p1, "md", 4330, "2026-11-08", "A", "SOLO_METADATOS", "MEDIA", "")
for n, i, sz in [("REMIX_FOREX_V1_MASTER_SPECIFICATION_2026-11-08.zip", "1QFKFHkCYb30agHRcYZanlMjF44oY6ARq", 30313),
                 ("REMIX_FOREX_V1_DISENO_RESEARCH_2026-11-08.zip", "19r837Qyafuqyumd5kmyvfb1wb-X_itFO", 41283),
                 ("REMIX_FOREX_V1_ARCHIVOS_PARA_CLAUDE.zip", "14aCao5Gibsn5AwiW6mlEGdsf8mjAVcwD", 86696)]:
    f(n, i, p1, "zip", sz, "2026-11-08", "A", "NO_PROCESABLE_ZIP", "MEDIA", "el conector no descomprime; contenido probablemente duplica los .md")
p2 = ROOT + "/02_Código Python y MQL5"
f("REMIX_FOREX_V1_TRANSFER_GITHUB.md", "1awxKlS-Xr5NRp-GRJeab9SERCt-PMegb", p2, "md", 29098, "2026-11-08", "A", "SOLO_METADATOS", "MEDIA", "traspaso fase 0")
f("REMIX_FOREX_V1_FASE0_ENTREGABLE.zip", "1qR2dUJIQjyb-3Hr7S4oerqmk-YjcG7YW", p2, "zip", 13476, "2026-11-08", "A", "NO_PROCESABLE_ZIP", "BAJA", "")
p5 = ROOT + "/05_Informes y auditorías"
f("MATRIZ_200_ESTRATEGIAS_INDICADORES.xlsx", "10h3QJrsO02fLo-9-Vn6VmIW5uy6Y8_Qu", p5, "xlsx", 31012, "2026-11-08", "A", "LEIDO_COMPLETO", "ALTA", "100 estrategias + 100 indicadores verificados (parser research/tools/parse_remix_matrix.py)")
f("08_REMIX_AUDIT_PROTOCOL.md", "1RblKTdJsx6xMWN3rvMLofmOhOELI3zGT", p5, "md", 6863, "2026-11-08", "A", "SOLO_METADATOS", "ALTA", "especificacion 8 de 8")
f("INFORME_FASE0.md", "1iIHyyidfCCbJd8t7DOyONkWOg8b3zcQL", p5, "md", 2857, "2026-11-08", "A", "SOLO_METADATOS", "MEDIA", "")
f("_CLAUDE_WRITE_TEST_2026-11-09.txt", "1-YSNLqY8iftjh33dVBP6hdXFKQWqjqFY", p5, "txt", 86, "2026-11-09", "CLAUDE", "LEIDO_COMPLETO", "NULA_PARA_EXNESS", "archivo de prueba de escritura creado por Claude; puede borrarse")
# ---- Fuente B
fo(B, "1k3DYzXSvffGm0O9IsS_t6I_r0uKUBhSP", "(My Drive)", "B", rel="ALTA", note="contenido de subcarpetas Z24/Z25/Z25B/Z1/COLAB sin enumerar")
for n, i in [("01_CODIGO_Y_VERSIONES", "1hu9TouyJoQXO7yGFFsUf2TpXVd0p0EIX"), ("02_CATALOGOS_Y_PROMPTS", "1cagCDSmfvQeEZ0Vw24kX9joe3fKb8xxU"),
             ("03_AUDITORIAS_Y_EXPORTADORES", "17sg2U39GClXsyBG25vWf57QpESy7RybP"), ("04_HISTORICOS_500_PARES_PENDIENTE", "16z132IqPpdHsgq3S9q14bSUj2FyTKktL"),
             ("05_CUADERNOS_GOOGLE_COLAB", "1yCD2A6JUQlimFruFXErbAFPna4AG4dx1"), ("06_RESULTADOS_COLAB", "1KnjxSbNSv_ERd6bYX8ra0HZtzvKpYz2S"),
             ("07_REVERSE_EDGE_Z25", "1jgBuZtrQMCXomOVV6YCYZ_mIoTcJzkxt"), ("08_REVERSE_EDGE_Z25B", "1xDsA4cwt0HbDfkDLYH1YARQQLkQ_Z2gm"),
             ("REVERSE_EDGE_Z24_200_INDICADORES_100_ESTRATEGIAS", "1YufLsiGWhwAhMEfWpdyxQW8Jj6TTe8KW"), ("REVERSE_EDGE_Z1_500_PARES", "1tg66Mx4RaOp6ticuxlfF2CwFL5nRc6Zj"),
             ("REVERSE_EDGE_Z24", "1CMSZEC-QGhctlnKDZgkgv0TvSl_mKIjp")]:
    fo(n, i, B, "B", st="CARPETA_NO_ENUMERADA", rel="MEDIA", note="pendiente de enumeracion; resultados Binance no transferibles a Exness sin revalidar")
fo("09_SPOT_EDGE_S1_INVESTIGACION", "1LjH2nRlylRxOxnm0D04E0RYbVf_lWMAY", B, "C", rel="ALTA")
bc = B + "/02_CATALOGOS_Y_PROMPTS"
for n, i, sz, st in [("ESTADO_ESTRATEGIAS_100.csv (v. mas antigua 19:02)", "1LwF80SUXp4meyxoQIw8zjuzm8f8JqJZ1", 20362, "SOLO_METADATOS"),
                     ("ESTADO_INDICADORES_200.csv (v. mas antigua 19:02)", "1Zehk9dirxcAQQd4ozu8wx11amEXGg5L1", 32352, "SOLO_METADATOS")]:
    f(n, i, bc, "csv", sz, "2026-11-06", "B", st, "MEDIA", "version con tamano distinto: deriva de versiones")
f("ESTADO_ESTRATEGIAS_100.csv (v. 19:44)", "1sEvnxYOQcqaIXmEckQ4yPgQzGpnWH_au", B + "/(carpeta 1-PFtYAWJ...)", "csv", 20544, "2026-11-06", "B", "SOLO_METADATOS", "MEDIA", "version intermedia")
f("ESTADO_INDICADORES_200.csv (v. 19:44)", "1mHjgnJOErW2Y_QG_1BS3UM3orpTV-umV", B + "/(carpeta 1-PFtYAWJ...)", "csv", 33539, "2026-11-06", "B", "SOLO_METADATOS", "MEDIA", "version intermedia")
f("ESTADO_ESTRATEGIAS_100.csv (v. 21:01, la mas reciente)", "1SOw-luWae8euXNu0LDYYnTx2MjeUK4IS", B + "/(carpeta 1xRb6Gwq...)", "csv", 20645, "2026-11-06", "B", "LEIDO_COMPLETO", "ALTA", "USADA para el catalogo (transcripcion compacta en research/_staging/B_strategies.txt)")
f("ESTADO_INDICADORES_200.csv (v. 21:01, la mas reciente)", "1OksLS1bawMSokNiHB9pKngzjUrT31EdV", B + "/(carpeta 1xRb6Gwq...)", "csv", 33740, "2026-11-06", "B", "LEIDO_COMPLETO", "ALTA", "USADA; DEFECTO: columna funcion_ta_opcional desplazada en filas 54-70")
f("FUENTE_ORIGINAL_200_INDICADORES_100_ESTRATEGIAS.txt", "1n-oybnNhwVKV_1GCXE-vDlYAnDKbN3lO", B + "/REVERSE_EDGE_Z24_.../REVERSE_EDGE_Z24", "txt", 34037, "2026-11-06", "B", "SOLO_METADATOS", "ALTA", "origen literal; pendiente de lectura para contrastar con ESTADO_*")
f("estrategias_fuente_100.csv", "1vPq-DKvGyRLnjR50EyFn1UMJBiNCwMk4", B + "/(carpeta 1X2nwxWw...)", "csv", 13618, "2026-11-06", "B", "SOLO_METADATOS", "MEDIA", "")
f("ESTRATEGIAS.md", "1sJwm1Sw-JXEpGGHxQ7Y6aeu2Rqfls5Xn", B + "/(carpeta 1-yjOh8f...)", "md", 1377, "2026-11-06", "B", "SOLO_METADATOS", "BAJA", "")
f("backtest_engine.py", "1mGPn30Upkvubwuakn7eeT1jcmOYwg6z6", C + "/SPOT_EDGE_S1_V3_SRC/(subcarpeta)", "py", 5274, "2026-11-07", "C", "SOLO_METADATOS", "MEDIA", "motor Binance Spot; no reutilizar sin auditoria")
# ---- Fuente C
for n, i, sz, st, rel, note in [
    ("CATALOGO_ESTRATEGIAS_200.json", "1qdZkgEdNKPsLqfoAsnMPSxSXsM-LNA7d", 66956, "LEIDO_COMPLETO", "ALTA", "200 estrategias, status UNVERIFIED_USER_ESTIMATE_NOT_BACKTESTED"),
    ("CATALOGO_INDICADORES_200.json", "1nGYV4I3CSGRNTv8lSjRwSxX6Buyf8UqS", 41174, "LEIDO_COMPLETO", "ALTA", "200 indicadores, PENDING_VERIFICATION"),
    ("03_EXTRAS_36_HIPOTESIS.csv", "1_GHnuAI5A0V0v_cYP-RqIuxbcP8zdFuh", 10330, "LEIDO_COMPLETO", "ALTA", "36 hipotesis"),
    ("04_NUEVAS_12_WEB.csv", "1u1wet3I0A2x9qWvy9xPMd6SPlT14oQUw", 3392, "LEIDO_COMPLETO", "ALTA", "12 hipotesis web"),
    ("01_RANKING_200_ESTRATEGIAS.csv", "1W32ViAmipGBFQUFnqRJ4aiznSJoMbzOR", 49476, "SOLO_METADATOS", "BAJA", "ranking nominal, no evidencia; no leido"),
    ("02_RANKING_200_INDICADORES.csv", "13vHiHlB5G5DQYGUHU5iN8um1SklrhG7e", 38226, "SOLO_METADATOS", "BAJA", "ranking nominal; no leido"),
    ("LISTA_ORIGINAL_USUARIO_200_INDICADORES_200_ESTRATEGIAS.txt", "1by-qDjBtj8h6JCKw10CUDjGjS91uLAmr", 51723, "SOLO_METADATOS", "ALTA", "origen literal; pendiente de contraste con los JSON"),
    ("ESTRATEGIAS_ADICIONALES_36_HIPOTESIS.json", "1sn5XB8HZ0Ergwd-rgGpJjt5egkAX6Pta", 16730, "SOLO_METADATOS", "MEDIA", "copia JSON de los 36 extras (hay otra copia en registry_source)"),
    ("SPOT_EDGE_60D_RANKING_448_Y_PROTOCOLO.xlsx", "1_j2qi7_RzfCO0OoueN6iQ6ugpEi3oAYV", 46561, "SOLO_METADATOS", "MEDIA", "ranking 448 + protocolo; no leido"),
    ("PROTOCOLO_180D_DOS_BRAZOS_100_USDT.md", "1nSvB4pBDDiBx2jaL7_Uf9V57_U1u1Kr0", 9804, "SOLO_METADATOS", "MEDIA", "protocolo metodologico Binance"),
    ("SCHEMA_DATOS_COMPLETO_CHATGPT.md", "1rA9UOuC2wd22QN3zGc1cxessDhz7d2Rh", 4851, "SOLO_METADATOS", "BAJA", ""),
    ("FUENTES_Y_EVIDENCIA_WEB.md", "1rGpSUKC5YfhrcnQBjD_5kzClq-gKAHyu", 2552, "SOLO_METADATOS", "MEDIA", "procedencia de las 12 hipotesis web"),
    ("PRUEBAS_ACEPTACION.txt", "1y6YUcHkTG2jhb6xjILfLiZ76q63Pkokd", 2189, "SOLO_METADATOS", "BAJA", ""),
    ("MANIFEST_V2.json", "19ENLQq0gPJ_56F9DSX8cH2NDBP1ZYxm3", 1636, "SOLO_METADATOS", "BAJA", ""),
    ("MANIFEST_BRIEF.json", "11pBNKKA2uEGWgAoA53VFoj6vTjAiWBvf", 750, "SOLO_METADATOS", "BAJA", ""),
    ("LEEME_PRIMERO.txt", "1aR-d8rakeKJ6U4u33fyM9IJZWOx13XY8", 1210, "SOLO_METADATOS", "BAJA", ""),
    ("LEEME_PARA_ENVIAR_A_CLAUDE.txt", "1muyfuWzBS_am9QgH7epBRft3kXlUTQAT", 805, "SOLO_METADATOS", "BAJA", ""),
    ("PROMPT_CLAUDE_SPOT_EDGE_S1.txt", "1dDEtjKHuveqdyiyN0711uQtwej4JQa1c", 14583, "SOLO_METADATOS", "BAJA", "prompt de otro proyecto"),
    ("PROMPT_CLAUDE_SPOT_EDGE_S1_V2.txt", "1-xFEy1jiFg6W7G2-FuvtT3X5pdkznaDX", 14549, "SOLO_METADATOS", "BAJA", "prompt de otro proyecto"),
]:
    f(n, i, C, n.rsplit(".", 1)[-1], sz, "2026-11-07", "C", st, rel, note)
for n, i, sz in [("SPOT_EDGE_S2_RESULTADOS_FULL_60D_69_PARES.zip", "13a1-VPMvcQNy363irVIb06SLRoVkywRg", 249801),
                 ("SPOT_EDGE_S1_V2_ENCARGO_CLAUDE_180D.zip", "1xOJLb20KIyzZ684oGLfaCwXVGYoUMA8m", 67649),
                 ("SPOT_EDGE_S1_ENCARGO_CLAUDE_200x200.zip", "1ivI-HxRSAkDNyguwdq4SDjygHIDCE1_Z", 44439)]:
    f(n, i, C, "zip", sz, "2026-11-07", "C", "NO_PROCESABLE_ZIP", "MEDIA", "resultados/encargos Binance Spot; NO transferibles; sin inspeccionar")
fo("registry_source", "14YeLDaAAfUz-834UrQ7__grSY9xq4k9w", C, "C", st="CARPETA_NO_ENUMERADA")
fo("SPOT_EDGE_S1_V3_SRC", "14pVuWMZdB4b8uheeEuWRHxoC-kn5pjUE", C, "C", st="CARPETA_NO_ENUMERADA")
# ---- Fuente D y adicionales
fo("Bot_Trading_Binance_Data", "1EqAqK6ddgfdc_FHSLissz1H77SM1Ej3q", "(My Drive)", "D", rel="ALTA")
fo("Exness data", "1GZTJZsi7A5zv9Y4o9kkYCnkVMuK349_d", "Bot_Trading_Binance_Data", "D", rel="ALTA")
f("exness_institutional_v1.db", "1ViMcQwXZxvEQjMhJmQfhh4RDZFEUJ4qV", D, "db(octet-stream)", 535846912, "2026-10-18", "D", "NO_DESCARGADO_GRANDE", "MEDIA",
  "536 MB; el conector no expone esquema; NO descargado. Segun el log: M1/M5/H1/H4 de 11 simbolos, ~100k filas max/serie, etiquetas BUY/SELL/HOLD DERIVADAS (no operaciones reales)")
f("exness_mt5_extractor.log", "1KkLHIOXuV8ijyxznMzmUBV684N59hs3_", D, "log", 6594, "2026-10-18", "D", "LEIDO_COMPLETO", "ALTA",
  "extraccion 2026-10-18 desde este terminal/cuenta demo; maxbars=100000; simbolos BTC,ETH,SOL,XRP,XAU,XAG,US30,USTEC,EUR,GBP,JPY (sufijo m)")
f("exness_news_events.csv", "11a73AgE_9fWQYtxDfyilB4CwOgkaDbiX", D, "csv", 36, "2026-10-18", "D", "LEIDO_COMPLETO", "BAJA", "SOLO cabecera datetime_utc,event,impact,currency: 0 eventos. No usar 0 como ausencia de noticias")
f("analizar_atr_costes.py", "1N9nfQ4jqBQx_VlPzpaLheNC8id0m-vPl", "Bot_Trading_Binance_Data", "py", 12170, "2026-10-27", "D", "SOLO_METADATOS", "MEDIA", "analisis ATR vs costes; relacionado con Exness; pendiente de lectura")
f("análisis exness data (Colab)", "1_EbmHFNMiTzdo9H_sxWjlgLOivDWsnz-", "(carpeta 1d9kq6id...)", "colab", 48741, "2026-10-18", "D", "SOLO_METADATOS", "MEDIA", "cuaderno de analisis de los datos Exness")
f("ANALISIS ESTADISTICO DE BINANCE FUTUROS (Colab)", "1FYe8-38TUqh8AYBUZpeTrbxT2nPvL4R2", "(carpeta 1d9kq6id...)", "colab", 242195, "2026-10-18", "B", "SOLO_METADATOS", "BAJA", "Binance Futures")
f("binance futuros trabajo (Colab)", "1j4bY4onbr6EQdiREURV8o4u-JsZz3dOM", "(carpeta 1d9kq6id...)", "colab", 324, "2026-11-06", "B", "SOLO_METADATOS", "BAJA", "")
f("bot binance futuros reversiones y estrategias (proyecto Drive)", "1zxb-KWz04Iym9_UTGwV3wS_Sb2hXocsZ", "(My Drive)", "drive-project", "", "2026-11-06", "B", "CARPETA_NO_ENUMERADA", "MEDIA", "")
fo("bot de binance prueba", "1ia0ImNkWUJGAPrAODkm-4VCwVdgm5a7G", "Bot_Trading_Binance_Data", "otro", st="CARPETA_NO_ENUMERADA", rel="BAJA")
fo("binance data 360", "1tTzhxULGe_CXKi1Q322xpgpKpDoP2_8l", "Bot_Trading_Binance_Data", "otro", st="CARPETA_NO_ENUMERADA", rel="BAJA", note="datos Binance; irrelevantes para Exness")

hdr = ["name", "drive_id", "url", "path", "type", "size_bytes", "created_date", "source", "read_status", "relevance", "note"]
with open(R / "SOURCE_MANIFEST.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(hdr)
    for n, i, p, t, sz, d, s, st, rel, note in F:
        url = (URL_D if t == "carpeta" else URL_F).format(i) if t not in ("colab", "drive-project") else f"https://drive.google.com/open?id={i}"
        w.writerow([n, i, url, p, t, sz, d, s, st, rel, note])
print(len(F), "filas;", {k: sum(1 for x in F if x[7] == k) for k in sorted({x[7] for x in F})})

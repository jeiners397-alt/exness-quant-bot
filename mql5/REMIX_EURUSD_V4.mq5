//+------------------------------------------------------------------+
//| REMIX_EURUSD_V4.mq5 - controlador de margen/lotaje/multiposicion  |
//| SOLO Strategy Tester. NINGUNA ESTRATEGIA TIENE VENTAJA DEMOSTRADA.|
//|                                                                   |
//| Que verifica (ordenes V4):                                        |
//|  - margen comprometido por simbolo <= MarginPct % de la EQUIDAD   |
//|    (posiciones + ordenes pendientes + la nueva), via OrderCalcMargin|
//|  - riesgo al SL (OrderCalcProfit) limitado por RiskPercent, independiente del margen|
//|  - volumen respetando SYMBOL_VOLUME_MIN/MAX/STEP; nunca se redondea|
//|    hacia arriba; minimo preferido 0,01 (no obligatorio)           |
//|  - varias posiciones simultaneas (cuenta hedging) y SL dinamico    |
//|    (estructural / ATR / ajustado por regimen)                     |
//| Modulos: V4_NONE (no opera) | V4_DIAG_MULTI (DIAGNOSTICO sintetico: |
//|  abre compras periodicas para estresar el controlador; NO es una  |
//|  estrategia ni busca beneficio).                                  |
//| Defecto: Module=V4_NONE, EnableTrading=false.                     |
//+------------------------------------------------------------------+
#property copyright "REMIX V4"
#property version   "4.00"
#property strict

#include <Trade\Trade.mqh>

enum ENUM_V4_MODULE { V4_NONE = 0, V4_DIAG_MULTI = 1 };

input group "=== Seguridad ==="
input ENUM_V4_MODULE Module      = V4_NONE;
input bool   EnableTrading       = false;     // solo Strategy Tester
input long   MagicNumber         = 20260401;
input group "=== Margen y riesgo (independientes) ==="
input double MarginPct           = 5.0;       // % de EQUIDAD de margen comprometido maximo POR SIMBOLO
input double GlobalMarginPct     = 15.0;      // limite global (todas las posiciones del EA)
input double RiskPercent         = 0.50;      // perdida maxima al SL por operacion (% equidad)
input double MaxTotalRiskPct     = 5.0;       // riesgo agregado al SL maximo (% equidad)
input bool   CheckPendingOrders  = true;
input bool   AllowMultiple       = true;
input int    MaxPositions        = 20;
input group "=== Diagnostico (V4_DIAG_MULTI) ==="
input int    DiagEveryBars       = 3;         // abre una operacion cada N barras
input int    DiagMaxHoldBars     = 60;        // cierre temporal
input double DiagRR              = 1.5;
input int    DiagPendingEvery    = 4;         // cada K-esima senal es BUY_LIMIT (prueba de ordenes pendientes); 0 = nunca
input int    ATR_N               = 14;
input double SL_ATR_Mult         = 1.5;
input int    SL_StructLookback   = 10;
input double SL_StructBufATR     = 0.1;
input double SL_MinATR           = 0.7;
input double SL_MaxATR           = 3.0;

CTrade   trade;
int      h_atr = INVALID_HANDLE;
datetime g_last_bar = 0;
long     g_sig = 0, g_open = 0, g_rej_margin = 0, g_rej_risk = 0, g_rej_minlot = 0, g_rej_pos = 0, g_pend = 0;
double   g_max_sym_margin_pct = 0.0, g_max_lots = 0.0, g_min_lots = 1e9, g_max_total_risk_pct = 0.0;
int      g_max_conc = 0;
string   g_log = "";

//+------------------------------------------------------------------+
bool TradingAllowed()
  {
   if(!MQLInfoInteger(MQL_TESTER))
      return false;
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return false;
   return EnableTrading && Module != V4_NONE;
  }
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     { Print("REMIX V4: BLOQUEADO fuera del Strategy Tester."); return INIT_FAILED; }
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return INIT_FAILED;
   if(MarginPct <= 0 || MarginPct > 100 || RiskPercent <= 0 || RiskPercent > 2.0)
      return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(20);
   trade.SetTypeFillingBySymbol(_Symbol);
   h_atr = iATR(_Symbol, _Period, ATR_N);
   if(h_atr == INVALID_HANDLE)
      return INIT_FAILED;
   g_log = StringFormat("REMIX_V4_margin_%s_%s.csv", _Symbol, EnumToString(_Period));
   FileDelete(g_log, FILE_COMMON);
   PrintFormat("REMIX V4 init | Module=%d | Trading=%d | %s | margin<=%.1f%% equity | risk<=%.2f%% | volmin=%.2f step=%.2f",
               (int)Module, (int)EnableTrading, _Symbol, MarginPct, RiskPercent,
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP));
   return INIT_SUCCEEDED;
  }
//+------------------------------------------------------------------+
void Log(const string ev, const string reason, const long ticket, const double lots, const double m_new, const double m_sym_before,
         const double budget, const double loss, const double sl_dist, const string slmode)
  {
   int fh = FileOpen(g_log, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
      return;
   if(FileSize(fh) == 0)
      FileWriteString(fh, "time,event,reason,ticket,lots,margin_new,margin_symbol_before,margin_symbol_after,budget,margin_pct_after,loss_at_sl,risk_pct,sl_dist,sl_mode,n_positions,n_pending,equity,balance,volmin,volstep\n");
   FileSeek(fh, 0, SEEK_END);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double after = m_sym_before + (ev == "OPEN" || ev == "PENDING" ? m_new : 0.0);
   FileWriteString(fh, StringFormat("%s,%s,%s,%I64d,%.2f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.5f,%s,%d,%d,%.2f,%.2f,%.2f,%.2f\n",
                   TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), ev, reason, ticket, lots, m_new, m_sym_before, after, budget,
                   eq > 0 ? 100.0 * after / eq : 0.0, loss, eq > 0 ? 100.0 * loss / eq : 0.0, sl_dist, slmode, CountPositions(), CountPending(), eq,
                   AccountInfoDouble(ACCOUNT_BALANCE), SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP)));
   FileClose(fh);
  }
//+------------------------------------------------------------------+
int CountPositions()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
         n++;
     }
   return n;
  }
int CountPending()
  {
   int n = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetInteger(ORDER_MAGIC) == MagicNumber)
         n++;
     }
   return n;
  }
//+------------------------------------------------------------------+
// margen comprometido (posiciones + pendientes) del simbolo; all=true => todos los simbolos del EA
double CommittedMargin(const bool all)
  {
   double tot = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      string s = PositionGetString(POSITION_SYMBOL);
      if(!all && s != _Symbol)
         continue;
      double m = 0.0;
      ENUM_ORDER_TYPE ot = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(OrderCalcMargin(ot, s, PositionGetDouble(POSITION_VOLUME), PositionGetDouble(POSITION_PRICE_OPEN), m))
         tot += m;
     }
   if(CheckPendingOrders)
      for(int i = OrdersTotal() - 1; i >= 0; i--)
        {
         ulong t = OrderGetTicket(i);
         if(t == 0 || OrderGetInteger(ORDER_MAGIC) != MagicNumber)
            continue;
         string s = OrderGetString(ORDER_SYMBOL);
         if(!all && s != _Symbol)
            continue;
         double m = 0.0;
         ENUM_ORDER_TYPE ot = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
         ENUM_ORDER_TYPE mt = (ot == ORDER_TYPE_BUY_LIMIT || ot == ORDER_TYPE_BUY_STOP) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
         if(OrderCalcMargin(mt, s, OrderGetDouble(ORDER_VOLUME_CURRENT), OrderGetDouble(ORDER_PRICE_OPEN), m))
            tot += m;
        }
   return tot;
  }
//+------------------------------------------------------------------+
// riesgo agregado al SL de posiciones abiertas (moneda de cuenta)
double OpenRiskMoney()
  {
   double tot = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      double sl = PositionGetDouble(POSITION_SL), op = PositionGetDouble(POSITION_PRICE_OPEN), p = 0.0;
      if(sl <= 0)
         continue;
      ENUM_ORDER_TYPE ot = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(OrderCalcProfit(ot, PositionGetString(POSITION_SYMBOL), PositionGetDouble(POSITION_VOLUME), op, sl, p) && p < 0)
         tot += -p;
     }
   return tot;
  }
//+------------------------------------------------------------------+
double FloorStep(const double v, const double step)
  {
   if(v <= 0 || step <= 0)
      return 0.0;
   return NormalizeDouble(MathFloor(v / step + 1e-9) * step, 8);
  }
//+------------------------------------------------------------------+
// Lotaje: min(margen disponible, riesgo permitido, volumen max). Devuelve 0 y el motivo si no cabe el minimo valido.
double SizeLots(const ENUM_ORDER_TYPE ot, const double price, const double sl, string &reason, double &m_new, double &loss_new)
  {
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double m1 = 0.0, p1 = 0.0;
   if(!OrderCalcMargin(ot, _Symbol, 1.0, price, m1) || m1 <= 0.0 || !OrderCalcProfit(ot, _Symbol, 1.0, price, sl, p1) || p1 >= 0.0)
     { reason = "CALC_FAIL"; return 0.0; }
   double l1 = -p1;
   double avail_sym = MathMax(0.0, eq * MarginPct / 100.0 - CommittedMargin(false));
   double avail_glob = MathMax(0.0, eq * GlobalMarginPct / 100.0 - CommittedMargin(true));
   double avail = MathMin(avail_sym, avail_glob);
   double risk_left = MathMax(0.0, eq * MaxTotalRiskPct / 100.0 - OpenRiskMoney());
   double lots_m = FloorStep(avail / m1, step);
   double lots_r = FloorStep(MathMin(eq * RiskPercent / 100.0, risk_left) / l1, step);
   double lots = MathMin(MathMin(lots_m, lots_r), vmax);
   if(lots < vmin - 1e-12)
     {
      reason = (lots_m < vmin) ? "MARGIN_BUDGET" : "RISK_LIMIT";
      return 0.0;
     }
   lots = NormalizeDouble(lots, 8);
   if(!OrderCalcMargin(ot, _Symbol, lots, price, m_new) || !OrderCalcProfit(ot, _Symbol, lots, price, sl, loss_new))
     { reason = "CALC_FAIL"; return 0.0; }
   loss_new = -loss_new;
   // re-verificacion con el volumen final contra el presupuesto agregado
   if(CommittedMargin(false) + m_new > eq * MarginPct / 100.0 + 1e-9) { reason = "MARGIN_BUDGET"; return 0.0; }
   if(CommittedMargin(true) + m_new > eq * GlobalMarginPct / 100.0 + 1e-9) { reason = "MARGIN_GLOBAL"; return 0.0; }
   reason = "OK";
   return lots;
  }
//+------------------------------------------------------------------+
// SL dinamico: modo 0 estructural, 1 ATR, 2 ajustado por regimen de volatilidad (percentil del ATR en 100 barras)
double DynamicSLDist(const int mode, const double atr, string &name)
  {
   double d = 0.0;
   if(mode == 0)
     {
      name = "STRUCT";
      double lo = iLow(_Symbol, _Period, iLowest(_Symbol, _Period, MODE_LOW, SL_StructLookback, 1));
      d = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - lo + SL_StructBufATR * atr;
     }
   else if(mode == 1)
     { name = "ATR"; d = SL_ATR_Mult * atr; }
   else
     {
      name = "REGIME";
      double a[];
      ArraySetAsSeries(a, true);
      int n = CopyBuffer(h_atr, 0, 1, 100, a);
      int below = 0;
      for(int i = 0; i < n; i++)
         if(a[i] <= atr)
            below++;
      double pct = n > 0 ? (double)below / n : 0.5;
      d = SL_ATR_Mult * atr * (pct > 0.8 ? 1.25 : (pct < 0.2 ? 0.85 : 1.0));
     }
   return MathMin(MathMax(d, SL_MinATR * atr), SL_MaxATR * atr);   // nunca ultrapegado ni ampliado sin limite
  }
//+------------------------------------------------------------------+
//| UNICO sitio de aperturas/pendientes                               |
//+------------------------------------------------------------------+
void OpenTrade(const bool pending, const double sl_dist, const string slmode)
  {
   if(!TradingAllowed())
      return;
   g_sig++;
   double budget = AccountInfoDouble(ACCOUNT_EQUITY) * MarginPct / 100.0, msym = CommittedMargin(false);
   if(CountPositions() + CountPending() >= MaxPositions || (!AllowMultiple && CountPositions() > 0))
     { g_rej_pos++; Log("REJECT", "MAX_POSITIONS", 0, 0, 0, msym, budget, 0, sl_dist, slmode); return; }
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double price = pending ? NormalizeDouble(ask - 0.5 * sl_dist, _Digits) : ask;
   double sl = NormalizeDouble(price - sl_dist, _Digits), tp = NormalizeDouble(price + DiagRR * sl_dist, _Digits);
   string reason; double m_new = 0.0, loss = 0.0;
   double lots = SizeLots(ORDER_TYPE_BUY, price, sl, reason, m_new, loss);
   if(lots <= 0.0)
     {
      if(reason == "MARGIN_BUDGET" || reason == "MARGIN_GLOBAL") g_rej_margin++;
      else if(reason == "RISK_LIMIT") g_rej_risk++;
      else g_rej_minlot++;
      Log("REJECT", reason, 0, 0, 0, msym, budget, 0, sl_dist, slmode);
      return;
     }
   bool ok;
   string cmt = "REMIX V4 " + slmode;
   if(pending)
      ok = trade.BuyLimit(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt);
   else
      ok = trade.Buy(lots, _Symbol, 0.0, sl, tp, cmt);
   uint rc = trade.ResultRetcode();
   if(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED))
     {
      if(pending) g_pend++; else g_open++;
      double msym_after = msym + m_new;
      g_max_sym_margin_pct = MathMax(g_max_sym_margin_pct, 100.0 * msym_after / AccountInfoDouble(ACCOUNT_EQUITY));
      g_max_lots = MathMax(g_max_lots, lots);
      g_min_lots = MathMin(g_min_lots, lots);
      g_max_conc = MathMax(g_max_conc, CountPositions() + CountPending());
      g_max_total_risk_pct = MathMax(g_max_total_risk_pct, 100.0 * (OpenRiskMoney()) / AccountInfoDouble(ACCOUNT_EQUITY));
      Log(pending ? "PENDING" : "OPEN", "OK", (long)(pending ? trade.ResultOrder() : trade.ResultDeal()), lots, m_new, msym, budget, loss, sl_dist, slmode);
     }
   else
     {
      PrintFormat("REMIX V4: orden rechazada ret=%u (%s)", rc, trade.ResultRetcodeDescription());
      Log("ORDER_FAILED", IntegerToString((int)rc), 0, lots, m_new, msym, budget, loss, sl_dist, slmode);
     }
  }
//+------------------------------------------------------------------+
void CloseOld()
  {
   if(!TradingAllowed())
      return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      int shift = iBarShift(_Symbol, _Period, (datetime)PositionGetInteger(POSITION_TIME), false);
      if(shift >= DiagMaxHoldBars)
         trade.PositionClose(t);
     }
  }
//+------------------------------------------------------------------+
void OnTick()
  {
   datetime bt = iTime(_Symbol, _Period, 0);
   if(bt == g_last_bar)
      return;
   g_last_bar = bt;
   CloseOld();
   if(!TradingAllowed() || Module != V4_DIAG_MULTI)
      return;
   static long bars = 0;
   bars++;
   if(DiagEveryBars <= 0 || bars % DiagEveryBars != 0)
      return;
   double a[];
   ArraySetAsSeries(a, true);
   if(CopyBuffer(h_atr, 0, 1, 1, a) != 1 || a[0] <= 0.0)
      return;
   int mode = (int)((g_sig) % 3);
   string nm;
   double d = DynamicSLDist(mode, a[0], nm);
   bool pend = (DiagPendingEvery > 0 && (g_sig + 1) % DiagPendingEvery == 0);
   OpenTrade(pend, d, nm);
  }
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(MQLInfoInteger(MQL_TESTER))
      PrintFormat("REMIX V4 resumen: senales=%I64d abiertas=%I64d pendientes=%I64d rech_margen=%I64d rech_riesgo=%I64d rech_minlote=%I64d rech_posiciones=%I64d | max_margen_simbolo=%.3f%% max_lotes=%.2f min_lotes=%.2f max_simultaneas=%d max_riesgo_agregado=%.3f%%",
                  g_sig, g_open, g_pend, g_rej_margin, g_rej_risk, g_rej_minlot, g_rej_pos, g_max_sym_margin_pct, g_max_lots, g_min_lots == 1e9 ? 0.0 : g_min_lots, g_max_conc, g_max_total_risk_pct);
   if(h_atr != INVALID_HANDLE)
      IndicatorRelease(h_atr);
  }
//+------------------------------------------------------------------+

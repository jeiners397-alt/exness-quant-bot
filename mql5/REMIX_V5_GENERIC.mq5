//+------------------------------------------------------------------+
//| REMIX_V5_GENERIC.mq5 - familias estrategicas GENERICAS multi-mercado|
//| SOLO Strategy Tester. NINGUNA FAMILIA TIENE VENTAJA DEMOSTRADA.    |
//|  Usa _Symbol y _Period; distancias en multiplos de ATR (sin pips); |
//|  lotaje por margen (OrderCalcMargin) y riesgo (OrderCalcProfit).   |
//|  F1 SWEEP_REV    barrida de maximo/minimo del dia previo + cierre dentro (reversion)|
//|  F2 DONCHIAN_BO  ruptura de maximo/minimo de N barras con expansion de rango (continuacion)|
//|  F3 ZSCORE_REV   desviacion extrema |z| vs SMA (reversion a la media)  |
//| Defecto: Family=FAM_NONE, EnableTrading=false.                     |
//+------------------------------------------------------------------+
#property copyright "REMIX V5"
#property version   "5.00"
#property strict

#include <Trade\Trade.mqh>

enum ENUM_FAMILY { FAM_NONE = 0, FAM_SWEEP_REV = 1, FAM_DONCHIAN_BO = 2, FAM_ZSCORE_REV = 3 };

input group "=== Seguridad ==="
input ENUM_FAMILY Family         = FAM_NONE;
input bool   EnableTrading       = false;
input long   MagicNumber         = 20260501;
input group "=== Margen y riesgo (independientes) ==="
input double MarginPct           = 5.0;       // margen maximo por simbolo (% equidad)
input double GlobalMarginPct     = 15.0;
input double RiskPercent         = 0.50;      // perdida maxima al SL por operacion (% equidad) - limite de seguridad configurable
input double MaxTotalRiskPct     = 5.0;
input bool   CheckPendingOrders  = true;
input bool   AllowMultiple       = false;
input int    MaxPositions        = 5;
input group "=== Costes / horario ==="
input double CostGateR           = 0.10;      // omitir si (spread+2pts)/SL > CostGateR
input int    HourFrom            = 0;         // hora servidor inclusive
input int    HourTo              = 24;        // exclusive
input int    MaxHoldBars         = 48;
input int    ATR_N               = 14;
input group "=== F1 SWEEP_REV ==="
input double F1_MinSweepATR      = 0.10;
input double F1_BufATR           = 0.10;
input double F1_RR               = 1.5;
input double F1_SLMinATR         = 0.5;
input double F1_SLMaxATR         = 3.0;
input group "=== F2 DONCHIAN_BO ==="
input int    F2_N                = 48;
input double F2_MinRangeATR      = 1.0;
input double F2_SL_ATR           = 1.5;
input double F2_RR               = 2.0;
input group "=== F3 ZSCORE_REV ==="
input int    F3_N                = 50;
input double F3_Z                = 2.5;
input double F3_SL_ATR           = 2.0;
input double F3_RR               = 1.0;

CTrade   trade;
int      h_atr = INVALID_HANDLE;
datetime g_last_bar = 0;
long     g_bars = 0, g_sig = 0, g_open = 0, g_rej_margin = 0, g_rej_risk = 0, g_rej_minlot = 0, g_skip_cost = 0, g_skip_hour = 0, g_rej_pos = 0, g_failed = 0;
double   g_max_sym_margin_pct = 0.0, g_max_lots = 0.0, g_min_lots = 1e9, g_sum_lots = 0.0;
int      g_max_conc = 0;

bool TradingAllowed()
  {
   if(!MQLInfoInteger(MQL_TESTER))
      return false;
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return false;
   return EnableTrading && Family != FAM_NONE;
  }
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     { Print("REMIX V5: BLOQUEADO fuera del Strategy Tester."); return INIT_FAILED; }
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return INIT_FAILED;
   if(MarginPct <= 0 || MarginPct > 100 || RiskPercent <= 0 || RiskPercent > 5.0)
      return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(30);
   trade.SetTypeFillingBySymbol(_Symbol);
   h_atr = iATR(_Symbol, _Period, ATR_N);
   if(h_atr == INVALID_HANDLE)
      return INIT_FAILED;
   PrintFormat("REMIX V5 init | Family=%d | Trading=%d | symbol=%s | period=%s (%d s) | margin<=%.1f%% | risk<=%.2f%% | volmin=%.2f step=%.2f digits=%d",
               (int)Family, (int)EnableTrading, _Symbol, EnumToString(_Period), PeriodSeconds(_Period), MarginPct, RiskPercent,
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), _Digits);
   return INIT_SUCCEEDED;
  }
//+------------------------------------------------------------------+
int CountPositions()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == MagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol)
         n++;
     }
   return n;
  }
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
double OpenRiskMoney()
  {
   double tot = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      double sl = PositionGetDouble(POSITION_SL), p = 0.0;
      if(sl <= 0)
         continue;
      ENUM_ORDER_TYPE ot = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(OrderCalcProfit(ot, PositionGetString(POSITION_SYMBOL), PositionGetDouble(POSITION_VOLUME), PositionGetDouble(POSITION_PRICE_OPEN), sl, p) && p < 0)
         tot += -p;
     }
   return tot;
  }
double FloorStep(const double v, const double step)
  {
   if(v <= 0 || step <= 0)
      return 0.0;
   return NormalizeDouble(MathFloor(v / step + 1e-9) * step, 8);
  }
//+------------------------------------------------------------------+
double SizeLots(const ENUM_ORDER_TYPE ot, const double price, const double sl, string &reason, double &m_new)
  {
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double m1 = 0.0, p1 = 0.0;
   if(!OrderCalcMargin(ot, _Symbol, 1.0, price, m1) || m1 <= 0.0 || !OrderCalcProfit(ot, _Symbol, 1.0, price, sl, p1) || p1 >= 0.0)
     { reason = "CALC_FAIL"; return 0.0; }
   double avail = MathMin(MathMax(0.0, eq * MarginPct / 100.0 - CommittedMargin(false)), MathMax(0.0, eq * GlobalMarginPct / 100.0 - CommittedMargin(true)));
   double risk_left = MathMax(0.0, eq * MaxTotalRiskPct / 100.0 - OpenRiskMoney());
   double lots_m = FloorStep(avail / m1, step);
   double lots_r = FloorStep(MathMin(eq * RiskPercent / 100.0, risk_left) / (-p1), step);
   double lots = MathMin(MathMin(lots_m, lots_r), vmax);
   if(lots < vmin - 1e-12)
     { reason = (lots_m < vmin) ? "MARGIN_BUDGET" : "RISK_LIMIT"; return 0.0; }
   lots = NormalizeDouble(lots, 8);
   if(!OrderCalcMargin(ot, _Symbol, lots, price, m_new))
     { reason = "CALC_FAIL"; return 0.0; }
   if(CommittedMargin(false) + m_new > eq * MarginPct / 100.0 + 1e-9 || CommittedMargin(true) + m_new > eq * GlobalMarginPct / 100.0 + 1e-9)
     { reason = "MARGIN_BUDGET"; return 0.0; }
   reason = "OK";
   return lots;
  }
//+------------------------------------------------------------------+
//| UNICO sitio de aperturas                                          |
//+------------------------------------------------------------------+
void OpenTrade(const int dir, const double sl_dist, const double tp_dist)
  {
   if(!TradingAllowed())
      return;
   g_sig++;
   if(sl_dist <= 0 || tp_dist <= 0)
      return;
   if(CountPositions() >= MaxPositions || (!AllowMultiple && CountPositions() > 0))
     { g_rej_pos++; return; }
   double spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
   if(CostGateR > 0 && (spread + 2.0 * _Point) / sl_dist > CostGateR)
     { g_skip_cost++; return; }
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double price = dir > 0 ? ask : bid;
   double sl = NormalizeDouble(dir > 0 ? price - sl_dist : price + sl_dist, _Digits);
   double tp = NormalizeDouble(dir > 0 ? price + tp_dist : price - tp_dist, _Digits);
   string reason; double m_new = 0.0;
   double lots = SizeLots(dir > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, price, sl, reason, m_new);
   if(lots <= 0.0)
     {
      if(StringFind(reason, "MARGIN") == 0) g_rej_margin++;
      else if(reason == "RISK_LIMIT") g_rej_risk++;
      else g_rej_minlot++;
      return;
     }
   string cmt = StringFormat("REMIX V5 F%d", (int)Family);
   bool ok = (dir > 0) ? trade.Buy(lots, _Symbol, 0.0, sl, tp, cmt) : trade.Sell(lots, _Symbol, 0.0, sl, tp, cmt);
   uint rc = trade.ResultRetcode();
   if(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED))
     {
      g_open++;
      double after = CommittedMargin(false);
      g_max_sym_margin_pct = MathMax(g_max_sym_margin_pct, 100.0 * after / AccountInfoDouble(ACCOUNT_EQUITY));
      g_max_lots = MathMax(g_max_lots, lots);
      g_min_lots = MathMin(g_min_lots, lots);
      g_sum_lots += lots;
      g_max_conc = MathMax(g_max_conc, CountPositions());
     }
   else
      g_failed++;
  }
//+------------------------------------------------------------------+
void CloseOld()
  {
   if(!TradingAllowed())
      return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != MagicNumber || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(iBarShift(_Symbol, _Period, (datetime)PositionGetInteger(POSITION_TIME), false) >= MaxHoldBars)
         trade.PositionClose(t);
     }
  }
//+------------------------------------------------------------------+
int HourOf(const datetime t) { MqlDateTime s; TimeToStruct(t, s); return s.hour; }
//+------------------------------------------------------------------+
void EvalSweep(const double atr)
  {
   double pdh = iHigh(_Symbol, PERIOD_D1, 1), pdl = iLow(_Symbol, PERIOD_D1, 1);
   if(pdh <= 0 || pdl <= 0)
      return;
   double h = iHigh(_Symbol, _Period, 1), l = iLow(_Symbol, _Period, 1), c = iClose(_Symbol, _Period, 1);
   double entry = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(h > pdh + F1_MinSweepATR * atr && c < pdh)           // barrida del maximo y cierre dentro -> corto
     {
      double sl = MathMin(MathMax(h + F1_BufATR * atr - c, F1_SLMinATR * atr), F1_SLMaxATR * atr);
      OpenTrade(-1, sl, F1_RR * sl);
     }
   else if(l < pdl - F1_MinSweepATR * atr && c > pdl)      // barrida del minimo -> largo
     {
      double sl = MathMin(MathMax(c - (l - F1_BufATR * atr), F1_SLMinATR * atr), F1_SLMaxATR * atr);
      OpenTrade(1, sl, F1_RR * sl);
     }
  }
//+------------------------------------------------------------------+
void EvalDonchian(const double atr)
  {
   int ih = iHighest(_Symbol, _Period, MODE_HIGH, F2_N, 2), il = iLowest(_Symbol, _Period, MODE_LOW, F2_N, 2);
   if(ih < 0 || il < 0)
      return;
   double hh = iHigh(_Symbol, _Period, ih), ll = iLow(_Symbol, _Period, il);
   double c = iClose(_Symbol, _Period, 1), rng = iHigh(_Symbol, _Period, 1) - iLow(_Symbol, _Period, 1);
   if(rng < F2_MinRangeATR * atr)
      return;
   if(c > hh)
      OpenTrade(1, F2_SL_ATR * atr, F2_RR * F2_SL_ATR * atr);
   else if(c < ll)
      OpenTrade(-1, F2_SL_ATR * atr, F2_RR * F2_SL_ATR * atr);
  }
//+------------------------------------------------------------------+
void EvalZ(const double atr)
  {
   double cl[];
   ArraySetAsSeries(cl, true);
   if(CopyClose(_Symbol, _Period, 1, F3_N, cl) != F3_N)
      return;
   double m = 0.0, v = 0.0;
   for(int i = 0; i < F3_N; i++) m += cl[i];
   m /= F3_N;
   for(int i = 0; i < F3_N; i++) v += (cl[i] - m) * (cl[i] - m);
   double sd = MathSqrt(v / F3_N);
   if(sd <= 0)
      return;
   double z = (cl[0] - m) / sd;
   if(z <= -F3_Z)
      OpenTrade(1, F3_SL_ATR * atr, F3_RR * F3_SL_ATR * atr);
   else if(z >= F3_Z)
      OpenTrade(-1, F3_SL_ATR * atr, F3_RR * F3_SL_ATR * atr);
  }
//+------------------------------------------------------------------+
void OnTick()
  {
   datetime bt = iTime(_Symbol, _Period, 0);
   if(bt == g_last_bar)
      return;
   g_last_bar = bt;
   g_bars++;
   CloseOld();
   if(!TradingAllowed())
      return;
   int hr = HourOf(bt);
   if(hr < HourFrom || hr >= HourTo)
     { g_skip_hour++; return; }
   double a[];
   ArraySetAsSeries(a, true);
   if(CopyBuffer(h_atr, 0, 1, 1, a) != 1 || a[0] <= 0.0)
      return;
   if(Family == FAM_SWEEP_REV) EvalSweep(a[0]);
   else if(Family == FAM_DONCHIAN_BO) EvalDonchian(a[0]);
   else if(Family == FAM_ZSCORE_REV) EvalZ(a[0]);
  }
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(MQLInfoInteger(MQL_TESTER))
      PrintFormat("REMIX V5 resumen: symbol=%s period=%s barras=%I64d senales=%I64d abiertas=%I64d rech_margen=%I64d rech_riesgo=%I64d rech_minlote=%I64d omit_coste=%I64d omit_hora=%I64d rech_pos=%I64d fallidas=%I64d | max_margen_simbolo=%.3f%% lotes(min/medio/max)=%.2f/%.3f/%.2f max_simultaneas=%d",
                  _Symbol, EnumToString(_Period), g_bars, g_sig, g_open, g_rej_margin, g_rej_risk, g_rej_minlot, g_skip_cost, g_skip_hour, g_rej_pos, g_failed,
                  g_max_sym_margin_pct, g_min_lots == 1e9 ? 0.0 : g_min_lots, g_open > 0 ? g_sum_lots / g_open : 0.0, g_max_lots, g_max_conc);
   if(h_atr != INVALID_HANDLE)
      IndicatorRelease(h_atr);
  }
//+------------------------------------------------------------------+

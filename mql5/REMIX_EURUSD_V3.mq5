//+------------------------------------------------------------------+
//| REMIX_EURUSD_V3.mq5 - laboratorio experimental, SOLO Strategy Tester|
//|                                                                   |
//| ESTADO: NINGUN MODULO TIENE VENTAJA ESTADISTICA DEMOSTRADA.       |
//|   Por defecto Module=NONE y EnableTrading=false (no opera).       |
//|   Modulos (hipotesis de investigacion, ver docs/REMIX_EURUSD_V3_REPORT.md):|
//|    A  False Breakout Reversal (M15/H1)                            |
//|    B  Volatility Momentum    (M15/H1)                             |
//|    C  Macro News             -> PENDIENTE DE DATOS (no operativo) |
//|    D  Regime Conditional Reversal (H1/H4)                         |
//| SEGURIDAD: solo opera con MQL_TESTER y cuenta no REAL. Las llamadas|
//| de trading estan solo en OpenTrade/ClosePosition/ModifySL.        |
//| Convenciones (= motor Python): senal en la barra cerrada [1];     |
//| entrada a mercado en la apertura de [0]; una posicion a la vez;   |
//| salidas por tiempo/barras a la apertura de la barra nueva y       |
//| reentrada en esa misma barra; horas = hora del servidor.          |
//+------------------------------------------------------------------+
#property copyright "REMIX EURUSD V3"
#property version   "3.00"
#property strict

#include <Trade\Trade.mqh>

enum ENUM_V3_MODULE
  {
   MOD_NONE               = 0,   // NONE (sin operaciones)
   MOD_A_FALSE_BREAKOUT   = 1,   // A False Breakout Reversal (M15/H1)
   MOD_B_VOL_MOMENTUM     = 2,   // B Volatility Momentum (M15/H1)
   MOD_C_MACRO_NEWS       = 3,   // C Macro News (PENDIENTE DE DATOS: no opera)
   MOD_D_REGIME_REVERSAL  = 4    // D Regime Conditional Reversal (H1/H4)
  };
enum ENUM_SIZING_POLICY { SIZE_STRICT = 0, SIZE_MIN_LOT = 1 };

input group "=== General (seguridad) ==="
input ENUM_V3_MODULE Module        = MOD_NONE;
input bool     EnableTrading       = false;      // Habilitar aperturas (solo Strategy Tester)
input bool     RequireTimeframe    = true;
input double   RiskPercent         = 0.50;
input ENUM_SIZING_POLICY SizingPolicy = SIZE_STRICT;
input double   MaxSpreadFracSL     = 0.15;       // spread <= frac * SL
input int      MaxSpreadPoints     = 30;
input double   CostGateR           = 0.10;       // omitir si (spread+2 pts)/SL > CostGateR (0 = sin filtro)
input int      DeviationPoints     = 20;
input int      MaxSlippagePoints   = 30;
input bool     CloseOnExcessSlip   = false;
input long     MagicNumber         = 20260301;
input bool     ExportDeals         = true;
input bool     LogSignals          = true;
input bool     RetryFailedClose    = false;
input group "=== Gestion opcional ==="
input bool     UseBreakEven        = false;
input double   BE_TriggerR         = 1.0;
input int      BE_BufferPoints     = 0;
input bool     UseTrailATR         = false;
input double   Trail_ActivateR     = 1.0;
input double   Trail_ATR_Mult      = 2.5;
input int      ATR_N               = 14;
input int      TimeExitHour        = 20;         // A y B: cierre temporal (hora servidor)

input group "=== A False Breakout ==="
input int      A_Levels            = 0;          // 0 = PDH/PDL dia anterior, 1 = maximo/minimo sesion asiatica (00-07)
input int      A_Confirm           = 1;          // 1 = la barra de barrida cierra dentro; 2 = barra siguiente cierra mas alla del extremo opuesto
input int      A_SLMode            = 0;          // 0 = estructural (extremo + buffer), 1 = ATR
input double   A_RR                = 1.5;
input int      A_H0                = 7;
input int      A_H1                = 17;
input double   A_BufATR            = 0.1;
input double   A_MinDepthATR       = 0.1;
input double   A_SL_ATR            = 1.5;
input double   A_SLMinATR          = 0.5;
input double   A_SLMaxATR          = 3.0;

input group "=== B Volatility Momentum ==="
input int      B_Mode              = 0;          // 0 = impulso, 1 = ruptura tras compresion (squeeze)
input double   B_K                 = 2.0;        // rango >= K * ATR previo
input double   B_BodyMin           = 0.6;
input bool     B_UseKER            = false;
input double   B_KERMin            = 0.3;
input int      B_SLMode            = 0;          // 0 = estructural, 1 = ATR
input double   B_RR                = 1.5;
input int      B_H0                = 7;
input int      B_H1                = 17;
input double   B_BufATR            = 0.1;
input double   B_SL_ATR            = 1.5;
input double   B_SLMinATR          = 0.5;
input double   B_SLMaxATR          = 3.0;
input double   B_SqPct             = 0.2;
input double   B_SqBody            = 0.5;

input group "=== D Regime Conditional Reversal (H1/H4) ==="
input int      D_SMA_N             = 50;
input double   D_Z                 = 2.0;
input double   D_SL_ATR            = 2.0;
input int      D_MaxBars           = 18;         // H4: 18 (H1: 48)
input bool     D_UseRegime         = true;       // filtro KER/CHOP (umbrales = terciles TRAIN 2018-21 de los eventos |z|>=2)
input double   D_KERMax            = 0.514;      // H4: p33 TRAIN de KER(10) (H1: 0.445)
input double   D_CHOPMin           = 43.587;     // H4: p67 TRAIN de CHOP(14) (H1: 45.031)
input bool     D_UseADX            = false;      // alternativa: ADX14 < D_ADXMax
input double   D_ADXMax            = 25.0;

CTrade   trade;
int      h_atr = INVALID_HANDLE, h_adx = INVALID_HANDLE;
datetime g_last_bar = 0, g_entry_bar = 0;
double   g_init_risk = 0.0, g_exp_price = 0.0;
int      g_max_bars = 0;
bool     g_close_pending = false;
long     g_skipped_minlot = 0, g_skipped_spread = 0, g_skipped_cost = 0, g_signals = 0, g_orders_sent = 0, g_orders_failed = 0, g_excess_slip = 0;

//+------------------------------------------------------------------+
bool TradingAllowed()
  {
   if(!MQLInfoInteger(MQL_TESTER))
      return false;
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return false;
   if(!EnableTrading || Module == MOD_NONE || Module == MOD_C_MACRO_NEWS)
      return false;
   return true;
  }
//+------------------------------------------------------------------+
bool TimeframeOK()
  {
   if(Module == MOD_A_FALSE_BREAKOUT || Module == MOD_B_VOL_MOMENTUM)
      return _Period == PERIOD_M15 || _Period == PERIOD_H1;
   if(Module == MOD_D_REGIME_REVERSAL)
      return _Period == PERIOD_H1 || _Period == PERIOD_H4;
   return true;
  }
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     {
      Print("REMIX EURUSD V3: BLOQUEADO. Solo funciona en el Strategy Tester. Sin operaciones.");
      Alert("REMIX_EURUSD_V3 solo funciona en el Strategy Tester.");
      return INIT_FAILED;
     }
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return INIT_FAILED;
   if(StringFind(_Symbol, "EURUSD") != 0)
     { PrintFormat("REMIX V3: simbolo %s no es EURUSD*.", _Symbol); return INIT_FAILED; }
   if(Module == MOD_C_MACRO_NEWS)
     { Print("REMIX V3: modulo C (Macro News) PENDIENTE DE DATOS: no hay calendario historico verificable. No opera."); return INIT_FAILED; }
   if(RequireTimeframe && Module != MOD_NONE && !TimeframeOK())
     { PrintFormat("REMIX V3: marco %s no valido para el modulo %d.", EnumToString(_Period), (int)Module); return INIT_FAILED; }
   if(RiskPercent <= 0.0 || RiskPercent > 2.0)
     { Print("REMIX V3: RiskPercent fuera de rango (0-2%)"); return INIT_PARAMETERS_INCORRECT; }
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(DeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   h_atr = iATR(_Symbol, _Period, ATR_N);
   if(h_atr == INVALID_HANDLE)
      return INIT_FAILED;
   if(Module == MOD_D_REGIME_REVERSAL && D_UseADX)
      h_adx = iADX(_Symbol, _Period, 14);
   // los logs se reinician en cada corrida (en V2.1 se acumulaban entre corridas)
   FileDelete(StringFormat("REMIX_V3_signals_M%02d_%s_%s.csv", (int)Module, _Symbol, EnumToString(_Period)), FILE_COMMON);
   PrintFormat("REMIX EURUSD V3 init | Module=%d | EnableTrading=%d | %s %s | Risk=%.2f%% | RESEARCH ONLY", (int)Module, (int)EnableTrading, _Symbol, EnumToString(_Period), RiskPercent);
   return INIT_SUCCEEDED;
  }
//+------------------------------------------------------------------+
void ExportDealsCsv()
  {
   if(!ExportDeals || !HistorySelect(0, TimeCurrent()))
      return;
   string name = StringFormat("REMIX_V3_deals_M%02d_%s_%s.csv", (int)Module, _Symbol, EnumToString(_Period));
   int fh = FileOpen(name, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
      return;
   FileWriteString(fh, "time,ticket,type,entry,volume,price,profit,commission,swap,fee,comment\n");
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
     {
      ulong t = HistoryDealGetTicket(i);
      if(t == 0 || HistoryDealGetInteger(t, DEAL_MAGIC) != MagicNumber)
         continue;
      FileWriteString(fh, StringFormat("%s,%I64u,%d,%d,%.2f,%.5f,%.2f,%.2f,%.2f,%.2f,%s\n",
                      TimeToString((datetime)HistoryDealGetInteger(t, DEAL_TIME), TIME_DATE | TIME_SECONDS), t, (int)HistoryDealGetInteger(t, DEAL_TYPE),
                      (int)HistoryDealGetInteger(t, DEAL_ENTRY), HistoryDealGetDouble(t, DEAL_VOLUME), HistoryDealGetDouble(t, DEAL_PRICE),
                      HistoryDealGetDouble(t, DEAL_PROFIT), HistoryDealGetDouble(t, DEAL_COMMISSION), HistoryDealGetDouble(t, DEAL_SWAP),
                      HistoryDealGetDouble(t, DEAL_FEE), HistoryDealGetString(t, DEAL_COMMENT)));
     }
   FileClose(fh);
  }
//+------------------------------------------------------------------+
void LogSignal(const string what, const int dir, const double sl, const double tp, const double lots)
  {
   if(!LogSignals || !MQLInfoInteger(MQL_TESTER))
      return;
   string name = StringFormat("REMIX_V3_signals_M%02d_%s_%s.csv", (int)Module, _Symbol, EnumToString(_Period));
   int fh = FileOpen(name, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
      return;
   if(FileSize(fh) == 0)
      FileWriteString(fh, "time,module,event,dir,sl_dist,tp_dist,lots,spread_pts,balance\n");
   FileSeek(fh, 0, SEEK_END);
   FileWriteString(fh, StringFormat("%s,%d,%s,%d,%.5f,%.5f,%.2f,%d,%.2f\n", TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), (int)Module, what, dir, sl, tp, lots,
                   (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), AccountInfoDouble(ACCOUNT_BALANCE)));
   FileClose(fh);
  }
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(MQLInfoInteger(MQL_TESTER))
     {
      ExportDealsCsv();
      PrintFormat("REMIX V3 resumen: senales=%I64d ordenes=%I64d fallidas=%I64d omitidas_lote_minimo=%I64d omitidas_spread=%I64d omitidas_coste=%I64d slip_excesivo=%I64d",
                  g_signals, g_orders_sent, g_orders_failed, g_skipped_minlot, g_skipped_spread, g_skipped_cost, g_excess_slip);
     }
   if(h_atr != INVALID_HANDLE) IndicatorRelease(h_atr);
   if(h_adx != INVALID_HANDLE) IndicatorRelease(h_adx);
  }
//+------------------------------------------------------------------+
double OnTester()
  {
   double n = TesterStatistics(STAT_TRADES);
   if(n < 30)
      return 0.0;
   return TesterStatistics(STAT_PROFIT) / MathMax(1.0, TesterStatistics(STAT_EQUITY_DD)) * MathMin(1.0, MathSqrt(n / 100.0));
  }
//+------------------------------------------------------------------+
bool GetBuf(const int handle, const int buffer, const int shift, const int count, double &arr[])
  {
   if(handle == INVALID_HANDLE)
      return false;
   ArraySetAsSeries(arr, true);
   return CopyBuffer(handle, buffer, shift, count, arr) == count;
  }
//+------------------------------------------------------------------+
double CalcLots(const double sl_dist)
  {
   double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(sl_dist <= 0 || tick_size <= 0 || tick_value <= 0 || step <= 0)
      return 0.0;
   double risk_money = AccountInfoDouble(ACCOUNT_BALANCE) * RiskPercent / 100.0;
   double loss_per_lot = sl_dist / tick_size * tick_value;
   double lots = MathFloor(risk_money / loss_per_lot / step + 1e-9) * step;
   if(lots < vmin)
     {
      if(SizingPolicy == SIZE_STRICT)
        { g_skipped_minlot++; return 0.0; }
      lots = vmin;
     }
   return NormalizeDouble(MathMin(lots, vmax), 2);
  }
//+------------------------------------------------------------------+
bool SelectMyPosition(ulong &ticket)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
        { ticket = t; return true; }
     }
   return false;
  }
bool HasPosition() { ulong t; return SelectMyPosition(t); }
//+------------------------------------------------------------------+
void ClosePosition(const string why)
  {
   if(!TradingAllowed())
      return;
   ulong t;
   if(SelectMyPosition(t))
     {
      if(!trade.PositionClose(t))
        {
         PrintFormat("REMIX V3: fallo al cerrar (%s) ret=%u", why, trade.ResultRetcode());
         if(RetryFailedClose)
            g_close_pending = true;
         LogSignal("CLOSE_FAILED_" + why, 0, 0, 0, 0);
        }
      else
        { g_close_pending = false; LogSignal("CLOSE_" + why, 0, 0, 0, 0); }
     }
  }
//+------------------------------------------------------------------+
void ModifySL(const ulong ticket, const double new_sl)
  {
   if(!TradingAllowed() || !PositionSelectByTicket(ticket))
      return;
   double minDist = MathMax((double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL), (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL)) * _Point;
   long type = PositionGetInteger(POSITION_TYPE);
   double px = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(MathAbs(px - new_sl) <= minDist)
      return;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(!trade.PositionModify(ticket, NormalizeDouble(new_sl, digits), PositionGetDouble(POSITION_TP)))
      PrintFormat("REMIX V3: fallo PositionModify ret=%u", trade.ResultRetcode());
  }
//+------------------------------------------------------------------+
void ManagePosition()
  {
   ulong t;
   if(!SelectMyPosition(t) || g_init_risk <= 0.0)
      return;
   long type = PositionGetInteger(POSITION_TYPE);
   double open = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL);
   double px = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   int ds = (type == POSITION_TYPE_BUY) ? 1 : -1;
   double fav = ds * (px - open);
   if(UseBreakEven && fav >= BE_TriggerR * g_init_risk)
     {
      double be = open + ds * BE_BufferPoints * _Point;
      if((ds > 0 && be > sl) || (ds < 0 && be < sl))
         ModifySL(t, be);
     }
   if(UseTrailATR && fav >= Trail_ActivateR * g_init_risk)
     {
      double atr[];
      if(GetBuf(h_atr, 0, 1, 1, atr))
        {
         double cand = px - ds * Trail_ATR_Mult * atr[0];
         if((ds > 0 && cand > sl) || (ds < 0 && cand < sl))
            ModifySL(t, cand);
        }
     }
  }
//+------------------------------------------------------------------+
//| Apertura. SL obligatorio. UNICO sitio de aperturas.               |
//+------------------------------------------------------------------+
void OpenTrade(const int dir, const double sl_dist, const double tp_dist, const int max_bars)
  {
   if(!TradingAllowed())
      return;
   g_signals++;
   if(sl_dist <= 0.0 || tp_dist <= 0.0)
     { LogSignal("SKIP_NO_SL", dir, sl_dist, tp_dist, 0); return; }
   double spread_pts = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), spread = spread_pts * _Point;
   if(spread > MaxSpreadFracSL * sl_dist || (MaxSpreadPoints > 0 && spread_pts > MaxSpreadPoints))
     { g_skipped_spread++; LogSignal("SKIP_SPREAD", dir, sl_dist, tp_dist, 0); return; }
   if(CostGateR > 0.0 && (spread + 2.0 * _Point) / sl_dist > CostGateR)
     { g_skipped_cost++; LogSignal("SKIP_COST", dir, sl_dist, tp_dist, 0); return; }
   double lots = CalcLots(sl_dist);
   if(lots <= 0.0)
     { LogSignal("SKIP_MINLOT", dir, sl_dist, tp_dist, 0); return; }
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   string cmt = StringFormat("REMIX V3 M%02d", (int)Module);
   bool ok;
   if(dir > 0)
     { g_exp_price = ask; ok = trade.Buy(lots, _Symbol, 0.0, NormalizeDouble(ask - sl_dist, digits), NormalizeDouble(ask + tp_dist, digits), cmt); }
   else
     { g_exp_price = bid; ok = trade.Sell(lots, _Symbol, 0.0, NormalizeDouble(bid + sl_dist, digits), NormalizeDouble(bid - tp_dist, digits), cmt); }
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
     {
      g_orders_sent++;
      g_entry_bar = iTime(_Symbol, _Period, 0);
      g_init_risk = sl_dist;
      g_max_bars = max_bars;
      LogSignal("OPEN", dir, sl_dist, tp_dist, lots);
      double slip_pts = MathAbs(trade.ResultPrice() - g_exp_price) / _Point;
      if(slip_pts > MaxSlippagePoints)
        {
         g_excess_slip++;
         if(CloseOnExcessSlip)
            ClosePosition("slip");
        }
     }
   else
     {
      g_orders_failed++;
      PrintFormat("REMIX V3: orden rechazada ret=%u (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
      LogSignal("ORDER_FAILED", dir, sl_dist, tp_dist, lots);
     }
  }
//+------------------------------------------------------------------+
//| Utilidades de datos                                               |
//+------------------------------------------------------------------+
datetime DayKey(const datetime t)
  {
   MqlDateTime s;
   TimeToStruct(t, s);
   datetime d = t - (datetime)(s.hour * 3600 + s.min * 60 + s.sec);
   if(s.day_of_week == 0)
      d += 86400;                           // las barras del domingo pertenecen al lunes (igual que Python)
   return d;
  }
int HourOf(const datetime t) { MqlDateTime s; TimeToStruct(t, s); return s.hour; }
//--- KER(10) en la barra con shift s: |c[s]-c[s+10]| / sum|c[i]-c[i+1]|
double KER10(const MqlRates &r[], const int s)
  {
   double path = 0.0;
   for(int i = s; i < s + 10; i++)
      path += MathAbs(r[i].close - r[i + 1].close);
   return path > 0.0 ? MathAbs(r[s].close - r[s + 10].close) / path : 0.0;
  }
//--- Choppiness(14) en la barra con shift s
double CHOP14(const MqlRates &r[], const int s)
  {
   double sumtr = 0.0, hh = -DBL_MAX, ll = DBL_MAX;
   for(int i = s; i < s + 14; i++)
     {
      double tr = MathMax(r[i].high - r[i].low, MathMax(MathAbs(r[i].high - r[i + 1].close), MathAbs(r[i].low - r[i + 1].close)));
      sumtr += tr; hh = MathMax(hh, r[i].high); ll = MathMin(ll, r[i].low);
     }
   if(hh - ll <= 0.0 || sumtr <= 0.0)
      return 0.0;
   return 100.0 * MathLog10(sumtr / (hh - ll)) / MathLog10(14.0);
  }
//+------------------------------------------------------------------+
//| A. False breakout reversal                                        |
//+------------------------------------------------------------------+
bool LevelsFor(const MqlRates &r[], const int n, const int shift, double &hi, double &lo)
  {
   datetime key = DayKey(r[shift].time);
   hi = -DBL_MAX; lo = DBL_MAX;
   if(A_Levels == 1)
     {
      if(HourOf(r[shift].time) < 7)
         return false;
      for(int i = shift; i < n; i++)
        {
         if(DayKey(r[i].time) != key)
            break;
         if(HourOf(r[i].time) < 7)
           { hi = MathMax(hi, r[i].high); lo = MathMin(lo, r[i].low); }
        }
      return hi > -DBL_MAX;
     }
   datetime prevkey = 0;
   for(int i = shift; i < n; i++)
     {
      datetime k = DayKey(r[i].time);
      if(k == key)
         continue;
      if(prevkey == 0)
         prevkey = k;
      if(k != prevkey)
         break;
      hi = MathMax(hi, r[i].high); lo = MathMin(lo, r[i].low);
     }
   return hi > -DBL_MAX;
  }
void EvalA()
  {
   int per_day = 1440 / (PeriodSeconds(_Period) / 60), n = 3 * per_day + 30;
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, _Period, 1, n, r) < 3 * per_day)
      return;
   n = ArraySize(r);                                   // r[0] = barra de senal (shift 1)
   double atr[];
   if(!GetBuf(h_atr, 0, 1, 2, atr))
      return;                                          // atr[0] = ATR(bar1), atr[1] = ATR(bar2)
   int hr = HourOf(r[0].time);
   if(hr < A_H0 || hr >= A_H1)
      return;
   double hi, lo;
   if(!LevelsFor(r, n, 0, hi, lo))
      return;
   int dir = 0;
   double ext_hi = r[0].high, ext_lo = r[0].low;
   if(A_Confirm == 1)
     {
      if(r[0].high > hi && r[0].close < hi && (r[0].high - hi) >= A_MinDepthATR * atr[1])
         dir = -1;
      else if(r[0].low < lo && r[0].close > lo && (lo - r[0].low) >= A_MinDepthATR * atr[1])
         dir = 1;
     }
   else
     {
      double hi2, lo2;
      if(HourOf(r[1].time) < A_H0 && A_Levels == 1)
         return;
      if(!LevelsFor(r, n, 1, hi2, lo2))
         return;
      double atr3[];
      if(!GetBuf(h_atr, 0, 2, 2, atr3))
         return;                                       // atr3[0] = ATR(bar2), atr3[1] = ATR(bar3)
      bool s2 = r[1].high > hi2 && r[1].close < hi2 && (r[1].high - hi2) >= A_MinDepthATR * atr3[1];
      bool l2 = r[1].low < lo2 && r[1].close > lo2 && (lo2 - r[1].low) >= A_MinDepthATR * atr3[1];
      ext_hi = MathMax(r[0].high, r[1].high); ext_lo = MathMin(r[0].low, r[1].low);
      if(s2 && r[0].close < r[1].low)
         dir = -1;
      else if(l2 && r[0].close > r[1].high)
         dir = 1;
     }
   if(dir == 0)
      return;
   double sl;
   if(A_SLMode == 0)
     {
      sl = (dir < 0) ? (ext_hi + A_BufATR * atr[0] - r[0].close) : (r[0].close - (ext_lo - A_BufATR * atr[0]));
      if(sl < A_SLMinATR * atr[0] || sl > A_SLMaxATR * atr[0])
         return;
     }
   else
      sl = A_SL_ATR * atr[0];
   OpenTrade(dir, sl, sl * A_RR, 0);
  }
//+------------------------------------------------------------------+
//| B. Volatility momentum                                            |
//+------------------------------------------------------------------+
void EvalB()
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, _Period, 1, 140, r) < 130)
      return;
   double atr[];
   if(!GetBuf(h_atr, 0, 1, 2, atr))
      return;
   int hr = HourOf(r[0].time);
   if(hr < B_H0 || hr >= B_H1)
      return;
   double rng = MathMax(r[0].high - r[0].low, 1e-9), body = MathAbs(r[0].close - r[0].open);
   int dir = 0;
   if(B_Mode == 0)
     {
      if(rng >= B_K * atr[1] && body >= B_BodyMin * rng)
         dir = (r[0].close > r[0].open) ? 1 : ((r[0].close < r[0].open) ? -1 : 0);
     }
   else
     {
      // anchura Bollinger(20,2) = 4*sigma/SMA ; percentil de la barra 2 (i-1) en sus 100 ultimas barras (incluida)
      double bw[101];
      for(int s = 1; s <= 100; s++)                      // s indexa r[s] = barra con shift s+1; bw[s] = BBW de r[s]
        {
         double m = 0.0, v = 0.0;
         for(int i = s; i < s + 20; i++) m += r[i].close;
         m /= 20.0;
         for(int i = s; i < s + 20; i++) v += (r[i].close - m) * (r[i].close - m);
         bw[s] = 4.0 * MathSqrt(v / 20.0) / m;
        }
      int le = 0;
      for(int s = 1; s <= 100; s++) if(bw[s] <= bw[1]) le++;
      double pct = le / 100.0;
      double m0 = 0.0, v0 = 0.0;
      for(int i = 0; i < 20; i++) m0 += r[i].close;
      m0 /= 20.0;
      for(int i = 0; i < 20; i++) v0 += (r[i].close - m0) * (r[i].close - m0);
      double sd0 = MathSqrt(v0 / 20.0);
      if(pct < B_SqPct && body >= B_SqBody * rng)
        {
         if(r[0].close > m0 + 2.0 * sd0) dir = 1;
         else if(r[0].close < m0 - 2.0 * sd0) dir = -1;
        }
     }
   if(dir == 0)
      return;
   if(B_UseKER && KER10(r, 0) < B_KERMin)
      return;
   double sl;
   if(B_SLMode == 0)
     {
      sl = (dir > 0) ? (r[0].close - (r[0].low - B_BufATR * atr[0])) : ((r[0].high + B_BufATR * atr[0]) - r[0].close);
      if(sl < B_SLMinATR * atr[0] || sl > B_SLMaxATR * atr[0])
         return;
     }
   else
      sl = B_SL_ATR * atr[0];
   OpenTrade(dir, sl, sl * B_RR, 0);
  }
//+------------------------------------------------------------------+
//| D. Regime conditional reversal (S05 con filtro de regimen)        |
//+------------------------------------------------------------------+
void EvalD()
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, _Period, 1, D_SMA_N + 20, r) < D_SMA_N + 16)
      return;
   double atr[], adx[];
   if(!GetBuf(h_atr, 0, 1, 1, atr))
      return;
   double m = 0.0, v = 0.0;
   for(int i = 0; i < D_SMA_N; i++) m += r[i].close;
   m /= D_SMA_N;
   for(int i = 0; i < D_SMA_N; i++) v += (r[i].close - m) * (r[i].close - m);
   double sd = MathSqrt(v / D_SMA_N);
   if(sd <= 0.0)
      return;
   double z = (r[0].close - m) / sd;
   int dir = (z <= -D_Z) ? 1 : (z >= D_Z ? -1 : 0);
   if(dir == 0)
      return;
   if(D_UseRegime && !(KER10(r, 0) < D_KERMax && CHOP14(r, 0) >= D_CHOPMin))
      return;
   if(D_UseADX && (!GetBuf(h_adx, 0, 1, 1, adx) || adx[0] >= D_ADXMax))
      return;
   OpenTrade(dir, atr[0] * D_SL_ATR, MathAbs(m - r[0].close), D_MaxBars);
  }
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!TradingAllowed())
      return;
   if(g_close_pending)
     {
      if(HasPosition()) ClosePosition("retry"); else g_close_pending = false;
     }
   datetime bar0 = iTime(_Symbol, _Period, 0);
   if(bar0 == g_last_bar)
      return;
   g_last_bar = bar0;
   bool has_pos = HasPosition();
   if(has_pos)
     {
      if((Module == MOD_A_FALSE_BREAKOUT || Module == MOD_B_VOL_MOMENTUM) && HourOf(bar0) >= TimeExitHour)
         ClosePosition("time");
      else if(g_max_bars > 0 && iBarShift(_Symbol, _Period, g_entry_bar, false) >= g_max_bars)
         ClosePosition("maxbars");
      has_pos = HasPosition();
      if(has_pos)
        { ManagePosition(); return; }
     }
   switch(Module)
     {
      case MOD_A_FALSE_BREAKOUT:  EvalA(); break;
      case MOD_B_VOL_MOMENTUM:    EvalB(); break;
      case MOD_D_REGIME_REVERSAL: EvalD(); break;
      default: break;
     }
  }
//+------------------------------------------------------------------+

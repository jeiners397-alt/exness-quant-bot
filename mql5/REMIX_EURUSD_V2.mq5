//+------------------------------------------------------------------+
//| REMIX_EURUSD_V2.mq5                                               |
//| Laboratorio experimental REMIX EURUSD V2 - SOLO Strategy Tester   |
//|                                                                   |
//| ESTADO: NINGUN MODULO TIENE VENTAJA ESTADISTICA DEMOSTRADA.       |
//|   Este EA NO esta aprobado para produccion y NO debe describirse  |
//|   como rentable. Por defecto: Module=NONE y EnableTrading=false   |
//|   (no abre operaciones). Los modulos son hipotesis experimentales |
//|   de la investigacion REMIX (ver docs/REMIX_EURUSD_PHASE_D_REPORT.md).|
//|                                                                   |
//| SEGURIDAD: solo opera si MQLInfoInteger(MQL_TESTER)==true y la    |
//| cuenta no es REAL. Fuera del tester OnInit devuelve INIT_FAILED.  |
//| Las llamadas de trading estan unicamente en OpenTrade/ClosePos/   |
//| ModifySL, todas detras de TradingAllowed().                       |
//|                                                                   |
//| Convenciones (identicas al motor Python): senal en la barra       |
//| cerrada [1]; entrada a mercado en la apertura de [0]; una         |
//| posicion a la vez; horas = hora servidor.                         |
//+------------------------------------------------------------------+
#property copyright "REMIX EURUSD V2"
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>

enum ENUM_V2_MODULE
  {
   MOD_NONE       = 0,   // NONE (sin operaciones)
   MOD_S01        = 1,   // S01 London Breakout (REFERENCIA, sin ventaja demostrada)
   MOD_S05_L2     = 5,   // S05 Z-score reversion (pista L2, H4)
   MOD_S06_L3     = 6,   // S06 RSI-2 + SMA100 (pista L3, H4)
   MOD_S08_L4     = 8,   // S08 Keltner reversion (pista L4, H4)
   MOD_L1_S03INV  = 11   // L1: S03 pullback LARGO invertido -> SELL (pista L1, H1)
  };

enum ENUM_SIZING_POLICY
  {
   SIZE_STRICT  = 0,   // Omitir si el lote minimo excede el riesgo
   SIZE_MIN_LOT = 1    // Operar lote minimo aunque exceda el riesgo (solo diagnostico)
  };

input group "=== General (seguridad) ==="
input ENUM_V2_MODULE Module        = MOD_NONE;   // Modulo activo (uno solo)
input bool     EnableTrading       = false;      // Habilitar aperturas (solo Strategy Tester)
input bool     RequireTimeframe    = true;       // Exigir el marco temporal de diseno del modulo
input double   RiskPercent         = 0.50;       // Riesgo por operacion (% balance)
input ENUM_SIZING_POLICY SizingPolicy = SIZE_STRICT; // Politica de lote minimo
input double   MaxSpreadFracSL     = 0.15;       // Spread maximo como fraccion del SL
input int      MaxSpreadPoints     = 30;         // Spread maximo absoluto (puntos); 0 = sin limite
input int      DeviationPoints     = 20;         // Desviacion maxima en la orden (puntos)
input int      MaxSlippagePoints   = 30;         // Deslizamiento maximo tolerado (se registra; ver CloseOnExcessSlip)
input bool     CloseOnExcessSlip   = false;      // Cerrar de inmediato si el deslizamiento supera el maximo
input long     MagicNumber         = 20260201;   // Magic
input bool     ExportDeals         = true;       // Exportar operaciones a CSV (Common\Files)
input bool     LogSignals          = true;       // Registrar cada decision (CSV, Common\Files)

input group "=== Gestion opcional ==="
input bool     UseBreakEven        = false;      // Break-even
input double   BE_TriggerR         = 1.0;        // Activar BE a +R
input int      BE_BufferPoints     = 0;          // SL = entrada +/- buffer (puntos)
input bool     UseTrailATR         = false;      // Trailing ATR
input double   Trail_ActivateR     = 1.0;        // Activar trailing a +R
input double   Trail_ATR_Mult      = 2.5;        // Distancia = mult * ATR(14)
input int      ATR_N               = 14;

input group "=== S01 London Breakout (referencia) ==="
input int      S01_RangeStartH     = 0;
input int      S01_RangeEndH       = 7;
input int      S01_EntryEndH       = 10;
input int      S01_ExitH           = 17;
input double   S01_SLRangeMult     = 1.0;
input double   S01_RR              = 1.5;
input double   S01_MinRangeSpreadMult = 10.0;

input group "=== S05 Z-score (L2: H4, ADX<25) ==="
input int      S05_SMA_N           = 50;
input double   S05_Z               = 2.0;
input bool     S05_UseADXFilter    = true;
input double   S05_ADXMax          = 25.0;
input double   S05_SL_ATR          = 2.0;
input int      S05_MaxBars         = 18;         // TP = retorno a la media; salida temporal de seguridad

input group "=== S06 RSI-2 + SMA100 (L3: H4) ==="
input int      S06_SMA_N           = 100;
input double   S06_RSI_Lo          = 5.0;
input double   S06_RSI_Hi          = 95.0;
input double   S06_ExitRsiLong     = 70.0;
input double   S06_ExitRsiShort    = 30.0;
input double   S06_SL_ATR          = 2.0;
input double   S06_TP_ATR          = 5.0;
input int      S06_MaxBars         = 20;

input group "=== S08 Keltner reversion (L4: H4, ADX<25) ==="
input int      S08_EMA_N           = 20;
input double   S08_K               = 2.0;
input bool     S08_UseADXFilter    = true;
input double   S08_ADXMax          = 25.0;
input double   S08_SL_ATR          = 1.5;
input int      S08_MaxBars         = 12;

input group "=== L1 S03 invertido (H1) ==="
input int      L1_EMA_Fast         = 20;
input int      L1_EMA_Mid          = 50;
input int      L1_EMA_Slow         = 200;
input double   L1_ADXMin           = 25.0;
input double   L1_SL_ATR           = 1.5;
input double   L1_TP_ATR           = 3.0;

CTrade   trade;
int      h_atr = INVALID_HANDLE, h_adx = INVALID_HANDLE, h_rsi = INVALID_HANDLE, h_sma = INVALID_HANDLE,
         h_ema_f = INVALID_HANDLE, h_ema_m = INVALID_HANDLE, h_ema_s = INVALID_HANDLE;
datetime g_last_bar = 0, g_s01_day_done = 0, g_entry_bar = 0;
double   g_init_risk = 0.0;          // distancia SL inicial (precio) de la posicion abierta
int      g_max_bars = 0;             // salida temporal de la posicion abierta (0 = ninguna)
long     g_skipped_minlot = 0, g_skipped_spread = 0, g_signals = 0, g_orders_sent = 0, g_orders_failed = 0, g_excess_slip = 0;
double   g_exp_price = 0.0;

//+------------------------------------------------------------------+
bool TradingAllowed()
  {
   if(!MQLInfoInteger(MQL_TESTER))
      return false;                                   // fuera del tester: NUNCA
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return false;                                   // nunca en cuenta real
   if(!EnableTrading || Module == MOD_NONE)
      return false;                                   // desactivado por defecto
   return true;
  }
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES DesignTimeframe()
  {
   switch(Module)
     {
      case MOD_S01:       return PERIOD_M15;
      case MOD_S05_L2:
      case MOD_S06_L3:
      case MOD_S08_L4:    return PERIOD_H4;
      case MOD_L1_S03INV: return PERIOD_H1;
     }
   return PERIOD_CURRENT;
  }
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     {
      Print("REMIX EURUSD V2: BLOQUEADO. Solo funciona en el Strategy Tester. Sin operaciones.");
      Alert("REMIX_EURUSD_V2 solo funciona en el Strategy Tester.");
      return INIT_FAILED;
     }
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return INIT_FAILED;
   if(StringFind(_Symbol, "EURUSD") != 0)
     { PrintFormat("REMIX V2: simbolo %s no es EURUSD*. Abortando.", _Symbol); return INIT_FAILED; }
   if(RequireTimeframe && Module != MOD_NONE && _Period != DesignTimeframe())
     {
      PrintFormat("REMIX V2: el modulo %d se diseno para %s; grafico actual %s. Use RequireTimeframe=false para forzar.",
                  (int)Module, EnumToString(DesignTimeframe()), EnumToString(_Period));
      return INIT_FAILED;
     }
   if(RiskPercent <= 0.0 || RiskPercent > 2.0)
     { Print("REMIX V2: RiskPercent fuera de rango (0-2%)"); return INIT_PARAMETERS_INCORRECT; }

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(DeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   h_atr = iATR(_Symbol, _Period, ATR_N);
   if(h_atr == INVALID_HANDLE)
      return INIT_FAILED;
   switch(Module)
     {
      case MOD_S01:
         if(S01_RangeEndH <= S01_RangeStartH || S01_EntryEndH <= S01_RangeEndH || S01_ExitH < S01_EntryEndH)
           { Print("S01: horas inconsistentes"); return INIT_PARAMETERS_INCORRECT; }
         break;
      case MOD_S05_L2:
         h_adx = iADX(_Symbol, _Period, 14);
         h_sma = iMA(_Symbol, _Period, S05_SMA_N, 0, MODE_SMA, PRICE_CLOSE);
         break;
      case MOD_S06_L3:
         h_rsi = iRSI(_Symbol, _Period, 2, PRICE_CLOSE);
         h_sma = iMA(_Symbol, _Period, S06_SMA_N, 0, MODE_SMA, PRICE_CLOSE);
         break;
      case MOD_S08_L4:
         h_adx   = iADX(_Symbol, _Period, 14);
         h_ema_f = iMA(_Symbol, _Period, S08_EMA_N, 0, MODE_EMA, PRICE_CLOSE);
         break;
      case MOD_L1_S03INV:
         h_adx   = iADX(_Symbol, _Period, 14);
         h_ema_f = iMA(_Symbol, _Period, L1_EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
         h_ema_m = iMA(_Symbol, _Period, L1_EMA_Mid,  0, MODE_EMA, PRICE_CLOSE);
         h_ema_s = iMA(_Symbol, _Period, L1_EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
         break;
      default: break;
     }
   PrintFormat("REMIX EURUSD V2 init | Module=%d | EnableTrading=%d | %s %s | Risk=%.2f%% | Sizing=%s | RESEARCH ONLY",
               (int)Module, (int)EnableTrading, _Symbol, EnumToString(_Period), RiskPercent, SizingPolicy == SIZE_STRICT ? "STRICT" : "MIN_LOT");
   return INIT_SUCCEEDED;
  }
//+------------------------------------------------------------------+
void ExportDealsCsv()
  {
   if(!ExportDeals || !HistorySelect(0, TimeCurrent()))
      return;
   string name = StringFormat("REMIX_V2_deals_M%02d_%s_%s.csv", (int)Module, _Symbol, EnumToString(_Period));
   int fh = FileOpen(name, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
     { PrintFormat("REMIX V2: no se pudo abrir %s (err %d)", name, GetLastError()); return; }
   FileWriteString(fh, "time,ticket,type,entry,volume,price,profit,commission,swap,fee,comment\n");
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
     {
      ulong t = HistoryDealGetTicket(i);
      if(t == 0 || HistoryDealGetInteger(t, DEAL_MAGIC) != MagicNumber)
         continue;
      FileWriteString(fh, StringFormat("%s,%I64u,%d,%d,%.2f,%.5f,%.2f,%.2f,%.2f,%.2f,%s\n",
                      TimeToString((datetime)HistoryDealGetInteger(t, DEAL_TIME), TIME_DATE | TIME_SECONDS),
                      t, (int)HistoryDealGetInteger(t, DEAL_TYPE), (int)HistoryDealGetInteger(t, DEAL_ENTRY),
                      HistoryDealGetDouble(t, DEAL_VOLUME), HistoryDealGetDouble(t, DEAL_PRICE),
                      HistoryDealGetDouble(t, DEAL_PROFIT), HistoryDealGetDouble(t, DEAL_COMMISSION),
                      HistoryDealGetDouble(t, DEAL_SWAP), HistoryDealGetDouble(t, DEAL_FEE),
                      HistoryDealGetString(t, DEAL_COMMENT)));
     }
   FileClose(fh);
  }
//+------------------------------------------------------------------+
void LogSignal(const string what, const int dir, const double sl, const double tp, const double lots)
  {
   if(!LogSignals || !MQLInfoInteger(MQL_TESTER))
      return;
   string name = StringFormat("REMIX_V2_signals_M%02d_%s_%s.csv", (int)Module, _Symbol, EnumToString(_Period));
   int fh = FileOpen(name, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
      return;
   if(FileSize(fh) == 0)
      FileWriteString(fh, "time,module,event,dir,sl_dist,tp_dist,lots,spread_pts,balance\n");
   FileSeek(fh, 0, SEEK_END);
   FileWriteString(fh, StringFormat("%s,%d,%s,%d,%.5f,%.5f,%.2f,%d,%.2f\n", TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), (int)Module, what, dir,
                   sl, tp, lots, (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), AccountInfoDouble(ACCOUNT_BALANCE)));
   FileClose(fh);
  }
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(MQLInfoInteger(MQL_TESTER))
     {
      ExportDealsCsv();
      PrintFormat("REMIX V2 resumen: senales=%I64d ordenes=%I64d fallidas=%I64d omitidas_lote_minimo=%I64d omitidas_spread=%I64d slip_excesivo=%I64d",
                  g_signals, g_orders_sent, g_orders_failed, g_skipped_minlot, g_skipped_spread, g_excess_slip);
     }
   int hs[7] = {h_atr, h_adx, h_rsi, h_sma, h_ema_f, h_ema_m, h_ema_s};
   for(int i = 0; i < 7; i++)
      if(hs[i] != INVALID_HANDLE)
         IndicatorRelease(hs[i]);
  }
//+------------------------------------------------------------------+
//| Criterio de optimizacion penalizado (NO premia solo el beneficio) |
//| = beneficio / max(1, DD equity) * min(1, sqrt(N/100)); 0 si N<30 |
//+------------------------------------------------------------------+
double OnTester()
  {
   double n = TesterStatistics(STAT_TRADES);
   if(n < 30)
      return 0.0;
   double profit = TesterStatistics(STAT_PROFIT);
   double dd = MathMax(1.0, TesterStatistics(STAT_EQUITY_DD));
   return profit / dd * MathMin(1.0, MathSqrt(n / 100.0));
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
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(sl_dist <= 0 || tick_size <= 0 || tick_value <= 0 || step <= 0)
      return 0.0;
   double risk_money   = AccountInfoDouble(ACCOUNT_BALANCE) * RiskPercent / 100.0;
   double loss_per_lot = sl_dist / tick_size * tick_value;
   double lots = MathFloor(risk_money / loss_per_lot / step + 1e-9) * step;
   if(lots < vmin)
     {
      if(SizingPolicy == SIZE_STRICT)
        { g_skipped_minlot++; return 0.0; }
      lots = vmin;
     }
   lots = MathMin(lots, vmax);
   return NormalizeDouble(lots, 2);
  }
//+------------------------------------------------------------------+
//| Apertura. SL obligatorio (sl_dist>0). UNICO sitio de aperturas.   |
//+------------------------------------------------------------------+
void OpenTrade(const int dir, const double sl_dist, const double tp_dist, const int max_bars)
  {
   if(!TradingAllowed())
      return;
   g_signals++;
   if(sl_dist <= 0.0)
     { LogSignal("SKIP_NO_SL", dir, sl_dist, tp_dist, 0); return; }          // nunca sin Stop Loss
   double spread_pts = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double spread = spread_pts * _Point;
   if(spread > MaxSpreadFracSL * sl_dist || (MaxSpreadPoints > 0 && spread_pts > MaxSpreadPoints))
     { g_skipped_spread++; LogSignal("SKIP_SPREAD", dir, sl_dist, tp_dist, 0); return; }
   double lots = CalcLots(sl_dist);
   if(lots <= 0.0)
     { LogSignal("SKIP_MINLOT", dir, sl_dist, tp_dist, 0); return; }
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   string cmt = StringFormat("REMIX V2 M%02d", (int)Module);
   bool ok;
   if(dir > 0)
     { g_exp_price = ask; ok = trade.Buy(lots, _Symbol, 0.0, NormalizeDouble(ask - sl_dist, digits), tp_dist > 0 ? NormalizeDouble(ask + tp_dist, digits) : 0.0, cmt); }
   else
     { g_exp_price = bid; ok = trade.Sell(lots, _Symbol, 0.0, NormalizeDouble(bid + sl_dist, digits), tp_dist > 0 ? NormalizeDouble(bid - tp_dist, digits) : 0.0, cmt); }
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
     {
      g_orders_sent++;
      g_entry_bar = iTime(_Symbol, _Period, 0);
      g_init_risk = sl_dist;
      g_max_bars = max_bars;
      double slip_pts = MathAbs(trade.ResultPrice() - g_exp_price) / _Point;
      LogSignal("OPEN", dir, sl_dist, tp_dist, lots);
      if(slip_pts > MaxSlippagePoints)
        {
         g_excess_slip++;
         PrintFormat("REMIX V2: deslizamiento %.1f pts > maximo %d", slip_pts, MaxSlippagePoints);
         if(CloseOnExcessSlip)
            ClosePosition("slip");
        }
     }
   else
     {
      g_orders_failed++;
      PrintFormat("REMIX V2: orden rechazada ret=%u (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
      LogSignal("ORDER_FAILED", dir, sl_dist, tp_dist, lots);
     }
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
         PrintFormat("REMIX V2: fallo al cerrar (%s) ret=%u", why, trade.ResultRetcode());
      else
         LogSignal("CLOSE_" + why, 0, 0, 0, 0);
     }
  }
//+------------------------------------------------------------------+
void ModifySL(const ulong ticket, const double new_sl)
  {
   if(!TradingAllowed())
      return;
   if(!PositionSelectByTicket(ticket))
      return;
   double stops = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   double freeze = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL) * _Point;
   long type = PositionGetInteger(POSITION_TYPE);
   double px = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double minDist = MathMax(stops, freeze);
   if(MathAbs(px - new_sl) <= minDist)
      return;                                                     // distancia minima del broker
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(!trade.PositionModify(ticket, NormalizeDouble(new_sl, digits), PositionGetDouble(POSITION_TP)))
      PrintFormat("REMIX V2: fallo PositionModify ret=%u", trade.ResultRetcode());
  }
//+------------------------------------------------------------------+
//| BE / trailing, evaluados una vez por barra nueva                  |
//+------------------------------------------------------------------+
void ManagePosition()
  {
   ulong t;
   if(!SelectMyPosition(t) || g_init_risk <= 0.0)
      return;
   long type = PositionGetInteger(POSITION_TYPE);
   double open = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL);
   double px = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double fav = (type == POSITION_TYPE_BUY) ? px - open : open - px;
   int dsgn = (type == POSITION_TYPE_BUY) ? 1 : -1;
   if(UseBreakEven && fav >= BE_TriggerR * g_init_risk)
     {
      double be = open + dsgn * BE_BufferPoints * _Point;
      if((dsgn > 0 && be > sl) || (dsgn < 0 && be < sl))
         ModifySL(t, be);
     }
   if(UseTrailATR && fav >= Trail_ActivateR * g_init_risk)
     {
      double atr[];
      if(GetBuf(h_atr, 0, 1, 1, atr))
        {
         double cand = px - dsgn * Trail_ATR_Mult * atr[0];
         if((dsgn > 0 && cand > sl) || (dsgn < 0 && cand < sl))
            ModifySL(t, cand);
        }
     }
  }
//+------------------------------------------------------------------+
//| S01 London Breakout (referencia)                                  |
//+------------------------------------------------------------------+
void EvalS01()
  {
   datetime t1 = iTime(_Symbol, _Period, 1);
   MqlDateTime d1;
   TimeToStruct(t1, d1);
   if(d1.hour < S01_RangeEndH || d1.hour >= S01_EntryEndH)
      return;
   datetime day = t1 - (datetime)(d1.hour * 3600 + d1.min * 60 + d1.sec);
   if(g_s01_day_done == day)
      return;
   int bars_per_day = 1440 / (PeriodSeconds(_Period) / 60);
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, _Period, 1, 2 * bars_per_day, r) <= 0)
      return;
   double rh = -DBL_MAX, rl = DBL_MAX;
   for(int i = 0; i < ArraySize(r); i++)
     {
      if(r[i].time < day)
         break;
      MqlDateTime s;
      TimeToStruct(r[i].time, s);
      if(s.hour >= S01_RangeStartH && s.hour < S01_RangeEndH)
        { rh = MathMax(rh, r[i].high); rl = MathMin(rl, r[i].low); }
     }
   if(rh == -DBL_MAX)
      return;
   double c1 = r[0].close;
   int dir = (c1 > rh) ? 1 : (c1 < rl ? -1 : 0);
   if(dir == 0)
      return;
   double width = rh - rl;
   if(width < S01_MinRangeSpreadMult * (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point)
      return;
   g_s01_day_done = day;
   double sl = width * S01_SLRangeMult;
   OpenTrade(dir, sl, sl * S01_RR, 0);
  }
//+------------------------------------------------------------------+
//| S05 Z-score reversion: z=(c-SMA)/std (poblacional, ventana [1..N]) |
//+------------------------------------------------------------------+
void EvalS05()
  {
   double cl[], atr[], adx[], sma[];
   ArraySetAsSeries(cl, true);
   if(CopyClose(_Symbol, _Period, 1, S05_SMA_N, cl) != S05_SMA_N || !GetBuf(h_atr, 0, 1, 1, atr))
      return;
   double m = 0.0;
   for(int i = 0; i < S05_SMA_N; i++)
      m += cl[i];
   m /= S05_SMA_N;
   double v = 0.0;
   for(int i = 0; i < S05_SMA_N; i++)
      v += (cl[i] - m) * (cl[i] - m);
   double sd = MathSqrt(v / S05_SMA_N);
   if(sd <= 0.0)
      return;
   double z = (cl[0] - m) / sd;
   int dir = (z <= -S05_Z) ? 1 : (z >= S05_Z ? -1 : 0);
   if(dir == 0)
      return;
   if(S05_UseADXFilter)
     {
      if(!GetBuf(h_adx, 0, 1, 1, adx) || adx[0] >= S05_ADXMax)
         return;
     }
   OpenTrade(dir, atr[0] * S05_SL_ATR, MathAbs(m - cl[0]), S05_MaxBars);
  }
//+------------------------------------------------------------------+
//| S06 RSI-2 + SMA100                                                |
//+------------------------------------------------------------------+
void EvalS06()
  {
   double rsi[], sma[], atr[];
   if(!GetBuf(h_rsi, 0, 1, 1, rsi) || !GetBuf(h_sma, 0, 1, 1, sma) || !GetBuf(h_atr, 0, 1, 1, atr))
      return;
   double c1 = iClose(_Symbol, _Period, 1);
   int dir = (c1 > sma[0] && rsi[0] < S06_RSI_Lo) ? 1 : ((c1 < sma[0] && rsi[0] > S06_RSI_Hi) ? -1 : 0);
   if(dir == 0)
      return;
   OpenTrade(dir, atr[0] * S06_SL_ATR, atr[0] * S06_TP_ATR, S06_MaxBars);
  }
//+------------------------------------------------------------------+
//| S08 Keltner reversion                                             |
//+------------------------------------------------------------------+
void EvalS08()
  {
   double ema[], atr[], adx[];
   if(!GetBuf(h_ema_f, 0, 1, 1, ema) || !GetBuf(h_atr, 0, 1, 1, atr))
      return;
   double c1 = iClose(_Symbol, _Period, 1);
   int dir = (c1 < ema[0] - S08_K * atr[0]) ? 1 : ((c1 > ema[0] + S08_K * atr[0]) ? -1 : 0);
   if(dir == 0)
      return;
   if(S08_UseADXFilter)
     {
      if(!GetBuf(h_adx, 0, 1, 1, adx) || adx[0] >= S08_ADXMax)
         return;
     }
   OpenTrade(dir, atr[0] * S08_SL_ATR, MathAbs(ema[0] - c1), S08_MaxBars);
  }
//+------------------------------------------------------------------+
//| L1: S03 pullback LARGO (ver S03) operado como SELL                |
//+------------------------------------------------------------------+
void EvalL1()
  {
   double ef[], em[], es[], adx[], pdi[], mdi[], atr[];
   if(!GetBuf(h_ema_f, 0, 1, 2, ef) || !GetBuf(h_ema_m, 0, 1, 1, em) || !GetBuf(h_ema_s, 0, 1, 1, es) ||
      !GetBuf(h_adx, 0, 1, 1, adx) || !GetBuf(h_adx, 1, 1, 1, pdi) || !GetBuf(h_adx, 2, 1, 1, mdi) || !GetBuf(h_atr, 0, 1, 1, atr))
      return;
   double c1 = iClose(_Symbol, _Period, 1), c2 = iClose(_Symbol, _Period, 2);
   bool s03_long = (em[0] > es[0]) && (adx[0] > L1_ADXMin) && (pdi[0] > mdi[0]) && (c2 < ef[1]) && (c1 > ef[0]);
   if(!s03_long)
      return;
   OpenTrade(-1, atr[0] * L1_SL_ATR, atr[0] * L1_TP_ATR, 0);
  }
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!TradingAllowed())
      return;
   datetime bar0 = iTime(_Symbol, _Period, 0);
   if(bar0 == g_last_bar)
      return;
   g_last_bar = bar0;                                  // una evaluacion por barra nueva

   bool has_pos = HasPosition();
   if(has_pos)
     {
      // salidas por tiempo / regla (a la apertura de la barra nueva, igual que el motor Python)
      MqlDateTime s;
      TimeToStruct(bar0, s);
      if(Module == MOD_S01 && s.hour >= S01_ExitH)
         ClosePosition("time");
      else if(g_max_bars > 0 && (int)((bar0 - g_entry_bar) / PeriodSeconds(_Period)) >= g_max_bars)
         ClosePosition("maxbars");
      else if(Module == MOD_S06_L3)
        {
         double rsi[];
         ulong tk;
         if(GetBuf(h_rsi, 0, 1, 1, rsi) && SelectMyPosition(tk))
           {
            long ty = PositionGetInteger(POSITION_TYPE);
            if((ty == POSITION_TYPE_BUY && rsi[0] > S06_ExitRsiLong) || (ty == POSITION_TYPE_SELL && rsi[0] < S06_ExitRsiShort))
               ClosePosition("rsi_exit");
           }
        }
      has_pos = HasPosition();
      if(has_pos)
        {
         ManagePosition();
         return;                                       // una posicion a la vez
        }
     }
   switch(Module)
     {
      case MOD_S01:       EvalS01(); break;
      case MOD_S05_L2:    EvalS05(); break;
      case MOD_S06_L3:    EvalS06(); break;
      case MOD_S08_L4:    EvalS08(); break;
      case MOD_L1_S03INV: EvalL1();  break;
      default: break;
     }
  }
//+------------------------------------------------------------------+

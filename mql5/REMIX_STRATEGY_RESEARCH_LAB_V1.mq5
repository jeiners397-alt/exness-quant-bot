//+------------------------------------------------------------------+
//| REMIX_STRATEGY_RESEARCH_LAB_V1.mq5                                |
//| Laboratorio de investigacion REMIX FOREX V1 - SOLO Strategy Tester|
//|                                                                    |
//| SEGURIDAD: este EA solo opera si MQLInfoInteger(MQL_TESTER)==true. |
//| Fuera del Strategy Tester OnInit devuelve INIT_FAILED y ninguna    |
//| funcion de trading es alcanzable.                                  |
//|                                                                    |
//| PROCEDENCIA DE PARAMETROS: valores canonicos de manual fijados a   |
//| priori (Donchian 20, ATR 14, BB 20/2, EMA 20/50/200, ADX 14...).   |
//| NO provienen de optimizacion. Ver docs/STRATEGY_SPECS.md.          |
//|                                                                    |
//| Convenciones (identicas al motor Python):                          |
//|  - Senal en la barra cerrada [1]; entrada a mercado en la apertura |
//|    de la barra [0]. Una posicion a la vez. Horas = hora servidor.  |
//|  - ATR = iATR (SMA del TR). Bollinger poblacional (iBands).        |
//+------------------------------------------------------------------+
#property copyright "REMIX FOREX V1"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

enum ENUM_REMIX_STRATEGY
  {
   STRAT_S01_LONDON_BREAKOUT = 1,   // S01 London Breakout
   STRAT_S02_DONCHIAN_ATR    = 2,   // S02 Donchian Channel + ATR
   STRAT_S03_EMA_ADX_PULL    = 3,   // S03 EMA + ADX Pullback
   STRAT_S04_BB_SQUEEZE_MOM  = 4    // S04 Bollinger Squeeze + Momentum
  };

enum ENUM_SIZING_POLICY
  {
   SIZE_STRICT  = 0,   // Omitir si el lote minimo excede el riesgo
   SIZE_MIN_LOT = 1    // Operar lote minimo aunque exceda el riesgo
  };

input group "=== General ==="
input ENUM_REMIX_STRATEGY Strategy_ID = STRAT_S01_LONDON_BREAKOUT; // Strategy_ID
input double   RiskPercent       = 0.50;       // Riesgo por operacion (% balance)
input ENUM_SIZING_POLICY SizingPolicy = SIZE_STRICT; // Politica de lote minimo
input double   MaxSpreadFrac     = 0.15;       // Spread maximo como fraccion del SL
input int      DeviationPoints   = 20;         // Desviacion maxima (puntos)
input long     MagicNumber       = 20260101;   // Magic
input bool     ExportDeals       = true;       // Exportar operaciones a CSV (Common\Files)

input group "=== S01 London Breakout ==="
input int      S01_RangeStartH   = 0;          // Inicio rango asiatico (hora servidor)
input int      S01_RangeEndH     = 7;          // Fin rango / inicio ventana de ruptura
input int      S01_EntryEndH     = 10;         // Fin ventana de ruptura
input int      S01_ExitH         = 17;         // Cierre forzado
input double   S01_SLRangeMult   = 1.0;        // SL = Rango * mult
input double   S01_RR            = 1.5;        // TP = SL * RR
input double   S01_MinRangeSpreadMult = 10.0;  // Rango >= mult * spread

input group "=== S02 Donchian + ATR ==="
input int      S02_DonchianN     = 20;
input int      S02_ATR_N         = 14;
input double   S02_SL_ATR        = 2.0;
input double   S02_TP_ATR        = 3.0;

input group "=== S03 EMA + ADX Pullback ==="
input int      S03_EMA_Fast      = 20;
input int      S03_EMA_Mid       = 50;
input int      S03_EMA_Slow      = 200;
input int      S03_ADX_N         = 14;
input double   S03_ADX_Min       = 25.0;
input int      S03_ATR_N         = 14;
input double   S03_SL_ATR        = 1.5;
input double   S03_TP_ATR        = 3.0;

input group "=== S04 Bollinger Squeeze + Momentum ==="
input int      S04_BB_N          = 20;
input double   S04_BB_K          = 2.0;
input int      S04_BW_Lookback   = 100;
input double   S04_SqRatio       = 0.75;
input int      S04_Mom_N         = 10;
input int      S04_ATR_N         = 14;
input double   S04_SL_ATR        = 2.0;
input double   S04_TP_ATR        = 3.0;

CTrade   trade;
int      h_atr = INVALID_HANDLE, h_ema_f = INVALID_HANDLE, h_ema_m = INVALID_HANDLE,
         h_ema_s = INVALID_HANDLE, h_adx = INVALID_HANDLE, h_bb = INVALID_HANDLE;
datetime g_last_bar = 0;
datetime g_s01_day_done = 0;      // dia (00:00) en que ya se consumio la primera senal de S01
long     g_skipped_minlot = 0, g_skipped_spread = 0, g_signals = 0, g_orders_sent = 0;

//+------------------------------------------------------------------+
bool IsTesterEnvironment()
  {
   return (bool)MQLInfoInteger(MQL_TESTER);
  }
//+------------------------------------------------------------------+
//| Unica puerta de entrada al trading                                |
//+------------------------------------------------------------------+
bool TradingAllowed()
  {
   if(!MQLInfoInteger(MQL_TESTER))
      return false;                                                    // fuera del tester: NUNCA
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return false;                                                    // nunca en cuenta real
   return true;
  }
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     {
      Print("REMIX LAB: BLOQUEADO. Este EA solo puede ejecutarse en el Strategy Tester. Sin operaciones.");
      Alert("REMIX_STRATEGY_RESEARCH_LAB_V1 solo funciona en el Strategy Tester.");
      return INIT_FAILED;
     }
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
      return INIT_FAILED;

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(DeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   switch(Strategy_ID)
     {
      case STRAT_S01_LONDON_BREAKOUT:
         if(S01_RangeEndH <= S01_RangeStartH || S01_EntryEndH <= S01_RangeEndH || S01_ExitH < S01_EntryEndH)
           { Print("S01: horas inconsistentes"); return INIT_PARAMETERS_INCORRECT; }
         break;
      case STRAT_S02_DONCHIAN_ATR:
         h_atr = iATR(_Symbol, _Period, S02_ATR_N);
         break;
      case STRAT_S03_EMA_ADX_PULL:
         h_atr   = iATR(_Symbol, _Period, S03_ATR_N);
         h_ema_f = iMA(_Symbol, _Period, S03_EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
         h_ema_m = iMA(_Symbol, _Period, S03_EMA_Mid,  0, MODE_EMA, PRICE_CLOSE);
         h_ema_s = iMA(_Symbol, _Period, S03_EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
         h_adx   = iADX(_Symbol, _Period, S03_ADX_N);
         if(h_ema_f == INVALID_HANDLE || h_ema_m == INVALID_HANDLE || h_ema_s == INVALID_HANDLE || h_adx == INVALID_HANDLE)
            return INIT_FAILED;
         break;
      case STRAT_S04_BB_SQUEEZE_MOM:
         h_atr = iATR(_Symbol, _Period, S04_ATR_N);
         h_bb  = iBands(_Symbol, _Period, S04_BB_N, 0, S04_BB_K, PRICE_CLOSE);
         if(h_bb == INVALID_HANDLE)
            return INIT_FAILED;
         break;
     }
   if(Strategy_ID != STRAT_S01_LONDON_BREAKOUT && h_atr == INVALID_HANDLE)
      return INIT_FAILED;

   PrintFormat("REMIX LAB init OK | Strategy=%d | %s %s | Risk=%.2f%% | Sizing=%s | tester=%d",
               (int)Strategy_ID, _Symbol, EnumToString(_Period), RiskPercent,
               SizingPolicy == SIZE_STRICT ? "STRICT" : "MIN_LOT", (int)MQLInfoInteger(MQL_TESTER));
   return INIT_SUCCEEDED;
  }
//+------------------------------------------------------------------+
void ExportDealsCsv()
  {
   if(!ExportDeals)
      return;
   if(!HistorySelect(0, TimeCurrent()))
      return;
   string name = StringFormat("REMIX_deals_S%02d_%s_%s.csv", (int)Strategy_ID, _Symbol, EnumToString(_Period));
   int fh = FileOpen(name, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
     { PrintFormat("REMIX LAB: no se pudo abrir %s (err %d)", name, GetLastError()); return; }
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
void OnDeinit(const int reason)
  {
   if(IsTesterEnvironment())
     {
      ExportDealsCsv();
      PrintFormat("REMIX LAB resumen: senales=%I64d ordenes=%I64d omitidas_lote_minimo=%I64d omitidas_spread=%I64d",
                  g_signals, g_orders_sent, g_skipped_minlot, g_skipped_spread);
     }
   int hs[6] = {h_atr, h_ema_f, h_ema_m, h_ema_s, h_adx, h_bb};
   for(int i = 0; i < 6; i++)
      if(hs[i] != INVALID_HANDLE)
         IndicatorRelease(hs[i]);
  }
//+------------------------------------------------------------------+
double OnTester()
  {
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 30)
      return 0.0;
   return TesterStatistics(STAT_PROFIT_FACTOR);   // criterio personalizado (solo para optimizacion)
  }
//+------------------------------------------------------------------+
bool GetBuf(const int handle, const int buffer, const int shift, const int count, double &arr[])
  {
   ArraySetAsSeries(arr, true);
   return CopyBuffer(handle, buffer, shift, count, arr) == count;
  }
//+------------------------------------------------------------------+
//| Tamano de lote por riesgo; devuelve 0 si se omite                 |
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
//| Apertura de posicion. UNICO sitio que envia ordenes de apertura.  |
//+------------------------------------------------------------------+
void OpenTrade(const int dir, const double sl_dist, const double tp_dist)
  {
   if(!TradingAllowed())             // doble candado: tester + no cuenta real
      return;
   g_signals++;
   double spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
   if(spread > MaxSpreadFrac * sl_dist)
     { g_skipped_spread++; return; }
   double lots = CalcLots(sl_dist);
   if(lots <= 0.0)
      return;
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   string cmt = StringFormat("REMIX S%02d", (int)Strategy_ID);
   bool ok;
   if(dir > 0)
      ok = trade.Buy(lots, _Symbol, 0.0, NormalizeDouble(ask - sl_dist, digits), NormalizeDouble(ask + tp_dist, digits), cmt);
   else
      ok = trade.Sell(lots, _Symbol, 0.0, NormalizeDouble(bid + sl_dist, digits), NormalizeDouble(bid - tp_dist, digits), cmt);
   if(ok)
      g_orders_sent++;
   else
      PrintFormat("REMIX LAB: orden rechazada ret=%u (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }
//+------------------------------------------------------------------+
bool HasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
         return true;
     }
   return false;
  }
//+------------------------------------------------------------------+
void ClosePosition()
  {
   if(!TradingAllowed())
      return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
         trade.PositionClose(t);
     }
  }
//+------------------------------------------------------------------+
//| S01 London Breakout                                               |
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
      return;                                               // primera senal del dia ya consumida
   // rango asiatico de ese dia
   int bars_per_day = 1440 / (PeriodSeconds(_Period) / 60);
   int need = 2 * bars_per_day;
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, _Period, 1, need, r) <= 0)
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
   double width  = rh - rl;
   double spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
   if(width < S01_MinRangeSpreadMult * spread)
      return;                                               // no cuenta como primera senal (igual que Python)
   g_s01_day_done = day;
   double sl = width * S01_SLRangeMult;
   OpenTrade(dir, sl, sl * S01_RR);
  }
//+------------------------------------------------------------------+
//| S02 Donchian + ATR                                                |
//+------------------------------------------------------------------+
void EvalS02()
  {
   double hi[], lo[], atr[];
   ArraySetAsSeries(hi, true);
   ArraySetAsSeries(lo, true);
   if(CopyHigh(_Symbol, _Period, 2, S02_DonchianN, hi) != S02_DonchianN ||
      CopyLow(_Symbol, _Period, 2, S02_DonchianN, lo) != S02_DonchianN || !GetBuf(h_atr, 0, 1, 1, atr))
      return;
   double hh = hi[ArrayMaximum(hi)], ll = lo[ArrayMinimum(lo)];
   double c1 = iClose(_Symbol, _Period, 1);
   int dir = (c1 > hh) ? 1 : (c1 < ll ? -1 : 0);
   if(dir != 0)
      OpenTrade(dir, atr[0] * S02_SL_ATR, atr[0] * S02_TP_ATR);
  }
//+------------------------------------------------------------------+
//| S03 EMA + ADX Pullback                                            |
//+------------------------------------------------------------------+
void EvalS03()
  {
   double ef[], em[], es[], adx[], pdi[], mdi[], atr[];
   if(!GetBuf(h_ema_f, 0, 1, 2, ef) || !GetBuf(h_ema_m, 0, 1, 1, em) || !GetBuf(h_ema_s, 0, 1, 1, es) ||
      !GetBuf(h_adx, 0, 1, 1, adx) || !GetBuf(h_adx, 1, 1, 1, pdi) || !GetBuf(h_adx, 2, 1, 1, mdi) ||
      !GetBuf(h_atr, 0, 1, 1, atr))
      return;
   double c1 = iClose(_Symbol, _Period, 1), c2 = iClose(_Symbol, _Period, 2);
   bool up = em[0] > es[0] && adx[0] > S03_ADX_Min && pdi[0] > mdi[0] && c2 < ef[1] && c1 > ef[0];
   bool dn = em[0] < es[0] && adx[0] > S03_ADX_Min && mdi[0] > pdi[0] && c2 > ef[1] && c1 < ef[0];
   if(up)
      OpenTrade(1, atr[0] * S03_SL_ATR, atr[0] * S03_TP_ATR);
   else
      if(dn)
         OpenTrade(-1, atr[0] * S03_SL_ATR, atr[0] * S03_TP_ATR);
  }
//+------------------------------------------------------------------+
//| S04 Bollinger Squeeze + Momentum                                  |
//+------------------------------------------------------------------+
void EvalS04()
  {
   double mid[], up[], lo[], atr[];
   // bandas en shifts 2..(L+1) para squeeze en la barra anterior a la senal; y banda de la barra [1]
   if(!GetBuf(h_bb, 0, 1, S04_BW_Lookback + 1, mid) || !GetBuf(h_bb, 1, 1, S04_BW_Lookback + 1, up) ||
      !GetBuf(h_bb, 2, 1, S04_BW_Lookback + 1, lo) || !GetBuf(h_atr, 0, 1, 1, atr))
      return;
   // indices: [0]=barra 1 (senal), [1]=barra 2 (squeeze), ..., [L]=barra L+1
   double sum = 0;
   for(int k = 1; k <= S04_BW_Lookback; k++)
     {
      if(mid[k] == 0)
         return;
      sum += (up[k] - lo[k]) / mid[k];
     }
   double sma_bw = sum / S04_BW_Lookback;
   double bw_prev = (up[1] - lo[1]) / mid[1];
   if(!(bw_prev < S04_SqRatio * sma_bw))
      return;
   double c1 = iClose(_Symbol, _Period, 1);
   double mom = c1 - iClose(_Symbol, _Period, 1 + S04_Mom_N);
   if(c1 > up[0] && mom > 0)
      OpenTrade(1, atr[0] * S04_SL_ATR, atr[0] * S04_TP_ATR);
   else
      if(c1 < lo[0] && mom < 0)
         OpenTrade(-1, atr[0] * S04_SL_ATR, atr[0] * S04_TP_ATR);
  }
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!TradingAllowed())
      return;
   datetime bar0 = iTime(_Symbol, _Period, 0);
   if(bar0 == g_last_bar)
      return;                                   // solo una evaluacion por barra nueva
   g_last_bar = bar0;

   bool has_pos = HasPosition();
   // cierre por tiempo (S01): primera barra con hora >= ExitH
   if(Strategy_ID == STRAT_S01_LONDON_BREAKOUT && has_pos)
     {
      MqlDateTime s;
      TimeToStruct(bar0, s);
      if(s.hour >= S01_ExitH)
        {
         ClosePosition();
         has_pos = HasPosition();
        }
     }
   if(has_pos)
      return;                                   // una posicion a la vez

   switch(Strategy_ID)
     {
      case STRAT_S01_LONDON_BREAKOUT: EvalS01(); break;
      case STRAT_S02_DONCHIAN_ATR:    EvalS02(); break;
      case STRAT_S03_EMA_ADX_PULL:    EvalS03(); break;
      case STRAT_S04_BB_SQUEEZE_MOM:  EvalS04(); break;
     }
  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| REMIX_V8_XAU_BREAKOUT.mq5 - EA EXPERIMENTAL, SOLO Strategy Tester |
//| HIPOTESIS NO VALIDADA (V7 clase C). Reproduce EXACTAMENTE la      |
//| definicion de research/v7_event_study.py::ev_sweep_96 invertida:  |
//|  VARIANT_A_V7: la vela cerrada i supera en >PierceATR*ATR el      |
//|     maximo/minimo de las Lookback velas previas PERO CIERRA DENTRO|
//|     (pico/sweep); se opera A FAVOR del pico (continuacion).       |
//|  VARIANT_B_CLOSE_OUT: primera vela que CIERRA fuera del nivel de  |
//|     Lookback velas (ruptura confirmada), continuacion. Hipotesis  |
//|     distinta, declarada aparte.                                   |
//| Entrada: mercado en la apertura de la vela siguiente a la senal.  |
//| SL = SL_ATR*ATR(senal), TP = RR*SL, salida temporal MaxHoldBars.  |
//| Sin martingala, sin recuperacion, sin aumento de lote tras perder.|
//| Bloqueado fuera del probador y en cuenta real.                    |
//+------------------------------------------------------------------+
#property copyright "REMIX V8"
#property version   "8.00"
#property strict

#include <Trade\Trade.mqh>

enum ENUM_V8_VARIANT { VARIANT_A_V7 = 0, VARIANT_B_CLOSE_OUT = 1 };

input group "=== Seguridad ==="
input bool            EnableTrading   = false;
input long            MagicNumber     = 20268001;
input group "=== Senal (parametrizada, defecto = V7 exacto) ==="
input ENUM_V8_VARIANT Variant         = VARIANT_A_V7;
input int             Lookback        = 96;
input double          PierceATR       = 0.10;
input int             ATR_N           = 14;
input int             CooldownBars    = 12;
input group "=== Salidas ==="
input double          SL_ATR          = 1.0;
input double          RR              = 1.5;
input int             MaxHoldBars     = 40;
input group "=== Tamano / margen / riesgo (independientes) ==="
input double          FixedLot        = 0.01;     // 0 = dinamico por margen/riesgo
input double          MarginPct       = 5.0;      // margen agregado maximo del simbolo (% equidad)
input double          RiskPctCap      = 3.0;      // rechaza si la perdida al SL del lote excede este % de equidad
input double          DynRiskPct      = 0.5;      // solo si FixedLot=0
input bool            CheckPending    = true;
input group "=== Registro ==="
input bool            LogFiles        = true;
input string          RunTag          = "V8";

struct Track { ulong pid; datetime t_open; double entry; double sl_dist; double mfe; double mae; double margin; double risk_money; double spread_pts; int dir; int bar_open; };

CTrade   trade;
int      h_atr = INVALID_HANDLE;
datetime g_last_bar = 0;
long     g_bar = 0, g_last_sig_bar = -1000000;
long     g_sig = 0, g_cool = 0, g_open = 0, g_rej_margin = 0, g_rej_risk = 0, g_rej_lot = 0, g_failed = 0;
double   g_max_margin_pct = 0.0;
Track    g_tr[];
int      g_hs = INVALID_HANDLE, g_ht = INVALID_HANDLE;

int CountOwn();
//+------------------------------------------------------------------+
bool TradingAllowed()
  {
   if(!MQLInfoInteger(MQL_TESTER)) return false;
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL) return false;
   return EnableTrading;
  }
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER)) { Print("REMIX V8: BLOQUEADO fuera del Strategy Tester."); return INIT_FAILED; }
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL) return INIT_FAILED;
   if(Lookback < 5 || RR <= 0 || SL_ATR <= 0 || MarginPct <= 0 || MarginPct > 100) return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFillingBySymbol(_Symbol);
   h_atr = iATR(_Symbol, _Period, ATR_N);
   if(h_atr == INVALID_HANDLE) return INIT_FAILED;
   if(LogFiles)
     {
      g_hs = FileOpen("REMIX_" + RunTag + "_signals.csv", FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
      g_ht = FileOpen("REMIX_" + RunTag + "_trades.csv", FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
      if(g_hs != INVALID_HANDLE)
         FileWrite(g_hs, "signal_bar_time", "decision", "side", "level", "atr", "bar_high", "bar_low", "bar_close", "lot", "margin", "margin_pct_eq", "risk_money", "risk_pct_eq", "spread_pts", "equity");
      if(g_ht != INVALID_HANDLE)
         FileWrite(g_ht, "position_id", "dir", "open_time", "close_time", "entry", "exit", "sl_dist", "volume", "profit", "commission", "swap", "R", "mfe_R", "mae_R", "bars_held", "exit_reason", "margin", "risk_money", "spread_pts_entry", "hour_entry");
     }
   PrintFormat("REMIX V8 init | variant=%d lookback=%d pierce=%.2f ATR_N=%d SL=%.2fxATR RR=%.2f hold=%d cool=%d lot=%.2f | %s %s | volmin=%.2f step=%.2f contract=%.1f",
               (int)Variant, Lookback, PierceATR, ATR_N, SL_ATR, RR, MaxHoldBars, CooldownBars, FixedLot, _Symbol, EnumToString(_Period),
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE));
   return INIT_SUCCEEDED;
  }
//+------------------------------------------------------------------+
double CommittedMargin()
  {
   double tot = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != MagicNumber || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      double m = 0.0;
      ENUM_ORDER_TYPE ot = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(OrderCalcMargin(ot, _Symbol, PositionGetDouble(POSITION_VOLUME), PositionGetDouble(POSITION_PRICE_OPEN), m)) tot += m;
     }
   if(CheckPending)
      for(int i = OrdersTotal() - 1; i >= 0; i--)
        {
         ulong t = OrderGetTicket(i);
         if(t == 0 || OrderGetInteger(ORDER_MAGIC) != MagicNumber || OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
         double m = 0.0;
         ENUM_ORDER_TYPE ot = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
         ENUM_ORDER_TYPE mt = (ot == ORDER_TYPE_BUY_LIMIT || ot == ORDER_TYPE_BUY_STOP) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
         if(OrderCalcMargin(mt, _Symbol, OrderGetDouble(ORDER_VOLUME_CURRENT), OrderGetDouble(ORDER_PRICE_OPEN), m)) tot += m;
        }
   return tot;
  }
double FloorStep(const double v, const double step)
  {
   if(v <= 0 || step <= 0) return 0.0;
   return NormalizeDouble(MathFloor(v / step + 1e-9) * step, 8);
  }
//+------------------------------------------------------------------+
void LogSignal(const datetime bt, const string decision, const int dir, const double level, const double atr, const double lot, const double margin, const double risk, const double spr)
  {
   if(g_hs == INVALID_HANDLE) return;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   FileWrite(g_hs, TimeToString(bt, TIME_DATE | TIME_MINUTES), decision, dir, DoubleToString(level, _Digits), DoubleToString(atr, 5),
             DoubleToString(iHigh(_Symbol, _Period, 1), _Digits), DoubleToString(iLow(_Symbol, _Period, 1), _Digits), DoubleToString(iClose(_Symbol, _Period, 1), _Digits),
             DoubleToString(lot, 2), DoubleToString(margin, 2), DoubleToString(eq > 0 ? 100.0 * margin / eq : 0, 3), DoubleToString(risk, 2), DoubleToString(eq > 0 ? 100.0 * risk / eq : 0, 3),
             DoubleToString(spr, 0), DoubleToString(eq, 2));
   FileFlush(g_hs);
  }
//+------------------------------------------------------------------+
void OpenTrade(const int dir, const double atr, const datetime signal_bar, const double level)
  {
   g_sig++;
   if(g_bar - g_last_sig_bar < CooldownBars)
     { g_cool++; LogSignal(signal_bar, "COOLDOWN", dir, level, atr, 0, 0, 0, 0); return; }
   g_last_sig_bar = g_bar;
   ENUM_ORDER_TYPE ot = dir > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double price = dir > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sld = SL_ATR * atr, tpd = RR * sld;
   double sl = NormalizeDouble(price - dir * sld, _Digits), tp = NormalizeDouble(price + dir * tpd, _Digits);
   double spr = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point;
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY), m1 = 0.0, p1 = 0.0;
   if(!OrderCalcMargin(ot, _Symbol, 1.0, price, m1) || !OrderCalcProfit(ot, _Symbol, 1.0, price, sl, p1) || m1 <= 0 || p1 >= 0)
     { g_failed++; LogSignal(signal_bar, "CALC_FAIL", dir, level, atr, 0, 0, 0, spr); return; }
   double lot = FixedLot;
   if(lot <= 0)
     {
      double avail = MathMax(0.0, eq * MarginPct / 100.0 - CommittedMargin());
      lot = MathMin(MathMin(FloorStep(avail / m1, step), FloorStep(eq * DynRiskPct / 100.0 / (-p1), step)), vmax);
     }
   lot = FloorStep(lot, step);
   if(lot < vmin - 1e-12) { g_rej_lot++; LogSignal(signal_bar, "REJ_MIN_LOT", dir, level, atr, lot, 0, 0, spr); return; }
   double m_new = m1 * lot, risk = -p1 * lot;
   if(CommittedMargin() + m_new > eq * MarginPct / 100.0 + 1e-9) { g_rej_margin++; LogSignal(signal_bar, "REJ_MARGIN", dir, level, atr, lot, m_new, risk, spr); return; }
   if(risk > eq * RiskPctCap / 100.0 + 1e-9) { g_rej_risk++; LogSignal(signal_bar, "REJ_RISK", dir, level, atr, lot, m_new, risk, spr); return; }
   if(!TradingAllowed()) { LogSignal(signal_bar, "TRADING_OFF", dir, level, atr, lot, m_new, risk, spr); return; }
   bool ok = dir > 0 ? trade.Buy(lot, _Symbol, 0.0, sl, tp, "V8") : trade.Sell(lot, _Symbol, 0.0, sl, tp, "V8");
   if(!ok || (trade.ResultRetcode() != TRADE_RETCODE_DONE && trade.ResultRetcode() != TRADE_RETCODE_PLACED))
     { g_failed++; LogSignal(signal_bar, "ORDER_FAIL_" + IntegerToString((int)trade.ResultRetcode()), dir, level, atr, lot, m_new, risk, spr); return; }
   g_open++;
   double mp = 100.0 * (CommittedMargin()) / eq;
   if(mp > g_max_margin_pct) g_max_margin_pct = mp;
   LogSignal(signal_bar, "OPEN", dir, level, atr, lot, m_new, risk, spr);
   // el seguimiento (MFE/MAE) se registra en OnTradeTransaction al llegar el deal de entrada
   ulong pid = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == MagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_TIME) >= (long)iTime(_Symbol, _Period, 0))
         pid = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
     }
   int k = ArraySize(g_tr);
   ArrayResize(g_tr, k + 1);
   g_tr[k].pid = pid; g_tr[k].t_open = TimeCurrent(); g_tr[k].entry = price; g_tr[k].sl_dist = sld; g_tr[k].mfe = 0; g_tr[k].mae = 0;
   g_tr[k].margin = m_new; g_tr[k].risk_money = risk; g_tr[k].spread_pts = spr; g_tr[k].dir = dir; g_tr[k].bar_open = (int)g_bar;
  }
//+------------------------------------------------------------------+
void UpdateExcursions()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   for(int k = 0; k < ArraySize(g_tr); k++)
     {
      double px = g_tr[k].dir > 0 ? bid : ask;
      double fav = g_tr[k].dir * (px - g_tr[k].entry), adv = -fav;
      if(fav > g_tr[k].mfe) g_tr[k].mfe = fav;
      if(adv > g_tr[k].mae) g_tr[k].mae = adv;
     }
  }
//+------------------------------------------------------------------+
void CloseOld()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != MagicNumber || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(iBarShift(_Symbol, _Period, (datetime)PositionGetInteger(POSITION_TIME), false) >= MaxHoldBars)
         trade.PositionClose(t);
     }
  }
//+------------------------------------------------------------------+
void OnTick()
  {
   if(CountOwn() > 0) UpdateExcursions();
   datetime bt = iTime(_Symbol, _Period, 0);
   if(bt == g_last_bar) return;
   g_last_bar = bt;
   g_bar++;
   if(TradingAllowed()) CloseOld();
   double a[];
   ArraySetAsSeries(a, true);
   if(CopyBuffer(h_atr, 0, 1, 1, a) != 1 || a[0] <= 0.0) return;
   double atr = a[0];
   int ih = iHighest(_Symbol, _Period, MODE_HIGH, Lookback, 2), il = iLowest(_Symbol, _Period, MODE_LOW, Lookback, 2);
   if(ih < 0 || il < 0) return;
   double ph = iHigh(_Symbol, _Period, ih), pl = iLow(_Symbol, _Period, il);
   double h1 = iHigh(_Symbol, _Period, 1), l1 = iLow(_Symbol, _Period, 1), c1 = iClose(_Symbol, _Period, 1);
   datetime sb = iTime(_Symbol, _Period, 1);
   if(Variant == VARIANT_A_V7)
     {
      bool up = (h1 > ph + PierceATR * atr) && (c1 < ph);
      bool dn = (l1 < pl - PierceATR * atr) && (c1 > pl);
      if(up) OpenTrade(+1, atr, sb, ph);            // pico al alza que cierra dentro -> LARGO (continuacion)
      else if(dn) OpenTrade(-1, atr, sb, pl);
     }
   else
     {
      int ih2 = iHighest(_Symbol, _Period, MODE_HIGH, Lookback, 3), il2 = iLowest(_Symbol, _Period, MODE_LOW, Lookback, 3);
      if(ih2 < 0 || il2 < 0) return;
      double ph2 = iHigh(_Symbol, _Period, ih2), pl2 = iLow(_Symbol, _Period, il2), c2 = iClose(_Symbol, _Period, 2);
      bool up = (c1 > ph) && (c2 <= ph2);
      bool dn = (c1 < pl) && (c2 >= pl2);
      if(up) OpenTrade(+1, atr, sb, ph);
      else if(dn) OpenTrade(-1, atr, sb, pl);
     }
  }
int CountOwn()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == MagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol) n++;
     }
   return n;
  }
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || g_ht == INVALID_HANDLE) return;
   ulong deal = trans.deal;
   if(!HistoryDealSelect(deal)) return;
   if(HistoryDealGetInteger(deal, DEAL_MAGIC) != MagicNumber) return;
   long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
   ulong pid = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
   if(entry == DEAL_ENTRY_IN)
     {
      for(int k = 0; k < ArraySize(g_tr); k++)
         if(g_tr[k].pid == 0) { g_tr[k].pid = pid; break; }
      return;
     }
   if(entry != DEAL_ENTRY_OUT) return;
   int k = -1;
   for(int j = 0; j < ArraySize(g_tr); j++) if(g_tr[j].pid == pid) { k = j; break; }
   if(k < 0) return;
   double px = HistoryDealGetDouble(deal, DEAL_PRICE), pr = HistoryDealGetDouble(deal, DEAL_PROFIT), cm = HistoryDealGetDouble(deal, DEAL_COMMISSION), sw = HistoryDealGetDouble(deal, DEAL_SWAP);
   double vol = HistoryDealGetDouble(deal, DEAL_VOLUME);
   long why = HistoryDealGetInteger(deal, DEAL_REASON);
   string rs = (why == DEAL_REASON_SL) ? "SL" : (why == DEAL_REASON_TP) ? "TP" : (why == DEAL_REASON_EXPERT) ? "TIME" : "OTHER_" + IntegerToString((int)why);
   double R = g_tr[k].dir * (px - g_tr[k].entry) / g_tr[k].sl_dist;
   MqlDateTime s; TimeToStruct(g_tr[k].t_open, s);
   FileWrite(g_ht, (long)pid, g_tr[k].dir, TimeToString(g_tr[k].t_open, TIME_DATE | TIME_MINUTES | TIME_SECONDS), TimeToString((datetime)HistoryDealGetInteger(deal, DEAL_TIME), TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             DoubleToString(g_tr[k].entry, _Digits), DoubleToString(px, _Digits), DoubleToString(g_tr[k].sl_dist, _Digits), DoubleToString(vol, 2), DoubleToString(pr, 2), DoubleToString(cm, 2), DoubleToString(sw, 2),
             DoubleToString(R, 4), DoubleToString(g_tr[k].mfe / g_tr[k].sl_dist, 4), DoubleToString(g_tr[k].mae / g_tr[k].sl_dist, 4), (int)(g_bar - g_tr[k].bar_open), rs,
             DoubleToString(g_tr[k].margin, 2), DoubleToString(g_tr[k].risk_money, 2), DoubleToString(g_tr[k].spread_pts, 0), s.hour);
   FileFlush(g_ht);
   int n = ArraySize(g_tr);
   for(int j = k; j < n - 1; j++) g_tr[j] = g_tr[j + 1];
   ArrayResize(g_tr, n - 1);
  }
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(MQLInfoInteger(MQL_TESTER))
      PrintFormat("REMIX V8 resumen: barras=%I64d senales=%I64d cooldown=%I64d abiertas=%I64d rech_margen=%I64d rech_riesgo=%I64d rech_lote=%I64d fallidas=%I64d max_margen_simbolo=%.3f%%",
                  g_bar, g_sig, g_cool, g_open, g_rej_margin, g_rej_risk, g_rej_lot, g_failed, g_max_margin_pct);
   if(g_hs != INVALID_HANDLE) FileClose(g_hs);
   if(g_ht != INVALID_HANDLE) FileClose(g_ht);
   if(h_atr != INVALID_HANDLE) IndicatorRelease(h_atr);
  }
//+------------------------------------------------------------------+

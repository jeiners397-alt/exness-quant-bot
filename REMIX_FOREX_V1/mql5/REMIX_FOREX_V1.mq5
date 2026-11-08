//+------------------------------------------------------------------+
//| REMIX FOREX V1 — Fase 0: diagnóstico EXCLUSIVAMENTE de solo lectura|
//| No importa Trade.mqh, no construye solicitudes ni envía órdenes.   |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "FASE 0: conectividad, modo demo y ticks (sin operaciones)"

input bool EnableTrading = false; // reservado; NO activa operaciones en esta versión
input int  RefreshSeconds = 5;

int OnInit()
  {
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
     {
      Print("REMIX FASE 0: ERROR. Se requiere una cuenta DEMO.");
      return INIT_FAILED;
     }
   if(EnableTrading)
     {
      Print("REMIX FASE 0: ERROR. EnableTrading debe ser false.");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(RefreshSeconds < 1 || RefreshSeconds > 3600)
      return INIT_PARAMETERS_INCORRECT;
   EventSetTimer(RefreshSeconds);
   Print("REMIX FOREX V1 FASE 0 activo, SOLO ANALISIS, DEMO, sin envío de órdenes.");
   RenderStatus();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
   PrintFormat("REMIX FASE 0 detenido, motivo=%d", reason);
  }

void OnTick()
  {
   // NO HAY NINGUNA FUNCIÓN DE TRADING EN ESTE EA.
  }

void OnTimer()
  {
   RenderStatus();
  }

void RenderStatus()
  {
   MqlTick tick;
   bool available = SymbolInfoTick(_Symbol, tick);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double spread_points = (available && point > 0.0) ? (tick.ask - tick.bid)/point : 0.0;
   string quote = available ? StringFormat("Bid: %s | Ask: %s | Spread: %.1f puntos",
                                            DoubleToString(tick.bid, _Digits),
                                            DoubleToString(tick.ask, _Digits), spread_points) : "Tick no disponible";
   string panel = "REMIX FOREX V1 | FASE 0\n"+
                  "ESTADO: SOLO ANALISIS — NO OPERA\n"+
                  "Cuenta: DEMO verificada\n"+
                  "Símbolo: "+_Symbol+" | TF: "+EnumToString(_Period)+"\n"+
                  quote+"\n"+
                  "Balance: "+DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2)+" "+AccountInfoString(ACCOUNT_CURRENCY)+"\n"+
                  "Equity: "+DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2)+"\n"+
                  "Margen libre: "+DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE),2)+"\n"+
                  "Órdenes enviadas por este EA: 0";
   Comment(panel);
  }

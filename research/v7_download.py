import MetaTrader5 as mt5, pandas as pd, json
from datetime import datetime
LAB=r"C:\REMIX_MT5_LAB\terminal\terminal64.exe"
SYMS=["EURUSDm","GBPUSDm","USDJPYm","XAUUSDm","XAGUSDm","US30m","US500m","USTECm","BTCUSDm","ETHUSDm"]
assert mt5.initialize(path=LAB, portable=True), mt5.last_error()
ai=mt5.account_info(); print("account",ai.login,ai.server,ai.trade_mode,"pos",mt5.positions_total())
out={}
for s in SYMS:
    mt5.symbol_select(s,True)
    si=mt5.symbol_info(s)
    import time
    r=None
    for k in range(3):
        mt5.copy_rates_from_pos(s,mt5.TIMEFRAME_M15,0,10)
        r=mt5.copy_rates_range(s,mt5.TIMEFRAME_M15,datetime(2024,1,1),datetime(2026,11,1))
        if r is not None and len(r)>1000: break
        time.sleep(5)
    if r is None or len(r)==0: out[s]=dict(err=str(mt5.last_error())); print(s,"SIN DATOS"); continue
    d=pd.DataFrame(r); d["time"]=pd.to_datetime(d.time,unit="s"); d.to_csv(f"data/raw/v7/{s}_M15.csv",index=False)
    out[s]=dict(bars=len(d),first=str(d.time.iloc[0]),last=str(d.time.iloc[-1]),digits=si.digits,point=si.point,min_lot=si.volume_min,step=si.volume_step,contract=si.trade_contract_size,tick_value=si.trade_tick_value,tick_size=si.trade_tick_size,cmode=si.trade_calc_mode,med_spread=float(d.spread.median()),commission_note="spread-only")
    print(s,out[s]["bars"],out[s]["first"],out[s]["last"],"spread",out[s]["med_spread"])
json.dump(out,open("data/raw/v7/download_info.json","w"),indent=1)
mt5.shutdown()




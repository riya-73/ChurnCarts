from __future__ import annotations
import sqlite3, json, warnings
from pathlib import Path
import numpy as np, pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.graphics.tsaplots import acf
ROOT=Path(__file__).resolve().parents[1]
def metrics(y,p):
    y,p=np.asarray(y),np.asarray(p); e=y-p
    return {'mae':float(np.mean(np.abs(e))),'rmse':float(np.sqrt(np.mean(e**2))),'mape':float(np.mean(np.abs(e/y))*100)}
def choose_model(y,season=12):
    best=None
    for order in [(0,1,1),(1,1,0),(1,1,1),(2,1,1),(1,1,2)]:
      for seasonal in [(0,1,1,season),(1,1,0,season),(1,1,1,season)]:
       try:
        fit=SARIMAX(y,order=order,seasonal_order=seasonal,enforce_stationarity=False,enforce_invertibility=False).fit(disp=False,maxiter=80)
        if best is None or fit.aic<best['aic']: best={'order':order,'seasonal_order':seasonal,'aic':float(fit.aic)}
       except Exception: pass
    return best or {'order':(1,1,1),'seasonal_order':(0,1,1,season),'aic':None}
def run_forecast(db_path=ROOT/'data/churncarts.db',horizon=6):
    con=sqlite3.connect(db_path); s=pd.read_sql_query("SELECT month, revenue FROM v_monthly_revenue ORDER BY month",con); con.close()
    s['month']=pd.to_datetime(s.month); y=s.set_index('month').revenue.asfreq('MS').fillna(0); season=12
    split=max(12,int(len(y)*0.85)); train,test=y.iloc[:split],y.iloc[split:]
    tests={}
    with warnings.catch_warnings():
      warnings.simplefilter('ignore');
      adf=adfuller(y.dropna(),autolag='AIC');
      try: kp=kpss(y.dropna(),regression='c',nlags='auto')
      except Exception: kp=(np.nan,np.nan)
      best=choose_model(train,season); fit=SARIMAX(train,order=best['order'],seasonal_order=best['seasonal_order'],enforce_stationarity=False,enforce_invertibility=False).fit(disp=False)
      pred=fit.get_forecast(len(test)).predicted_mean
    naive=pd.Series(np.resize(train.iloc[-season:].values, len(test)),index=test.index) if len(train)>=season else pd.Series(train.iloc[-1],index=test.index)
    tests['sarima']=metrics(test,pred); tests['seasonal_naive']=metrics(test,naive)
    with warnings.catch_warnings():
      warnings.simplefilter('ignore'); full=SARIMAX(y,order=best['order'],seasonal_order=best['seasonal_order'],enforce_stationarity=False,enforce_invertibility=False).fit(disp=False); fc=full.get_forecast(horizon); ci=fc.conf_int()
    forecast=pd.DataFrame({'month':fc.predicted_mean.index,'forecast':fc.predicted_mean.values,'lower':ci.iloc[:,0].values,'upper':ci.iloc[:,1].values}); forecast.to_csv(ROOT/'artifacts/forecast.csv',index=False)
    resid=full.resid.dropna(); lb=acorr_ljungbox(resid,lags=[min(12,max(1,len(resid)//5))],return_df=True)
    diagnostics={'adf_stat':float(adf[0]),'adf_pvalue':float(adf[1]),'kpss_stat':float(kp[0]),'kpss_pvalue':float(kp[1]),'ljung_box_pvalue':float(lb['lb_pvalue'].iloc[0]),'residual_mean':float(resid.mean()),'residual_std':float(resid.std())}
    out={'model':best,'holdout_start':str(test.index[0].date()),'holdout_periods':len(test),'metrics':tests,'diagnostics':diagnostics,'history_start':str(y.index.min().date()),'history_end':str(y.index.max().date())}
    (ROOT/'artifacts/forecast_metrics.json').write_text(json.dumps(out,indent=2));
    try: seasonal_decompose(y,model='additive',period=12).observed.to_csv(ROOT/'artifacts/seasonal_observed.csv')
    except Exception: pass
    return out,forecast
if __name__=='__main__': print(json.dumps(run_forecast()[0],indent=2))

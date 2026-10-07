from __future__ import annotations
import sqlite3, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
SEGMENTS={
 'Champions': lambda r: r>=4 and f>=4,
 'Loyal': lambda r: r>=3 and f>=3,
 'Potential Loyalists': lambda r: r>=3 and f>=2,
 'New': lambda r: r>=4 and f<=2,
 'Promising': lambda r: r>=3 and f<=2,
 'Need Attention': lambda r: r==3 and f==3,
 'At Risk': lambda r: r<=2 and f>=3,
 "Can't Lose Them": lambda r: r<=2 and f>=4,
 'Hibernating': lambda r: r<=2 and f<=2,
 'Lost': lambda r: r==1 and f==1,
}
def _segment(row):
    r,f=row['r_score'],row['f_score']
    if r>=4 and f>=4:return 'Champions'
    if r>=3 and f>=3:return 'Loyal'
    if r>=3 and f>=2:return 'Potential Loyalists'
    if r>=4 and f<=2:return 'New'
    if r==3 and f<=2:return 'Promising'
    if r==3 and f==3:return 'Need Attention'
    if r<=2 and f>=4:return "Can't Lose Them"
    if r<=2 and f>=3:return 'At Risk'
    if r==2 and f<=2:return 'Hibernating'
    return 'Lost'

def calculate_rfm(db_path=ROOT/'data/churncarts.db'):
    con=sqlite3.connect(db_path)
    q='''SELECT customer_id, MAX(country) country, MIN(DATE(invoice_date)) first_purchase, MAX(DATE(invoice_date)) last_purchase, COUNT(DISTINCT invoice) frequency, SUM(revenue) monetary FROM fact_sales GROUP BY customer_id'''
    df=pd.read_sql_query(q,con); con.close()
    max_date=pd.to_datetime(df['last_purchase']).max(); df['recency']=(max_date-pd.to_datetime(df['last_purchase'])).dt.days+1
    for col in ['recency','frequency','monetary']:
        # duplicates at ties are given the lower score via rank(method=first), producing stable 1..5 quintiles
        df[f'{col[0]}_score']=pd.qcut(df[col].rank(method='first'),5,labels=[5,4,3,2,1] if col=='recency' else [1,2,3,4,5]).astype(int)
    df['segment']=df.apply(_segment,axis=1)
    df['churn_risk']=((df.recency>90)&(df.frequency>=2)).astype(int)
    df.to_csv(ROOT/'artifacts/rfm_customers.csv',index=False)
    summary=df.groupby('segment',as_index=False).agg(customers=('customer_id','count'),revenue=('monetary','sum'),avg_recency=('recency','mean'),avg_frequency=('frequency','mean'),avg_monetary=('monetary','mean'),churn_risk_customers=('churn_risk','sum')).sort_values('revenue',ascending=False)
    summary['revenue_share']=summary.revenue/summary.revenue.sum()
    summary.to_csv(ROOT/'artifacts/rfm_segments.csv',index=False)
    return df,summary
if __name__=='__main__':
    df,s=calculate_rfm(); print(s.to_string(index=False))

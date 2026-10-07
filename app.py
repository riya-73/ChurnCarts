from pathlib import Path
import json, sqlite3, sys
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
ROOT=Path(__file__).resolve().parent; DB=ROOT/'data/churncarts.db'
st.set_page_config(page_title='ChurnCarts',page_icon='🛒',layout='wide')
@st.cache_data
def q(sql,params=()):
    with sqlite3.connect(DB) as c:return pd.read_sql_query(sql,c,params=params)
@st.cache_data
def load_artifact(name): return pd.read_csv(ROOT/'artifacts'/name)

def sidebar():
    st.sidebar.title('ChurnCarts'); st.sidebar.caption('E-commerce analytics | Online Retail II')
    page=st.sidebar.radio('Navigate',['Overview','Customer Segments','Sales Forecast','Data Pipeline'])
    return page

def overview():
    st.title('Overview')
    c=q('SELECT SUM(revenue) revenue, COUNT(DISTINCT invoice) orders, COUNT(DISTINCT customer_id) customers, SUM(revenue)/COUNT(DISTINCT invoice) aov FROM fact_sales').iloc[0]
    cols=st.columns(4)
    for col,label,val,fmt in zip(cols,['Revenue','Orders','Customers','AOV'],[c.revenue,c.orders,c.customers,c.aov],['£{:,.0f}','{:,.0f}','{:,.0f}','£{:,.2f}']): col.metric(label,fmt.format(val))
    st.subheader('Monthly revenue'); m=q('SELECT * FROM v_monthly_revenue ORDER BY month'); m['month']=pd.to_datetime(m.month); st.plotly_chart(px.line(m,x='month',y='revenue',markers=True),use_container_width=True)
    a,b=st.columns(2); topc=q('SELECT country,SUM(revenue) revenue FROM fact_sales GROUP BY country ORDER BY revenue DESC LIMIT 10'); topp=q('SELECT f.stock_code,p.description,SUM(f.revenue) revenue FROM fact_sales f LEFT JOIN dim_product p ON f.stock_code=p.stock_code GROUP BY f.stock_code,p.description ORDER BY revenue DESC LIMIT 10')
    a.plotly_chart(px.bar(topc.sort_values('revenue'),x='revenue',y='country',orientation='h',title='Top countries'),use_container_width=True); b.plotly_chart(px.bar(topp.sort_values('revenue'),x='revenue',y='description',orientation='h',title='Top products'),use_container_width=True)

def segments():
    st.title('Customer Segments'); r=load_artifact('rfm_customers.csv'); s=load_artifact('rfm_segments.csv')
    a,b=st.columns(2); a.plotly_chart(px.bar(s,x='segment',y='customers',title='Customers by segment'),use_container_width=True); b.plotly_chart(px.pie(s,names='segment',values='revenue',title='Revenue share'),use_container_width=True)
    st.plotly_chart(px.scatter(r,x='recency',y='monetary',size='frequency',color='segment',hover_data=['customer_id','country'],log_y=True,title='RFM: recency vs monetary'),use_container_width=True)
    risk=r[r.churn_risk==1].sort_values(['monetary','frequency'],ascending=False); st.subheader(f'At-risk customers ({len(risk):,})'); st.download_button('Download at-risk CSV',risk.to_csv(index=False),'at_risk_customers.csv','text/csv'); st.dataframe(risk,use_container_width=True)

def forecast():
    st.title('Sales Forecast'); f=load_artifact('forecast.csv'); met=json.loads((ROOT/'artifacts/forecast_metrics.json').read_text()); horizon=st.slider('Forecast horizon (months)',1,6,6); f=f.head(horizon); h=q('SELECT month,revenue FROM v_monthly_revenue ORDER BY month'); h['month']=pd.to_datetime(h.month); f['month']=pd.to_datetime(f.month)
    fig=go.Figure(); fig.add_trace(go.Scatter(x=h.month,y=h.revenue,name='History')); fig.add_trace(go.Scatter(x=f.month,y=f.forecast,name='Forecast',line=dict(dash='dash'))); fig.add_trace(go.Scatter(x=pd.concat([f.month,f.month[::-1]]),y=pd.concat([f.upper,f.lower[::-1]]),fill='toself',line=dict(color='rgba(0,0,0,0)'),name='95% CI')); st.plotly_chart(fig,use_container_width=True)
    a,b,c=st.columns(3); sm=met['metrics']['sarima']; base=met['metrics']['seasonal_naive']; a.metric('SARIMA MAE',f"£{sm['mae']:,.0f}"); b.metric('RMSE',f"£{sm['rmse']:,.0f}"); c.metric('MAPE',f"{sm['mape']:.1f}%",f"vs naive {base['mape']:.1f}%")
    st.json({'selected_model':met['model'],'tests':met['diagnostics']})

def pipeline():
    st.title('Data Pipeline'); summary=json.loads((ROOT/'artifacts/etl_summary.json').read_text()); st.dataframe(pd.DataFrame(summary['counts']),use_container_width=True); st.subheader('Data quality'); st.json(summary['data_quality']); st.caption('Raw workbook → SQLite staging → cleaned returns/facts → star schema → views → RFM + SARIMA artifacts')
page=sidebar(); {'Overview':overview,'Customer Segments':segments,'Sales Forecast':forecast,'Data Pipeline':pipeline}[page]()

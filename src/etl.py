from __future__ import annotations
import sqlite3, zipfile, os, logging, json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = ROOT/'data/online_retail_II.xlsx'
DEFAULT_DB = ROOT/'data/churncarts.db'
LOG = logging.getLogger('churncarts.etl')


def _norm(df):
    df = df.rename(columns={'Customer ID':'customer_id','InvoiceDate':'invoice_date','Invoice':'invoice','StockCode':'stock_code','Description':'description','Quantity':'quantity','Price':'price','Country':'country'})
    df['invoice'] = df['invoice'].astype(str).str.strip()
    df['stock_code'] = df['stock_code'].astype(str).str.strip()
    df['customer_id'] = df['customer_id'].where(df['customer_id'].notna(), None)
    df['customer_id'] = df['customer_id'].map(lambda x: str(int(x)) if isinstance(x,(int,float)) and pd.notna(x) else (str(x).strip() if pd.notna(x) else None))
    df['invoice_date'] = pd.to_datetime(df['invoice_date'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    return df[['invoice','stock_code','description','quantity','invoice_date','price','customer_id','country']]


def run_etl(input_path=DEFAULT_XLSX, db_path=DEFAULT_DB):
    input_path, db_path = Path(input_path), Path(db_path); db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists(): db_path.unlink()
    con = sqlite3.connect(db_path); con.execute('PRAGMA journal_mode=WAL')
    con.executescript((ROOT/'sql/01_schema.sql').read_text())
    counts=[]
    for sheet in pd.ExcelFile(input_path, engine='openpyxl').sheet_names:
        LOG.info('Loading %s', sheet)
        df = _norm(pd.read_excel(input_path, sheet_name=sheet, engine='openpyxl'))
        df.to_sql('raw_transactions', con, if_exists='append', index=False)
        counts.append({'step':f'load_{sheet}', 'rows':len(df)})
    counts.append({'step':'raw_transactions', 'rows':con.execute('SELECT COUNT(*) FROM raw_transactions').fetchone()[0]})
    def n(sql): return con.execute(sql).fetchone()[0]
    con.executescript((ROOT/'sql/02_transform.sql').read_text())
    for name in ['returns','fact_sales','dim_customer','dim_product','dim_date']:
        counts.append({'step':name,'rows':n(f'SELECT COUNT(*) FROM {name}')})
    dq = {'fact_null_customers':n("SELECT COUNT(*) FROM fact_sales WHERE customer_id IS NULL OR customer_id=''"), 'fact_nonpositive':n('SELECT COUNT(*) FROM fact_sales WHERE quantity<=0 OR price<=0'), 'fact_duplicate_lines':n('SELECT COALESCE(SUM(cnt-1),0) FROM (SELECT COUNT(*) cnt FROM raw_transactions GROUP BY invoice, stock_code, description, quantity, invoice_date, price, customer_id, country)')}
    counts.append({'step':'data_quality',**dq})
    con.commit(); con.close()
    (ROOT/'artifacts/etl_summary.json').write_text(json.dumps({'input':str(input_path),'database':str(db_path),'counts':counts,'data_quality':dq}, indent=2))
    return counts

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    run_etl()

import sys, logging
from src.etl import run_etl
from src.rfm import calculate_rfm
from src.forecast import run_forecast
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
if __name__=='__main__':
    counts=run_etl(); print('ETL complete'); print(counts)
    rfm,summary=calculate_rfm(); print('RFM complete:',len(rfm),'customers')
    metrics,_=run_forecast(); print('Forecast complete:',metrics['model'])

import matplotlib; matplotlib.use('Agg')
import warnings; warnings.filterwarnings('ignore')
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd, numpy as np
d=pd.read_excel('Dataset4_EWS.xlsx',sheet_name='Markets'); d['Data']=pd.to_datetime(d['Data'],dayfirst=True); d=d.set_index('Data')
X_df=d.drop('Y',axis=1); y=d['Y'].values
ic=['XAUBGNL','BDIY','CRY','Cl1','DXY','EMUSTRUU','GBP','JPY','LF94TRUU','LF98TRUU','LG30TRUU','LMBITR','LP01TREU','LUACTRUU','LUMSTRUU','MXBR','MXCN','MXEU','MXIN','MXJP','MXRU','MXUS','VIX']
ir=['EONIA','GTDEM10Y','GTDEM2Y','GTDEM30Y','GTGBP20Y','GTGBP2Y','GTGBP30Y','GTITL10YR','GTITL2YR','GTITL30YR','GTJPY10YR','GTJPY2YR','GTJPY30YR','US0001M','USGG3M','USGG2YR','GT10','USGG30YR']
sdf=pd.DataFrame(index=X_df.index[1:])
for c in ic: sdf[c]=np.diff(np.log(X_df[c]))
for c in ir: sdf[c]=np.diff(X_df[c])
sdf['ECSURPUS']=X_df['ECSURPUS'].values[1:]; stationary_df=sdf; y_stationary=y[1:]
g=dict(globals())
nb=json.load(open('EarlyWarningSystemPoliMI.ipynb',encoding='utf-8'))
cells=nb['cells']
start=next(i for i,c in enumerate(cells) if ''.join(c['source']).startswith('# Parte 1'))
for i in range(start,len(cells)):
    if cells[i]['cell_type']!='code': continue
    src=''.join(cells[i]['source'])
    print('--- exec code cell',i,'|',src.split(chr(10))[0][:50])
    exec(src,g)
print('END-TO-END (5 parti) OK')

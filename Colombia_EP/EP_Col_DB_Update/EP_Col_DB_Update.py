#!/opt/dgweb/venv1/bin/python3

# The above shebang needs to be updated to match configuration.

import pandas as pd
import sqlalchemy
import pymysql
from sqlalchemy import create_engine
from sqlalchemy import text

import datetime as dt

from dgxm import precio_horario
from dgxm import precio_diario

# Este es el inicio de todo, pues en el archivo de Tablas.csv hay que indicar qué tablas actualizar y poner las características de cada una.
tables = pd.read_csv('Tablas.csv')

# Aquí croe la engine de la base de datos.
engine_on = False
try:
    with open('db_string', 'r') as cadena:
        engine = create_engine(cadena.readline())
    engine_on = True
except:
    with open('log.txt', 'a') as log:
        log.write('{} - Problemas con la creación del motor. \n'.format(dt.datetime.now().isoformat(' ')[0:16]))    

#Aquí saco las fechas máximas presentes en la base de datos, para que a partir de esa fecha haga la llamada a la api y lo guarde en la BD.
fechas_on = False
if engine_on:
    try:
        fechas_max = {}
        with engine.connect() as conn:
            for i in range(len(tables)):
                sql = text('SELECT MAX(Fecha) FROM {}'.format(tables.iloc[i]['Tabla']))
                res = conn.execute(sql)
                fechas_max[tables.iloc[i]['Tabla']] = res.all()[0][0]
        fechas_on = True
    except:
        with open('log.txt', 'a') as log:
            log.write('{} - Problemas con la query de las fechas max actuales. \n'.format(dt.datetime.now().isoformat(' ')[0:16]))

# Aquí hago la llamada a la librería dgxm para que saque los datos de la API y cargue esos datos en la base de datos.

if fechas_on:
    #updates = {} #si no lo usas cuando conviertas a meter a base de datos, bórralo.
    for i in range(len(tables)):
        
        if tables.iloc[i]['Freq'] == 'hourly':
            tmp_df = precio_horario(tables.iloc[i]['Dato'], \
                                    fechas_max[tables.iloc[i]['Tabla']].isoformat()[0:10], \
                                    dt.datetime.now().isoformat()[0:10])
            #pass
        else:
            tmp_df = precio_diario(tables.iloc[i]['Dato'], \
                                   fechas_max[tables.iloc[i]['Tabla']].isoformat()[0:10], \
                                    dt.datetime.now().isoformat()[0:10])
            #pass
        
        if tmp_df.loc[0,][0] == 'Problemas con la API':
            with open('log.txt', 'a') as log:
                log.write('{} - Problemas con la API. \n'.format(dt.datetime.now().isoformat(' ')[0:16]))
            
        else:
            #A quí más adelate hace el: tmp_df.dropna().to_sql(tables.iloc[i]['Tabla'], engine, index=False, if_exists='append') 
            
            hms = dt.datetime.min.time()
            if tables.iloc[i]['Freq'] == 'hourly':
                tmp_df = tmp_df[tmp_df['Fecha']>fechas_max[tables.iloc[i]['Tabla']]].dropna()
            else:
                tmp_df = tmp_df[tmp_df['Fecha']> dt.datetime.combine(fechas_max[tables.iloc[i]['Tabla']], hms)].dropna()
    
                
            try:
                if not tmp_df.empty:
                    tmp_df.to_sql(tables.iloc[i]['Tabla'], engine, index=False, if_exists='append') 
                    #updates[tables.iloc[i]['Tabla']] = tmp_df
                    with open('log.txt', 'a') as log:
                        log.write('{} - Éxito con la actualización de {}. \n'.format(dt.datetime.now().isoformat(' ')[0:16], tables.iloc[i]['Tabla']))
                    
            except:
                with open('log.txt', 'a') as log:
                    log.write('{} - Problemas con la Carga_final. \n'.format(dt.datetime.now().isoformat(' ')[0:16]))
### Aquí acaba la llamada a la librería dgxm para que saque los datos de la API y cargue esos datos en la base de datos.


try:
    engine.dispose()
except:
    pass
        

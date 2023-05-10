#!/opt/dgweb/venv1/bin/python3

# -*- coding: utf-8 -*-

# The above shebang needs to be updated to match configuration.

#Import Packages:
import pandas as pd
import datetime as dt

import requests

import sqlalchemy
import pymysql
from sqlalchemy import create_engine
from sqlalchemy import text

#Engine Creation (Part of data and functions).
with open('db_string', 'r') as cadena:
    engine = create_engine(cadena.readline())
    
#EIA's API Key:
with open('API_KEY', 'r') as cadena:
    api_key = cadena.readline().strip()
    
#Tables:
tables = pd.read_csv('APIStrings.csv')

#Functions for queries and other transformations:

def eia_from_date(dbtable, fecha='1900-01-01', engine=engine, periodDate = 'periodDate', columns = '*'):
    '''
    Esta función regresa un dataframe, le das la tabla, la fecha (en formato fecha de datetime.date o 'AAAA-MM-DD'), y el engine con el motor de la base de datos. Se pueden ajustar otros parámetros.
    OJO con que definiste engine=engine, por lo tanto va a asumir que hay un motor creado con ese nombre, como es el caso de este archivo.
    Semejante con el nombre de la columna del WHERE, el periodDate, que es el nombre de la columna, que se hizo para la definición de la base de datos.
    El WHERE lo evalúa periodDate >= fecha.
    No es segura vs inyección si se usara de un formulario.
    '''
    if type(fecha) == type(dt.date.today()):
        fecha = fecha.isoformat()
    if type(fecha) == type(dt.datetime.now()):
        fecha = fecha.isoformat()[0:10]
    if type(fecha) == type(str()):
        if len(fecha) == 7:
            fecha = fecha+'-01'
    return pd.read_sql(text("SELECT {} FROM {} WHERE {} >= '{}' ;".format(columns, dbtable, periodDate, fecha)), con=engine.connect())


def steo_from_date(dbtable='STEO', fecha='1900-01-01', engine=engine, periodDate = 'periodDate', updateDate = 'updateDate', columns = ['HH_NG_PROY_MMBTU', 'WTI_PROY_BBL']):
    """
    Esta función regresa un dataframe, le das la tabla, la fecha desde donde quieres la data (en formato fecha de datetime.date o 'AAAA-MM-DD'), y el engine con el motor de la base de datos. 
    (Se pueden ajustar las columnas a pedir y las columnas con las fechas)
    Lo relevante que hace es que toma el valor mayor de updateDate para considerar esa captura
    en este caso columns DEBE SER UNA LISTA (O UNA TUPLA DE PRONTO) O NO FUNCIONA!
    El HAVING / WHERE lo evalúa periodDate >= fecha.
    No es segura vs inyección si se usara de un formulario.
    """
    if type(fecha) == type(dt.date.today()):
        fecha = fecha.isoformat()
    if type(fecha) == type(dt.datetime.now()):
        fecha = fecha.isoformat()[0:10]
    if type(fecha) == type(str()):
        if len(fecha) == 7:
            fecha = fecha+'-01'
    
    txt=''
    for i in range(len(columns)):
        txt = txt + 'b.'+columns[i]+' AS '+columns[i]+' '
        if i != len(columns)-1:
            txt = txt+', '
 
    txt2=''
    for i in range(len(columns)):
        txt2 = txt2+columns[i]+' '
        if i != len(columns)-1:
            txt2 = txt2+', '
    
    qry = '''
    select a.{2} as periodDate, a.{3}_ as updateDate,
    ''' + txt +'''
    from
    (select {2}, max({3}) as {3}_ from {1} group by {2} HAVING {2}>={4}) a 
    inner join
    (select {2}, {3}, 
    ''' + txt2 + '''
    from {1} WHERE {2} >= '{4}') b
    on (a.{2} = b.{2} AND a.{3}_ = b.{3}) 
    ;
    '''
    #fecha_valor por periodDate, fecha_carga por updateDate,  valoro es el  
    #                                     0         1         2          3         4
    return pd.read_sql(text(qry.format(columns, dbtable, periodDate, updateDate, fecha)), con=engine.connect())



def eia_max_date(dbtable, engine=engine, periodDate = 'periodDate'):
    with engine.connect() as conn:
        res = conn.execute(text("SELECT max({}) FROM {} ;".format(periodDate, dbtable)))
    
    return res.all()[0][0] #El res.all() saca una lista de tuplas (siendo las tuplas el renglón del query), el primer cero toma el primer elemento de la lista y el segundo el primer valor de la tupla


#Functions for API:

#Esta se presta para hacer un objeto que tenga los métodos y sólo llamarlos. 
def eia_api_from_date(call, fecha, api_key=api_key):
    '''
    Esta función está diseñada para usar de la tabla el Strings_Sin_Fin en la call, poner la fecha desde cuando se quiera la llamada y luego la api_key
    regresa el objeto de la call (requests)
    #hay que validar que lo que aviente, el .status_code sea 200
    #que .json()['response']['total'] sea mayor a uno
    #y sobre el .json()['response']['data'] pivotar periodo como índice, columnas como series y values como value, series hay que mapearlas a metadata.
    '''
    if type(fecha) == type(dt.date.today()):
        fecha = fecha.isoformat()[0:7]
    if type(fecha) == type(dt.datetime.now()):
        fecha = fecha.isoformat()[0:7]
    if type(fecha) == type(str()):
        if len(fecha) != 7:
            fecha = fecha[0:7]
    
    return requests.get(call.format(fecha, api_key))

#Process:

#Getting max date in DB:
max_date=[]
with engine.connect() as conn:
    for i in range(len(tables)):
        sql = text('SELECT MAX(periodDate) FROM {}'.format(tables.iloc[i]['dbtable']))
        res = conn.execute(sql).all()[0][0]
        max_date.append(res)
tables['max_date'] = max_date

#Turning Mappers in tables from strings to dicts:
tables['Mapper'] = tables['Mapper'].apply(lambda x: eval(x))

#Work table by table, retrieve data and if available, store in DB:

for i in range(len(tables)):
    if tables.dbtable[i] == 'STEO':
        with engine.connect() as conn:
            sql = text('SELECT MAX(updateDate) FROM {}'.format(tables.iloc[i]['dbtable']))
            max_update = conn.execute(sql).all()[0][0]
        
        #We want to update every month on the 15th (or onwards, if the API was not available or something), also if it was updated 30+ days ago... note that the data should be available on the first Tuesday following the first thursday of the month... so between the 6th and the 12th. 
        update = False
        if abs(max_update-dt.date.today()).days >=30:
            update = True
        if max_update.month != dt.date.today().month and dt.date.today().day >=15:
            update = True
        if max_update.month == dt.date.today().month and dt.date.today().day >=15 and max_update.day < 15:
            update = True
        
        
        if update:
                    
            #Get min max available date between natgas and oil prices table in DB, does not matter if it is from the previous day, should be updated by the 15th...
            fecha = min(tables['max_date'][tables['dbtable']=='OilPrice'].values[0], tables['max_date'][tables['dbtable']=='NGasPrice'].values[0])
            
            call = eia_api_from_date(call=tables.Strings_Sin_Fin[i], fecha=fecha_call)
            if call.status_code != 200:
                with open('log.txt', 'a') as log:
                        log.write('{} - API no dando respuesta adecuada para {}, error: {}. \n'.format(dt.datetime.now().isoformat(' ')[0:16], tables.dbtable[i], call.status_code))
            else:
                if call.json()['response']['total'] > 0:
                    #DataFrame Creation (from ☎️)
                    df_1 = pd.DataFrame( call.json()['response']['data'] )
                    #DF mapping to get DB columns:
                    df_1['prod'] = df_1[tables.series[i]].map(tables.Mapper[i])
                    #Creating date column:
                    df_1['periodDate'] = df_1['period'].apply(lambda x : dt.date.fromisoformat(x+'-01'))
                    #Pivoting DF to match DB structure and index reset:
                    df_1_1 = df_1.pivot(index='periodDate', columns= 'prod', values='value')
                    df_1_1.reset_index(inplace=True)
                    #Create updateDate column:
                    df_1_1['updateDate'] = dt.date.today()
                    #Insert into database:
                    try:
                        #To test, switch to:
                        #display(df_1_1)
                        df_1_1.to_sql(tables.iloc[i]['dbtable'], engine, index=False, if_exists='append')
                        with open('log.txt', 'a') as log:
                            log.write('{} - Datos actualizados, tabla {}. \n'.format(dt.datetime.now().isoformat(' ')[0:16], tables.dbtable[i]))
                    except:
                        with open('log.txt', 'a') as log:
                                log.write('{} - Problemas al cargar en la base de datos, tabla {}. \n'.format(dt.datetime.now().isoformat(' ')[0:16], tables.dbtable[i]))
    #######################not steo:
    else:
        fecha = tables.max_date[i]
        if fecha.month == 12:
            fecha_call = str(fecha.year+1)+'-01'
        else:
            fecha_call = str(fecha.year)+'-'+str(fecha.month+1).zfill(2)
        
        call = eia_api_from_date(call=tables.Strings_Sin_Fin[i], fecha=fecha_call)
        if call.status_code != 200:
            with open('log.txt', 'a') as log:
                    log.write('{} - API no dando respuesta adecuada para {}, error: {}. \n'.format(dt.datetime.now().isoformat(' ')[0:16], tables.dbtable[i], call.status_code))
        else:
            if call.json()['response']['total'] > 0:
                #DataFrame Creation (from ☎️)
                df_1 = pd.DataFrame( call.json()['response']['data'] )
                #DF mapping to get DB columns:
                df_1['prod'] = df_1[tables.series[i]].map(tables.Mapper[i])
                #Creating date column:
                df_1['periodDate'] = df_1['period'].apply(lambda x : dt.date.fromisoformat(x+'-01'))
                #Pivoting DF to match DB structure and index reset:
                df_1_1 = df_1.pivot(index='periodDate', columns= 'prod', values='value')
                df_1_1.reset_index(inplace=True)
                #Insert into database:
                try:
                    #To test, switch to:
                    #display(df_1_1)
                    df_1_1.to_sql(tables.iloc[i]['dbtable'], engine, index=False, if_exists='append')
                    with open('log.txt', 'a') as log:
                            log.write('{} - Datos actualizados, tabla {}. \n'.format(dt.datetime.now().isoformat(' ')[0:16], tables.dbtable[i]))                    
                except:
                    with open('log.txt', 'a') as log:
                            log.write('{} - Problemas al cargar en la base de datos, tabla {}. \n'.format(dt.datetime.now().isoformat(' ')[0:16], tables.dbtable[i]))



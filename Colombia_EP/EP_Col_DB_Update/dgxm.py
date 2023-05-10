## Recuerda el archivo del  __pycache__ que queda...
##las funciones principales: precio_horario, precio_diario, 
##Recuerda, cuando uses la librería esta poner un validador if DataFrame.loc[0,][0] == 'Problemas con la API'...
## Como está ahorita, cuando la uses, tienen que dropear los NaN... 

import pandas as pd
import numpy as np
import requests
import datetime as dt

def precio_horario(MetricId : 'PrecBolsNaci', StartDate, EndDate):
    """
    Función para descargar el precio de bolsa de XM (Colombia) a partir de una fecha de inicio y una final.
    Se ha generalizado el método para funciones horias, por defecto da el precio en COP/kWh del precio de bolsa
    para dar el precio promedio de los contratos no regulados, pasar en el parámetro MetricId: 'PrecPromContNoRegu' 
    "MetricId": "PrecBolsNaci" ó "PrecPromContNoRegu"
    Las fechas deben darse en isoformat: 'YYYY-MM-DD', así como strings, y nada de que 1 en lugar de 01 para mes o día.
    ##Ej para instanciar a pedir precios de bolsa: precio_bolsa = precio_horario('PrecBolsNaci', '2021-04-23', '2021-07-13')
    ## del anterior para ver la cantidad de NAs que tienes: precio_bolsa.isna().sum()
    ## para guardarlo en un archivo que se llame 'csvpbolsaTest.csv': precio_bolsa.to_csv(path_or_buf=r'csvpbolsaTest.csv', index=False)
    ## Con el cambio, si hay un error en el request - servidor de la API - va a regresar un dataframe con DataFrame.loc[0,][0] = 'Problemas con la API'
    (La info sale en pbolsa_data (un dataframe de pandas).)
    """
    # datetime(year, month, day, hour, minute, second, microsecond) Nota que la hora es de las 0 a las  23
    
    #lo siguiente en caso de que quien usa la función la embarre y meta las fechas al revés.
    fecha_mayor = max(dt.datetime.fromisoformat(EndDate), dt.datetime.fromisoformat(StartDate))
    fecha_menor = min(dt.datetime.fromisoformat(EndDate), dt.datetime.fromisoformat(StartDate))
    rango = (dt.datetime.fromisoformat(EndDate) - dt.datetime.fromisoformat(StartDate)).days
    
    indice = pd.date_range(start=fecha_menor, end= fecha_mayor.isoformat()[0:10]+' 23:00:00', freq = "H", inclusive = 'both') # El isoformat es para que se vuelva de texto otra vez y puedas hacerlo fácil, este método perimte que le des un datetime o un isofromat y solito lo detecta, por eso los puedo combinar como hago aquí.
    
    pbolsa_data = pd.DataFrame({ 'Fecha': indice, MetricId : np.nan}) # puedes poner la fecha de índice con , index = indice Y CAMBIÉ EL MetricId, antes ponía siempre 'Precio_Bolsa' como encabezado de la columna.

    
    if(rango <= 30):
        pbolsa_data = apicall_pbolsa(MetricId, pbolsa_data, fecha_mayor.isoformat()[0:10], fecha_menor.isoformat()[0:10])
        
    else:
        ciclos = rango // 30
        extra =  rango % 30
        nva_menor = fecha_menor 
        nva_mayor = nva_menor + dt.timedelta(days=29)
        for i in range(ciclos):
            pbolsa_data = apicall_pbolsa(MetricId, pbolsa_data, nva_mayor.isoformat()[0:10], nva_menor.isoformat()[0:10])
            nva_menor = nva_mayor + dt.timedelta(days=1)
            nva_mayor = nva_menor + dt.timedelta(days=29)
            #condicion para arregalr los errores y que no pierda el tiempo.
            if pbolsa_data.loc[0,][0] == 'Problemas con la API':
                break
            
        if(extra >0):
            nva_mayor = nva_menor + dt.timedelta(days=(extra))
            pbolsa_data = apicall_pbolsa(MetricId, pbolsa_data, nva_mayor.isoformat()[0:10], nva_menor.isoformat()[0:10])
    
    #por los cambios hechos, si hay un error va a regresar un dataframe con DataFrame.loc[0,][0] = 'Problemas con la API'
    #aquí podrías poner el que quite los antes del return, o hacerlo de quitar la búsqueda...
    return pbolsa_data

#.-.-.-.-.#

def apicall_pbolsa(MetricId, pbolsa_data, fecha_mayor, fecha_menor):
    """
    Función auxiliar, para simplificar la de precio horario, no está hecha para llamarse sola.
    """
    
    #Llamada a la API ☎
    q = {"MetricId": MetricId,"StartDate": fecha_menor,"EndDate": fecha_mayor,"Entity":"Sistema"}
    respuesta = requests.post('http://servapibi.xm.com.co/hourly', json = q) #algunas apis -get- usan params en vez de json
    
    #este if else es para arreglar los errores de la API
    if str(respuesta.status_code)[0]!='2':
        di = {'Error': ["Problemas con la API"], 'Status_Code' : [respuesta.status_code]}
        a = pd.DataFrame(di)
        return a
    
    else:
        datos = respuesta.json()
        
        
        #Almacenamiento de los datos en el dataframe
        
        for j in range(len(datos['Items'])): #es la iteración de afuera j
            fecha = datos['Items'][j]['Date']
            #
            i=-1
            for key, value in datos['Items'][j]['HourlyEntities'][0]['Values'].items():
                if i == -1:
                    i+=1
                    pass
                else:
                    fecha_query = fecha +" "+("0" if i<10 else "")+ str(i)+':00:00'
                    try:
                    	pbolsa_data.loc[pbolsa_data.Fecha == fecha_query, MetricId] = float(value)  ########## esto es lo que hace la carga detallada feha a fecha, se puede cambiar para optmizar.
                    except:
                    	pbolsa_data.loc[pbolsa_data.Fecha == fecha_query, MetricId] = np.nan ##Agregado para evitar errores en caso de que no haya valores.                   	  
                    i+=1
            #
        return pbolsa_data

#.-.-.-.-.#

## Con el cambio, si hay un error en el request - servidor de la API - va a regresar un dataframe con DataFrame.loc[0,][0] = 'Problemas con la API'

#----------#
#Ahora hago la función para los diarios....
#___________#

def precio_diario(MetricId : 'PrecEsca', StartDate, EndDate): ### Cambia la URL
    """
    Función que sirve para extraer los precios diarios (que en su mayoría en realidad son mensuales), así como la demanda del sistema.
    La salida es un dataframe. #######Pend envío directo a una base de datos...
    los precios diarios están en COP/kWh, la demanda en kWh
    Las fechas a meter en StartDate y EndDate son con el formato 'AAAA-MM-DD' ej '1986-04-23'
    Algunas de las posibles MetricID son: 'PrecEsca', 'PrecEscaMarg', 'PrecEscaAct', 'PrecEscaPon', 'DemaSIN' (esta última es la demanda en kWh)
    ## Con el cambio, si hay un error en el request - servidor de la API - va a regresar un dataframe con DataFrame.loc[0,][0] = 'Problemas con la API'
    """
    #lo siguiente en caso de que quien usa la función la embarre y meta las fechas al revés.
    fecha_mayor = max(dt.date.fromisoformat(EndDate), dt.date.fromisoformat(StartDate))
    fecha_menor = min(dt.date.fromisoformat(EndDate), dt.date.fromisoformat(StartDate))
    rango = (dt.date.fromisoformat(EndDate) - dt.date.fromisoformat(StartDate)).days
    
    indice = pd.date_range(start=fecha_menor, end=fecha_mayor, freq = "D", inclusive = 'both') 
    #len(indice)
    buffer_data = pd.DataFrame({ 'Fecha': indice, MetricId : np.nan}) # puedes poner la fecha de índice con , index = indice Y CAMBIÉ EL MetricId, antes ponía siempre 'Precio_Bolsa' como encabezado de la columna.

    
    if(rango <= 30):
        buffer_data = apicall_pdiario(MetricId, buffer_data, fecha_mayor.isoformat(), fecha_menor.isoformat()) ####vas a tener uqe hacer una apicall_diario!!!!
        
    else:
        ciclos = rango // 30
        extra =  rango % 30
        nva_menor = fecha_menor 
        nva_mayor = nva_menor + dt.timedelta(days=29)
        for i in range(ciclos):
            buffer_data = apicall_pdiario(MetricId, buffer_data, nva_mayor.isoformat(), nva_menor.isoformat())
            nva_menor = nva_mayor + dt.timedelta(days=1)
            nva_mayor = nva_menor + dt.timedelta(days=29)
            #condicion para arregalr los errores y que no pierda el tiempo.
            if buffer_data.loc[0,][0] == 'Problemas con la API':
                break
            
        if(extra >0):
            nva_mayor = nva_menor + dt.timedelta(days=(extra))
            buffer_data = apicall_pdiario(MetricId, buffer_data, nva_mayor.isoformat()[0:10], nva_menor.isoformat()[0:10])
    
    #por los cambios hechos, si hay un error va a regresar un dataframe con DataFrame.loc[0,][0] = 'Problemas con la API'
    #aquí podrías poner el que quite los antes del return, o hacerlo de quitar la búsqueda...
    return buffer_data

#.-.-.-.-.#

def apicall_pdiario(MetricId, buffer_data, fecha_mayor, fecha_menor):  
    """
    Función auxiliar, para simplificar la de precio horario, no está pensada para llamarse sola.
    """
    #########################
    
    #Llamada a la API ☎
    q = {"MetricId": MetricId,"StartDate": fecha_menor,"EndDate": fecha_mayor,"Entity":"Sistema"}
    respuesta = requests.post('http://servapibi.xm.com.co/daily', json = q) #algunas apis -get- usan params en vez de json
    
    #este if else es para arreglar los errores de la API
    if str(respuesta.status_code)[0]!='2':
        di = {'Error': ["Problemas con la API"], 'Status_Code' : [respuesta.status_code]}
        a = pd.DataFrame(di)
        return a
    
    else:
        datos = respuesta.json()
        
        
        #Almacenamiento de los datos en el dataframe
        
        for i in range(len(datos['Items'])): #es la iteración de afuera j
            fecha = datos['Items'][i]['Date']
            valor = datos['Items'][i]['DailyEntities'][0]['Value']
            #
            try:
            	buffer_data.loc[buffer_data.Fecha == fecha, MetricId] = float(valor)  ########## esto es lo que hace la carga, se podría hacer distinto, se usa así para efectos de validación  // considera que cambié el 'Precio_Bolsa' del título de columna por el MetricId  hourly
            except:
            	buffer_data.loc[buffer_data.Fecha == fecha, MetricId] = np.nan ##Agregado para evitar errores en caso de que no haya valores.

        return buffer_data

#.-.-.-.-.#
    

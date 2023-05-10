#Imports:
import dash
from dash import html
from dash import dcc
#from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc

import pandas as pd
import datetime as dt

import plotly.graph_objects as go


import sqlalchemy
import pymysql
from sqlalchemy import create_engine
from sqlalchemy import text

#Color definition:
colores = ['#001741', '#a1c9f4', '#fab0e4', '#8de5a1', '#ff9f9b', '#d0bbff', '#debb9b', '#b9f2f0', '#cfcfcf', '#fffea3', '#ffb482']

#Engine Creation (Part of data and functions).
with open('db_string', 'r') as cadena:
    engine = create_engine(cadena.readline())
    
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


def eia_range_from_date(dbtable, fecha='2023-01-01', engine=engine, periodDate = 'periodDate', column = '*', range_=5, suffix = ''):
    """
    fecha es la fecha MAXIMA que debe entrar a la función, dbtable es la tabla en la base de datos, periodDate es el nombre de la columna con la fecha en la base de datos.
    """
    if type(fecha) == type(dt.datetime.now()):
        fecha = dt.date.fromisoformat(fecha.isoformat()[0:10])
    if type(fecha) == type(str()):
        if len(fecha) == 7:
            fecha = fecha+'-01'
        fecha = dt.date.fromisoformat(fecha[0:10]) 
    
    fechaInicio = dt.date(fecha.year - range_, fecha.month, fecha.day) #pass ##############################PPendiente!!! periodDate.year - range_
    
    qry = """
    SELECT DATE_FORMAT({0}, "%m") AS MM, min({1}) AS Min_{5}, 
    max({1}) as Max_{5} FROM {2} WHERE {0}>="{3}" AND {0}<="{4}" GROUP BY MM;
    """
    return pd.read_sql(text(qry.format(periodDate, column, dbtable, fechaInicio, fecha, suffix)), con=engine.connect())   

#Data:

    #Tables definition
tables = pd.read_csv('APIStrings.csv')

max_date=[]
with engine.connect() as conn:
    for i in range(len(tables)):
        sql = text('SELECT MAX(periodDate) FROM {}'.format(tables.iloc[i]['dbtable']))
        res = conn.execute(sql).all()[0][0]
        max_date.append(res)

tables['max_date'] = max_date
tables['18atras'] = tables['max_date'].apply(lambda x : dt.date(x.year-2, x.month+7, 1) if x.month<=5 else dt.date(x.year-1, x.month-5, 1) )
tables['12atras'] = tables['max_date'].apply(lambda x : dt.date(x.year-1, x.month+1, 1) if x.month<=11 else dt.date(x.year, x.month-11, 1) )

    #Dataframes Dictionary creation:
fecha_steo = min(tables['max_date'][tables['dbtable']== 'NGasPrice'].values[0], tables['max_date'][tables['dbtable']== 'OilPrice'].values[0])
dic_df = {}
for i in range(len(tables)):
    if tables.iloc[i]['_12'] == 1:
        #pass #pendiente hacer el df de 12 valores, creo que ya tienes la función de la query. eia_from_date
        dic_df[tables.iloc[i]['dbtable']+"_12"] = eia_from_date(tables.iloc[i]['dbtable'], fecha = tables.iloc[i]['12atras'])
    if tables.iloc[i]['_18'] ==1:
        #pass #pendiente hacer el df de 18 valores, creo que ya tienes la función de la query. eia_from_date
        dic_df[tables.iloc[i]['dbtable']+"_18"] = eia_from_date(tables.iloc[i]['dbtable'], fecha = tables.iloc[i]['18atras'])
    if tables.iloc[i]['_AsOf'] == 1:
        #pass # pendiente hacer la query a partir del mínimo entre la fecha max de NGasPrice y OilPrice
        dic_df[tables.iloc[i]['dbtable']+"_AsOf"] = steo_from_date(tables.iloc[i]['dbtable'], fecha = fecha_steo)
        
    #Adding month column for ranges:
dic_df['NGasPrice_18']['MM'] = dic_df['NGasPrice_18']['periodDate'].apply(lambda x: str(x.month).zfill(2))
dic_df['OilPrice_18']['MM'] = dic_df['OilPrice_18']['periodDate'].apply(lambda x:  str(x.month).zfill(2))

    #max and min tables and merging:
dic_df['NGasPrice_18']['MM'] = dic_df['NGasPrice_18']['periodDate'].apply(lambda x: str(x.month).zfill(2))
dic_df['OilPrice_18']['MM'] = dic_df['OilPrice_18']['periodDate'].apply(lambda x:  str(x.month).zfill(2))

fechaGas = tables[tables['dbtable']== 'NGasPrice']['max_date'].values[0]
fechaOil = tables[tables['dbtable']== 'OilPrice']['max_date'].values[0]

dic_df['NGasPriceRange5yr'] = eia_range_from_date(dbtable='NGasPrice', fecha=fechaGas, column = 'HH_NG_SPOT_MMBTU', suffix='HH_NG_SPOT_MMBTU')
dic_df['OilPriceRange5yr'] = eia_range_from_date(dbtable='OilPrice', fecha=fechaOil, column = 'WTI_FOB_BBL', suffix='WTI_FOB_BBL')

dic_df['NGasPrice_18'] = pd.merge(dic_df['NGasPrice_18'], dic_df['NGasPriceRange5yr'], how="left", on='MM')
dic_df['OilPrice_18'] = pd.merge(dic_df['OilPrice_18'], dic_df['OilPriceRange5yr'], how="left", on='MM')

engine.dispose()

##################################

#Plots:
    
#CRUDO.
x_largo_crude = pd.concat([dic_df['OilPrice_18']['periodDate'], dic_df['OilPrice_18']['periodDate'][::-1] ]).tolist()
y_largo_crude = pd.concat([dic_df['OilPrice_18']['Min_WTI_FOB_BBL'], dic_df['OilPrice_18']['Max_WTI_FOB_BBL'][::-1] ]).tolist()
max_steo = min(len(dic_df['STEO_AsOf']), 18)
fig1 = go.Figure()
fig1.add_trace( go.Scatter(
    x=x_largo_crude,
    y=y_largo_crude,
    fill = 'toself',
    fillcolor = colores[1],
    opacity= 0.2,
    line_color= colores[1],  #'rgba(255,255,255,0)',
    #showlegend=False,
    name='WTI 5 yr. Price Range',
    legendrank=2
) )
fig1.add_trace(go.Scatter(x=dic_df['OilPrice_18'].periodDate, y=dic_df['OilPrice_18']['WTI_FOB_BBL'], name='WTI USD/BBL', line_color=colores[1], 
                          line_width = 4, legendrank=1, 
                          hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'
                         ))
fig1.add_trace(go.Scatter(x=dic_df['OilPrice_18'].periodDate, y=dic_df['OilPrice_18']['BRENT_FOB_BBL'], name = 'Brent USD/BBL', line_color = colores[2], line_width=3, legendrank=3, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))
fig1.add_trace(go.Scatter(x=dic_df['STEO_AsOf'].periodDate.iloc[0:max_steo], y=dic_df['STEO_AsOf'].WTI_PROY_BBL.iloc[0:max_steo], name='WTI USD/BBL STEO Proj', line_dash='dot', line_color=colores[1], line_width=3, legendrank=4, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))

fig1.update_layout(title='Crude Oil Prices, Historic and STEO Projection (FOB). Monthly Avg.',
                  title_x=0.5,
                  height=600,
                  paper_bgcolor=colores[0],
                  #paper_bgcolor = 'rgba(0,0,0,0)',
                  plot_bgcolor='rgba(0,0,0,0)',
                  yaxis_gridcolor = colores[8],
                  xaxis_gridcolor = colores[8],
                  xaxis_linewidth = 1,
                  yaxis_linewidth = 1,
                  xaxis_gridwidth = 1,
                  yaxis_gridwidth = 1,
                  #xaxis_griddash='dot',
                  #yaxis_griddash='dot',
                  #xaxis_showgrid = False,
                  #yaxis_showgrid = False,
                  #xaxis_title='Como sale el título del eje x',
                  yaxis_title='USD/BBL',
                  #yaxis_tickformat = ',.2e',
                  #yaxis_range=[0,120],
                 font=dict(
                    family="Arial, sans-serif",
                    size=11,  # Set the font size here
                    color=colores[8]   #"DarkBlue"
                    
                ),
                 
                 xaxis=dict(
                     rangeslider=dict(
                         visible=True,
                         thickness = 0.05  ### así lo haces más delgado 
                     ),
                     type="date"
                 ),
                 legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=0.99,
                    xanchor="right",
                    x=1
                 )
                 )

#Derivados Petróleo:
fig2 = go.Figure()

fig2.add_trace(go.Scatter(x=dic_df['OilPrice_18'].periodDate.iloc[6:18], y=dic_df['OilPrice_18'].WTI_FOB_BBL.apply(lambda x: x/42).iloc[6:18], name='WTI Crude', line_color=colores[1], line_width = 4, legendrank=1, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))
fig2.add_trace(go.Scatter(x=dic_df['OilPrice_18'].periodDate.iloc[6:18], y=dic_df['OilPrice_18'].MBTX_C3_GAL.iloc[6:18], name='Mt. Belvieu Propane', line_color=colores[3], line_width = 3, legendrank=2, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))
fig2.add_trace(go.Scatter(x=dic_df['OilPrice_18'].periodDate.iloc[6:18], y=dic_df['OilPrice_18'].NYH_RGAS_GAL.iloc[6:18], name='NYH Reg. Gasoline', line_color=colores[4], line_width = 3, legendrank=3, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))
fig2.add_trace(go.Scatter(x=dic_df['OilPrice_18'].periodDate.iloc[6:18], y=dic_df['OilPrice_18'].NYH_ULSD_N2_GAL.iloc[6:18], name='NYH ULS Diesel #2', line_color=colores[5], line_width = 3, legendrank=5, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))
fig2.add_trace(go.Scatter(x=dic_df['OilPrice_18'].periodDate.iloc[6:18], y=dic_df['OilPrice_18'].USGC_RGAS_GAL.iloc[6:18], name='USGC Reg. Gasoline', line_color=colores[6], line_width = 3, legendrank=4, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))
fig2.add_trace(go.Scatter(x=dic_df['OilPrice_18'].periodDate.iloc[6:18], y=dic_df['OilPrice_18'].USGC_ULSD_N2_GAL.iloc[6:18], name='USGC ULS Diesel #2', line_color=colores[7], line_width = 3, legendrank=6, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))


fig2.update_layout(title='Historical Prices of Oil Products (Fuels) USD/GAL. Monthly Avg.',
                  title_x=0.5,
                  height=500,
                  paper_bgcolor=colores[0],
                  #paper_bgcolor = 'rgba(0,0,0,0)',
                  plot_bgcolor='rgba(0,0,0,0)',
                  yaxis_gridcolor = colores[8],
                  xaxis_gridcolor = colores[8],
                  xaxis_linewidth = 1,
                  yaxis_linewidth = 1,
                  xaxis_gridwidth = 1,
                  yaxis_gridwidth = 1,
                  #xaxis_griddash='dot',
                  #yaxis_griddash='dot',
                  #xaxis_showgrid = False,
                  #yaxis_showgrid = False,
                  #xaxis_title='Como sale el título del eje x',
                  yaxis_title='USD/GAL',
                  #yaxis_tickformat = ',.2e',
                  #yaxis_range=[0,120],
                 font=dict(
                    family="Arial, sans-serif",
                    size=11,  # Set the font size here
                    color=colores[8]   #"DarkBlue"
                    
                ),
                 
                 xaxis=dict(
                     #rangeslider=dict(
                     #    visible=True,
                     #    thickness = 0.05  ### así lo haces más delgado 
                     #),
                     type="date"
                 ),
                 legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=0.99,
                    xanchor="right",
                    x=1
                 )
                 )

#Producción:
fig3 = go.Figure(data=[
    go.Bar(name='Gulf Coast', x=dic_df['OilProd_12'].periodDate, y=dic_df['OilProd_12'].Gulf_Coast_MBBL, marker_color=colores[1], legendrank=1, hovertemplate ='%{x|%b-%Y}'+ ', %{y:,} MBBL'),
    go.Bar(name='East Coast', x=dic_df['OilProd_12'].periodDate, y=dic_df['OilProd_12'].East_Coast_MBBL, marker_color=colores[2], legendrank=2, hovertemplate ='%{x|%b-%Y}'+ ', %{y:,} MBBL'),
    go.Bar(name='Midwest', x=dic_df['OilProd_12'].periodDate, y=dic_df['OilProd_12'].Midwest_MBBL, marker_color=colores[3], legendrank=3, hovertemplate ='%{x|%b-%Y}'+ ', %{y:,} MBBL'),
    go.Bar(name='Rocky Mountain', x=dic_df['OilProd_12'].periodDate, y=dic_df['OilProd_12'].Rocky_Mountain_MBBL, marker_color=colores[4], legendrank=4, hovertemplate ='%{x|%b-%Y}'+ ', %{y:,} MBBL'),
    go.Bar(name='West Coast', x=dic_df['OilProd_12'].periodDate, y=dic_df['OilProd_12'].West_Coast_MBBL, marker_color=colores[5], legendrank=5, hovertemplate ='%{x|%b-%Y}'+ ', %{y:,} MBBL')
])


# Change the bar mode insidic_df['OilProd_12'].periodDatede the layout:

fig3.update_layout(
    barmode='stack', #para hacer la gráfica apilada.
    title='Historical Oil Production (Thousand Barrels)',
    title_x=0.5,
    height=500,
    paper_bgcolor=colores[0],
    #paper_bgcolor = 'rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    yaxis_gridcolor = colores[8],
    xaxis_gridcolor = colores[8],
    xaxis_linewidth = 1,
    yaxis_linewidth = 1,
    xaxis_gridwidth = 1,
    yaxis_gridwidth = 1,
    #xaxis_griddash='dot',
    #yaxis_griddash='dot',
    xaxis_showgrid = False,
    #yaxis_showgrid = False,
    #xaxis_title='Como sale el título del eje x',
    yaxis_title='Thousand Barrels (MBBL)',
    yaxis_tickformat = ',.2e',
    #yaxis_range=[0,120],
    font=dict(
        family="Arial, sans-serif",
        size=11,  # Set the font size here
        color=colores[8]   #"DarkBlue"
                    
    ),
                 
    xaxis=dict(
        #rangeslider=dict(
        #    visible=True,
        #    thickness = 0.05  ### así lo haces más delgado 
        #),
        type="date"
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=0.99,
        xanchor="right",
        x=1
        )
)

#GAS
x_largo_gas = pd.concat([dic_df['NGasPrice_18']['periodDate'], dic_df['NGasPrice_18']['periodDate'][::-1] ]).tolist()
y_largo_gas = pd.concat([dic_df['NGasPrice_18']['Min_HH_NG_SPOT_MMBTU'], dic_df['NGasPrice_18']['Max_HH_NG_SPOT_MMBTU'][::-1] ]).tolist()
max_steo = min(len(dic_df['STEO_AsOf']), 18)
fig4 = go.Figure()
fig4.add_trace( go.Scatter(
    x=x_largo_gas,
    y=y_largo_gas,
    fill = 'toself',
    fillcolor = colores[1],
    opacity= 0.2,
    line_color= colores[1],  #'rgba(255,255,255,0)',
    #showlegend=False,
    name='HH 5 yrs. Price Range',
    legendrank=2, 
    hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'
) )
fig4.add_trace(go.Scatter(x=dic_df['NGasPrice_18'].periodDate, y=dic_df['NGasPrice_18']['HH_NG_SPOT_MMBTU'], name='HH Spot Nat. Gas', line_color=colores[1], line_width = 4, legendrank=1, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))
fig4.add_trace(go.Scatter(x=dic_df['STEO_AsOf'].periodDate.iloc[0:max_steo], y=dic_df['STEO_AsOf'].HH_NG_PROY_MMBTU.iloc[0:max_steo], name='HH Nat. Gas STEO Proj.', line_dash='dot', line_color=colores[1], line_width=3, legendrank=3, hovertemplate ='%{x|%b-%Y}'+ ', $%{y:.2f}'))

fig4.update_layout(title='Natural Gas Prices (Henry Hub Spot), Historic and STEO Projection. Monthly Avg.',
                  title_x=0.5,
                  height=600,
                  paper_bgcolor=colores[0],
                  #paper_bgcolor = 'rgba(0,0,0,0)',
                  plot_bgcolor='rgba(0,0,0,0)',
                  yaxis_gridcolor = colores[8],
                  xaxis_gridcolor = colores[8],
                  xaxis_linewidth = 1,
                  yaxis_linewidth = 1,
                  xaxis_gridwidth = 1,
                  yaxis_gridwidth = 1,
                  #xaxis_griddash='dot',
                  #yaxis_griddash='dot',
                  #xaxis_showgrid = False,
                  #yaxis_showgrid = False,
                  #xaxis_title='Como sale el título del eje x',
                  yaxis_title='USD/MMBTU',
                  #yaxis_tickformat = ',.2e',
                  #yaxis_range=[0,120],
                 font=dict(
                    family="Arial, sans-serif",
                    size=11,  # Set the font size here
                    color=colores[8]   #"DarkBlue"
                    
                ),
                 
                 xaxis=dict(
                     rangeslider=dict(
                         visible=True,
                         thickness = 0.05  ### así lo haces más delgado 
                     ),
                     type="date"
                 ),
                 legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=0.99,
                    xanchor="right",
                    x=1
                 )
                 )

#gas storage
fig5 = go.Figure(data=[
    go.Bar(name='Lower 48 States Underground Storage', x=dic_df['NGasStorage_12'].periodDate, y=dic_df['NGasStorage_12'].LOWER48_NATGAS_STORAGE_MMCF, marker_color=colores[7], legendrank=1, hovertemplate ='%{x|%b-%Y}'+ ', %{y:,} MMcf')
])

fig5.update_layout(
    #barmode='stack', #para hacer la gráfica apilada.
    title='Lower 48 States Underground Storage (Million Cubic Feet)',
    title_x=0.5,
    height=400,
    paper_bgcolor=colores[0],
    #paper_bgcolor = 'rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    yaxis_gridcolor = colores[8],
    xaxis_gridcolor = colores[8],
    xaxis_linewidth = 1,
    yaxis_linewidth = 1,
    xaxis_gridwidth = 1,
    yaxis_gridwidth = 1,
    #xaxis_griddash='dot',
    #yaxis_griddash='dot',
    xaxis_showgrid = False,
    #yaxis_showgrid = False,
    #xaxis_title='Como sale el título del eje x',
    yaxis_title='Million cubic feet (MMcf)',
    yaxis_tickformat = ',.2e',
    #yaxis_range=[0,120],
    font=dict(
        family="Arial, sans-serif",
        size=11,  # Set the font size here
        color=colores[8]   #"DarkBlue"
                    
    ),
                 
    xaxis=dict(
        #rangeslider=dict(
        #    visible=True,
        #    thickness = 0.05  ### así lo haces más delgado 
        #),
        type="date"
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=0.99,
        xanchor="right",
        x=1
        )
)

#gas production
fig6 = go.Figure(data=[
    go.Bar(name='Dry Natural Gas Production', x=dic_df['DryGasProd_12'].periodDate, y=dic_df['DryGasProd_12'].DRYNATGAS_PROD_MMCF, marker_color=colores[5], legendrank=1, hovertemplate ='%{x|%b-%Y}'+ ', %{y:,} MMcf')
])

fig6.update_layout(
    #barmode='stack', #para hacer la gráfica apilada.
    title='U.S. Dry Natural Gas Production (Million Cubic Feet)',
    title_x=0.5,
    height=400,
    paper_bgcolor=colores[0],
    #paper_bgcolor = 'rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    yaxis_gridcolor = colores[8],
    xaxis_gridcolor = colores[8],
    xaxis_linewidth = 1,
    yaxis_linewidth = 1,
    xaxis_gridwidth = 1,
    yaxis_gridwidth = 1,
    #xaxis_griddash='dot',
    #yaxis_griddash='dot',
    xaxis_showgrid = False,
    #yaxis_showgrid = False,
    #xaxis_title='Como sale el título del eje x',
    yaxis_title='Million cubic feet (MMcf)',
    yaxis_tickformat = ',.2e',
    #yaxis_range=[0,120],
    font=dict(
        family="Arial, sans-serif",
        size=11,  # Set the font size here
        color=colores[8]   #"DarkBlue"
                    
    ),
                 
    xaxis=dict(
        #rangeslider=dict(
        #    visible=True,
        #    thickness = 0.05  ### así lo haces más delgado 
        #),
        type="date"
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=0.99,
        xanchor="right",
        x=1
        )
)

##########################################################################
#############################

#App creation:
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP]) #aquí sería metiendo una hoja de estilo externa.
#app = dash.Dash(__name__) #este es el que usualmente funciona.
server = app.server

app.title = "EIA by DataGarage"

#App layout:
def serve_layout():
    return html.Div(className="flex-wrapper",
        children=[
        	#html.Div(className="cabecera", children=[
        	#	html.Img(className="center", src = app.get_asset_url("DataGarage_w_curves.svg"), alt="DataGarage", style={'height':'40px'})
        	#]
        	#),
        	#html.Div(className="banderas", style={"background-image": 'url("assets/bandera_ready.svg")'}),
            html.Div(className="normal", children=[
                html.H2("U.S. EIA Crude Oil, Gas & Fuels",style={'textAlign': 'center', 'color': '#cfcfcf', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif']}), 
                html.P("Values from the U.S. Energy Information Administration's API, monthly aggregations.", style={'textAlign':'justify', 'color': '#cfcfcf', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif'], 'padding-left':'2%', 'padding-right':'2%'}),
                #html.P("Notes2 ", style={'textAlign':'justify', 'color': '#cfcfcf', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif'], 'padding-left':'2%', 'padding-right':'2%'}),
                #html.P("notes3", style={'textAlign':'justify', 'color': '#cfcfcf', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif'], 'padding-left':'2%', 'padding-right':'2%'}),
                #html.P("Notes4", style={'textAlign':'justify', 'color': '#cfcfcf', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif'], 'padding-left':'2%', 'padding-right':'2%'}),
                html.Div(dcc.Graph(figure=fig1, config={'displayModeBar': False} )),
                
                html.Div(children=[
                    dbc.Row([
                        dbc.Col(html.Div(dcc.Graph(figure=fig2, config={'displayModeBar': False} )), width={"size": 6}, xs=12, sm=12, md=12, lg=6),
                        dbc.Col(html.Div(dcc.Graph(figure=fig3, config={'displayModeBar': False} )), width={"size": 6}, xs=12, sm=12, md=12, lg=6)
                    ])
                ]),
                
                html.Div(dcc.Graph(figure=fig4, config={'displayModeBar': False} )),
                
                html.Div(children=[
                    dbc.Row([
                        dbc.Col(html.Div(dcc.Graph(figure=fig5, config={'displayModeBar': False} )), width={"size": 6}, xs=12, sm=12, md=12, lg=6),
                        dbc.Col(html.Div(dcc.Graph(figure=fig6, config={'displayModeBar': False} )), width={"size": 6}, xs=12, sm=12, md=12, lg=6)
                    ])
                ])
                
            ]),
                
        	html.Footer(className="pie", children=[
        		html.Div(children=[
        			html.A(html.Img(className="center", src = app.get_asset_url("DataGarage_dev_w_curves.svg"), alt="DataGarage.dev", style={'height':'25px'}), href="https://datagarage.dev"
        			)
        		]
        		),
        		html.Div(style={"padding-top":"5px", "text-align":"center"}, children=[
        			html.P(
        				html.A('CC-BY-NC ', href="https://creativecommons.org/licenses/by-nd/4.0/", style={'color':'white', "text-align":"center", "text-decoration": "none"}), 
        				style={"display":"inline", "color":"white", "text-align":"center"}
        			),
        			html.P(
        				'Jordi Tarragó ',
        				style={"display":"inline", "color":"white", "text-align":"center"}
        			),

        			html.Br(),        			
        			
        			html.P(
        				' jordi@datagarage.dev',
        				style={"display":"inline", "color":"white", "text-align":"center"}
        			)
        		]
        		)
        	]
        	),            
             
        ]
        )

app.layout = serve_layout
    

# Run the application                   
if __name__ == '__main__':
#	app.run_server()
	app.run(host='0.0.0.0')

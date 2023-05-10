#Imports:
import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output

import pandas as pd
import datetime as dt

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import sqlalchemy
import pymysql
from sqlalchemy import create_engine
from sqlalchemy import text



#Data:
with open('db_string', 'r') as cadena:
    engine = create_engine(cadena.readline())

#DEFINE start and end dates: ## Could be modified with a call back to make date ranges dynamic and interactive.
with engine.connect() as conn:
    fecha_mayor_df = pd.read_sql(text('select max(Fecha) as Fecha_max from PrecioBolsa'), conn)

fecha_mayor = fecha_mayor_df.iloc[0]['Fecha_max'].isoformat(' ')[0:10]
fecha_menor = (fecha_mayor_df.iloc[0]['Fecha_max']-dt.timedelta(days=365)).isoformat(' ')[0:10]

##Min Max Prices
qry = """
SELECT DATE_FORMAT(Fecha, "%Y-%m-%d") AS Date_, min(PrecBolsNaci) AS Min_1_yr, 
max(PrecBolsNaci) as Max_1_yr FROM PrecioBolsa WHERE Fecha>="{0}" AND Fecha<"{1}" GROUP BY Date_;
"""
with engine.connect() as conn:
    pbolsa_diario_1_anyo = pd.read_sql(text(qry.format(fecha_menor, dt.datetime.fromisoformat(fecha_mayor)+dt.timedelta(days=1))), conn)
pbolsa_diario_1_anyo['Date_'] = pd.to_datetime(pbolsa_diario_1_anyo['Date_'])
pbolsa_diario_1_anyo.set_index('Date_', inplace= True)

##Get tables to load:
tables = pd.read_csv('Tabla_elec_col_1.csv')

##Load tables, function definition:
def load_daily_avg(tabla, columna, fecha_ini, fecha_fin, engine): ##sólo si se han de cargar Y DATETIME en fecha.
    
    qry = """
    SELECT DATE_FORMAT(Fecha, "%Y-%m-%d") AS Date_,  avg({1}) AS daily 
    FROM {0} WHERE Fecha>="{2}" AND Fecha<"{3}" GROUP BY Date_;
    """
    ##modifiqué a que sea < fecha mayor y en fecha mayor le sumé un día, porque creo que del último día quitaría todas las horas menos las primera como estaba.
    
    fecha_mayor = max(dt.datetime.fromisoformat(fecha_ini), dt.datetime.fromisoformat(fecha_fin))+dt.timedelta(days=1)
    fecha_menor = min(dt.datetime.fromisoformat(fecha_ini), dt.datetime.fromisoformat(fecha_fin))
    
    with engine.connect() as conn:
        temp_ret_df = pd.read_sql(text(qry.format(tabla, columna, fecha_menor, fecha_mayor)), conn)
    
    return temp_ret_df


def load_daily(tabla, columna, fecha_ini, fecha_fin, engine):
    qry = """
    SELECT Fecha AS Date_, {1} AS daily 
    FROM {0} WHERE Fecha>="{2}" AND Fecha<="{3}" GROUP BY Date_;
    """
    fecha_mayor = max(dt.datetime.fromisoformat(fecha_ini), dt.datetime.fromisoformat(fecha_fin))
    fecha_menor = min(dt.datetime.fromisoformat(fecha_ini), dt.datetime.fromisoformat(fecha_fin))
    with engine.connect() as conn:
        temp_ret_df = pd.read_sql(text(qry.format(tabla, columna, fecha_menor, fecha_mayor)), conn) 
    return temp_ret_df

##Load tables, actual loading:
indice = pd.date_range(start=fecha_menor, end= fecha_mayor, freq = "D", inclusive = 'both')

data = pd.DataFrame({'Date_': indice})
data.set_index('Date_', inplace= True)

for i in range(len(tables)):
    if tables.iloc[i]['Load'] != 'y':
        pass
    if tables.iloc[i]['Freq'] == 'hourly':
        df_temp = load_daily_avg(tables.iloc[i]['Tabla'], tables.iloc[i]['Dato'], \
                                                      fecha_menor, fecha_mayor, engine)
        
        df_temp['Date_'] = pd.to_datetime(df_temp['Date_']) 
        df_temp.set_index('Date_', inplace= True) 
        df_temp.rename(columns={'daily':tables.iloc[i]['Tabla']}, inplace = True)
        data = data.join(df_temp, how = 'left') #data.merge(df_temp, how = 'left', left_index=True, right_index = True )
        #display(df_temp.head(2))
    else:
        df_temp = load_daily(tables.iloc[i]['Tabla'], tables.iloc[i]['Dato'], \
                                                      fecha_menor, fecha_mayor, engine)
        df_temp.set_index('Date_', inplace= True)
        df_temp.rename(columns={'daily':tables.iloc[i]['Tabla']}, inplace = True)
        data = data.join(df_temp, how = 'left')
        #display(df_temp.head(2))

data['Fecha'] = data.index
data['Fecha'] = data.Fecha.apply(lambda x: str(x.isoformat()[0:10]))
    
data = data.merge(pbolsa_diario_1_anyo, how = 'left', left_index=True, right_index = True )

##Para corregir errores de sombra:
    
indice = pd.date_range(start=fecha_menor, end= fecha_mayor, freq = "D", inclusive = 'both')
tmp_data = pd.DataFrame({ 'Date_': indice})
tmp_data.set_index('Date_', inplace= True)
data = tmp_data.merge(data, how = 'left', left_index=True, right_index = True )

values = {"Min_1_yr": 0, "Max_1_yr": 0}
data.fillna(value = values, inplace=True)

    

#Data2
#Definición de plazos 
max_hora = fecha_mayor_df.iloc[0]['Fecha_max']
dias_antes_7 = max_hora - dt.timedelta(days=7) + dt.timedelta(hours=1)

semanas_12 = max_hora - dt.timedelta(days=7*12) + dt.timedelta(hours=1)
anyos_5 = max_hora - dt.timedelta(days=(365*5)) + dt.timedelta(hours=1)

#Query
qry="""
SELECT A.Date_,  A.Date_2, A.Precio_latest,
B.Avg_12_w, B.Min_12_w, B.Max_12_w,
C.Avg_5_yr, C.Min_5_yr, C.Max_5_yr
FROM 
(SELECT Fecha as Date_, DATE_FORMAT(Fecha, "%a-%H") AS Date_2, PrecBolsNaci AS Precio_latest
FROM PrecioBolsa WHERE Fecha>="{0}" AND Fecha<="{1}") A
LEFT JOIN 
(SELECT DATE_FORMAT(Fecha, "%a-%H") AS Date_2, avg(PrecBolsNaci) as Avg_12_w, min(PrecBolsNaci) AS Min_12_w, 
max(PrecBolsNaci) as Max_12_w FROM PrecioBolsa WHERE Fecha>="{2}" AND Fecha<="{1}" GROUP BY Date_2) B
ON A.Date_2 = B.Date_2
LEFT JOIN
(SELECT DATE_FORMAT(Fecha, "%a-%H") AS Date_2, avg(PrecBolsNaci) as Avg_5_yr, min(PrecBolsNaci) AS Min_5_yr, 
max(PrecBolsNaci) as Max_5_yr FROM PrecioBolsa WHERE Fecha>="{3}" AND Fecha<="{1}" GROUP BY Date_2) C
ON A.Date_2 = C.Date_2
ORDER BY A.Date_
;
"""


with engine.connect() as conn:
    data2 = pd.read_sql(text(qry.format(dias_antes_7, max_hora, semanas_12, anyos_5)), conn)

data2['Date_'] = pd.to_datetime(data2['Date_'])


##Close the engine:
engine.dispose()


##END of data1 & data2 


#Plots:


x_largo = pd.concat([data["Fecha"], data["Fecha"][::-1]]).tolist() # como string
y_largo = pd.concat([data["Min_1_yr"], data["Max_1_yr"][::-1]]).tolist()

fig = make_subplots(rows=2, cols=1, shared_xaxes=True)  ####Aquí metí que compartan el eje y que sean dos subplots uno arriba del otro (por eso no puse =go.Figure()

##--## First plot:

fig.add_trace(go.Scatter(
    x=x_largo,
    y=y_largo,
    fill='toself',
    fillcolor='#001741', #en lugar de en el úlitmo poner 255 puedes poner 0.2 como tenía en lugar de usar opacity, pero así puedo usar hex colors-
    opacity=0.2, #supuestamente puedes meter la opacidad aquí
    line_color='rgba(255,255,255,0)',
    #showlegend=False,
    name='Daily Range Spot Price',
), row=1, col=1)

fig.add_trace(go.Scatter(x=data.index, y=data.PrecioBolsa, name='Spot Price', line_color='#001741', line_width = 3), row=1, col=1)

fig.add_trace(go.Scatter(x=data.index, y=data.PrecioContReg, name='Reg. Contract Price', line_color='#00318C', line_width = 2.3), row=1, col=1)

fig.add_trace(go.Scatter(x=data.index, y=data.PrecioContNoReg, name='Dereg. Contract Price', line_color='#088799', line_width = 2.3), row=1, col=1)

fig.add_trace(go.Scatter(x=data.index, y=data.PrecioTX1, name='TX1 Index', line_color='#2D4003', visible= 'legendonly'), row=1, col=1)  #.update_traces(visible='legendonly')

fig.add_trace(go.Scatter(x=data.index, y=data.PrecioEscasez, name='Escasez', line_color='#8C0E4D'), row=1, col=1)

fig.add_trace(go.Scatter(x=data.index, y=data.PrecioEscasezAct, name='Escasez de Activación', line_color='#A30808', visible= 'legendonly'), row=1, col=1)


##--## Second plot...

fig.add_trace(go.Bar(x=data.index, y=data.VolumenUtilTotal, name = 'Volume Available', marker_color='#14FFFF'), 
              row=2, col=1)

fig.add_trace(go.Scatter(x=data.index, y=data.CapacidadUtilTotal, name = 'Total Capacity', line_color='#668C0E', line_dash='dot'), row=2, col=1)

##..## Layout config

fig.update_layout(title='Colombia XM Average Daily Prices & Energy Available in Reservoirs',
                  title_x=0.5,
                  yaxis2_domain = [0, 0.26], ### en teoría esto es lo que hace uqe la gráfica se cambie de tamaño
                  yaxis_domain = [0.35, 1], ### en teoría esto es lo que hace uqe la gráfica se cambie de tamaño
                  height=700,
                  paper_bgcolor='rgba(0,0,0,0)',
                  plot_bgcolor='rgba(0,0,0,0)',
                  yaxis_gridcolor = 'rgba(0,0,0,0.2)',
                  xaxis_gridcolor = 'rgba(0,0,0,0.2)',
                  yaxis2_gridcolor = 'rgba(0,0,0,0.2)',
                  xaxis2_gridcolor = 'rgba(0,0,0,0.2)',
                  #xaxis_title='Como sale el título del eje x',
                  yaxis_title='COP/kWh',
                  yaxis2_title = 'kWh (in Reservoirs)',
                  #xaxis2_title = 'Tiempo',
                  yaxis2_tickformat = ',.2e',
                  #yaxis2_range=[0,21000000000],
                 font=dict(
                    family="Arial, sans-serif",
                    size=14,  # Set the font size here
                    color='Black'    #"DarkBlue"
                ),
                 
                 xaxis=dict(
                     rangeslider=dict(
                         visible=True,
                         thickness = 0.05  ### así lo haces más delgado 
                     ),
                     type="date"
                 )
                 )
    
 
## End mainxm-plot

#second plot
x_largo_2 = pd.concat([data2['Date_2'], data2['Date_2'][::-1]]).tolist() # como string
semanas_12_largo = pd.concat([data2["Min_12_w"], data2["Max_12_w"][::-1]]).tolist()
anyo_5_largo = pd.concat([data2["Min_5_yr"], data2["Max_5_yr"][::-1]]).tolist()


fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=x_largo_2,
    y=semanas_12_largo,
    fill='toself',
    fillcolor='#00318C', 
    opacity=0.2, 
    line_color='rgba(255,255,255,0)',
    #showlegend=False,
    name='12 week range',
    legendrank=4
))

fig2.add_trace(go.Scatter(
    x=x_largo_2,
    y=anyo_5_largo,
    fill='toself',
    fillcolor='#088799', 
    opacity=0.2, 
    line_color='rgba(255,255,255,0)',
    #showlegend=False,
    name='5 year range',
    legendrank=5
))

fig2.add_trace(go.Scatter(x=data2.Date_2, y=data2.Precio_latest, name='Latest Price', line_color='#001741', legendrank=1))
fig2.add_trace(go.Scatter(x=data2.Date_2, y=data2.Avg_12_w, name = '12 week avg.', line_color='#00318C', legendrank=2))
fig2.add_trace(go.Scatter(x=data2.Date_2, y=data2.Avg_5_yr, name = '5 year avg.', line_color='#088799', legendrank=3))

fig2.update_layout(title='Colombia XM Hourly Prices & Historic Behaviour<br><sup>Latest Price from {} to {}</sup>'.format(dias_antes_7.isoformat(' ')[0:16], max_hora.isoformat(' ')[0:16]),
                  title_x=0.5,
                  height=400,
                  paper_bgcolor='rgba(0,0,0,0)',
                  plot_bgcolor='rgba(0,0,0,0)',
                  yaxis_gridcolor = 'rgba(0,0,0,0.2)',
                  xaxis_gridcolor = 'rgba(0,0,0,0.2)',
                  #xaxis_title='Como sale el título del eje x',
                  yaxis_title='COP/kWh',
                 font=dict(
                    family="Arial, sans-serif",
                    size=14,  
                    color='Black'    #"DarkBlue"
                ),
                 
                 xaxis=dict(
                     rangeslider=dict(
                         visible=True,
                         thickness = 0.05  ### así lo haces más delgado 
                     ),
                     #type="date"
                 )
                 )
##END of second plot definition.



#App creation:
#app = dash.Dash(__name__, server=server) #aquí también cambié
app = dash.Dash(__name__)
server = app.server

app.title = "Colombia by DataGarage"

#App layout:
def serve_layout():
    return html.Div(className="flex-wrapper",
        children=[
        	html.Div(className="cabecera", children=[
        		html.Img(className="center", src = app.get_asset_url("DataGarage_w_curves.svg"), alt="DataGarage", style={'min-height':'50px'})
        	]
        	),
        	html.Div(className="banderas", style={"background-image": 'url("assets/bandera_ready.svg")'}),
            html.H1('Electricity in Colombia',style={'textAlign': 'center', 'color': 'Black', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif']}), 
            html.P('Here you can see the most relevant historic data of the Colombian Energy Grid Prices.', style={'textAlign':'justify', 'color': 'Black', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif'], 'padding-left':'2%', 'padding-right':'2%'}),
            html.P("The report is updated daily with the latest available data from XM's API and might take a few seconds for the charts to load. If left opened overnight refresh the page to see updates (if any). Data is extracted and stored by us with automated software and is offered as a reference. ", style={'textAlign':'justify', 'color': 'Black', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif'], 'padding-left':'2%', 'padding-right':'2%'}),
            html.P("Feel free to click on the legends on the charts to hide / unhide the traces. The sliders (located between the two subplots for the first chart, and at the bottom of the second) allow for a detailed view of a time window within the presented data.", style={'textAlign':'justify', 'color': 'Black', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif'], 'padding-left':'2%', 'padding-right':'2%'}),
            html.P("Historic prices are presented with the nominal values they had when published.", style={'textAlign':'justify', 'color': 'Black', 'font-family': ['Helvetica', 'Tahoma', 'sans-serif'], 'padding-left':'2%', 'padding-right':'2%'}),
            html.Div(dcc.Graph(figure=fig, config={'displayModeBar': False} )),
            html.Div(dcc.Graph(figure=fig2, config={'displayModeBar': False} )),
            
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

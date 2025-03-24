from dash import Dash, html, dcc, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from flask import Flask
import pytz
from datetime import datetime, date
import pandas as pd
import psycopg2

Total = 9999
A = 100
B = 2000
C = 1500 
# Define the time zone for Brazil
tz = pytz.timezone('America/Sao_Paulo')
current_time = datetime.now(tz)
today = current_time.strftime('%Y-%m-%d') 
YY = int(current_time.strftime('%Y'))
MM = int(current_time.strftime('%m'))
DD = int(current_time.strftime('%d'))

from helper import get_date_picker_days, get_past_days
dis_day_integrados, st_day_integrados, end_day_integrados = get_date_picker_days('integrados', 'chicken', 'date')
dis_day_paws, st_day_paws, end_day_paws = get_date_picker_days('paws', 'chicken', 'data')



def read_database_financeiro():
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    
    
    query = f"SELECT DISTINCT name FROM integrados"
    int_names = pd.read_sql_query(query, conn)

    conn.close()

    return int_names





#print(datetime.now(tz))
integrados = read_database_financeiro()
integrados = integrados.sort_values(['name'])

    
#print(datetime.now(tz))


app = Flask(__name__)
dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], url_base_pathname='/', server=app)
dash_app.title = 'THEIA - tester'
dash_app._favicon = "icon.png"


dash_app.layout = dbc.Container([ 
    html.Hr(),
    dbc.Card(  # cabeçalho
        dbc.Row([
            dbc.Col(html.Img(src=r'assets/logo.png', className='responsive-img'),
		xs=6, sm=4, md=4, lg=4, xl=4
		),
            dbc.Col([
                dbc.Row(html.H3('Contagem e Qualidade')),
                dbc.Row(html.H5('Un. São Sebastião do Caí'))
            ], xs = 6, sm = 8, md = 8, lg=6, xl=6),
        ], align="center"),
    ),  # fim do cabeçalho
    # dcc.Store(id='screen-size-store'),
    # dcc.Interval(id='screen_size_interval', interval=1000, n_intervals=0, max_intervals=1),  # Interval runs once on load
    html.Hr(),

    dcc.Tabs([
        dcc.Tab(  # inicio aba financeiro
            dbc.Card([            
                dbc.Row([
                        dbc.Col(
                            dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas A', color='success', className="me-3", id='valor-A')),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('US$/kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='dolar-A', 
                                                    value='3.80', 
                                                    style={"width": 50, "height": 30},)
                                )]),                         
                                ]),
                            ),xs=6, sm=6, md=2, lg=2
                        ),
                        dbc.Col(
                            dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas B', color='warning', className="me-3", id='valor-B')),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('US$/kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='dolar-B', 
                                                    value='3.50', 
                                                    style={"width": 50, "height": 30},)
                                )]),                         
                                ]),
                            ),xs=6, sm=6, md=2, lg=2
                        ),
                        dbc.Col(
                            dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas C', color='danger', className="me-3", id='valor-C')),
                                html.Hr(),
                                dbc.Row([
                                    dbc.Col(
                                        html.H5('US$/kg:'),
                                    ),
                                    dbc.Col(
                                        dcc.Input(id='dolar-C', 
                                                        value='3.30', 
                                                        style={"width": 50, "height": 30}),
                                    )]),                         
                                ]),
                            ),xs=6, sm=6, md=2, lg=2
                        ),
                        dbc.Col(
                            dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Peso/pata', color='primary', className="me-3", id='valor-peso')),
                                html.Hr(),
                                dbc.Row([
                                    dbc.Col(
                                        html.H5('kg:'), xs=6, sm=6, md=2, lg=4
                                    ),
                                    dbc.Col(
                                        dcc.Input(id='peso', 
                                                value='0.05', 
                                                style={"width": 50, "height": 30}),
                                    xs=6, sm=6, md=2, lg=4
                                    ),
                                    ]),                         
                                ]),
                            ),xs=6, sm=6, md=2, lg=2
                        ),
                    ]),
                                    
                html.Hr(),

                dbc.Row([                                   
                    dbc.Col([
                            dbc.Row(html.H4("Integrado:")),
                            dbc.Row(dcc.Dropdown(id='integrado-seletor', 
                                                 placeholder="Selecione um integrado",
                                                 options=integrados['name'],))
                        ],xs=12, sm=12, md=4, lg=4, xl=4),                    

                    ]),
                dbc.Card(id='output-financeiro',
                         body=True, 
                         outline=False
                         ),    

               
                
                ], body=True, outline=False),            
            label='Financeiro', id='financeiro-tab'),  # fim aba financeiro

    ]), # fim dos tabs 
    html.Hr(),
]) # fim do layout
# Callback tab 'financeiro'
@dash_app.callback(
        Output('output-financeiro','children'),
        Input("integrado-seletor", 'value'),
)
def calback_finaneiro(nome):
    print(nome)
    return [
        html.H4(nome, className="card-title"),
        #dcc.Graph(figure=fig)
    ]

if __name__ == '__main__':
    dash_app.run(debug=True)    
    #app.run(host='127.0.0.1', port=8050)
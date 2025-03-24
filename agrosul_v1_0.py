from flask import Flask
import os
from dash import dcc, html, Dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

# Import the content of each tab from the separate module files
from tabs import dia_tab, financeiro_tab, historico_tab, upload_tab, video_tab

# careful here, it seems this warning is irrelevant:
# https://stackoverflow.com/questions/71082494/getting-a-warning-when-using-a-pyodbc-connection-object-with-pandas
from warnings import filterwarnings
filterwarnings("ignore", category=UserWarning, message='.*pandas only supports SQLAlchemy connectable.*')

# upload folder
UPLOAD_DIRECTORY = "uploads"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


app = Flask(__name__)
dash_app = Dash(__name__, 
                external_stylesheets=[dbc.themes.FLATLY, '/assets/styles.css'],  
                url_base_pathname='/', 
                server=app, 
                suppress_callback_exceptions=True)
dash_app.title = 'THEIA - Agrosul'
dash_app._favicon = "icon.png"


# Define the layout with tabs
dash_app.layout = dbc.Container([

    html.Hr(),
    dbc.Card(  # cabeçalho
        dbc.Row([
            dbc.Col(html.Img(src=r'assets/logo2.png', className='responsive-img'),
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

    dcc.Tabs(id="tabs", value='tab-dia', children=[
        dcc.Tab(label='Dados diários', value='tab-dia'),
        dcc.Tab(label='Histórico', value='tab-historico'),
        dcc.Tab(label='Financeiro', value='tab-financeiro'),
        dcc.Tab(label='Vídeo', value='tab-video'),
        dcc.Tab(label='Upload', value='tab-upload'),
    ]),
    html.Div(id='tabs-content')
])

# Callback to switch between tabs and render content
@dash_app.callback(
    Output('tabs-content', 'children'),
    [Input('tabs', 'value')]
)
def render_tab_content(tab):
    if tab == 'tab-dia':
        return dia_tab.layout  # Render the financeiro tab content
    elif tab == 'tab-historico':
        return historico_tab.layout
    elif tab == 'tab-financeiro':
        return financeiro_tab.layout
    elif tab == 'tab-video':
        #return financeiro_tab.layout
        return video_tab.layout
    elif tab == 'tab-upload':
        return upload_tab.layout


# Register callbacks from tab modules
financeiro_tab.register_callbacks_financeiro(dash_app)
dia_tab.register_callbacks(dash_app)
historico_tab.register_callbacks(dash_app)
video_tab.register_callbacks(dash_app)
upload_tab.register_callbacks(dash_app)


if __name__ == '__main__':
    dash_app.run_server(debug=True)
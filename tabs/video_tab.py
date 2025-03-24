from dash import html, Dash
from dash.dependencies import Output
from flask import Flask
import dash_bootstrap_components as dbc
import dash_dangerously_set_inner_html

import dash_player as dp
from flask import Flask





# Callback tab 'financeiro'
def register_callbacks(dash_app):
    pass
    
        # agora por integrado:


# Dia Tab Layout
layout = dbc.Card([
    dbc.Row([
      dbc.Col(
        dp.DashPlayer(
                            id="player",
                            url="https://stream.theiasistemas.com.br/hls/ds-test-2.m3u8",
                            controls=True,
                            playing=True,
                            width="100%",
                            height="520px",
                        ),
                xs=12, sm=12, md = 12, lg = 6, xl = 6),
      dbc.Col(
        dp.DashPlayer(
                            id="player2",
                            url="",
                            playing=True,
                            controls=True,
                            width="100%",
                            height="520px",
                        ),
                xs=12, sm=12, md = 12, lg = 6, xl = 6),
    ])
            ]),
# fim da aba 'video'

       

if __name__ == '__main__':   
    print('\n\nrunning locally\n\n')
    app = Flask(__name__)
    dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], 
                    url_base_pathname='/', 
                    server=app)
    server = dash_app.server
    dash_app.title = 'THEIA - video'
    dash_app.layout = layout
    register_callbacks(dash_app)  # Register the callback with the local app
    dash_app.run_server(debug=True)
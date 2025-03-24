import dash
from dash import dcc, html, Dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import pandas as pd
import psycopg2
import pytz
from flask import Flask
from datetime import datetime, date

if __name__ == '__main__':   
    print('\n\nrunning locally\n\n')
    app = Flask(__name__)
    dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], url_base_pathname='/', server=app)
    dash_app.title = 'THEIA - financeiro'



# Financeiro Tab Layout
layout = dbc.Container(
  # inicio aba financeiro
            dbc.Card([    
                html.Hr(),

                ], body=True, outline=False))  # fim aba financeiro


if __name__ == '__main__':
    dash_app.layout = layout
    dash_app.run_server(debug=True)
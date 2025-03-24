import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Dropdown(
        id='dropdown',
        options=[
            {'label': 'Option 1', 'value': 'option1'},
            {'label': 'Option 2', 'value': 'option2'}
        ],
        placeholder="Select an option",
        style={'width': '50%'}
    ),
    html.Div(id='output-div'),
    html.Script('''
        function openWindowWithCard(url) {
            window.open(url, '_blank');
        }
    ''')
])

@app.callback(
    Output('output-div', 'children'),
    [Input('dropdown', 'value')]
)
def open_new_window(value):
    if value:
        # Define the URL or the page you'd like to open
        new_window_url = f'/new-page/{value}'
        # Inject JavaScript into the page to open a new window
        script = html.Script(f'openWindowWithCard("{new_window_url}");')
        return script
    return None

# In a full application, the following would be another route/page
@app.server.route("/new-page/<value>")
def new_page(value):
    # Render a new page with a dbc.Card
    return html.Div([
        dbc.Card(
            dbc.CardBody([
                html.H5(f"You selected {value}", className="card-title"),
                html.P("This is a new window with more information.")
            ])
        )
    ])

if __name__ == '__main__':
    app.run_server(debug=True)

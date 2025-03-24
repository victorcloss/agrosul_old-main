import dash
import dash_bootstrap_components as dbc
from dash import html
import dash_player

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    html.Div([
        dash_player.DashPlayer(
                            id="player",
                            url="http://stream.theiasistemas.com.br:8080/hls/ds-test-2.m3u8",
                            controls=True,
                            width="100%",
                            height="520px",
                        )
            ]),
       
    style={"padding": "50px"}
)

if __name__ == "__main__":
    app.run_server(debug=True)
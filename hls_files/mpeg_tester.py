import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import os

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the app
app.layout = html.Div([
    html.H1("MJPEG Video Player"),
    html.Video(
        id='video-player',
        controls=True,
        autoPlay=False,
        src='/output.mjpeg',  # File served from the assets folder
        style={'width': '80%', 'height': 'auto'}
    ),
])

# Run the Dash app
if __name__ == '__main__':
    # Ensure the file exists in the 'assets' directory
    if not os.path.exists('hls_files/output.mjpeg'):
        print("Error: 'output.mjpeg' file not found!")
    else:
        app.run_server(debug=True)

# app.py
import dash
from dash import html
from flask import Flask, Response
import requests

# Initialize the Flask server
server = Flask(__name__)

# Initialize the Dash app with the Flask server and external scripts
app = dash.Dash(
    __name__,
    server=server,
    external_scripts=[
        "https://cdn.jsdelivr.net/npm/hls.js@latest/dist/hls.min.js"  # hls.js CDN
    ]
)

# Define the layout of the Dash app
app.layout = html.Div([
    html.H1("Live HLS Stream"),
    html.Video(
        id='live-video',
        controls=True,
        autoPlay=False,  # Autoplay can be enabled if desired
        muted=True,      # Some browsers restrict autoplay unless muted
        style={
            'width': '100%',
            'height': 'auto',
            'maxWidth': '800px',
            'margin': '0 auto',
            'display': 'block'
        }
    )
])

# Proxy route to handle HLS stream requests
@server.route('/proxy/hls/<path:filename>')
def proxy_hls(filename):
    # Base URL of the HLS stream server
    base_url = 'http://stream.theiasistemas.com.br:8080/hls/'
    
    # Construct the full URL to the requested file
    stream_url = f"{base_url}{filename}"
    
    try:
        # Fetch the content from the HLS server
        resp = requests.get(stream_url, stream=True)
        
        # If the request was successful, forward the content
        if resp.status_code == 200:
            # Create a Flask Response object with the streamed content
            response = Response(
                resp.iter_content(chunk_size=1024),
                status=resp.status_code,
                content_type=resp.headers.get('Content-Type', 'application/octet-stream')
            )
            
            # Add CORS headers to allow access from any origin
            response.headers['Access-Control-Allow-Origin'] = '*'
            
            return response
        else:
            # If the HLS server returned an error, forward the same status code
            return Response(f"Error fetching stream: {resp.status_code}", status=resp.status_code)
    except Exception as e:
        # Handle any exceptions and return a 500 error
        return Response(f"Internal Server Error: {str(e)}", status=500)

if __name__ == '__main__':
    app.run_server(debug=True)

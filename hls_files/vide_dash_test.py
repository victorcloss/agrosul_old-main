import dash
import dash_html_components as html

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Live RTSP Stream (HLS via VLC)"),
    
    # Create the video container and video element
    html.Div(id="video-container", children=[
        html.Video(id="video", controls=True, autoPlay=True, style={"width": "100%", "height": "auto"})
    ]),
    
    # Include the hls.js library using a script tag
    html.Script(src="https://cdn.jsdelivr.net/npm/hls.js@latest"),
    
    # Inject JavaScript to use hls.js to play the HLS stream in non-Safari browsers
    html.Script("""
    if (Hls.isSupported()) {
        var video = document.getElementById('video');
        var hls = new Hls();
        hls.loadSource('http://your_domain_or_ip/hls/stream.m3u8');  // Replace with your HLS stream URL
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, function() {
            video.play();
        });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = 'http://your_domain_or_ip/hls/stream.m3u8';  // Replace with your HLS stream URL
        video.addEventListener('loadedmetadata', function() {
            video.play();
        });
    }
    """)
])

if __name__ == '__main__':
    app.run_server(debug=True)

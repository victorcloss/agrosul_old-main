import cv2
from dash import html, Dash
from dash.dependencies import Output
from flask import Response, Flask
import threading
import dash_bootstrap_components as dbc
import os
import time


from flask import Flask

# Global variables to store the latest frames from both streams
latest_frame_1 = None
latest_frame_2 = None

# Suppress OpenCV warnings and errors
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

# RTSP Stream URLs
rtsp_url_1 = "rtsp://158.220.127.126:5202/ds-test"
rtsp_url_2 = "rtsp://158.220.127.126:5203/ds-test-2"

# Function to capture the first RTSP stream
def capture_stream_1():
    global latest_frame_1
    cap = cv2.VideoCapture(rtsp_url_1)
    time.sleep(1)  # Wait for a second to allow the stream to stabilize
    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            # Convert the frame to JPEG format
            _, jpeg = cv2.imencode('.jpg', frame)
            latest_frame_1 = jpeg.tobytes()
        

# Function to capture the second RTSP stream
def capture_stream_2():
    global latest_frame_2
    cap = cv2.VideoCapture(rtsp_url_2)
    time.sleep(1)  # Wait for a second to allow the stream to stabilize
    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            # Convert the frame to JPEG format
            _, jpeg = cv2.imencode('.jpg', frame)
            latest_frame_2 = jpeg.tobytes()

# Start both RTSP streams in background threads
stream_thread_1 = threading.Thread(target=capture_stream_1)
stream_thread_1.daemon = True
stream_thread_1.start()

stream_thread_2 = threading.Thread(target=capture_stream_2)
stream_thread_2.daemon = True
stream_thread_2.start()









# Callback tab 'financeiro'
def register_callbacks(dash_app):
    @dash_app.server.route('/video_feed_1')
    def video_feed_1():
        """Video streaming route for the first stream."""
        def generate():
            global latest_frame_1
            while True:
                if latest_frame_1:
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + latest_frame_1 + b'\r\n\r\n')
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
    @dash_app.server.route('/video_feed_2')
    def video_feed_2():
        """Video streaming route for the second stream."""
        def generate():
            global latest_frame_2
            while True:
                if latest_frame_2:
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + latest_frame_2 + b'\r\n\r\n')
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


        # agora por integrado:


# Dia Tab Layout
layout = dbc.Card([
        html.H1("RTSP Video Streams"),
        html.Div([
            html.Img(src="/video_feed_1", style={"width": "49%", "display": "inline-block", "vertical-align": "top"}),
            html.Img(src="/video_feed_2", style={"width": "49%", "display": "inline-block", "vertical-align": "top"}),
    ], style={"display": "flex", "justify-content": "space-between"})

])# fim da aba 'historico'

       

if __name__ == '__main__':   
    print('\n\nrunning locally\n\n')
    app = Flask(__name__)
    dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], 
                    url_base_pathname='/', 
                    server=app)
    server = dash_app.server
    dash_app.title = 'THEIA - hivideotorico'
    dash_app.layout = layout
    register_callbacks(dash_app)  # Register the callback with the local app
    dash_app.run_server(debug=True)
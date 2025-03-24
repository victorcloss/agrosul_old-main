from flask import Flask, Response

app = Flask(__name__)

def mjpeg_stream():
    with open('/tmp/stream.mjpeg', 'rb') as f:
        while True:
            frame = f.read(1024)
            if not frame:
                break
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/feed.mjpg')
def video_feed():
    return Response(mjpeg_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
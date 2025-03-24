import subprocess

def convert_rtsp_to_mjpeg():
    """
    Use FFmpeg to convert an RTSP stream into an MJPEG output file.
    """
    ffmpeg_command2= [
        'ffmpeg', 
        '-rtsp_transport', 'tcp', 
        '-i', 'rtsp://127.0.0.1:5203/ds-test-2', 
        '-vcodec', 'libx264', 
        '-f', 'flv', 
        '-r', '25', 
        '-s', '640x480', 
        '-an', 'rtmp://localhost:1935/live/ds-test-2'
    ]

    ffmpeg_command = [
        'ffmpeg', 
        '-rtsp_transport', 'tcp', 
        '-i', 'rtsp://127.0.0.1:5202/ds-test', 
        '-vcodec', 'libx264', 
        '-f', 'flv', 
        '-r', '25', 
        '-s', '640x480', 
        '-an', 'rtmp://localhost:1935/live/ds-test'
    ]



    try:
        # Start the FFmpeg process
        subprocess.run(ffmpeg_command2, check=True)

        print('\n\n\n hello \n\n\n')
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during FFmpeg conversion: {e}")

if __name__ == "__main__":
    convert_rtsp_to_mjpeg()

import psutil

def kill_all_ffmpeg_processes():
    """
    Terminate all running ffmpeg processes on the server.
    """
    killed_processes = []  # List to keep track of terminated processes

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'ffmpeg' in proc.info['name'] or any('ffmpeg' in cmd for cmd in proc.info['cmdline']):
                proc.terminate()  # Send termination signal to the process
                killed_processes.append(proc.pid)  # Record the PID of the terminated process
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass  # Ignore errors when accessing or terminating a process

    if killed_processes:
        print(f"Terminated ffmpeg processes with PIDs: {killed_processes}")
    else:
        print("No ffmpeg processes found running.")

# Call the function to kill all ffmpeg processes
kill_all_ffmpeg_processes()
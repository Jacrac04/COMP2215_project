import network
import socket
import time
import ntptime
from machine import Pin
from time import localtime
import urequests

# Setup WiFi connection
SSID = 'YourSSID'
PASSWORD = 'YourPassword'

TIMEZONE_OFFSET = 1

CHECK_INTERVAL = 60  # seconds

led = Pin('LED', Pin.OUT)

is_ON = False

# Time variables (default)
wake_time = [7, 0]   # 07:00
sleep_time = [22, 0] # 22:00

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        time.sleep(1)
    print("Connected to WiFi:", wlan.ifconfig())


def localtime_with_offset():
    t = time.time() + TIMEZONE_OFFSET * 3600
    return time.localtime(t)


# Sync with NTP
def sync_time():
    try:
        ntptime.settime()
        print("Time synced with NTP")
    except:
        print("Failed to sync time")

# Check if current time is between wake and sleep times
def is_awake():
    now = localtime_with_offset()
    current_minutes = now[3] * 60 + now[4]
    wake_minutes = wake_time[0] * 60 + wake_time[1]
    sleep_minutes = sleep_time[0] * 60 + sleep_time[1]

    if wake_minutes < sleep_minutes:
        return wake_minutes <= current_minutes < sleep_minutes
    else:
        # Spans midnight
        return current_minutes >= wake_minutes or current_minutes < sleep_minutes
    
def shut_server_down():

    url = "http://myserver.com/shutdown"
    headers = {
        "Authorization": "Bearer YOUR_AUTH_TOKEN",
        "Content-Type": "application/json"
    }
    try:
        response = urequests.post(url, headers=headers)
        if response.status_code == 200:
            print("Server shutdown request successful.")
        else:
            print("Failed to shut down server. Status:", response.status_code)
        response.close()
    except Exception as e:
        print("Error sending shutdown request:", e)

# Start web server
def start_webserver():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Listening on", addr)

    while True:
        cl, addr = s.accept()
        print("Client connected from", addr)
        request = cl.recv(1024).decode()

        if 'GET /set?' in request:
            try:
                params = request.split(' ')[1].split('?')[1]
                param_dict = {kv.split('=')[0]: kv.split('=')[1] for kv in params.split('&')}
                global wake_time, sleep_time
                wake_time = [int(param_dict['wh']), int(param_dict['wm'])]
                sleep_time = [int(param_dict['sh']), int(param_dict['sm'])]
            except Exception as e:
                print("Error parsing parameters:", e)
            # Redirect to main page
            cl.send('HTTP/1.1 302 Found\r\n')
            cl.send('Location: /\r\n')
            cl.send('Connection: close\r\n\r\n')
            cl.close()
            continue
        
        now = localtime_with_offset()

        # Build HTML response
        html = f"""<!DOCTYPE html>
<html>
    <head><title>Wake/Sleep Timer</title>
    <meta http-equiv="refresh" content="10"></head>
    <body>
        <h1>Set Wake and Sleep Times</h1>
        <form action="/set">
            Wake Time: <input type="number" name="wh" min="0" max="23" value="{wake_time[0]}">:
            <input type="number" name="wm" min="0" max="59" value="{wake_time[1]}"><br><br>
            Sleep Time: <input type="number" name="sh" min="0" max="23" value="{sleep_time[0]}">:
            <input type="number" name="sm" min="0" max="59" value="{sleep_time[1]}"><br><br>
            <input type="submit" value="Set Times">
        </form>
        <p>Current Wake Time: {wake_time[0]:02d}:{wake_time[1]:02d}</p>
        <p>Current Sleep Time: {sleep_time[0]:02d}:{sleep_time[1]:02d}</p>
        <p>Current Time: {now[3]:02d}:{now[4]:02d}</p>
        <p>Device is currently {'ON' if is_ON else 'OFF'}</p>
    </body>
</html>"""

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(html)
        cl.close()

# Main execution
connect_wifi()
sync_time()

# Start web server in background (optional)
import _thread
_thread.start_new_thread(start_webserver, ())

# Main LED loop
while True:
    if is_awake():
        if not is_ON:
            led.on()
            is_ON = True
            time.sleep(1)
            led.off()
    else:
        if is_ON:
            if shut_server_down():
                print("Shutting down server...")
                led.on()
                time.sleep(30)
                led.off()
            led.on()
            is_ON = False
            time.sleep(1)
            led.off()
    time.sleep(CHECK_INTERVAL)

import network
import socket
import time
import ntptime
from machine import Pin
from time import localtime
import urequests


from machine import Pin,SPI
import framebuf
import time

DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9


# This class is from Pico_OLED_code.7z\Pico-code\Python\Pico-OLED-1.3\Pico-OLED-1.3(spi).py from https://files.waveshare.com/upload/5/5a/Pico_code.7z
class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 64
        
        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,2000_000)
        self.spi = SPI(1,20000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self.init_display()
        
        self.white =   0xffff
        self.balck =   0x0000
        
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize dispaly"""  
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)
        
        self.write_cmd(0xAE)#turn off OLED display

        self.write_cmd(0x00)   #set lower column address
        self.write_cmd(0x10)   #set higher column address 

        self.write_cmd(0xB0)   #set page address 
      
        self.write_cmd(0xdc)    #et display start line 
        self.write_cmd(0x00) 
        self.write_cmd(0x81)    #contract control 
        self.write_cmd(0x6f)    #128
        self.write_cmd(0x21)    # Set Memory addressing mode (0x20/0x21) #
    
        self.write_cmd(0xa0)    #set segment remap 
        self.write_cmd(0xc0)    #Com scan direction
        self.write_cmd(0xa4)   #Disable Entire Display On (0xA4/0xA5) 

        self.write_cmd(0xa6)    #normal / reverse
        self.write_cmd(0xa8)    #multiplex ratio 
        self.write_cmd(0x3f)    #duty = 1/64
  
        self.write_cmd(0xd3)    #set display offset 
        self.write_cmd(0x60)

        self.write_cmd(0xd5)    #set osc division 
        self.write_cmd(0x41)
    
        self.write_cmd(0xd9)    #set pre-charge period
        self.write_cmd(0x22)   

        self.write_cmd(0xdb)    #set vcomh 
        self.write_cmd(0x35)  
    
        self.write_cmd(0xad)    #set charge pump enable 
        self.write_cmd(0x8a)    #Set DC-DC enable (a=0:disable; a=1:enable)
        self.write_cmd(0XAF)
    def show(self):
        self.write_cmd(0xb0)
        for page in range(0,64):
            self.column = 63 - page              
            self.write_cmd(0x00 + (self.column & 0x0f))
            self.write_cmd(0x10 + (self.column >> 4))
            for num in range(0,16):
                self.write_data(self.buffer[page*16+num])
        


class Server():
    def __init__(self, pin):
        self.pin = pin
        self.is_ON = False
        self.wake_time = [7, 0]
        self.sleep_time = [22, 0]
        self.check_interval = 60  # seconds
        self.timezone_offset = 1
        self.endpoint = "http://myserver.com/shutdown"
    
    # Getter for wake_time
    def get_wake_time(self):
        return self.wake_time
    # Setter for wake_time
    def set_wake_time(self, hour, minute):
        self.wake_time = [hour, minute]
    # Getter for sleep_time
    def get_sleep_time(self):
        return self.sleep_time
    # Setter for sleep_time
    def set_sleep_time(self, hour, minute):
        self.sleep_time = [hour, minute]
    # Getter for check_interval
    def get_check_interval(self):
        return self.check_interval
    
    def is_awake(self, time):
        # Check if current time is between wake and sleep times
        current_minutes = time[3] * 60 + time[4]
        wake_minutes = self.wake_time[0] * 60 + self.wake_time[1]
        sleep_minutes = self.sleep_time[0] * 60 + self.sleep_time[1]

        if wake_minutes < sleep_minutes:
            return wake_minutes <= current_minutes < sleep_minutes
        else:
            # Spans midnight
            return current_minutes >= wake_minutes or current_minutes < sleep_minutes
        
    def shut_server_down(self):
        # Send shutdown request to the server
        headers = {
        "Authorization": "Bearer YOUR_AUTH_TOKEN",
        "Content-Type": "application/json"
        }
        try:
            response = urequests.post(self.endpoint, headers=headers)
            if response.status_code == 200:
                print("Server shutdown request successful.")
            else:
                print("Failed to shut down server. Status:", response.status_code)
            response.close()
        except Exception as e:
            print("Error sending shutdown request:", e)
        
    def update(self, time2):
        # Update the server state based on the current time
        if self.is_awake(time2):
            if not self.is_ON:
                self.pin.on()
                self.is_ON = True
                time.sleep(1)
                self.pin.off()
        else:
            if self.is_ON:
                if self.shut_server_down():
                    print("Shutting down server...")
                    self.pin.on()
                    time.sleep(30)
                    self.pin.off()
                self.pin.on()
                self.is_ON = False
                time.sleep(1)
                self.pin.off()
                
                
class WebServer():
    def __init__(self, ssid, password, server_manager):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.connect(self.ssid, self.password)
        while not self.wlan.isconnected():
            time.sleep(1)
        print("Connected to WiFi:", self.wlan.ifconfig())
        self.addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        self.server_man = server_manager
        

        
    def start(self):
        s = socket.socket()
        s.bind(self.addr)
        s.listen(1)
        print("Listening on", self.addr)

        while True:
            cl, addr = s.accept()
            print("Client connected from", addr)
            request = cl.recv(1024).decode()

            if 'GET /set?' in request:
                self.handle_set_request(cl, request)
                continue
            
            elif 'GET /server?' in request:
                self.handle_server_request(cl, request)
                continue
            
            elif 'GET /add_server_page' in request:
                self.handle_add_server_page_request(cl)
                continue
            
            elif 'GET /add_server' in request:
                self.handle_add_server_request(cl, request)
                continue
            
            elif 'GET /' in request:
                self.handle_index_request(cl)
                continue
        
            
    def handle_set_request(self, cl, request):
        try:
            # Params are id of the server
            # and wake/sleep times
            params = request.split(' ')[1].split('?')[1]
            param_dict = {kv.split('=')[0]: kv.split('=')[1] for kv in params.split('&')}
            try:
                id = int(param_dict['id'])
                self.server_man.get_server(id)
            except Exception as e:
                cl.send('HTTP/1.1 400 Bad Request\r\n')
                cl.send('Content-type: text/html\r\n\r\n')
                cl.send('<html><body><h1>Bad Request</h1></body></html>')
                cl.close()
                return
            self.server_man.get_server(id).set_wake_time(int(param_dict['wh']), int(param_dict['wm']))
            self.server_man.get_server(id).set_sleep_time(int(param_dict['sh']), int(param_dict['sm']))
        except Exception as e:
            print("Error parsing parameters:", e)
        # Redirect to main page
        cl.send('HTTP/1.1 302 Found\r\n')
        cl.send('Location: /\r\n')
        cl.send('Connection: close\r\n\r\n')
        cl.close()
    
    
    def handle_server_request(self, cl, request):
        # Params are id of the server
        params = request.split(' ')[1].split('?')[1]
        param_dict = {kv.split('=')[0]: kv.split('=')[1] for kv in params.split('&')}
        try:
            id = int(param_dict['id'])
            self.server_man.get_server(id)
        except Exception as e:
            cl.send('HTTP/1.1 400 Bad Request\r\n')
            cl.send('Content-type: text/html\r\n\r\n')
            cl.send('<html><body><h1>Bad Request</h1></body></html>')
            cl.close()
            return
        
        now = localtime_with_offset()

        # Build HTML response
        now = localtime_with_offset()

        # Build HTML response
        html = f"""<!DOCTYPE html>
<html>
    <head><title>Wake/Sleep Timer</title>
    <meta http-equiv="refresh" content="10"></head>
    <body>
        <h1>Set Wake and Sleep Times</h1>
        <form action="/set">
            <input type="hidden" name="id" value="{id}">
            Wake Time: <input type="number" name="wh" min="0" max="23" value="{self.server_man.get_server(id).get_wake_time()[0]}">:
            <input type="number" name="wm" min="0" max="59" value="{self.server_man.get_server(id).get_wake_time()[1]}"><br><br>
            Sleep Time: <input type="number" name="sh" min="0" max="23" value="{self.server_man.get_server(id).get_sleep_time()[0]}">:
            <input type="number" name="sm" min="0" max="59" value="{self.server_man.get_server(id).get_sleep_time()[1]}"><br><br>
            <input type="submit" value="Set Times">
        </form>
        <p>Current Wake Time: {self.server_man.get_server(id).get_wake_time()[0]:02d}:{self.server_man.get_server(id).get_wake_time()[1]:02d}</p>
        <p>Current Sleep Time: {self.server_man.get_server(id).get_sleep_time()[0]:02d}:{self.server_man.get_server(id).get_sleep_time()[1]:02d}</p>
        <p>Current Time: {now[3]:02d}:{now[4]:02d}</p>
        <p>Device is currently {'ON' if self.server_man.get_server(id).is_ON else 'OFF'}</p>
        <p>Server ID: {id}</p>
        <br><br>
        <a href="/">Back to Main Page</a>
    </body>
</html>"""

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(html)
        cl.close()
    
    
    def handle_index_request(self, cl):
        # Build HTML response
        html = """<!DOCTYPE html>
<html>
    <head><title>Wake/Sleep Timer</title>
    <meta http-equiv="refresh" content="10"></head>
    <body>
        """
        for i, server in enumerate(self.server_man.get_servers()):
            html += f"""
            <h1>Server {i}</h1>
            <p>Wake Time: {server.get_wake_time()[0]:02d}:{server.get_wake_time()[1]:02d}</p>
            <p>Sleep Time: {server.get_sleep_time()[0]:02d}:{server.get_sleep_time()[1]:02d}</p>
            <p>Device is currently {'ON' if server.is_ON else 'OFF'}</p>
            <a href="/server?id={i}">Configure Server {i}</a><br><br>
            """
        
        html += """
        <h1>Add Server</h1>
        <a href="/add_server_page">Add Server</a><br><br>
        """
        
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(html)
        cl.close()
    
    def handle_add_server_page_request(self, cl):
        html = """<!DOCTYPE html>
<html>

    <head><title>Add Server</title></head>
    <body>
        <h1>Add Server</h1>
        <form action="/add_server">

            <label for="pin">Pin Number:</label>
            <input type="number" id="pin" name="pin" min="0" max="40" required><br><br>
            <input type="submit" value="Add Server">
        </form>
        <br><br>
        <a href="/">Back to Main Page</a>
    </body>
</html>"""
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(html)
        cl.close()
        
    def handle_add_server_request(self, cl, request):
        # Parse the request to get the pin number
        try:
            params = request.split(' ')[1].split('?')[1]
            param_dict = {kv.split('=')[0]: kv.split('=')[1] for kv in params.split('&')}
            pin_number = int(param_dict['pin'])
            new_server = Server(Pin(pin_number, Pin.OUT))
            self.server_man.add_server(new_server)
            print(f"Server added on pin {pin_number}")
        except Exception as e:
            print("Error parsing parameters:", e)
        # Redirect to main page
        cl.send('HTTP/1.1 302 Found\r\n')
        cl.send('Location: /\r\n')
        cl.send('Connection: close\r\n\r\n')
        cl.close()
                

class Server_Manager():
    def __init__(self):
        self.servers = []
    
    def add_server(self, server):
        self.servers.append(server)
    
    def get_server(self, id):
        return self.servers[id]
    
    def get_servers(self):
        return self.servers
    
    def get_on_servers(self):
        return [server for server in self.servers if server.is_ON]
    
class OLED_Manager():
    def __init__(self, server_man, web_server):
        self.oled = OLED_1inch3()
        self.server_man = server_man
        self.web_server = web_server
        self.time_row = None
        self.server_count_row = None
        self.page = -1
        
    def go_home_timer(self):
        while True:
            if self.page != -1:
                self.show_home()
                break
            time.sleep(5)
        
    def show_home(self):
        self.page = -1
        self.oled.fill(0x0000)
        self.oled.text("Wake/Sleep Timer", 0, 0, self.oled.white)
        self.oled.text("IP Address:", 0, 10, self.oled.white)
        self.oled.text(f"{self.web_server.wlan.ifconfig()[0]}", 8, 20, self.oled.white)
        self.oled.text("Current Time:", 0, 30, self.oled.white)
        self.oled.text(f"{localtime_with_offset()[3]:02d}:{localtime_with_offset()[4]:02d}", 8, 40, self.oled.white)
        self.time_row = 40
        self.oled.text(f"{len(self.server_man.get_servers())} servers ({len(self.server_man.get_on_servers())} on)", 0, 50, self.oled.white)
        self.server_count_row = 50
        self.oled.show()
    
    def update_time(self, time):
        if self.time_row is not None:
            self.oled.fill_rect(0, self.time_row, 128, 8, self.oled.balck)
            self.oled.text(f"{time[3]:02d}:{time[4]:02d}", 8, self.time_row, self.oled.white)
            self.oled.show()
            
    def update_server_count(self):
        if self.server_count_row is not None:
            self.oled.fill_rect(0, self.server_count_row, 128, 8, self.oled.balck)
            self.oled.text(f"{len(self.server_man.get_servers())} servers ({len(self.server_man.get_on_servers())} on)", 0, self.server_count_row, self.oled.white)
        
    def show_server_page(self, i):
        if i >= len(self.server_man.get_servers()):
            return 0
            
        self.time_row = None
        self.server_count_row = None
        
        server = self.server_man.get_server(i)
        self.page = i
        self.oled.fill(0x0000)
        pin_number = str(server.pin)[4:10]
        pin_number = pin_number.replace(",", "")
        
        self.oled.text(f"PIN: {pin_number}", 0, 0, self.oled.white)
        self.oled.text(f"Times:", 0, 10, self.oled.white)
        self.oled.text(f"{server.get_wake_time()[0]:02d}:{server.get_wake_time()[1]:02d} - {server.get_sleep_time()[0]:02d}:{server.get_sleep_time()[1]:02d}", 8, 20, self.oled.white)
        self.oled.text(f"Device is {'ON' if server.is_ON else 'OFF'}", 0, 30, self.oled.white)
        
        self.oled.text(f"{self.page + 1} of {len(self.server_man.get_servers())}", 0, 50, self.oled.white)
        
        self.oled.show()
        
        return 1
        
    def increment_page(self):
        if self.page == -1:
            self.show_server_page(0)
            return
        if self.show_server_page(self.page + 1) == 0:
            self.show_home()
            

class Button_Handler():
    def __init__(self, oled_manager):
        self.keyA = Pin(15,Pin.IN,Pin.PULL_UP)
        self.keyB = Pin(17,Pin.IN,Pin.PULL_UP)
        self.oled_manager = oled_manager
    
        self.keyA.irq(trigger=Pin.IRQ_FALLING, handler=self.keyA_callback)
        self.keyB.irq(trigger=Pin.IRQ_FALLING, handler=self.keyB_callback)
    
    def keyA_callback(self, pin):
        # Button A pressed
        print("Button A pressed")
        self.oled_manager.increment_page()
        
    def keyB_callback(self, pin):
        pass


# Setup WiFi connection
SSID = "Your_SSID"
PASSWORD = 'Your_PASSWORD'

TIMEZONE_OFFSET = 1

CHECK_INTERVAL = 3  # seconds



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




# Start web server in background (optional)
import _thread
server_man = Server_Manager()
webserver = WebServer(SSID, PASSWORD, server_man)
# led = Pin('LED', Pin.OUT)
# server = Server(led)
# server_man.add_server(server)
_thread.start_new_thread(webserver.start, ())

sync_time()


# Initialize OLED display
oled_manager = OLED_Manager(server_man, webserver)
oled_manager.show_home()

button_handler = Button_Handler(oled_manager)

# Main LED loop
while True:
    # Get current time
    now = localtime_with_offset()
    oled_manager.update_time(now)
    oled_manager.update_server_count()
    
    # Update server state
    for server in server_man.get_servers():
        server.update(now)
    
    
    # Sleep for the check interval
    time.sleep(CHECK_INTERVAL)

from pythonosc.udp_client import SimpleUDPClient
import time

ip = "192.168.20.226"
#ip = "192.168.20.238"
port = 10023
server_port = 10023  # Port your client listens on

def msg_handler(address, *args):
    """Handler function that receives messages from the server"""
    print(f"Received message at {address}: {args}")


def main():   



    #create client
    client = SimpleUDPClient(ip, port)
    
    #tell the x32 that we exist
    client.send_message("/xinfo", "")
    #sending a command to set fader level to 0.7
    # client.send_message("/ch/09/mix/fader", 0.7)    
    # time.sleep(1)
    # client.send_message("/ch/09/mix/fader", 0.0)


if __name__ == "__main__":
    main()  


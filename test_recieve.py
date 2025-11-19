
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

import xair_api
import threading
import time

ip = "192.168.20.226"
port = 10023
server_port = 10023  # Port your client listens on
kind_id = "X32"



def main():
    with xair_api.connect(kind_id, ip=ip) as mixer:
        # mixer.strip[8].config.name = 'Ch09'
        # mixer.strip[8].mix.on = True
        # time.sleep(0.05)
        # print(
        #     f'strip 09 ({mixer.strip[8].config.name}) on has been set to {mixer.strip[8].mix.on}'
        # )
        mixer.strip[8].mix.fader = -90
        print(mixer.strip[8].mix.fader)






if __name__ == "__main__":
    main()
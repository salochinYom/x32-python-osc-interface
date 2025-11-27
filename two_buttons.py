#hack to import the DFRobot_VisualRotaryEncoder from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from DFRobot_VisualRotaryEncoder import *



def main():
    sensor1 = DFRobot_VisualRotaryEncoder(i2c_addr = 0x54, bus = 1, gain_coefficient=51)
    sensor2 = DFRobot_VisualRotaryEncoder(i2c_addr = 0x55, bus = 1, gain_coefficient=51)
    time.sleep(1)
    while True:
        #handle sensor button updates
        sensor1.handle_sensor()
        sensor2.handle_sensor()
        #print the button presses
        if sensor1.check_down_button_unhandled():
            print("Sensor 1 Button pressed!")
        if sensor2.check_down_button_unhandled():
            print("Sensor 2 Button pressed!")


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*
'''!
  @file  DFRobot_VisualRotaryEncoder.py
  @brief  Define the infrastructure of DFRobot_VisualRotaryEncoder class.
  @copyright  Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license  The MIT License (MIT)
  @author  [qsjhyy](yihuan.huang@dfrobot.com)
  @version  V1.0
  @date  2021-09-15
  @url  https://github.com/DFRobot/DFRobot_VisualRotaryEncoder
'''
import sys
import time
#import smbus
#from smbus3 import SMBus as smbus
import smbus3 as smbus
import logging
from ctypes import *

logger = logging.getLogger()
#logger.setLevel(logging.INFO)   # Display all print information
logger.setLevel(logging.FATAL)   # If you don’t want to display too many prints, only print errors, please use this option
ph = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - [%(filename)s %(funcName)s]:%(lineno)d - %(levelname)s: %(message)s")
ph.setFormatter(formatter) 
logger.addHandler(ph)

## default I2C communication address 
VISUAL_ROTARY_ENCODER_DEFAULT_I2C_ADDR = 0x54
## module PID (SEN0502)(The highest two of 16-bit data are used to determine SKU type: 00: SEN, 01: DFR, 10: TEL, the next 14 are numbers.)
VISUAL_ROTARY_ENCODER_PID              = 0x01F6

# VISUAL_ROTARY_ENCODER register address
## module PID memory register，default value is 0x01F6 (The highest two of 16-bit data are used to determine SKU type: 00: SEN, 01: DFR, 10: TEL, the next 14 are numbers.)
VISUAL_ROTARY_ENCODER_PID_MSB_REG     = 0x00
VISUAL_ROTARY_ENCODER_PID_LSB_REG     = 0x01
## module VID memory register，default value is 0x3343（for manufacturer DFRobot）
VISUAL_ROTARY_ENCODER_VID_MSB_REG     = 0x02
VISUAL_ROTARY_ENCODER_VID_LSB_REG     = 0x03
## memory register of firmware revision number：0x0100 represents V0.1.0.0
VISUAL_ROTARY_ENCODER_VERSION_MSB_REG = 0x04
VISUAL_ROTARY_ENCODER_VERSION_LSB_REG = 0x05
## memory register of module communication address，default value is 0x54，module device address (1~127)
VISUAL_ROTARY_ENCODER_ADDR_REG        = 0x07
## encoder count values，range 0-1023
VISUAL_ROTARY_ENCODER_COUNT_MSB_REG   = 0x08
VISUAL_ROTARY_ENCODER_COUNT_LSB_REG   = 0x09
## encoder button status
VISUAL_ROTARY_ENCODER_KEY_STATUS_REG  = 0x0A
## encoder incremental factor
VISUAL_ROTARY_ENCODER_GAIN_REG        = 0x0B

class DFRobot_VisualRotaryEncoder(object):
    '''!
      @brief define DFRobot_VisualRotaryEncoder as class
      @details to drive visual rotary encoder
    '''

    PID = 0
    VID = 0
    version = 0
    I2C_addr = 0
    #counts the number of button presses
    button_count = 0
    #counts the time since last button press
    button_time = 0
    #keeps track of last time since handle
    button_handle_time = 0
    #update interval time (s)
    button_handle_interval = 0.1
    #reset button time (downward timeout)
    button_down_time_reset = 2
    #keeps track of if there is a unhandled button press
    button_down_unhandled = False
    button_up_unhandled = False

    def __init__(self, i2c_addr=VISUAL_ROTARY_ENCODER_DEFAULT_I2C_ADDR, bus=1, gain_coefficient=25):
        '''!
          @brief Module init
          @param i2c_addr I2C communication address
          @param bus I2C communication bus
        '''
        '''initialize configuration parameters'''
        self._i2c_addr = i2c_addr
        self._i2c = smbus.SMBus(bus)
        self.set_gain_coefficient(gain_coefficient)

    def begin(self):
        '''!
          @brief Initialize sensor
          @return  return initialization status
          @retval True indicate initialization succeed
          @retval False indicate initialization failed
        '''
        ret = True
        chip_id = self._read_reg(VISUAL_ROTARY_ENCODER_PID_MSB_REG, 2)
        logger.info((chip_id[0] << 8) | chip_id[1])
        if VISUAL_ROTARY_ENCODER_PID != (chip_id[0] << 8) | chip_id[1]:
            ret = False
        return ret

    def read_basic_info(self):
        '''!
          @brief read the module basic information
          @n     retrieve basic information from the sensor and buffer it into a variable that stores information:
          @n     PID, VID, version, I2C_addr
        '''
        data = self._read_reg(VISUAL_ROTARY_ENCODER_PID_MSB_REG, 8)

        self.PID = (data[0] << 8) | data[1]   # PID
        self.VID = (data[2] << 8) | data[3]   # VID
        self.version = (data[4] << 8) | data[5]   # version
        self.I2C_addr = data[7]   # I2C addr

    def get_encoder_value(self):
        '''!
          @brief get the current encoder count
          @return return value range： 0-1023
        '''
        data = self._read_reg(VISUAL_ROTARY_ENCODER_COUNT_MSB_REG, 2)
        return (data[0] << 8) | data[1]

    def set_encoder_value(self, value):
        '''!
          @brief set the encoder count
          @param value range[0, 1023], the setting is invalid when out of range
        '''
        if ((0x0000 <= value) and (0x3FF >= value)):
            temp_buf = [(value & 0xFF00) >> 8, value & 0x00FF]
            self._write_reg(VISUAL_ROTARY_ENCODER_COUNT_MSB_REG, temp_buf)

    def get_gain_coefficient(self):
        '''!
          @brief get the current gain factor of the encoder, and the numerical accuracy of turning one step
          @n     accuracy range：1~51，the minimum is 1 (light up one LED about every 2.5 turns), the maximum is 51 (light up one LED every one step rotation)
          @return return value range： 1-51
        '''
        return self._read_reg(VISUAL_ROTARY_ENCODER_GAIN_REG, 1)[0]

    def set_gain_coefficient(self, gain_value):
        '''!
          @brief set the current gain factor of the encoder, and the numerical accuracy of turning one step
          @n     accuracy range：1~51，the minimum is 1 (light up one LED about every 2.5 turns), the maximum is 51 (light up one LED every one step rotation)
          @param gain_value range[1, 51], the setting is invalid when out of range
        '''
        if ((0x01 <= gain_value) and (0x33 >= gain_value)):
            self._write_reg(VISUAL_ROTARY_ENCODER_GAIN_REG, gain_value)
    def handle_sensor(self):
        '''!
          @brief handle the button press counting and timing
        '''
        if time.time() - self.button_handle_time > self.button_handle_interval:
          prev_count = self.button_count
          self.button_handle_time = time.time()

          if self.detect_button_change():
              self.button_count += 1
              self.button_time = time.time()
              #print("Button count:", self.button_count)
          #handle odd number of button presses when timeout occurs
          if time.time() - self.button_time > self.button_down_time_reset and self.button_count % 2 == 1:
              self.button_count = 0
              self.button_down_unhandled = False
              print("Button count reset due to timeout")

          #set unhandled flag if button count has changed
          if prev_count % 2 == 0 and self.button_count % 2 == 1 and not self.button_down_unhandled:
              self.button_down_unhandled = True
    
    def check_down_button_unhandled(self):
        '''!
          @brief check if there is an unhandled button press
          @return return true when there is an unhandled button press，otherwise, return false
        '''
        ret = self.button_down_unhandled
        if ret:
            self.button_down_unhandled = False
        return ret
    
    
    def detect_button_down(self):
        '''!
          @brief detect if the button is pressed
          @return return true when the button pressed，otherwise, return false
        '''
        return self.button_count % 2 == 1
    
    def detect_button_change(self):
        '''!
          @brief detect if the button status changed
          @return return true when the button status changed，otherwise, return false
        '''
        ret = False
        if(1 == self._read_reg(VISUAL_ROTARY_ENCODER_KEY_STATUS_REG, 1)[0]):
            self._write_reg(VISUAL_ROTARY_ENCODER_KEY_STATUS_REG, 0)
            ret = True
        return ret
    
    def encoder_as_float(self):
        '''!
          @brief gets encoder value as a float between 0.0 and 1.0`
          @return float value between 0.0 and 1.0
        '''
        return self.get_encoder_value() / 1023.0

    def _write_reg(self, reg, data):
        '''!
          @brief writes data to a register
          @param reg register address
          @param data written data
        '''
        if isinstance(data, int):
            data = [data]
            #logger.info(data)
        self._i2c.write_i2c_block_data(self._i2c_addr, reg, data)

    def _read_reg(self, reg, length):
        '''!
          @brief read the data from the register
          @param reg register address
          @param length read data length
        '''
        return self._i2c.read_i2c_block_data(self._i2c_addr, reg, length)

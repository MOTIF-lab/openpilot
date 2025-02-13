#!/usr/bin/env python3
import os
import time
import threading
import cereal.messaging as messaging
from openpilot.selfdrive.car.card import can_comm_callbacks, obd_callback
from openpilot.common.params import Params
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery
from openpilot.common.realtime import  Ratekeeper
from hexdump import hexdump

ECU_ADDR = 0x7e0

def make_isotp_query(service: int, pid:int):
  request_byte = bytearray(service)
  request_byte.append(pid)
  response_byte = bytearray(0x40 + pid)
  response_byte.append(pid)
  return request_byte, response_byte

class OBDCar:
  def __init__(self):
    self.ecu_addr = ECU_ADDR

    self.rk = Ratekeeper(10, print_delay_threshold=None)

    self.logcan = messaging.sub_sock('can')
    self.sendcan = messaging.pub_sock('sendcan')
    self.pm = messaging.PubMaster(['customReserved2'])

    self.can_transiver = can_comm_callbacks(self.logcan, self.sendcan)
    self.params = Params()
    self.set_obd_multiplexing = obd_callback(self.params)

    self.retry = 2
    self.can_bus_id = 0

    self.engineStatus = 0

    print('Init OBD query')
    self.params.put_bool("IsOnroad", False)
    time.sleep(0.2)  # thread is 10 Hz
    self.params.put_bool("IsOnroad", True)
    self.set_obd_multiplexing(True)

  def exec_query(self, query: IsoTpParallelQuery):
    for i in range(self.retry):
      self.set_obd_multiplexing(True)
      result = query.get_data(0.1)
      self.set_obd_multiplexing(False)
      if len(result) > 0:
        return result
    return None

  def query_engine_status(self):
    # req_bytes, res_bytes = make_isotp_query(
    #   0x01, # show current data
    #   0x03 # fuel system status
    # )
    for i in range(self.retry):
      query = IsoTpParallelQuery(
        self.can_transiver[1], self.can_transiver[0], self.can_bus_id,
        [0x7e4], [b'\x22\x01\x01'], [b''], debug=True
      )
      result = self.exec_query(query)
      if result == None:
        pass
      else:
        break

      # if result == None:
      #   self.engineStatus = 0
      # else:
      #   self.engineStatus = result

  def update(self):
    # self.query_engine_status()
    self.state_publish()

  def state_publish(self):
    obdState = messaging.new_message('customReserved2')
    obdState.customReserved2.ignitionObd = True
    obdState.customReserved2.speedObdValid = True
    obdState.customReserved2.speedObd = 0
    obdState.valid = True
    print(obdState)
    self.pm.send('customReserved2', obdState)

  def obd_thread(self):
    e = threading.Event()
    try:
      while True:
        self.update()
        self.rk.keep_time()
    except Exception as e:
      print(e)
    finally:
      e.set()


def main():
  obd_car = OBDCar()
  obd_car.obd_thread()

if __name__ == '__main__':
  main()
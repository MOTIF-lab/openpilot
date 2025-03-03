#!/usr/bin/env python3
import time
import argparse
import cereal.messaging as messaging
from cereal import car
from opendbc.car.fw_versions import get_fw_versions, match_fw_to_car
from opendbc.car.vin import get_vin
from openpilot.common.params import Params
from openpilot.selfdrive.car.card import can_comm_callbacks, obd_callback
from typing import Any
from opendbc.car.fw_query_definitions import STANDARD_VIN_ADDRS, StdQueries
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery
from opendbc.car import carlog, uds
from hexdump import hexdump

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Send OBD query')
  parser.add_argument('--bus', type=int, default=0)
  args = parser.parse_args()

  logcan = messaging.sub_sock('can')
  pandaStates_sock = messaging.sub_sock('pandaStates')
  sendcan = messaging.pub_sock('sendcan')
  can_recv, can_send = can_comm_callbacks(logcan, sendcan)

  # Set up params for pandad
  params = Params()
  params.remove("FirmwareQueryDone")
  params.put_bool("IsOnroad", False)
  time.sleep(0.2)  # thread is 10 Hz
  params.put_bool("IsOnroad", True)
  set_obd_multiplexing = obd_callback(params)
  set_obd_multiplexing(True)

  # query = IsoTpParallelQuery(
  #   can_send, can_recv, args.bus, [0x7e2],
  #   [b'\x09\x02', ],[b''],
  #   response_offset=0x08,
  #   functional_addrs=[],
  #   debug=True
  # )
  # result = query.get_data(1)
  # hexdump(result)

  # vin_rx_addr, vin_rx_bus, vin = get_vin(can_recv, can_send, (0,), debug=True)
  # print(f'RX: {hex(vin_rx_addr)}, BUS: {vin_rx_bus}, VIN: {vin}')
  # print()

  for i in range(3):
    set_obd_multiplexing(True)
    query = IsoTpParallelQuery(
      can_send, can_recv, 0, [0x7E4],
      [bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER, 0x01, 0x01])],
      [bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER + 0x40, 0x01, 0x01])],
      functional_addrs=[],
      debug=True
    )
    result = query.get_data(0.1)
    set_obd_multiplexing(False)
    if len(result) > 0:
      for dat in result.values():
        hexdump(dat)
      break
    time.sleep(0.2)



#!/usr/bin/env python3
import os
import time
import threading

import cereal.messaging as messaging
from cereal import car, log

from panda import ALTERNATIVE_EXPERIENCE

from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, Priority, Ratekeeper
from openpilot.common.swaglog import cloudlog, ForwardingHandler

from opendbc.car import DT_CTRL, carlog, structs
from opendbc.car.car_helpers import get_car, get_radar_interface
from openpilot.selfdrive.pandad import can_capnp_to_list
from openpilot.selfdrive.car.cruise import VCruiseHelper
from openpilot.selfdrive.car.car_specific import MockCarState

REPLAY = "REPLAY" in os.environ
EventName = log.OnroadEvent.EventName

# forward
carlog.addHandler(ForwardingHandler(cloudlog))

class Car:
  CI: car.CarInterfaceBase
  RI: car.RadarInterfaceBase
  CP: car.CarParams

  def __init__(self, CI=None, RI=None) -> None:
    # Initialize messaging sockets
    self.can_sock = messaging.sub_sock('can', timeout=20)
    self.sm = messaging.SubMaster(['pandaStates', 'carControl', 'onroadEvents'])
    self.pm = messaging.PubMaster(['sendcan', 'carState', 'carParams', 'carOutput', 'liveTracks'])

    self.can_rcv_cum_timeout_counter = 0
    self.CC_prev = car.CarControl.new_message()
    self.initialized_prev = False
    self.last_actuators_output = structs.CarControl.Actuators()
    self.params = Params()

    # Skip waiting for CAN messages by bypassing the CAN wait loop
    # Remove the blocking loop that waits for CAN packets to initialize
    print("Skipping CAN message wait and forcing mock mode...")

    # Initialize the car interface in mock mode if no real interface is provided
    if CI is None:
      # Force mock mode by setting carName to "mock"
      experimental_long_allowed = self.params.get_bool("ExperimentalLongitudinalEnabled")
      num_pandas = 1  # Set to 1, as no real Panda devices are connected
      cached_params = None

      # Initialize a mock Car Interface and Radar Interface
      self.CI = get_car(lambda: [], lambda _: None, lambda _: None, experimental_long_allowed, num_pandas, cached_params)
      self.RI = get_radar_interface(self.CI.CP)
      self.CP = self.CI.CP

      # Set the car to "mock" mode for simulated operation
      self.CP.carName = "mock"
      self.params.put_bool("FirmwareQueryDone", True)
    else:
      self.CI, self.CP = CI, CI.CP
      self.RI = RI

    # Configure alternative experiences based on parameters
    disengage_on_accelerator = self.params.get_bool("DisengageOnAccelerator")
    self.CP.alternativeExperience = 0
    if not disengage_on_accelerator:
      self.CP.alternativeExperience |= ALTERNATIVE_EXPERIENCE.DISABLE_DISENGAGE_ON_GAS

    # Toggle OpenPilot on-road mode based on params
    self.params.put_bool("OpenpilotEnabledToggle", True)
    openpilot_enabled_toggle = True

    # Check if the controller is available
    controller_available = self.CI.CC is not None and openpilot_enabled_toggle and not self.CP.dashcamOnly
    self.CP.passive = not controller_available or self.CP.dashcamOnly

    if self.CP.passive:
      # Ensure no safety outputs if passive mode is enabled
      safety_config = structs.CarParams.SafetyConfig()
      safety_config.safetyModel = structs.CarParams.SafetyModel.noOutput
      self.CP.safetyConfigs = [safety_config]

    # Initialize mock car state and cruise helper
    self.mock_carstate = MockCarState()
    self.v_cruise_helper = VCruiseHelper(self.CP)
    self.is_metric = self.params.get_bool("IsMetric")
    self.experimental_mode = self.params.get_bool("ExperimentalMode")
    self.rk = Ratekeeper(100, print_delay_threshold=None)

  def state_update(self) -> tuple[car.CarState, structs.RadarDataT | None]:
    """Update car state using mock data if in mock mode"""
    if self.CP.carName == 'mock':
      # Update using mock car state if in mock mode
      CS = self.mock_carstate.update(self.CI.update([]))
    else:
      can_strs = messaging.drain_sock_raw(self.can_sock, wait_for_one=True)
      can_list = can_capnp_to_list(can_strs)
      CS = self.CI.update(can_list)

    # Radar data (RD) is not required for mock mode
    RD = None
    self.sm.update(0)
    return CS, RD

  def state_publish(self, CS: car.CarState, RD: structs.RadarDataT | None):
    """Publish car state and parameters for logging and vision-based processes"""

    # Publish carParams periodically
    if self.sm.frame % int(50. / DT_CTRL) == 0:
      cp_send = messaging.new_message('carParams')
      cp_send.valid = True
      cp_send.carParams = self.CP
      self.pm.send('carParams', cp_send)

    # Publish car state to activate logging and vision processes
    cs_send = messaging.new_message('carState')
    cs_send.valid = CS.canValid
    cs_send.carState = CS
    cs_send.carState.canErrorCounter = self.can_rcv_cum_timeout_counter
    cs_send.carState.cumLagMs = -self.rk.remaining * 1000.
    self.pm.send('carState', cs_send)

  def step(self):
    """Main loop for updating car state and controls"""
    CS, RD = self.state_update()
    self.state_publish(CS, RD)

  def params_thread(self, evt):
    """Thread for updating parameters periodically"""
    while not evt.is_set():
      self.is_metric = self.params.get_bool("IsMetric")
      self.experimental_mode = self.params.get_bool("ExperimentalMode") and self.CP.openpilotLongitudinalControl
      time.sleep(0.1)

  def card_thread(self):
    """Main thread that runs the step loop to simulate on-road mode"""
    e = threading.Event()
    t = threading.Thread(target=self.params_thread, args=(e,))
    try:
      t.start()
      while True:
        self.step()
        self.rk.monitor_time()
    finally:
      e.set()
      t.join()

def main():
  config_realtime_process(4, Priority.CTRL_HIGH)
  car = Car()
  car.card_thread()

if __name__ == "__main__":
  main()

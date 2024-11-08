#!/usr/bin/env python3
import signal
import threading
import functools
import time

from collections import namedtuple
from enum import Enum
from typing import Any
from multiprocessing import Process, Queue, Value
from abc import ABC, abstractmethod
import cereal.messaging as messaging

from openpilot.tools.sim.lib.simulated_car import SimulatedCar
from openpilot.selfdrive.test.helpers import set_params_enabled
from openpilot.common.realtime import Ratekeeper
from openpilot.common.params import Params
from openpilot.tools.sim.lib.common import SimulatorState

from tools.sim.lib.common import vec3

file_launch = False

def rk_loop(function, hz, exit_event: threading.Event):
  rk = Ratekeeper(hz, None)
  while not exit_event.is_set():
    function()
    rk.keep_time()

class SimulatedCarCan:

  def __init__(self):
    set_params_enabled()
    self.params = Params()
    self.rk = Ratekeeper(100, None)

    self._keep_alive = True
    signal.signal(signal.SIGTERM, self._on_shutdown)
    self._exit = threading.Event()
    self._exit_event = threading.Event()

    self.simulator_state = SimulatorState()
    self.simulator_state.ignition = False
    self.started = Value('i', False)

    self.sm = messaging.SubMaster(['gpsLocation', 'customReserved0'])

    self.test_run = False

  def _on_shutdown(self, signal, frame):
    self.shutdown()

  def shutdown(self):
    self._keep_alive = False

  def bridge_keep_alive(self, q: Queue, retries: int):
    try:
      self._run(q)
    finally:
      self.close("bridge terminated")

  def close(self, reason):
    self.started.value = False
    self._exit_event.set()

  def run(self, queue, retries=-1):
    bridge_p = Process(name="bridge", target=self.bridge_keep_alive, args=(queue, retries))
    bridge_p.start()
    return bridge_p

  def print_status(self):
    print(
    f"""
State:
Ignition: {self.simulator_state.ignition} Engaged: {self.simulator_state.is_engaged}
    """)

  def _run(self, q: Queue):

    self.simulated_car = SimulatedCar()

    self.simulated_car_thread = threading.Thread(target=rk_loop, args=(functools.partial(self.simulated_car.update, self.simulator_state),
                                                                        100, self._exit_event))
    self.simulated_car_thread.start()

    while self._keep_alive:

      self.simulator_state.cruise_button = 0
      self.simulator_state.left_blinker = False
      self.simulator_state.right_blinker = False

      throttle_manual = steer_manual = brake_manual = 0.

      self.sm.update(0)
      if self.sm.updated["gpsLocation"]:
        msg = self.sm['gpsLocation']
        if msg.hasFix:
          self.simulator_state.speed = msg.speed

      if self.sm.updated['customReserved0']:
        msg = self.sm['customReserved0']
        self.simulator_state.ignition = msg.dashcamEnable

      self.simulator_state.user_brake = brake_manual
      self.simulator_state.user_gas = throttle_manual
      self.simulator_state.user_torque = steer_manual * -10000
      self.simulator_state.steering_angle = 0

      steer_manual = steer_manual * -40

      # Update openpilot on current sensor state
      self.simulated_car.sm.update(0)
      self.simulator_state.is_engaged = self.simulated_car.sm['selfdriveState'].active

      # don't print during test, so no print/IO Block between OP and metadrive processes
      if not self.test_run and self.rk.frame % 25 == 0 and file_launch:
        self.print_status()

      self.started.value = True

      self.rk.keep_time()

def main():
  queue: Any = Queue()

  carCan = SimulatedCarCan()
  carCan.run(queue)

if __name__ == '__main__':
  file_launch = True
  main()

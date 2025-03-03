import traceback
import cereal.messaging as messaging

from opendbc.can.packer import CANPacker
from opendbc.can.parser import CANParser
from opendbc.car.honda.values import HondaSafetyFlags
from openpilot.common.params import Params
from openpilot.selfdrive.pandad.pandad_api_impl import can_list_to_can_capnp
from openpilot.tools.sim.lib.common import SimulatorState


class SimulatedCar:
  """Simulates a honda civic 2022 (panda state + can messages) to OpenPilot"""

  def __init__(self):
    self.pm = messaging.PubMaster(['pandaStates'])
    self.sm = messaging.SubMaster(['carControl', 'controlsState', 'carParams', 'selfdriveState'])
    self.idx = 0
    self.params = Params()
    self.obd_multiplexing = True

  def send_can_messages(self, simulator_state: SimulatorState):
    if not simulator_state.valid:
      print("sim not valid, refuse to send can")
      return

  def send_panda_state(self, simulator_state):
    self.sm.update(0)

    if self.params.get_bool("ObdMultiplexingEnabled") != self.obd_multiplexing:
      self.obd_multiplexing = not self.obd_multiplexing
      self.params.put_bool("ObdMultiplexingChanged", True)

    dat = messaging.new_message('pandaStates', 1)
    dat.valid = True
    dat.pandaStates[0] = {
      'ignitionLine': simulator_state.ignition,
      'pandaType': "blackPanda",
      'controlsAllowed': True,
      'safetyModel': 'elm327',
      'alternativeExperience': self.sm["carParams"].alternativeExperience,
      'safetyParam': 0,
    }
    self.pm.send('pandaStates', dat)

  def update(self, simulator_state: SimulatorState):
    try:
      simulator_state.valid = True
      self.send_can_messages(simulator_state)

      if self.idx % 50 == 0: # only send panda states at 2hz
        self.send_panda_state(simulator_state)

      self.idx += 1
    except Exception:
      traceback.print_exc()
      raise

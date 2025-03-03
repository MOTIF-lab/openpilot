#!/usr/bin/env python3
import os
import time
import threading

import cereal.messaging as messaging
from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper

class MockSelfdriveD:
  def __init__(self):
    # Setup sockets
    self.pm = messaging.PubMaster(['selfdriveState', 'onroadEvents'])

  def update(self, frame):
    ss_msg = messaging.new_message('selfdriveState')
    ss_msg.valid = True
    ss = ss_msg.selfdriveState
    ss.enabled = False
    ss.active = False
    ss.state = 0
    ss.engageable = False
    ss.experimentalMode = False
    ss.personality = 1

    ss.alertText1 = ''
    ss.alertText2 = ''
    ss.alertSize = 0
    ss.alertStatus = 0
    ss.alertType = ''
    ss.alertSound = 0
    ss.alertHudVisual = 0

    self.pm.send('selfdriveState', ss_msg)

  def run(self):
    self.rk = Ratekeeper(100, print_delay_threshold=None)

    while True:
      frame = self.rk.frame
      self.update(frame)
      self.rk.keep_time()

def main():
  mock_selfdrived = MockSelfdriveD()
  mock_selfdrived.run()

if __name__ == "__main__":
  main()
#!/usr/bin/env python3
import sys
import time
import signal
import serial
import struct
import requests
import urllib.parse
from datetime import datetime, UTC
import os
import glob

from cereal import messaging
from openpilot.common.time_helpers import system_time_valid
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.system.hardware import PC, TICI
from openpilot.common.gpio import gpio_init, gpio_set
from openpilot.system.hardware.tici.pins import GPIO

TICI_UBLOX_TTY = "/dev/ttyHS0"
UBLOX_USB_DID = '1-1'

UBLOX_ACK = b"\xb5\x62\x05\x01\x02\x00"
UBLOX_NACK = b"\xb5\x62\x05\x00\x02\x00"
UBLOX_SOS_ACK = b"\xb5\x62\x09\x14\x08\x00\x02\x00\x00\x00\x01\x00\x00\x00"
UBLOX_SOS_NACK = b"\xb5\x62\x09\x14\x08\x00\x02\x00\x00\x00\x00\x00\x00\x00"
UBLOX_BACKUP_RESTORE_MSG = b"\xb5\x62\x09\x14\x08\x00\x03"
UBLOX_ASSIST_ACK = b"\xb5\x62\x13\x60\x08\x00"

def set_power(enabled: bool) -> None:
  gpio_init(GPIO.UBLOX_SAFEBOOT_N, True)
  gpio_init(GPIO.GNSS_PWR_EN, True)
  gpio_init(GPIO.UBLOX_RST_N, True)

  gpio_set(GPIO.UBLOX_SAFEBOOT_N, True)
  gpio_set(GPIO.GNSS_PWR_EN, enabled)
  gpio_set(GPIO.UBLOX_RST_N, enabled)

def get_ublox_usb_did() -> str:
  cdc_acm = glob.glob("/sys/bus/usb/drivers/cdc_acm/*/")
  if len(cdc_acm) == 0:
    cloudlog.error("No cdc_acm driver found")
    return None
  for device_path in cdc_acm:
    # check if tty directory exists
    if not os.path.exists(os.path.join(device_path, "tty")):
      continue
    with open(os.path.join(device_path, "uevent"), "r") as f:
      uevent = f.read()
      if "PRODUCT=1546/1a8" in uevent:
        # found ublox device
        usb_did = device_path.split("/")[-2]
        cloudlog.info(f"Found ublox USB device with did: {usb_did}")
        return usb_did
  cloudlog.error("No ublox USB device found")
  return None

def get_ublox_tty(usb_did) -> str:
  try:
    tty = glob.glob(f"/sys/bus/usb/devices/{usb_did}/tty/*")[0]
    tty = tty.split("/")[-1]  # get the tty name
    cloudlog.info(f"Using ublox tty: {tty}")
    return f"/dev/{tty}"
  except IndexError:
    cloudlog.error(f"Failed to find ublox tty for usb did: {usb_did}")
    return None


def add_ubx_checksum(msg: bytes) -> bytes:
  A = B = 0
  for b in msg[2:]:
    A = (A + b) % 256
    B = (B + A) % 256
  return msg + bytes([A, B])

def get_assistnow_messages(token: bytes) -> list[bytes]:
  # make request
  # TODO: implement adding the last known location
  r = requests.get("https://online-live2.services.u-blox.com/GetOnlineData.ashx", params=urllib.parse.urlencode({
    'token': token,
    'gnss': 'gps,glo',
    'datatype': 'eph,alm,aux',
  }, safe=':,'), timeout=5)
  assert r.status_code == 200, "Got invalid status code"
  dat = r.content

  # split up messages
  msgs = []
  while len(dat) > 0:
    assert dat[:2] == b"\xB5\x62"
    msg_len = 6 + (dat[5] << 8 | dat[4]) + 2
    msgs.append(dat[:msg_len])
    dat = dat[msg_len:]
  return msgs


class TTYPigeon:
  def __init__(self, tty_port):
    self.tty = serial.VTIMESerial(tty_port, baudrate=9600, timeout=0)

  def send(self, dat: bytes) -> None:
    self.tty.write(dat)

  def receive(self) -> bytes:
    dat = b''
    while len(dat) < 0x1000:
      d = self.tty.read(0x40)
      dat += d
      if len(d) == 0:
        break
    return dat

  def set_baud(self, baud: int) -> None:
    self.tty.baudrate = baud

  def wait_for_ack(self, ack: bytes = UBLOX_ACK, nack: bytes = UBLOX_NACK, timeout: float = 0.5) -> bool:
    dat = b''
    st = time.monotonic()
    while True:
      dat += self.receive()
      if ack in dat:
        cloudlog.debug("Received ACK from ublox")
        return True
      elif nack in dat:
        cloudlog.error("Received NACK from ublox")
        return False
      elif time.monotonic() - st > timeout:
        cloudlog.error("No response from ublox")
        raise TimeoutError('No response from ublox')
      time.sleep(0.001)

  def send_with_ack(self, dat: bytes, ack: bytes = UBLOX_ACK, nack: bytes = UBLOX_NACK) -> None:
    self.send(dat)
    self.wait_for_ack(ack, nack)

  def wait_for_backup_restore_status(self, timeout: float = 1.) -> int:
    dat = b''
    st = time.monotonic()
    while True:
      dat += self.receive()
      position = dat.find(UBLOX_BACKUP_RESTORE_MSG)
      if position >= 0 and len(dat) >= position + 11:
        return dat[position + 10]
      elif time.monotonic() - st > timeout:
        cloudlog.error("No backup restore response from ublox")
        raise TimeoutError('No response from ublox')
      time.sleep(0.001)

  def reset_device(self) -> bool:
    # deleting the backup does not always work on first try (mostly on second try)
    for _ in range(5):
      # device cold start
      self.send(b"\xb5\x62\x06\x04\x04\x00\xff\xff\x00\x00\x0c\x5d")
      time.sleep(1) # wait for cold start

      if PC:
        return True
      init_baudrate(self)

      # clear configuration
      self.send_with_ack(b"\xb5\x62\x06\x09\x0d\x00\x1f\x1f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x17\x71\xd7")

      # clear flash memory (almanac backup)
      self.send_with_ack(b"\xB5\x62\x09\x14\x04\x00\x01\x00\x00\x00\x22\xf0")

      # try restoring backup to verify it got deleted
      self.send(b"\xB5\x62\x09\x14\x00\x00\x1D\x60")
      # 1: failed to restore, 2: could restore, 3: no backup
      status = self.wait_for_backup_restore_status()
      if status == 1 or status == 3:
        return True
    return False

def init_baudrate(pigeon: TTYPigeon):
  # ublox default setting on startup is 9600 baudrate
  pigeon.set_baud(9600)

  # $PUBX,41,1,0007,0003,460800,0*15\r\n
  pigeon.send(b"\x24\x50\x55\x42\x58\x2C\x34\x31\x2C\x31\x2C\x30\x30\x30\x37\x2C\x30\x30\x30\x33\x2C\x34\x36\x30\x38\x30\x30\x2C\x30\x2A\x31\x35\x0D\x0A")
  time.sleep(0.1)
  pigeon.set_baud(460800)


def initialize_pigeon(pigeon: TTYPigeon) -> bool:
  # try initializing a few times
  for _ in range(10):
    try:

      # setup port config
      pigeon.send_with_ack(b"\xb5\x62\x06\x00\x14\x00\x03\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x1E\x7F")
      pigeon.send_with_ack(b"\xb5\x62\x06\x00\x14\x00\x00\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x19\x35")
      pigeon.send_with_ack(b"\xb5\x62\x06\x00\x14\x00\x01\x00\x00\x00\xC0\x08\x00\x00\x00\x08\x07\x00\x01\x00\x01\x00\x00\x00\x00\x00\xF4\x80")
      pigeon.send_with_ack(b"\xb5\x62\x06\x00\x14\x00\x04\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1D\x85")
      pigeon.send_with_ack(b"\xb5\x62\x06\x00\x00\x00\x06\x18")
      pigeon.send_with_ack(b"\xb5\x62\x06\x00\x01\x00\x01\x08\x22")
      pigeon.send_with_ack(b"\xb5\x62\x06\x00\x01\x00\x03\x0A\x24")

      # UBX-CFG-RATE (0x06 0x08)
      pigeon.send_with_ack(b"\xB5\x62\x06\x08\x06\x00\x64\x00\x01\x00\x00\x00\x79\x10")

      # UBX-CFG-NAV5 (0x06 0x24)
      pigeon.send_with_ack(b"\xB5\x62\x06\x24\x24\x00\x05\x00\x04\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x5A\x63")

      # UBX-CFG-ODO (0x06 0x1E)
      pigeon.send_with_ack(b"\xB5\x62\x06\x1E\x14\x00\x00\x00\x00\x00\x01\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3C\x37")
      pigeon.send_with_ack(b"\xB5\x62\x06\x39\x08\x00\xFF\xAD\x62\xAD\x1E\x63\x00\x00\x83\x0C")
      pigeon.send_with_ack(b"\xB5\x62\x06\x23\x28\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x56\x24")

      # UBX-CFG-NAV5 (0x06 0x24)
      pigeon.send_with_ack(b"\xB5\x62\x06\x24\x00\x00\x2A\x84")
      pigeon.send_with_ack(b"\xB5\x62\x06\x23\x00\x00\x29\x81")
      pigeon.send_with_ack(b"\xB5\x62\x06\x1E\x00\x00\x24\x72")
      pigeon.send_with_ack(b"\xB5\x62\x06\x39\x00\x00\x3F\xC3")

      # UBX-CFG-MSG (set message rate)
      pigeon.send_with_ack(b"\xB5\x62\x06\x01\x03\x00\x01\x07\x01\x13\x51")
      pigeon.send_with_ack(b"\xB5\x62\x06\x01\x03\x00\x02\x15\x01\x22\x70")
      pigeon.send_with_ack(b"\xB5\x62\x06\x01\x03\x00\x02\x13\x01\x20\x6C")
      pigeon.send_with_ack(b"\xB5\x62\x06\x01\x03\x00\x0A\x09\x01\x1E\x70")
      pigeon.send_with_ack(b"\xB5\x62\x06\x01\x03\x00\x0A\x0B\x01\x20\x74")
      pigeon.send_with_ack(b"\xB5\x62\x06\x01\x03\x00\x01\x35\x01\x41\xAD")
      cloudlog.debug("pigeon configured")

      # try restoring almanac backup
      pigeon.send(b"\xB5\x62\x09\x14\x00\x00\x1D\x60")
      restore_status = pigeon.wait_for_backup_restore_status()
      if restore_status == 2:
        cloudlog.warning("almanac backup restored")
      elif restore_status == 3:
        cloudlog.warning("no almanac backup found")
      else:
        cloudlog.error(f"failed to restore almanac backup, status: {restore_status}")

      # sending time to ublox
      if system_time_valid():
        t_now = datetime.now(UTC).replace(tzinfo=None)
        cloudlog.warning("Sending current time to ublox")

        # UBX-MGA-INI-TIME_UTC
        msg = add_ubx_checksum(b"\xB5\x62\x13\x40\x18\x00" + struct.pack("<BBBBHBBBBBxIHxxI",
          0x10,
          0x00,
          0x00,
          0x80,
          t_now.year,
          t_now.month,
          t_now.day,
          t_now.hour,
          t_now.minute,
          t_now.second,
          0,
          30,
          0
        ))
        pigeon.send_with_ack(msg, ack=UBLOX_ASSIST_ACK)

      # try getting AssistNow if we have a token
      token = Params().get('AssistNowToken')
      if token is not None:
        try:
          for msg in get_assistnow_messages(token):
            pigeon.send_with_ack(msg, ack=UBLOX_ASSIST_ACK)
          cloudlog.warning("AssistNow messages sent")
        except Exception:
          cloudlog.warning("failed to get AssistNow messages")

      cloudlog.warning("Pigeon GPS on!")
      break
    except TimeoutError:
      cloudlog.warning("Initialization failed, trying again!")
  else:
    cloudlog.warning("Failed to initialize pigeon")
    return False
  return True

def deinitialize_and_exit(pigeon: TTYPigeon | None):
  cloudlog.warning("Storing almanac in ublox flash")

  if pigeon is not None:
    # controlled GNSS stop
    pigeon.send(b"\xB5\x62\x06\x04\x04\x00\x00\x00\x08\x00\x16\x74")

    # store almanac in flash
    pigeon.send(b"\xB5\x62\x09\x14\x04\x00\x00\x00\x00\x00\x21\xEC")
    try:
      if pigeon.wait_for_ack(ack=UBLOX_SOS_ACK, nack=UBLOX_SOS_NACK):
        cloudlog.warning("Done storing almanac")
      else:
        cloudlog.error("Error storing almanac")
    except TimeoutError:
      pass

  # turn off power and exit cleanly
  if PC:
    pigeon.reset_device()
    time.sleep(0.5)
  else:
    set_power(False)
    time.sleep(0.1)
  sys.exit(0)

def create_pigeon(tty_port=TICI_UBLOX_TTY) -> tuple[TTYPigeon, messaging.PubMaster]:
  pigeon = None
  # register exit handler
  signal.signal(signal.SIGINT, lambda sig, frame: deinitialize_and_exit(pigeon))
  pm = messaging.PubMaster(['ubloxRaw'])

  if PC:
    pass
  else:
    # power cycle ublox
    set_power(False)
    time.sleep(0.1)
    set_power(True)
    time.sleep(0.5)

  pigeon = TTYPigeon(tty_port=tty_port)
  return pigeon, pm

def run_receiving(pigeon: TTYPigeon, pm: messaging.PubMaster, duration: int = 0):

  start_time = time.monotonic()
  def end_condition():
    return True if duration == 0 else time.monotonic() - start_time < duration

  while end_condition():
    dat = pigeon.receive()
    if len(dat) > 0:
      if dat[0] == 0x00:
        if not PC:
          cloudlog.warning("received invalid data from ublox, re-initing!")
          init_baudrate(pigeon)
          initialize_pigeon(pigeon)
          continue

      # send out to socket
      msg = messaging.new_message('ubloxRaw', len(dat), valid=True)
      msg.ubloxRaw = dat[:]
      pm.send('ubloxRaw', msg)
    else:
      # prevent locking up a CPU core if ublox disconnects
      time.sleep(0.001)


def main():
  ublox_tty = None
  if PC:
    usb_did = get_ublox_usb_did()
    ublox_tty = get_ublox_tty(usb_did)
    print(f"Using ublox USB did: {ublox_tty}")
  else:
    assert TICI, "unsupported hardware for pigeond"
  pigeon, pm = create_pigeon(ublox_tty if ublox_tty else TICI_UBLOX_TTY)
  init_baudrate(pigeon)
  initialize_pigeon(pigeon)

  # start receiving data
  run_receiving(pigeon, pm)

if __name__ == "__main__":
  main()

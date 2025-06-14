import sys
import subprocess
import re
from datetime import datetime
from pathlib import Path
import logging
import json
from typing import List, Dict, Any
import cereal.messaging as messaging
import time

logging.basicConfig(level=logging.INFO)

pm = messaging.PubMaster(['customReserved5'])

def get_iw_status(iface) -> str:
    """Get the output of the `iw dev wlan0 link` command."""
    try:
        result = subprocess.run(['iw', 'dev', iface, 'link'], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get iw status: {e}")
        return ""
    except FileNotFoundError:
        logging.error("The 'iw' command is not found. Ensure it is installed and in the system PATH.")
        return ""
def parse_iw_status(iw_output: str) -> Dict[str, Any]:
    """Parse the output of `iw dev wlan0 link` into a structured dictionary."""
    status = {}
    lines = iw_output.strip().split('\n')

    if not lines or "Not connected." in lines[0]:
        status['connected'] = False
        return status

    status['connected'] = True
    for line in lines:
        if 'Connected to' in line:
            match = re.search(r'Connected to ([0-9a-f:]{17})', line)
            if match:
                status['bssid'] = match.group(1)
        elif 'SSID:' in line:
            status['ssid'] = line.split('SSID:')[1].strip()
        elif 'freq:' in line:
            status['frequency'] = int(line.split('freq:')[1].strip())
        elif 'signal:' in line:
            match = re.search(r'signal: (-?\d+) dBm', line)
            if match:
                status['signal'] = int(match.group(1))
        elif 'tx bitrate:' in line:
            match = re.search(r'tx bitrate: ([\d.]+) ([\w/]+)', line)
            if match:
                status['tx_bitrate'] = {'value': float(match.group(1)), 'unit': match.group(2)}
        elif 'rx bitrate:' in line:
            match = re.search(r'rx bitrate: ([\d.]+) ([\w/]+)', line)
            if match:
                status['rx_bitrate'] = {'value': float(match.group(1)), 'unit': match.group(2)}
        elif 'tx failed:' in line:
            match = re.search(r'tx failed: (\d+)', line)
            if match:
                status['tx_failed'] = int(match.group(1))
        elif 'rx drop misc:' in line:
            match = re.search(r'rx drop misc: (\d+)', line)
            if match:
                status['rx_drop_misc'] = int(match.group(1))

    return status
def log_iw_status(log_path: Path, interval: int = 60, iface: str = 'wlan0'):
    """Log the iw status to a file at regular intervals."""
    log_file = log_path / f"iw_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.info(f"Logging iw status to {log_file}")

    with log_file.open('a') as f:
        while True:
            iw_output = get_iw_status(iface)
            dat = messaging.new_message('customReserved5', valid=True)
            if iw_output:
                status = parse_iw_status(iw_output)
                timestamp = datetime.now().isoformat()
                log_entry = {'timestamp': timestamp, 'status': status}
                dat.customReserved5.wifiConnected = status.get('connected', False)
                dat.customReserved5.wifiFrequency = status.get('frequency', '')
                dat.customReserved5.wifiPhyTxRate = status.get('tx_bitrate', {}).get('value', 0.0)
                dat.customReserved5.wifiPhyRxRate = status.get('rx_bitrate', {}).get('value', 0.0)
                dat.customReserved5.wifiSignalStrength = status.get('signal', 0)
                f.write(json.dumps(log_entry) + '\n')
                f.flush()
            else:
                dat.customReserved5.wifiConnected = False
                logging.warning("No iw status output to log.")
            pm.send('customReserved5', dat)
            time.sleep(interval)

def main():
    logging.basicConfig(level=logging.INFO)
    log_path = Path("/home/linux/.log/wifi")
    log_path.mkdir(parents=True, exist_ok=True)
    log_iw_status(log_path, interval=30, iface='wlp5s0')
if __name__ == "__main__":
    main()
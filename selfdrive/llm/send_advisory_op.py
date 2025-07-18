import cereal.messaging as messaging
import argparse
import os
import json
import sys
import time

pm = messaging.PubMaster(['customReserved4'])

def main(file_path):
    advisory_data = None
    with open(file_path, 'r', encoding='utf-8') as f:
        advisory_data = json.load(f)
    if advisory_data is None:
        print("Failed to load advisory data.")
        sys.exit(1)
    if advisory_data.get('alert_message').get('show') == False:
        print("No alert to show.")
        sys.exit(0)
    alert_msg = advisory_data.get('alert_message')
    while True:
        dat = messaging.new_message('customReserved4', valid=True)
        dat.customReserved4.advisoryAlertText1 = alert_msg.get('title', "")
        dat.customReserved4.advisoryAlertText2 = alert_msg.get('description', "")
        print(dat)
        pm.send('customReserved4', dat)
        time.sleep(1)
    print("Advisory op sent to panda.")
    return 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send advisory op to panda")
    parser.add_argument("file_path", type=str, help="Path to the advisory JSON file")
    args = parser.parse_args()
    main(args.file_path)
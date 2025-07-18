import numpy as np
from PIL import Image

import cereal.messaging as messaging
from msgq.visionipc import VisionIpcClient, VisionStreamType
from openpilot.common.params import Params
import op_util.cam_img
from openpilot.common.realtime import DT_MDL


import cv2

VISION_STREAMS = {
  "roadCameraState": VisionStreamType.VISION_STREAM_ROAD,
  "wideRoadCameraState": VisionStreamType.VISION_STREAM_WIDE_ROAD,
}

def get_image_from_stream():
    sockets = [s for s in ('roadCameraState', 'wideRoadCameraState') if s is not None]
    sm = messaging.SubMaster(sockets)
    vipc_clients = {s: VisionIpcClient("camerad", VISION_STREAMS[s], True) for s in sockets}

    while sm[sockets[0]].frameId < int(1 / DT_MDL):
        sm.update()

    for client in vipc_clients.values():
        client.connect(True)

    road_img = None
    wide_road_img = None

    while True:
        buf = vipc_clients['roadCameraState'].recv()
        if buf is None:
            continue

        road_img = op_util.cam_img.extract_image(buf)
        break

    while True:
        buf = vipc_clients['wideRoadCameraState'].recv()
        if buf is None:
            continue
        wide_road_img = op_util.cam_img.extract_image(buf)
        break

    assert road_img is not None, "Failed to get road image"
    assert wide_road_img is not None, "Failed to get wide road image"
    return road_img, wide_road_img
        
def main():
    try:
        while True:
            road_img, wide_road_img = get_image_from_stream()
            road_img = cv2.cvtColor(road_img, cv2.COLOR_RGB2BGR)
            wide_road_img = cv2.cvtColor(wide_road_img, cv2.COLOR_RGB2BGR)
            cv2.imshow("Road Camera", road_img)
            cv2.imshow("Wide Road Camera", wide_road_img)

            cv2.imwrite("road_camera.jpg", road_img)
            cv2.imwrite("wide_road_camera.jpg", wide_road_img)
            print("Images saved as road_camera.jpg and wide_road_camera.jpg")

            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
            break
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
import cv2
import numpy as np

class Camera:
    def __init__(self, cam_type_state, stream_type, camera_id):
        # Initialize camera with the provided camera_id or default to 0
        self.camera = cv2.VideoCapture(camera_id)
        self.cam_type_state = cam_type_state
        self.stream_type = stream_type
        self.cur_frame_id = 0
        if not self.camera.isOpened():
            raise ValueError(f"Can't open video stream for camera {camera_id}")

        self.W = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.H = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))


    @staticmethod
    def bgr2nv12(bgr_frame):
        yuv = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2YUV_I420)
        uv_row_cnt = yuv.shape[0] // 3
        uv_plane = np.transpose(yuv[uv_row_cnt * 2:].reshape(2, -1), [1, 0])
        yuv[uv_row_cnt * 2:] = uv_plane.reshape(uv_row_cnt, -1)
        return yuv

    def read_frames(self):
        while self.camera.isOpened():
            ret, frame = self.camera.read()
            if not ret:
                break

            # Convert to NV12 format
            nv12_frame = self.bgr2nv12(frame)

            # Yield the NV12 data
            yield nv12_frame.tobytes()

        self.camera.release()

# Example usage:
# camera = Camera("/dev/video0")
# for nv12_frame in camera.read_frames():
#     # Process or display `nv12_frame`
#     pass

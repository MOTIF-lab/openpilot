import av
import cv2 as cv


class Camera:
    def __init__(self, cam_type_state, stream_type, camera_id):
        try:
            camera_id = int(camera_id)
        except ValueError:  # allow strings, ex: /dev/video0
            pass
        self.cam_type_state = cam_type_state
        self.stream_type = stream_type
        self.cur_frame_id = 0

        self.cap = cv.VideoCapture(
            camera_id, cv.CAP_DSHOW if cam_type_state == "dshow" else cv.CAP_V4L2
        )
        self.cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter.fourcc("M", "J", "P", "G"))

        # Set the desired resolution (1080p)
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)

        # Set the desired FPS
        self.cap.set(cv.CAP_PROP_FPS, 30.0)

        self.W = self.cap.get(cv.CAP_PROP_FRAME_WIDTH)
        self.H = self.cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        self.fourcc = self.cap.get(cv.CAP_PROP_FOURCC)

        print(
            f"cam h: {self.H} w: {self.W} type: {self.cam_type_state} stream: {self.stream_type}, fourcc: {"".join([chr((int(self.fourcc) >> 8 * i) & 0xFF) for i in range(4)])}"
        )
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {camera_id}")

    @classmethod
    def bgr2nv12(self, bgr):
        frame = av.VideoFrame.from_ndarray(bgr, format="bgr24")
        return frame.reformat(format="nv12").to_ndarray()

    def read_frames(self):
        while True:
            sts, frame = self.cap.read()
            if not sts:
                break
            # Rotate the frame 180 degrees (flip both axes)
            frame = cv.flip(frame, -1)
            yuv = Camera.bgr2nv12(frame)
            yield yuv.data.tobytes()
        self.cap.release()


import av
import numpy as np
from pathlib import Path

Path("outputs").mkdir(exist_ok=True)
path = "outputs/cineforge_cpu_test.mp4"

container = av.open(path, "w")
stream = container.add_stream("libx264", rate=24)
stream.width = 640
stream.height = 360
stream.pix_fmt = "yuv420p"

for i in range(48):
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:, :, 0] = 20 + i * 2
    frame[:, :, 1] = 50
    frame[:, :, 2] = 120
    video_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
    for packet in stream.encode(video_frame):
        container.mux(packet)

for packet in stream.encode():
    container.mux(packet)

container.close()
print("MP4 created:", path)

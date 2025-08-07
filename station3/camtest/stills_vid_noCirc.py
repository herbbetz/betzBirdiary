from picamera2 import Picamera2
# Changed to import H264Encoder instead of MJPEGEncoder
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FileOutput
import libcamera
import io
import time
# Removed: from picamera2 import controls # No longer needed if not using ExposureMode enum

# --- CONFIGURATION ---
vidsize = (1280, 960)       # main stream size for stills/videos
hflip_val = 0
vflip_val = 1
videodurate = 5             # seconds of video to record per trigger
max_stills = 7              # exit after this many still images

# Exposure settings based on your successful rpicam-still test
camsetting = {
    "AeEnable": False,           # Disable Automatic Exposure (may show a warning, but should work)
    "AnalogueGain": 4.0,         # Analog gain (e.g., 4.0)
    "ExposureTime": 10000,       # Shutter speed in microseconds (10ms)
    "AwbEnable": False,          # Disable Automatic White Balance
    "ColourGains": (1.5, 1.2)    # Set manual color gains (Red, Blue)
}
# Create transform using libcamera.Transform object
# This is now explicitly used as the value for the 'transform' argument.
camera_transform = libcamera.Transform(hflip=hflip_val, vflip=vflip_val)

def capture_still(picamera, dest):
    """
    Captures a still image from the Picamera2 and saves it to the specified destination.

    Args:
        picamera (Picamera2): The Picamera2 instance.
        dest (str): The file path to save the JPEG image.
    """
    picamera.capture_file(dest, name="main", format="jpeg")

def record_video(picamera, encoder, duration):
    """
    Records a video for a specified duration using the given encoder.

    Args:
        picamera (Picamera2): The Picamera2 instance.
        encoder (H264Encoder): The encoder to use for video recording.
        duration (int): The duration in seconds to record the video.

    Returns:
        io.BytesIO: A BytesIO object containing the recorded video data.
    """
    vid_data = io.BytesIO()
    output = FileOutput(vid_data)
    # For H264, Quality.MEDIUM is a good starting point
    picamera.start_recording(encoder, output, quality=Quality.MEDIUM)
    time.sleep(duration)
    picamera.stop_encoder() # Stop the encoder
    # ADDED: Small delay to allow the encoder/pipeline to settle
    time.sleep(0.2) # A short delay, e.g., 50 milliseconds, to ensure clean stop
    return vid_data

def main_loop():
    """
    Main loop to control the camera, capturing stills and triggered videos.
    """
    with Picamera2() as picam2:
        # Create still configuration. The 'transform' argument now uses
        # the libcamera.Transform object directly.
        still_config = picam2.create_still_configuration(
            main={"size": vidsize, "format": "RGB888"}, # RGB888 for still JPEGs
            transform=camera_transform # Pass the libcamera.Transform object
        )

        # Create video configuration for H264.
        # Format remains YUV420, as the encoder will handle H264 compression.
        video_config = picam2.create_video_configuration(
            main={"size": vidsize, "format": "YUV420"}, # YUV420 standard for H264 video
            transform=camera_transform # Pass the libcamera.Transform object
        )

        # Instantiate H264Encoder
        encoder = H264Encoder()
        img_count = 0

        # Configure the camera with the still configuration initially
        picam2.configure(still_config)
        time.sleep(0.5) # A larger initial delay to allow the camera to stabilize
        picam2.start() # Start the camera once at the beginning of the loop

        # Set initial controls for exposure and gain
        # "AeEnable": False is retained as it worked to produce recognizable images.
        picam2.set_controls(camsetting)
        print(f"Initial controls set: AeEnable=False, ExposureTime={camsetting['ExposureTime']}, AnalogueGain={camsetting['AnalogueGain']}, ColourGains=(1.5, 1.2)")

        while img_count < max_stills:
            # --- Still Image Capture Loop ---
            img_name = f"image_{img_count:04d}.jpg"
            capture_still(picam2, img_name)
            print(f"Captured still: {img_name}")
            img_count += 1

            # --- Trigger check (This part acts as a placeholder for a real trigger) ---
            # For demonstration, a video is triggered every 5 still images.
            if img_count % 5 == 0:
                print("Trigger detected! Starting video recording (H.264)...")
                # Switch the camera to video configuration before recording
                picam2.switch_mode(video_config)
                # Re-apply exposure controls after mode switch to ensure they persist
                picam2.set_controls(camsetting)
                print("Controls re-applied after mode switch for video.")


                video_buffer = record_video(picam2, encoder, videodurate)

                # --- Placeholder for Web Upload (demonstrates saving to file) ---
                # Changed extension back to .h264
                video_name = f"video_{img_count:04d}.h264"
                with open(video_name, "wb") as f:
                    f.write(video_buffer.getvalue())
                print(f"Recorded video to buffer (and saved to file for demo): {video_name}")
                # --- End Placeholder ---

                # Switch back to still configuration after video recording
                picam2.switch_mode(still_config)
                # Re-apply exposure controls after switching back to still mode
                picam2.set_controls(camsetting)
                print("Controls re-applied after mode switch for stills.")

            time.sleep(2) # Pause between still captures

    print("Program exiting cleanly.")

if __name__ == "__main__":
    main_loop()

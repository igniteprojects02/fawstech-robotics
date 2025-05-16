import ffmpeg
import os

def get_video_duration(filepath):
    try:
        probe = ffmpeg.probe(filepath)
        duration = float(probe['format']['duration'])  # in seconds
        return round(duration / 60, 2)  # return in minutes (2 decimal)
    except Exception as e:
        print(f"FFmpeg error: {e}")
        return 0

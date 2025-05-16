from django.core.mail import EmailMessage
import subprocess
import os

def send_otp_email(email, otp):
    subject = 'Your Fawstech Verification OTP'
    message = f'Your OTP for Fawstech verification is: {otp}'
    email_message = EmailMessage(subject, message, to=[email])
    email_message.send()


def get_video_duration1(file_path):
    """Returns video duration in minutes using ffmpeg."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return float(result.stdout) / 60
    except Exception as e:
        print(f"ffmpeg error: {e}")
        return 0
    
def calculate_course_duration(course):
    """
    Calculates total duration (in minutes) for a course by summing up all chapter video durations.
    """
    total_duration = 0
    for module in course.modules.all():
        for chapter in module.chapters.all():
            if chapter.video and hasattr(chapter.video, 'path'):
                total_duration += get_video_duration1(chapter.video.path)
    return total_duration
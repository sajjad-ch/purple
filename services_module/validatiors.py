from moviepy.editor import VideoFileClip
from rest_framework import serializers
from io import BytesIO


def validate_video_duration_and_size(file):
    try:
        # Use BytesIO to handle in-memory file
        file_bytes = BytesIO(file.read())

        # Use VideoFileClip to check the duration and size
        clip = VideoFileClip(file_bytes)
        duration = clip.duration
        width, height = clip.size
        clip.close()

        # Reset the file pointer to the beginning
        file.seek(0)

        if duration > 60:
            raise serializers.ValidationError("Video duration should be less than 60 seconds.")

        if width != 1 or height != 1:
            raise serializers.ValidationError("Video resolution must be 1x1.")
    except Exception as e:
        raise serializers.ValidationError(f"An error occurred while processing the video: {str(e)}")

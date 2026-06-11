import os
import tempfile
import uuid

import cv2
from django.core.files.base import ContentFile
from PIL import Image


def generate_video_thumbnail(exercise):
    if not exercise.video:
        return

    suffix = os.path.splitext(exercise.video.name)[1] or '.mp4'
    with tempfile.NamedTemporaryFile(suffix=suffix) as video_file:
        for chunk in exercise.video.chunks():
            video_file.write(chunk)
        video_file.flush()

        capture = cv2.VideoCapture(video_file.name)
        success, frame = capture.read()
        capture.release()

    if not success:
        return

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame)
    image.thumbnail((720, 720))

    with tempfile.NamedTemporaryFile(suffix='.jpg') as thumbnail_file:
        image.save(thumbnail_file, format='JPEG', quality=85)
        thumbnail_file.seek(0)
        thumbnail_name = f'{uuid.uuid4()}.jpg'
        exercise.video_thumbnail.save(
            thumbnail_name,
            ContentFile(thumbnail_file.read()),
            save=False,
        )

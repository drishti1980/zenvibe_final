"""Staff-only stateless jobs. No app dependency upgrades or database changes."""
import base64
import binascii
import fcntl
import io
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid

from django.http import JsonResponse

CONFIG = Path.home()/'.zenvibe-template-converter/runtime.json'
WORKER = Path(__file__).resolve().parent/'paddle_template/worker.py'
CHILDREN = {}
MAX_BYTES = 15*1024*1024


class ConversionError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def runtime():
    try:
        data = json.loads(CONFIG.read_text())
        python = Path(data['python'])
        jobs = Path(data['jobs'])
        if data.get('version') != 'zenvibe-paddle-1' or not python.is_file() or not jobs.is_dir():
            raise ValueError('Invalid runtime')
        return python, jobs
    except (OSError, ValueError, KeyError):
        raise ConversionError('The Paddle converter has not passed its hosting compatibility check. Run prepare_runtime.py before enabling it.', 503)


def decode_image(data):
    from PIL import Image, ImageOps, UnidentifiedImageError
    if not isinstance(data, str):
        raise ConversionError('An image data URL is required.')
    if len(data) > MAX_BYTES*4//3+100:
        raise ConversionError('Image exceeds 15 MB.', 413)
    if not re.match(r'^data:image/(png|jpeg|webp);base64,', data):
        raise ConversionError('Use a PNG, JPEG or WEBP image data URL.')
    try:
        raw = base64.b64decode(data.split(',', 1)[1], validate=True)
        if len(raw) > MAX_BYTES:
            raise ConversionError('Image exceeds 15 MB.', 413)
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in {'PNG', 'JPEG', 'WEBP'}:
                raise ConversionError('Use a PNG, JPEG or WEBP image.')
            if image.width*image.height > 24_000_000:
                raise ConversionError('Image dimensions too large.', 413)
            image = ImageOps.exif_transpose(image).convert('RGB')
            normalized = io.BytesIO()
            image.save(normalized, 'PNG')
            return normalized.getvalue()
    except (binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ConversionError('Image cannot be decoded safely.')


def cleanup(jobs):
    for token, child in list(CHILDREN.items()):
        if child.poll() is not None:
            CHILDREN.pop(token, None)
    # A worker is bounded to seven minutes. Never delete an active job.
    for folder in jobs.iterdir():
        if re.fullmatch(r'[0-9a-f]{32}', folder.name) and folder.is_dir() and time.time()-folder.stat().st_mtime > 3600:
            shutil.rmtree(folder)


def start(image, user):
    python, jobs = runtime()
    # One engine at a time per account, regardless of the number of web workers.
    lock = open(jobs/'worker.lock', 'a')
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ConversionError('Another image is being converted. Wait for it to finish, then retry.', 409)
        cleanup(jobs)
        content = decode_image(image)
        token = uuid.uuid4().hex
        folder = jobs/token
        folder.mkdir(mode=0o700)
        (folder/'source.png').write_bytes(content)
        (folder/'owner.json').write_text(json.dumps({'user': user, 'created': time.time()}))
        environment = os.environ.copy()
        environment.update({'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
                            'MKL_NUM_THREADS': '1', 'FLAGS_use_mkldnn': '0',
                            'PYTHONNOUSERSITE': '1', 'CUDA_VISIBLE_DEVICES': ''})
        environment.pop('PYTHONPATH', None)
        environment.pop('PYTHONHOME', None)
        try:
            with open(folder/'worker.log', 'wb') as log:
                child = subprocess.Popen([str(python), str(WORKER), str(folder/'source.png'), str(folder/'result.json')],
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=environment,
                    pass_fds=(lock.fileno(),), start_new_session=True)
            CHILDREN[token] = child
        except OSError:
            shutil.rmtree(folder)
            raise ConversionError('The hosting account could not start the converter worker.', 503)
        return {'status': 'running', 'job': token}
    finally:
        # Do not unlock explicitly: the detached worker retains this descriptor.
        lock.close()


def status(token, user):
    _, jobs = runtime()
    if not isinstance(token, str) or not re.fullmatch(r'[0-9a-f]{32}', token):
        raise ConversionError('Invalid conversion job.')
    folder = jobs/token
    try:
        owner = json.loads((folder/'owner.json').read_text())
    except (OSError, ValueError):
        raise ConversionError('Conversion job was not found or has expired.', 404)
    if owner.get('user') != user:
        raise ConversionError('Conversion job was not found or has expired.', 404)
    if time.time()-owner['created'] > 3600:
        raise ConversionError('Conversion job was not found or has expired.', 404)
    child = CHILDREN.get(token)
    if child is not None and child.poll() is not None:
        CHILDREN.pop(token, None)
    result = folder/'result.json'
    if result.is_file():
        payload = json.loads(result.read_text())
        if payload.get('status') != 'complete':
            raise ConversionError(payload.get('error', 'Conversion failed.'), 503)
        return payload
    if time.time()-owner['created'] > 450 or (child is not None and child.returncode is not None):
        raise ConversionError('Conversion worker stopped or timed out. Original artwork was preserved; check the private worker log.', 503)
    return {'status': 'running', 'job': token}


def handle_request(request):
    try:
        if len(request.body) > MAX_BYTES*4//3+1024:
            raise ConversionError('Image exceeds 15 MB.', 413)
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ConversionError('A JSON object is required.')
        action = payload.get('action', 'start')
        if action == 'status':
            return JsonResponse(status(payload.get('job'), request.user.pk))
        if action != 'start':
            raise ConversionError('Unknown conversion action.')
        return JsonResponse(start(payload.get('image'), request.user.pk), status=202)
    except ConversionError as exc:
        return JsonResponse({'error': str(exc)}, status=exc.status)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid conversion request.'}, status=400)
    except Exception:
        logging.getLogger(__name__).exception('Paddle conversion request failed')
        return JsonResponse({'error': 'Conversion could not complete. Original artwork was preserved.'}, status=503)

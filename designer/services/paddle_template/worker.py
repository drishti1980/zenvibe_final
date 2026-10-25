"""Bounded, isolated worker for Zenvibe's existing template builder."""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

VERSION = 'zenvibe-paddle-1'


def write_json(path, payload):
    fd, name = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(payload, stream, allow_nan=False)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def convert(image):
    import cv2
    import numpy as np
    from PIL import Image
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from paddle_template.ocr import extract
    from paddle_template.imaging import polygon_mask, repair_background
    pixels = np.asarray(image.convert('RGB'))
    regions = extract(pixels)
    if len(regions) > 256:
        raise ValueError('Too many text regions. Divide this artwork into smaller surfaces.')
    lines = []
    h, w = pixels.shape[:2]
    for region in regions:
        pts = np.asarray(region['polygon'], dtype=float)
        x0, y0 = np.floor(pts.min(axis=0)).astype(int)
        x1, y1 = np.ceil(pts.max(axis=0)).astype(int)
        # Repair in a bounded local crop using the supplied glyph-mask algorithm.
        left, top = max(0, x0-16), max(0, y0-16)
        right, bottom = min(w, x1+17), min(h, y1+17)
        crop = pixels[top:bottom, left:right].copy()
        local = dict(region, polygon=(pts-[left, top]).tolist())
        mask, color = polygon_mask(crop, local['polygon'])
        repaired = repair_background(crop, [local], [region['id']])
        rgba = np.dstack((repaired, mask))
        out = io.BytesIO()
        Image.fromarray(rgba).save(out, 'PNG')
        lines.append({
            'text': region['text'], 'confidence': region['confidence']*100,
            'bbox': {'x0': int(x0), 'y0': int(y0), 'x1': int(x1), 'y1': int(y1)},
            'angle': region['angle'], 'origin': {'x': region['x'], 'y': region['y']},
            'textBox': {'w': region['width']/w, 'h': region['height']/h,
                        'x': region['x']/w, 'y': region['y']/h},
            'color': color, 'polygon': region['polygon'],
            'repair': {'src': 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode('ascii'),
                       'box': {'x': left/w, 'y': top/h, 'w': (right-left)/w, 'h': (bottom-top)/h}},
        })
    lines.sort(key=lambda line: (line['bbox']['y0'], line['bbox']['x0']))
    return {'status': 'complete', 'engine': 'paddleocr-3.3.2', 'version': VERSION,
            'width': w, 'height': h, 'lines': lines}


def execute(source, target, check=False):
    from PIL import Image, ImageDraw, ImageFont
    if check:
        import paddle
        paddle.utils.run_check()
        image = Image.new('RGB', (900, 220), 'white')
        draw = ImageDraw.Draw(image)
        # Bundled check font makes the gate independent of system fonts.
        font = ImageFont.truetype(str(source), 64)
        draw.text((35, 65), 'ZENVIBE 12345', fill='black', font=font)
        result = convert(image)
        recognized = ''.join(line['text'] for line in result['lines']).upper().replace(' ', '')
        if 'ZENVIBE' not in recognized or '12345' not in recognized:
            raise RuntimeError('Paddle loaded, but the real OCR smoke image was not recognized: '+recognized)
        result['smoke_test'] = True
    else:
        with Image.open(source) as original:
            if original.width*original.height > 24_000_000:
                raise ValueError('Image dimensions too large.')
            result = convert(original)
    write_json(target, result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.execute:
        execute(args.source, args.target, args.check)
        return
    command = [sys.executable, str(Path(__file__).resolve()), str(args.source), str(args.target), '--execute']
    if args.check:
        command.append('--check')
    try:
        subprocess.run(command, check=True, timeout=900 if args.check else 420)
    except Exception:
        write_json(args.target, {'status': 'failed', 'error':
            'Paddle conversion failed or exceeded the hosting time limit. Original artwork was preserved. Check the private converter worker log.'})
        raise


if __name__ == '__main__':
    main()

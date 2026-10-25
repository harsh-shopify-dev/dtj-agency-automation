"""Erase the reference ad's corner logo and bottom 'Available on' strip with LaMa: clean_brand.py <out_dir> <img>..."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from reel_factory.watermark import lama
BOXES = [(520, 118, 675, 210), (40, 1058, 475, 1135)]   # in a 720x1280 frame
lama = lama()
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
for p in sys.argv[2:]:
    im = Image.open(p).convert('RGB'); w, h = im.size; k = w / 720
    m = np.zeros((h, w), np.uint8)
    for x0, y0, x1, y1 in BOXES:
        m[int(y0 * k):int(y1 * k), int(x0 * k):int(x1 * k)] = 255
    res = lama(im, Image.fromarray(m)).crop((0, 0, w, h))
    res.save(out / (Path(p).stem + '.png')); print('cleaned', p)

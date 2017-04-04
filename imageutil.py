#!/usr/bin/python3
import os
from PIL import Image

def make_thumbnail(dirpath, thumbnail_name, thumbnail_size=200, num = None, quality=100):
    files = os.listdir(dirpath)[:num]
    if num:
        files = files[:num]
    # マージに利用する下地画像を作成する
    canvas = Image.new('RGB', (thumbnail_size * 2, thumbnail_size * ((len(files)+1) // 2)), (255, 255, 255))

    for i, f in enumerate(files):
        try:
            img = Image.open('{}/{}'.format(dirpath, f), 'r')
        except OSError:
            # # 処理する画像を開けなかった
            continue
        img.thumbnail((thumbnail_size, thumbnail_size), Image.ANTIALIAS)
        # 左上の座標
        x = i % 2 * thumbnail_size
        y = (i//2) * thumbnail_size
        canvas.paste(img, (x, y))
    # 保存
    canvas.save('{}/{}.jpg'.format(dirpath, thumbnail_name), 'JPEG', quality=quality, optimize=True)
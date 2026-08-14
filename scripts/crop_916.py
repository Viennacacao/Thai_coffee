#!/usr/bin/env python3
"""把下载到的小红书图片统一中心裁剪为 9:16 竖图（JPEG）。

用法:
  python3 crop_916.py <raw_dir> <out_dir>

raw_dir 下可以再有子目录（每个笔记一个目录），会递归收集所有图片。
输出: out_dir/<原名>.jpg  (RGB, quality=88)
"""
import sys, os
from PIL import Image

TARGET_RATIO = 9 / 16  # w / h （竖图）

SUPPORTED = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif', '.heic')

def list_images(d):
    out = []
    for root, _, files in os.walk(d):
        for f in sorted(files):
            if f.lower().endswith(SUPPORTED):
                out.append(os.path.join(root, f))
    return out

def crop_to_916(im, max_edge=1600):
    w, h = im.size
    if w <= 0 or h <= 0:
        return None
    cur = w / h
    if cur > TARGET_RATIO:
        # 太宽 -> 裁宽度
        new_w = int(h * TARGET_RATIO)
        x = (w - new_w) // 2
        box = (x, 0, x + new_w, h)
    else:
        # 太高 -> 裁高度
        new_h = int(w / TARGET_RATIO)
        y = (h - new_h) // 2
        box = (0, y, w, y + new_h)
    im = im.crop(box)
    # 限制最长边，避免文件过大
    if max(im.size) > max_edge:
        scale = max_edge / max(im.size)
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    return im

def main():
    if len(sys.argv) < 3:
        print("usage: python3 crop_916.py <raw_dir> <out_dir>")
        sys.exit(1)
    raw_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    imgs = list_images(raw_dir)
    if not imgs:
        print(f"! 在 {raw_dir} 没找到图片")
        sys.exit(1)
    n = 0
    for p in imgs:
        try:
            im = Image.open(p).convert("RGB")
            im = crop_to_916(im)
            if im is None:
                continue
            base = os.path.splitext(os.path.basename(p))[0]
            # 去重
            dst = os.path.join(out_dir, f"{base}.jpg")
            i = 1
            while os.path.exists(dst):
                dst = os.path.join(out_dir, f"{base}_{i}.jpg"); i += 1
            im.save(dst, "JPEG", quality=88)
            n += 1
        except Exception as e:
            print(f"  跳过 {p}: {e}")
    print(f"✓ 裁剪完成: {n} 张 -> {out_dir}")

if __name__ == "__main__":
    main()

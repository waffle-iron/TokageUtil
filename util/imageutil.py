# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import argparse, re, os, sys, glob, traceback
import tensorflow as tf
from PIL import Image, ImageEnhance
from util.fileutil import FilePair
from util.vectorutil import VectorReverseIndex

VectDir = './vector'
ImgDir = './img'

def generateCropedImages(srcDir='/workspace/', dstDir='./tmp/', fixedBox=None, bkcmp=False):
    baseDir = os.path.join(srcDir, 'img-buff/motions')
    VectorReverseIndex.updateVectors(os.path.join(baseDir, VectDir))

    imgDir = os.path.join(baseDir, ImgDir)
    # vectDir = os.path.join(srcDir, VectDir)
    images = [x for x in glob.glob(imgDir + '/*.jpeg')]
    # vects = [x for x in glob.glob(vectDir + '/*.npy')]
    # if len(images) <= len(vects):
    assert(fixedBox is not None)
    pairs = [FilePair(img=i, backcmp=bkcmp, fixedBox=fixedBox) for i in images]
    # else:
    #    pairs = [FilePair(i, fixedBox) for i in vects]
    print('Start cropping %d files by %s'%(len(pairs), fixedBox))
    i = 1
    for c in pairs:
        c.PILCrop(dstDir, fixedBox)
        sys.stdout.write('\r%d/%d'%(i, len(pairs)))
        i += 1

def convRGBByteArray(img:Image):
    """
    tfも含め、画像のRGB配列化
    """
    # http://pillow.readthedocs.io/en/3.4.x/handbook/concepts.html#concept-modes
    w, h, depth, rgb = __rgb(img)
    asBytes = rgb[0] + rgb[1] + rgb[2]
    return w, h, depth, np.array(asBytes, dtype=np.uint8).tobytes()

def convCalcPixelByteArray(img:Image, f=lambda r, g, b: r * 0.2126 + g * 0.7152 + b * 0.0722):
    """ Lumix Grayscale配列化 
    デフォルトでLumix Grayscaleとする
    p = r*0.2126 + g*0.7152 + b*0.0722 
    平均値で良ければ、
    p = (r + g + b) / 3 
    """
    # http://pillow.readthedocs.io/en/3.4.x/handbook/concepts.html#concept-modes
    w, h, depth, rgb = __rgb(img)
    asBytes = [f(rgb[0][i], rgb[1][i], rgb[2][i]) for i in range(len(rgb[0]))]
    depth = 1 # 上記で１項に圧縮しているため、ここで書き換える
    return w, h, depth, np.array(asBytes, dtype=np.uint8).tobytes()

def __rgb(img:Image):
    cImg = img.convert(mode='RGB')
    rgb = ([], [], [])
    w, h = cImg.size
    depth = len(rgb)
    for i in range(h):
        for j in range(w):
            r, g, b = cImg.getpixel((j, i))
            assert r < 256 and r >= 0
            rgb[0].append(r)
            assert g < 256 and g >= 0
            rgb[1].append(g)
            assert b < 256 and b >= 0
            rgb[2].append(b)
    assert(len(rgb[0]) == len(rgb[1]))
    assert(len(rgb[1]) == len(rgb[2]))
    assert len(rgb[0]) == w * h, 'not applicable size natural:%d but wxh:%d'%(len(rgb[0]), w * h)
    return w, h, depth, rgb

def openImageForTFfeature(fName:str='', _img:Image=None, 
                            contrast:float=2.0, sharp:float=1.0, 
                            origin=(0, 0), isBin=True):
    """ 
    _imgは直接Imageを渡す時用
    """
    if not fName == '':
        assert(os.path.exists(fName))
    # ()をつけないとelse lambda ... が展開されないまま返される？
    f = (lambda x:convCalcPixelByteArray(x)) if isBin else (lambda x:convRGBByteArray(x))
    try:
        img = Image.open(fName) if not fName == '' else _img
        cropped = img.crop((origin[0], origin[1], img.size[0], img.size[1]))
        # cnt = ImageEnhance.Contrast(cropped)
        # contImg = cnt.enhance(contrast)
        # sharpness = ImageEnhance.Sharpness(contImg)
        # sharpness は[0.5, 2.0]とする
        # assert(0.5 <= sharp and sharp <= 2.0)
        # sharped_image = sharpness.enhance(cropped).resize(img.size)
        sharped_image = cropped.resize(img.size)
        # print('w: %s, h: %s, d: %s, shape: %s'%(w, h, depth, imgarray.shape))
        return f(sharped_image)
    except:
        traceback.print_exc()
    finally:
        img.close()


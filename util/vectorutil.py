from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os, traceback, glob, threading
import datetime as dt
import numpy as np

from util import printutil as pu

DEFAULTVECTOR_DIR = os.path.expanduser('~/workspace/img-buff/motions/vector')
MACROSQURE = 16
# 人間が決めるものなので、5x2固定にしてある
# BIASを考慮して、200 -> 100, 200 -> 140 領域を4x2に対応させる 右へ行くほど-yへ傾斜をかける
CAM02_SHOOT_ORIGINS = [[(195, 125), (150, 125), (130, 125), (100, 120), (80, 117)],
                        [(195, 195), (150, 180), (130, 170), (100, 165), (60, 150)]]
                        # 'noLenz': [[(180, 117), (130, 117), (100, 117), (65, 90)],
                        #            [(180, 195), (130, 180), (100, 160), (60, 130)]]
AREA_DIV = (len(CAM02_SHOOT_ORIGINS[0]), len(CAM02_SHOOT_ORIGINS))

class VectorReverseIndex(object):
    """ Thread safed Singleton """
    _instance = None
    _lock = threading.Lock()

    def __init__(self, path):
       # print('__init__ entered path = %s'%path)
        self.__vectPath = path
        pass

    def __new__(cls, path):
       # print('__new__ entered path = %s'%path)
        with cls._lock:
            if cls._instance is None:
               # print('_instance was None')
                cls._instance = super().__new__(cls)
                cls.__vectPath = path
                cls.__checkedFiles = set([])
                cls.__Img2Vect = {}
            else:
                if cls.__vectPath != path:
                    cls.__vectPath = path
               # print('_instance is/ path = %s'%cls.__vectPath)
        return cls._instance

    @property
    def queryVectFile(self):
        return self.__Img2Vect

    def __expandImgNamesInVect(self, vectFile:str):
       # print('$$ process entered %s'%vectFile)
        imgs = np.load(vectFile)[1]
       # print('$$ %s'%imgs)
        root = os.path.basename(vectFile)
        for i in imgs:
            self.__Img2Vect[i] = root
       # print('$$ stocked %s'%self.__Img2Vect)

    @staticmethod
    def updateVectors(path=DEFAULTVECTOR_DIR):
        ins = VectorReverseIndex(path=path)
       # print('search in %s'%os.path.join(ins.__vectPath, '*.npy'))
        files = glob.glob(os.path.join(ins.__vectPath, '*.npy'))
       # print('*** %s ***'%files)
        notYets = set(files) - ins.__checkedFiles
       # print('### notYets = %s ###'%notYets)
        if len(notYets) == 0:
            return
        [ins.__expandImgNamesInVect(n) for n in notYets]

class ScreenRatio(object):
    """ Cam001の座標をCam002サーボ座標に変換 """
    def __init__(self, screenSize, dim, origins):
        assert len(screenSize) == 2
        assert (isinstance(screenSize[0], int) and isinstance(screenSize[1], int)) == True
        self.__screen_size = screenSize
        assert len(dim) == 2
        assert (isinstance(dim[0], int) and isinstance(dim[1], int)) == True
        # dim[0], dim[0] + 1いずれかは偶数なので、必ず2で割り切れる
        #self.__dim = (dim[0] * (1 + dim[0]) // 2, dim[1])
        self.__dim = dim
        # 毎度N回足すのではなく、一度算出されたら変わらないので持っておく
        self.includeX = [self.__sumFromOne(i + 1) for i in range(self.dim[0])]
        self.includeY = [self.__sumFromOne(i + 1) for i in range(self.dim[1])]
        assert len(origins) > 0, 'origins type donot fulfill requirements'
        self.__origins = origins

    def __sumFromOne(self, n):
        assert n > 0
        return (1 + n) * n / 2

    @property
    def screen_size(self):
        return self.__screen_size
    @property
    def dim(self):
        return self.__dim
    @property
    def origins(self):
        return self.__origins
    @origins.setter
    def origins(self, val):
        assert isinstance(val, list)
        assert len(val) > 0, 'value type donot fulfill requirements'
        self.__origins = val

    @property
    def divided_units(self):
        if not hasattr(self, '__divided_units'):
            assert self.__origins is not None, 'not fulfill requirements'
            self.__divided_units = (self.screen_size[0] // self.dim[0], 
                                    self.screen_size[1] // self.dim[1])
        return self.__divided_units

    def whereisHitArea(self, x, y, isCenter=True):
        """ どのエリアに属するかを算出する """
        if isinstance(x, int) and isinstance(y, int):
            o = x, y
        else:
            o = midXY(x, y) if isCenter else minXY(x, y)
        rawX, rawY = int(o[0] // self.divided_units[0]), int(o[1] // self.divided_units[1])
        # 左から走査する
        # hitX = 0
        # for bX in self.includeX:
        #     if rawX >= bX:
        #         break
        #     else:
        #         hitX += 1
        return rawX, rawY

def minXY(xVector, yVector):
    return xVector.min() * MACROSQURE, yVector.min() * MACROSQURE

def maxXY(xVector, yVector):
    return xVector.max() * MACROSQURE, yVector.max() * MACROSQURE

def midXY(xVector, yVector):
    """ min, maxの中点 """
    minX, minY = minXY(xVector, yVector)
    maxX, maxY = maxXY(xVector, yVector)
    # (max - min) / 2 + min = max / 2 + min / 2 = (max + min) / 2
    return (minX + maxX) / 2, (minY + maxY) / 2

def motionFrame(xVector, yVector):
    assert len(xVector) == len(yVector), 'xy not matches %d:%d'%(len(xVector), len(yVector))
    minPX, minPY = minXY(xVector, yVector)
    maxPX, maxPY = maxXY(xVector, yVector)
    return (minPX, minPY, maxPX - minPX, maxPY - minPY)

def cropedFrame(x, y, isCenter:bool, box):
    assert len(x) == len(y), 'xy not matches %d:%d'%(len(x), len(y))
    assert len(box) == 2, 'Illegal box has found %s'%box
    midPX, midPY = midXY(x, y)
    diffX, diffY = box[0] / 2, box[1] / 2
    return (midPX - diffX, midPY - diffY, box[0], box[1])

def __divideArea(screenSize, dividedBy=AREA_DIV):
    """ 領域をAREA_DEVで分割かつSHOOT_ORIGINSの比率から算出した対応領域比を返す """
    assert len(screenSize) == 2
    assert len(dividedBy) == 2
    return screenSize[0] // dividedBy[0], screenSize[1] // dividedBy[1]

def whereIsHitArea(screenSize, x, y, isCenter=True):
    """
    xy座標群の中点が、divAreaの中でどこに包含されるかを返す
    領域をAREA_DEVで分割かつSHOOT_ORIGINSの比率から算出した対応領域を配列で返す
    """
    divArea = __divideArea(screenSize)
    if isinstance(x, int) and isinstance(y, int):
        o = x, y
    else:
        o = midXY(x, y) if isCenter else minXY(x, y)
    # 0,0,0に横分割の単位元、1,0,1に縦分割の単位元がはいっている
    # 単位元で割ることで、何番目のマスに属するかを算出している
    hitX, hitY = int(o[0] // divArea[0]), int(o[1] // divArea[1])
    assert hitX < divArea[0]
    assert hitY < divArea[1]
    return hitX, hitY



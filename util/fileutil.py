from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import yaml, os, traceback
import subprocess as sp
import datetime as dt
import numpy as np
from glob import glob
import tensorflow as tf
from PIL import Image, ImageDraw, ImageFont

from . import printutil as pu
from . import vectorutil as vu


MACROSQURE = 16
# エメラルドグリーン
WEAKCOLOR = (71, 234, 126)
# ターコイズブルー
MEDIUMCOLOR = (67, 135, 233)
# ローズ
STRONGCOLOR = (255, 0, 55)

L_TEXTHEIGHT = 24
S_TEXTHEIGHT = 14
try:
    # raspiの時のみを考慮
    DEFAULT_FONT = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeMono.ttf', L_TEXTHEIGHT)
    IMAGE_FONT = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeMono.ttf', S_TEXTHEIGHT)
except:
    # macOS
    DEFAULT_FONT = ImageFont.truetype('/System/Library/Fonts/Keyboard.ttf', L_TEXTHEIGHT)
    IMAGE_FONT = ImageFont.truetype('/System/Library/Fonts/Keyboard.ttf', S_TEXTHEIGHT)
    pass

class FilePair(object):
    FIXEDBOX_EDGE = 64

    def __init__(self, img='', backcmp=False, fileInfo=None, fixedBox=None):
        self.printfunc = pu.PrintUtil(prefix=self.__class__.__name__, loglevel='DEBUG')
        if fileInfo is None:
            assert img != '', 'filename not found in args'
            self.__fileName = FileName(delegateFile=img, backcmp=backcmp)
        else:
            self.__fileName = FileName(fileInfo=fileInfo, backcmp=backcmp)
            pass

        if fixedBox is None:
            self.__fixedbox = (FilePair.FIXEDBOX_EDGE, FilePair.FIXEDBOX_EDGE)
        else:
            assert(isinstance(fixedBox, tuple))
            assert(len(fixedBox) == 2)
            self.__fixedbox = fixedBox
        self.__BKCMP = backcmp
        pass

    @property
    def name(self):
        return self.__fileName.name

    @property
    def image(self):
        return self.__fileName.files[0]

    @property
    def vector(self):
        return self.__fileName.files[1]

    @property
    def fixedbox(self):
        return self.__fixedbox

    @property
    def vectorasnpy(self):
        if not hasattr(self, '__vect'):
            self.__vect = np.load(self.vector)
        return self.__vect

    @property
    def xy(self):
        if not hasattr(self, '__xy'):
            # 内部仕様を封じ込める
            y, x = self.vectorasnpy[0][0] if not self.__BKCMP else self.vectorasnpy[0]
            # print('x=%d, y=%d'%(len(x), len(y)))
            self.__xy = (x, y)
        return self.__xy

    @property
    def motionFrame(self):
        if not hasattr(self, '__motionFrame'):
            x, y = self.xy
            self.__motionFrame = vu.motionFrame(x, y)
        return self.__motionFrame

    @property
    def cropFrame(self):
        if not hasattr(self, '__cropFrame'):
            x, y = self.xy
            self.__cropFrame = vu.cropedFrame(x, y, isCenter=True, box=self.fixedbox)
        return self.__cropFrame

    @property
    def motionInfo(self):
        """ 
        PILのDraw.rectangleの場合とcropとで座標仕様が違うので注意
        http://pillow.readthedocs.io/en/4.1.1/reference/ImageDraw.html
        """
        if not hasattr(self, '__motionInfo'):
            x, y = self.xy
            minPX, minPY = vu.minXY(x, y)
            maxPX, maxPY = vu.maxXY(x, y)
            scalars = np.array(self.vectorasnpy[1], dtype=np.int32)
            mean = scalars.mean()
            if mean < 5.0:
                fill = WEAKCOLOR
            elif mean < 15.0:
                fill = MEDIUMCOLOR
            else:
                fill = STRONGCOLOR
            self.__motionInfo = ((minPX, minPY), (maxPX, maxPY), fill)
        return self.__motionInfo

    @property
    def cropedImageAsTensor(self):
        if not hasattr(self, '__cropedImageAsTensor'):
            x, y = self.xy
            left, top = vu.minXY(x, y)
            w, h = self.fixedbox
            from . import imageutil as iu
            # Memo: isBinの扱いを自動にするか検討すること
            img = iu.openImageForTFfeature(_img=self.croppedImageAsPIL, isBin=False)
            record = tf.train.Example(features=tf.train.Features(
                        feature={
                            'image': tf.train.Feature(bytes_list=tf.train.BytesList(value=[img[3]])),
                            'height': tf.train.Feature(int64_list=tf.train.Int64List(value=[img[1]])),
                            'width' : tf.train.Feature(int64_list=tf.train.Int64List(value=[img[0]])),
                            'depth' : tf.train.Feature(int64_list=tf.train.Int64List(value=[img[2]])),
                            }
                        )
            )
            pu._print(self, record)
            self.__cropedImageAsTensor = record
        return self.__cropedImageAsTensor

    @property
    def croppedImageAsPIL(self) -> Image:
        if not hasattr(self, '__croppedImageAsPIL'):
            self.__croppedImageAsPIL = self.__cropImage(self.fixedbox)
        return self.__croppedImageAsPIL

    def __cropImage(self, fixedBox=None):
        try:
            img = Image.open(self.image)
            fname = os.path.basename(self.image)
            # pu._print(self, img.size)
            # pu._print(self, self.motionFrame)
            left, top, _, _ = self.cropFrame
            if fixedBox is None:
                fixedBox = (FilePair.FIXEDBOX_EDGE, FilePair.FIXEDBOX_EDGE)
            width, height = fixedBox
            return img.crop((left, top, left + width, top + height))
        except:
            pu._print(self, '%s was ignored!'%self.image)
            traceback.print_exc()
        finally:
            img.close()
            pass

    def PILCrop(self, outputDir, fixedBox=None):
        fname = os.path.basename(self.image)
        # pu._print(self, img.size)
        # pu._print(self, self.motionFrame)
        if fixedBox is None:
            fixedBox = self.fixedbox
        width, height = fixedBox
        # pu._print(self, os.path.join(outputDir, fname))
        cropped = self.__cropImage(fixedBox)
        if cropped.size == fixedBox:
            cropped.save(os.path.join(outputDir, fname))
        else:
            raise ValueError('Cropped box didn\'t correctly.')

    def drawDebugInfo(self, outputDir, meta=None):
        """ imgにdetect状況などのdebugInfoを書き込む 
        outputDir: 加工後の画像出力先
        meta: dict {str:str} tfなど外部から得られる文字列情報など
        矩形, 線幅, 色はvectから内部で算出
        """
        try:
            pu._print(self, '### Try to draw CV image %s ###'%self.name)
            fname = os.path.basename(self.image)
            img = Image.open(self.image).convert('RGBA')
            txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
            drawed = ImageDraw.Draw(img)
            minPos, maxPos, fill = self.motionInfo
            drawed.rectangle([minPos, maxPos], outline=fill)
            dtxt = ImageDraw.Draw(txt)
            txtPos = (minPos[0], minPos[1] - (S_TEXTHEIGHT * 1.4))
            dtxt.text((10, img.size[1] - L_TEXTHEIGHT), '%s'%(self.name), fill=(128, 128, 128, 255), font=DEFAULT_FONT)
            dtxt.text(txtPos, 'Debug: %s -> %s'%(minPos, maxPos), fill=fill, font=IMAGE_FONT)
            del drawed
            #Debug 
            pu._print(self, '### save drawed image %s ###'%fname)
            out = Image.alpha_composite(img, txt)
            # img.save(os.path.join(outputDir, fname), "JPEG")
            out.save(os.path.join(outputDir, fname))
        except:
            traceback.print_exc()
        finally:
            img.close()


class FileName(object):
    """ """
    ImageDir = 'img'
    VectorDir = 'vector'
    def __init__(self, delegateFile, fileInfo=None, backcmp=False):
        """ delegateFile はjpegもしくはnpyどちらでも良い
        fileInfo: (path, filelabel)  
        <CONTRACT/>
            - pathは{img, vector}の一段上を想定
            - filelabelは'{timestamp:%H-%M-%S}-{counter:02d}'を想定 
        """
        self.printfunc = pu.PrintUtil(prefix=self.__class__.__name__, loglevel='DEBUG')
        if fileInfo is None:
            path, fname = os.path.split(delegateFile)
            filelabel, ext = os.path.splitext(fname)
            self.__dir = os.path.join(path, '..')
        else:
            assert isinstance(fileInfo, tuple), 'fileInfo validation Assert Found!'
            path, filelabel = fileInfo
            self.__dir = path

        #pathとfilelabelは生成する
        self.__name = filelabel
        self.__BKCMP = backcmp
        pass

    @property
    def path(self):
        return self.__dir

    @property
    def vectortable(self):
        assert not hasattr(self, '__name'), 'prepare not yet'
        if not hasattr(self, '__vectortable'):
            self.__vectortable = vu.VectorReverseIndex(path=os.path.join(self.path, FileName.VectorDir))
        return self.__vectortable

    @property
    def name(self):
        return self.__name

    @property
    def imgPath(self):
        return os.path.join(self.__dir, FileName.ImageDir)

    @property
    def vectPath(self):
        return os.path.join(self.__dir, FileName.VectorDir)

    @property
    def imgFile(self):
        """ basename """
        if not hasattr(self, '__imgFile'):
            self.__imgFile = self.__name + '.jpeg'
        return self.__imgFile

    @property
    def vectFile(self):
        """ basename """
        # print('%s -> %s'%(self.imgFile, self.vectortable.queryVectFile))
        if not hasattr(self, '__vectFile'):
            self.__vectFile = self.vectortable.queryVectFile[self.imgFile] if not self.__BKCMP else self.__name + '.npy'
        return self.__vectFile

    @property
    def files(self):
        return (os.path.join(self.imgPath, self.imgFile),
                os.path.join(self.vectPath, self.vectFile))


def readYamlSetting(fileloc):
    """ 
    各YAML設定ファイルを読み込み
    この関数以外から個別に読み込まないこと 

    e.g., 
    somedict = fileutil.readYamlSetting('../settings/rpc.yml')
    """
    assert(fileloc != '')
    assert(os.path.isfile(fileloc))
    with open(fileloc, 'r') as f:
        try:
            yml = yaml.load(f)
            for k, v in yml.items():
                if isinstance(v, str):
                    yml[k] = v.replace('~', os.environ['HOME'] + '/')
        except:
            traceback.print_exc()
    return yml

def getGitInfo():
    os.chdir('.')
    return _getBranchStatus() + '\nMRC = %s'%getLastCommitId()

def _getBranchStatus():
    status = sp.check_output('/usr/bin/git status -b -s', shell=True).decode().rstrip().split('\n')
    branch = sp.check_output('/usr/bin/git branch|grep "*"', shell=True).decode().rstrip()
    print(status)
    print('>>' + branch)
    branch = branch.replace('*', '')
    if len(status) > 0:
        fileStatus = status[1:]
        branch += ' [%d NC]'%len(fileStatus)
    return branch

def getLastCommitId():
    return sp.check_output('/usr/bin/git log -1 --pretty=format:"%h"', shell=True).decode().rstrip()

def _makeOnlyFileNames(files):
    """Thesis: ファイル名のみの配列にする"""
    return [os.path.splitext(os.path.basename(f))[0] for f in files]

def searchNearlyFramePairs(startTime:dt.datetime, diffNSec:int=0, 
                            durationBySec:int=1, srcDir='/workspace/img-buff/motions'):
    """ startTimeから最低duration分のjpeg, npyファイルをFilePair配列で返す
    生成されたファイル名がわからない場合に使用する
    diffNSec : (True, N) -> start以降をN秒後からdurationBySec分のファイルを返す
               (False, N) -> start N秒前からdurationBySec分返す
    srcDir (CONTRACT): motions/{img, vector}/ 以下からファイルを検索する　<- FilePairの仕様
    return [FilePair]
    """
    assert durationBySec > 0, 'Illegal durationBySec was found!'
    # 想定されるjpegファイル名を仮想的に生成する
    baseNames = ['/img/' + (startTime + dt.timedelta(seconds=n)).strftime('%H-%M-%S') + \
                '-*.jpeg' for n in range(diffNSec, durationBySec)]
    wilds = [os.path.join(srcDir, b) for b in baseNames]
    # 実際に存在するファイルしか候補には挙がらないので、exists判定はしない
    globs = [glob(w) for w in wilds] # 2-Dで返ってくる
    files = []
    for exs in globs:
        # 1-Dへreshape np使った方が速い？
        [files.append(e) for e in exs]
    fps = [FilePair(f) for f in files]
    return fps

def findVectorFiles(seedTime, srcDir='/workspace/img-buff/motions', durationSec=0):
    time = seedTime.split('_')
    # %m%d_%H%M%S
    assert(len(time) == 2)
    l = [(i+j) for (i,j) in zip(time[1][::2],time[1][1::2])]
    assert(len(l) == 3)
    h, m, s = l[0], l[1], l[2]
    print('%s*.npy'%(h+m+s))
    asBaseDate = dt.datetime.strptime(h+m+s, '%H%M%S')
    files = []
    for proceed in range(durationSec):
        asDate = asBaseDate + dt.timedelta(seconds=proceed)
        files.append(glob(os.path.join(srcDir, '%s*.npy'%asDate.strftime('%H-%M-%S'))))
    return files


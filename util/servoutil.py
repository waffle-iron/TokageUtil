#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# this made for python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import traceback, time, pickle
from threading import Thread

try:
    import Adafruit_PCA9685
except:
    traceback.print_exc()

from util import printutil as pu
from util.vectorutil import MACROSQURE
from util.vectorutil import AREA_DIV, ScreenRatio
from util.vectorutil import CAM02_SHOOT_ORIGINS

CAM02_BIAS = (100, 140)
CAM02_SHOOT_AREADIV = AREA_DIV

ORIGINAL_TICK = 2

# Registers/etc:
PCA9685_ADDRESS = 0x40

def getServoControl(id:str, mainRes, subRes):
    if id == '01':
        servo = Servo(0, 4, (308, 310), mainRes, mainRes)
    elif id == '02':
        servo = Servo(3, 7, (280, 310), mainRes, subRes, True)
    else:
        raise ValueError
    servo.calibrate()
    return servo

def reset():
    # _ = Adafruit_PCA9685.PCA9685()
    pass

def set_servo_pulse(channel, pulse):
    pulse_length = 1000000    # 1,000,000 us per second
    pulse_length //= 60       # 60 Hz
    print('{0}us per period'.format(pulse_length))
    pulse_length //= 4096     # 12 bits of resolution
    print('{0}us per bit'.format(pulse_length))
    pulse *= 1000
    pulse //= pulse_length
    __pwm.set_pwm(channel, 0, pulse)

class Servo(object):
    RangeOfMotion = (0, 200)
    # H/W Info (Horizon, Vertical)
    def __init__(self, pwmPinH, pwmPinV, minimum, mainResolution, myResolution, tick=ORIGINAL_TICK):
        self.printfunc = pu.PrintUtil(prefix=self.__class__.__name__, loglevel='DEBUG')
        self.__horizon, self.__vertical = pwmPinH, pwmPinV
        self.__tick= (tick, tick)
        self.__pwm = Adafruit_PCA9685.PCA9685()
        self.__pwm.set_pwm_freq(60)
        # モーター個体差吸収
        self.__currentH, self.__currentV = self.__minH, self.__minV = minimum
        self.__myRes = myResolution
        self.__mainRes = mainResolution
        ORIGINAL_TICK = tick
        pass

    @property
    def servoId(self):
        return (self.__horizon, self.__vertical)

    @property
    def tick(self):
        return self.__tick
    @tick.setter
    def tick(self, val):
        assert isinstance(val, tuple)
        assert len(val) == 2
        self.__tick = val

    @property
    def mainRes(self):
        return self.__mainRes

    @property
    def myRes(self):
        return self.__myRes

    @property
    def isMainCam(self):
         return self.__myRes == self.__mainRes

    # cam台数が増えるようであれば、配列を考慮する
    @property
    def cam02_range(self):
        if not hasattr(self, '__02range'):
            self.__02range = (Servo.RangeOfMotion[1] - CAM02_BIAS[0])
        return self.__02range
    @property
    def cam02_domain(self):
        if not hasattr(self, '__02domain'):
            self.__02domain = (Servo.RangeOfMotion[1] - CAM02_BIAS[1])
        return self.__02domain

    @property
    def angleratioX(self):
        if not hasattr(self, '__xratio'):
            self.__xratio = (self.cam02_range / self.mainRes[0])
        return self.__xratio

    @property
    def angleratioY(self):
        if not hasattr(self, '__yratio'):
            self.__yratio = (self.cam02_domain / self.mainRes[1])
        return self.__yratio

    @property
    def horizonPos(self):
        return self.__currentH

    @horizonPos.setter
    def horizonPos(self, val):
        self.__currentH = val

    @property
    def verticalPos(self):
        return self.__currentV
    
    @verticalPos.setter
    def verticalPos(self, val):
        self.__currentV = val

    @property
    def verticalROM(self):
        min = self.__minV
        return (min + Servo.RangeOfMotion[0], min + Servo.RangeOfMotion[1])

    @property
    def horizonROM(self):
        min = self.__minH
        return (min + Servo.RangeOfMotion[0], min + Servo.RangeOfMotion[1])

    @property
    def relPosH(self):
        return self.horizonPos - self.horizonROM[0]
    @relPosH.setter
    def relPosH(self, val):
        self.horizonPos = val + self.horizonROM[0]
        self.__move(True, self.horizonPos)

    @property
    def relPosV(self):
        return self.verticalPos - self.verticalROM[0]
    @relPosV.setter
    def relPosV(self, val):
        self.verticalPos = val + self.verticalROM[0]
        self.__move(False, self.verticalPos)

    def calibrate(self):
        self.__move(True, self.__currentH)
        self.__move(False, self.__currentV)

    def __panRange(self, diff:int, ratio):
        """ 前後10%と80%に分ける """
        slowzone1, slowzone2 = diff * ratio[0] / 100, diff * ratio[1] / 100
        fastzone = int(diff - (slowzone1 + slowzone2))
        # (slow, fast + diff - (slow * 2 + fast), slow)
        return (int(slowzone1), fastzone, int(slowzone2))

    def __panTripleZone(self, movzone, f, iRatio=(0.1, 0.1, 0.1)):
        """ fはfunction """
        div = 2
        assert movzone >= 0, 'movzone must be positive number'
        start, fast, end = self.__panRange(movzone, (10, 20))
        origTick = ORIGINAL_TICK
        try:
            tick = origTick // div
            self.__action(f, tick, range(0, start // tick), iRatio[0])
            tick = origTick
            self.__action(f, tick, range(0, fast // tick), iRatio[1])
            tick = origTick // div
            self.__action(f, tick, range(0, end // tick), iRatio[2])
        except:
            traceback.print_exc()
        pass

    def __action(self, f, t, r, i):
        for x in r:
            f(t)
            time.sleep(i)
        pass

    def __movRatio(self, a):
        """ 3zone各movementのインターバル"""
        return (0.1, 0.05, 0.15) if abs(a) > 100 else (0.2, 0.2, 0.2)

    def panH(self, rel):
        """ relは相対座標 (0, Servo.RangeOfMotion[1]] """
        if not self.__checkRange(rel, True):
            self.print('Horizon ROM overflow! %d'%rel)
        a = rel - self.relPosH
        if a == 0:
            return
        f = self.panLeft if a > 0 else self.panRight
        self.__panTripleZone(abs(a), f, self.__movRatio(a))
        pass

    def panV(self, rel):
        """ relは相対座標 (0, Servo.RangeOfMotion[1]] """
        if not self.__checkRange(rel, False):
            self.print('Vertical ROM overflow! %d'%rel)
        a = rel - self.relPosV
        if a == 0:
            return
        f = self.panDown if a > 0 else self.panUp
        self.__panTripleZone(abs(a), f, self.__movRatio(a))
        pass

    def __checkRange(self, rel, isH:bool, minmax=None) -> bool:
        # V,Hでrangeガ違う場合はisH使うこと
        min, max = Servo.RangeOfMotion if minmax is None else minmax
        idx = 0 if isH else 1
        return (rel > min - self.tick[idx]) and (rel < max + self.tick[idx])

    def panRight(self, tick):
        if self.horizonPos > self.horizonROM[0]:
            self.horizonPos -= tick
        else:
            self.print('horizon position under min range')
        self.__move(True, self.horizonPos)
        pass

    def panLeft(self, tick):
        if self.horizonPos < self.horizonROM[1]:
            self.horizonPos += tick
        else:
            self.print('horizon position over max range')
        self.__move(True, self.horizonPos)
        pass

    def panUp(self, tick):
        if self.verticalPos > self.verticalROM[0]:
            self.verticalPos -= tick
        else:
            self.print('vertical position under min range')
        self.__move(False, self.verticalPos)
        pass

    def panDown(self, tick):
        if self.verticalPos < self.verticalROM[1]:
            self.verticalPos += tick
        else:
            self.print('vertical position over max range')
        self.__move(False, self.verticalPos)
        pass

    def move(self, h, pos):
        """ Debug method"""
        self.__move(h, pos)

    def __move(self, horizon:bool, pos):
        id = 0 if horizon else 1
        self.__pwm.set_pwm(self.servoId[id], 0, pos)

    def pan(self, h, v):
        """ h, v両方同時に稼働 """
        Ths = []
        if self.relPosH != h:
            Ths.append(Thread(target=self.panH, args=(h,)))
        if self.relPosV != v:
            Ths.append(Thread(target=self.panV, args=(v,)))
        self.print('Servo %s: I\'ll turn to %s, %s from %s, %s'%(self.servoId, h, v, self.relPosH, self.relPosV))
        if len(Ths) == 0:
            self.print('Ignore this moving!')
            return
        try:
            [t.start() for t in Ths]
            # timeout以内に回転が終わることを想定
            [t.join(0.5) for t in Ths]
            # 最終回転角保証
            #self.relPosH, self.relPosV = h, v
            reset()
        except:
            self.print(traceback.format_exc())
        pass

    def trackCamAngle(self, origin):
        if self.isMainCam:
            raise EnvironmentError
        h, v = self._getOriginAsServoCam(origin)
        try:
            self.pan(h, v) # Threadがスタックすることがある？
        except:
            self.print('Illegal Point h:%d v:%d'%(h, v))
        reset()
        pass

    def shootArea(self, areaId):
        assert len(areaId) == 2
        # assert (areaId[0] + 1) * (areaId[1] + 1) <= (CAM02_SHOOT_AREADIV[0] * CAM02_SHOOT_AREADIV[1])
        h, v = CAM02_SHOOT_ORIGINS[areaId[1]][areaId[0]]
        try:
            self.pan(h, v) # Threadがスタックすることがある？
        except:
            self.print('Illegal Point h:%d v:%d'%(h, v))
        reset()
        pass

    def _getOriginAsServoCam(self, origin):
        """ 
        このカメラにおける、mainScreenのmotion vector座標に対応した座標を返す
        origin: motionvectorから得られた向かせたい座標
        (MACROSQUREはかかっていること前提 -> 1280x720空間で飛んでくる)
        cam02 固有値として、  x: [100, 200]
                            y: [140, 200]
        をとるものとする
        ただし、カメラ位置に依存する
        """
        assert len(origin) == 2, 'Caught Illegal Value: %s'%origin
        # 左右が反転するため、x成分はROMから引く x, y ともにbiasを足す
        tgtX = (self.cam02_range - int((origin[0] - CAM02_RESOLUTION[0] / 2) * self.angleratioX)) + CAM02_BIAS[0]
        tgtY = int((origin[1] - CAM02_RESOLUTION[1] / 2 * self.angleratioY)) + CAM02_BIAS[1]
        return tgtX, tgtY

    def print(self, message):
        pu._print(obj=self, message=message)
        pass

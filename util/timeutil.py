#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# this made for python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime as dt
import time, traceback

def printTimeStamp(obj=None, msg='', who=''):
    TODAY = generateTimeStamp()
    str = '%s %s'%(msg, TODAY)
    if who is not '':
        str += ' [ from %s ]'%who
    if obj is None:
        print(str)
    else:
        from . import printutil as pu
        pu._print(obj, message=str)
    pass

def timedeltaFrom(aTime):
    assert(isinstance(aTime, dt.datetime))
    return dt.datetime.now() - aTime

def generateTimeStamp(asStr=True, format='%Y-%m-%dT%H%M%S %Z'):
    aDatetime = dt.datetime.now()
    if asStr:
        return aDatetime.strftime('%s'%format)
    else:
        return aDatetime

def synthTimeStamp(base, proceed, format='%H%M%S'):
    aDateTime = dt.datetime.strptime(base, format)
    return aDatetime

def datetimeFromEpochFloat(epochFloat):
    # tzinfoがある場合とない場合で、比較時TypeErrorとなるので注意
    # 強制的にutcを入れる手もある
    epochFromFloat = time.localtime(epochFloat)
    # pu._print(epochFromFloat, False)
    # pu._print(tuple(epochFromFloat[:6]), False)
    return dt.datetime(*epochFromFloat[:6])
    # pu._print(ret, False)
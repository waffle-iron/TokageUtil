from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys, os, traceback, logging

try:
    from . import timeutil as tu
except:
    print('timeutil import twice? %s'%traceback.format_exc())

LOGDIR = '/workspace/log/'
levelsigns = {'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'CRITICAL': logging.CRITICAL,
                'ERROR': logging.ERROR}

CONSOLE_COLORS = {
    'BLUE': '\033[94m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'END': '\033[0m',
}

def colored(color, msg):
    assert color in CONSOLE_COLORS, 'color not registed! %s'%color
    return '%s%s%s'%(CONSOLE_COLORS[color], msg, CONSOLE_COLORS['END'])

# e,g,,
# print WARNING + 'Warning' + ENDC
# print FAIL + 'Fail' + ENDC

def _print(obj=None, message='', DebugFlag=True, loglevel='DEBUG'):
    if DebugFlag:
        if obj is not None and hasattr(obj, 'printfunc'):
            obj.printfunc.print(message, loglevel)
        else:
            print(message)
    pass

def _printTraceBacks(obj=None, msg=''):
    if obj is not None and hasattr(obj, 'printfunc'):
        _print(obj=obj, message='%s:'%msg, DebugFlag=True, loglevel='INFO')
        obj.printfunc.exception(traceback.format_exc())

class PrintUtil(object):
    """ CONTRACT: printfuncというインスタンスとして委譲すること """
    def __init__(self, logDir=LOGDIR, prefix='basic', ext='.log', loglevel='DEBUG'):
        timestamp = tu.generateTimeStamp().rstrip()
        FORMAT = '%(asctime)-15s %(levelname)-8s: %(message)s'
        logging.basicConfig(format=FORMAT,
                         filename=os.path.join(logDir, '%s%s%s'%(prefix, timestamp, ext)), 
                         level=levelsigns[loglevel])
        self.logID = prefix
        self.logger = logging.getLogger(self.logID)
        self.logger.debug('Start logging')
        pass

    def print(self, message='', ll='DEBUG'):
        # funcs = {'INFO': self.logger.info,
        #         'DEBUG': self.logger.debug,
        #        'WARNING': self.logger.warning,
        #        'CRITICAL': self.logger.critical,
        #        'ERROR': self.logger.error}
        # funcs[loglevel](message)
        if ll == 'INFO':
            logging.getLogger(self.logID).info(message)
        elif ll == 'DEBUG':
            logging.getLogger(self.logID).debug(message)
        elif ll == 'WARNING':
            logging.getLogger(self.logID).warning(message)
        elif ll == 'CRITICAL':
            logging.getLogger(self.logID).critical(message)
        elif ll == 'ERROR':
            logging.getLogger(self.logID).error(message)
        pass

    def exception(self, err):
        logging.getLogger(self.logID).info('Exception\n%s'%err)
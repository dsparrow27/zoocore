import logging
import os


class CentralLogManager(object):
    """This class is a singleton object that globally handles logging, any log added will managed by the class
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if CentralLogManager._instance is None:
            CentralLogManager._instance = super(CentralLogManager, cls).__new__(cls, *args, **kwargs)
        return CentralLogManager._instance

    def __init__(self):
        self.logs = {"root": logging.root}

    def addLog(self, logger):
        if logger.name not in self.logs:
            self.logs[logger.name] = logger

    def removeLog(self, loggerName):
        if loggerName in self.logs:
            del self.logs[loggerName]

    def changeLevel(self, loggerName, level):
        if loggerName in self.logs:
            log = self.logs[loggerName]
            if log.level != level:
                log.setLevel(level)

    def setFormatter(self, handler, formatString):
        handler.setFormatter(formatString)


def logLevels():
    return [logging.getLevelName(n) for n in xrange(0, logging.CRITICAL + 1, 10)]


def levelsDict():
    return dict(zip(logLevels(), range(0, logging.CRITICAL + 1, 10)))


def getLogger(name):
    logger = logging.getLogger(name)
    globalLogLevelOverride(logger)
    CentralLogManager().addLog(logger)
    return logger


def globalLogLevelOverride(logger):
    globalLoggingLevel = os.environ.get("ZOO_LOG_LEVEL")
    if globalLoggingLevel:
        envLvl = levelsDict()[globalLoggingLevel]
        currentLevel = logger.getEffectiveLevel()

        if not currentLevel or currentLevel != envLvl:
            logger.setLevel(envLvl)


def reloadLoggerHierarchy():
    for log in logging.Logger.manager.loggingDict.values():
        if hasattr(log, "children"):
            del log.children
    for name, log in logging.Logger.manager.loggingDict.items():
        if not isinstance(log, logging.Logger):
            continue

        try:
            if log not in log.parent.children:
                log.parent.children.append(log)
        except AttributeError:
            log.parent.children = [log]


zooLogger = getLogger("zoocore")
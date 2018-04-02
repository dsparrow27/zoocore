"""
root
    |-hotkeys
    |-tools
        |- toolName
                |-settingOne.json
                |SettingTwoFolder
                            |-setting.json


"""
import os
import logging
import copy
from collections import OrderedDict

from zoo.libs.utils import filesystem
from zoo.libs.utils import file, path

logger = logging.getLogger(__name__)
# global storage of root paths which store tooldata
# {"name": path}
ROOTS = OrderedDict()


class RootAlreadyExistsError(Exception):
    pass


class InvalidSettingsPath(Exception):
    pass


class InvalidRootError(Exception):
    pass


class ToolSet(object):
    """
    Example::
        Create some roots
        >>> tset = ToolSet()
        # the order you add roots is important
        >>> tset.addRoot(os.path.expanduser("~/Documents/maya/2018/scripts/zootools_preferences"), "userPreferences")
        # create a settings instance, if one exists already within one of the roots that setting will be used unless you
        # specify the root to use, in which the associated settingsObject for the root will be returned
        >>> newSetting = tset.createSetting(relative="tools/tests/helloworld",
        ...                                root="userPreferences",
        ...                                data={"someData": "hello"})
        >>> print os.path.exists(newSetting.path())
        >>> print newSetting.path()
        # lets open a setting
        >>> foundSetting = tset.findSetting(relative="tools/tests/helloworld", root="userPreferences")

    """

    def addRoot(self, fullPath, name):
        if name in ROOTS:
            raise RootAlreadyExistsError("Root already exists: {}".format(name))
        ROOTS[name] = path.Path(fullPath)

    def findSetting(self, relativePath, root=None):
        """ finds a settings object by searching the roots in reverse order.

        The first path to exist will be the one to be resolved. If a root is specified
        and the root+relativePath exists then that will be returned instead

        :param relativePath:
        :type relativePath:
        :param root:
        :type root:
        :return:
        :rtype:
        """
        if root is not None:
            rootPath = ROOTS.get(root)
            if rootPath is not None:
                fullpath = rootPath / relativePath
                if not fullpath.exists():
                    return SettingObject(root, relativePath)
                return SettingObject.open(root, relativePath)
        else:
            for name, path in reversed(ROOTS.items()):
                # we're working with an ordered dict
                fullpath = path / relativePath
                if not fullpath.exists():
                    continue
                return SettingObject.open(name, relativePath)

        return SettingObject(root, relativePath)

    def createSetting(self, relative, root, data):
        setting = self.findSetting(relative, root)
        setting.update(data)
        setting.save()
        return setting


class SettingObject(dict):
    """Settings class to encapsulate the json data for a given setting
    """

    def __init__(self, root, relativePath=None, **kwargs):
        kwargs["relativePath"] = relativePath or ""
        kwargs["root"] = root
        super(SettingObject, self).__init__(**kwargs)

    def rootPath(self):
        if self.root and self.root in ROOTS:
            return ROOTS[self.root]
        return path.Path()

    def path(self):
        return self.rootPath() / self["relativePath"]

    def isValid(self):
        if self.root is None:
            return False
        elif (self.rootPath() / self.relativePath).exists():
            return True
        return False

    def __repr__(self):
        return "<{}> root: {}, path: {}".format(self.__class__.__name__, self.rootPath(), self.relativePath)

    def __cmp__(self, other):
        return self.name == other and self.version == other.version

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return super(SettingObject, self).__getattribute__(item)

    def __setattr__(self, key, value):
        self[key] = value

    def save(self):
        root = self.rootPath()

        if not root:
            return path.Path()
        fullPath = root / self.relativePath
        filesystem.ensureFolderExists(os.path.dirname(str(fullPath)))
        output = copy.deepcopy(self)
        del output["root"]
        del output["relativePath"]
        exts = fullPath.getExtension(True)
        if not exts:
            fullPath.setExtension("json", True)
        file.saveJson(output, str(fullPath))
        return self.path()

    @classmethod
    def open(cls, root, relativePath):
        rootPath = str(ROOTS[root])
        fullPath = os.path.join(rootPath, relativePath)
        if not os.path.exists(fullPath):
            raise InvalidSettingsPath(fullPath)
        data = file.loadJson(fullPath)
        return cls(root, relativePath, **data)

import re
from maya.api import OpenMaya as om2
from zoo.libs.maya.api import attrtypes
import contextlib


def asMObject(name):
    """ Returns the MObject from the given name

    :param name: The name to get from maya to convert to an mobject
    :type name: str
    :return: The mobject for the given str
    :rtype: MObject
    """
    sel = om2.MSelectionList()
    sel.add(name)
    plug = sel.getPlug(0)

    return plug.asMObject()


def asMPlug(name):
    """returns the MPlug instance for the given name

    :param name: The mobject to convert to MPlug
    :rtype name: str
    :return: MPlug, or None
    """
    try:
        names = name.split(".")
        sel = om2.MSelectionList()
        sel.add(names[0])
        node = om2.MFnDependencyNode(sel.getDependNode(0))
        return node.findPlug(".".join(names[1:]), False)
    except RuntimeError:
        sel = om2.MSelectionList()
        sel.add(str(name))
        return sel.getPlug(0)


def connectPlugs(source, destination):
    """Connects to MPlugs together

    :param source: MObject
    :param destination: MObject
    """
    mod = om2.MDGModifier()
    mod.connect(source, destination)
    mod.doIt()


def disconnectPlug(plug, source=True, destination=True):
    dep = om2.MFnDependencyNode(plug.node())
    changedNodeState = False
    if dep.isLocked:
        dep.isLocked = False
        changedNodeState = True
    if plug.isLocked:
        plug.isLocked = False
    mod = om2.MDGModifier()
    if source and plug.isDestination:
        if plug.source().isLocked:
            plug.source().isLocked = False
        mod.disconnect(plug.source(), plug)
    if destination and plug.isSource:
        for conn in plug.destinations():
            if conn.isLocked:
                conn.isLocked = False
            mod.disconnect(conn, plug)
    mod.doIt()
    if changedNodeState:
        dep.isLocked = True
    return True


def isValidMPlug(plug):
    """Checks whether the MPlug is valid in the scene

    :param plug: OpenMaya.MPlug
    :return: bool
    """
    return True if not plug.isNull else False


@contextlib.contextmanager
def setLockedContext(plug):
    if plug.isLocked:
        plug.isLocked = False
    yield
    plug.isLocked = True


def setLockState(plug, state):
    if plug.isLocked != state:
        plug.isLocked = state
        return True
    return False


def filterConnected(plug, filter):
    filteredNodes = []
    if not plug.isConnected:
        return []
    for connected in plug.connectedTo(False, True) + plug.connectedTo(True, False):
        grp = re.search(filter, connected.name())
        if grp:
            filteredNodes.append(connected)
    return filteredNodes


def filterConnectedNodes(plug, filter, source=True, destination=False):
    filteredNodes = []
    if (source and not plug.isSource) or (destination and not plug.isDestination):
        return []
    destinations = []
    if destination and plug.isDestination:
        destinations.extend(plug.connectedTo(False, True))
    if source and plug.isSource:
        destinations.extend(plug.connectedTo(True, False))
    for connected in destinations:
        node = connected.node()
        if node.hasFn(om2.MFn.kDagNode):
            dep = om2.MFnDagNode(node)
            name = dep.fullPathName()
        else:
            dep = om2.MFnDependencyNode(node)
            name = dep.name()
        grp = re.search(filter, name)
        if grp:
            filteredNodes.append(connected)
    return filteredNodes


def iterDependencyGraph(plug, alternativeName="", depthLimit=256, transverseType="down"):
    """This recursive function walks the dependency graph based on the name. so each node it visits if that attribute
    exists it will be return.
    example connections : nodeA.test -> nodeB.test -> nodeC.test
    [nodeA,nodeB, nodeC] will be return as a generator

    :param plug:
    :type plug: om2.MPlug
    :param alternativeName:
    :type alternativeName: str
    :param depthLimit:
    :type depthLimit: int
    :return:
    :rtype: generator(MObject)
    """

    plugSearchname = alternativeName or plug.partialName(useLongNames=True)
    if transverseType == "down":
        connections = plug.destinations()
    else:
        connections = [plug.source()]
    for connection in connections:
        node = connection.node()
        dep = om2.MFnDependencyNode(node)
        if not dep.hasAttribute(plugSearchname):
            continue
        nodePlug = dep.findPlug(plugSearchname, False)
        if depthLimit < 1:
            return
        yield nodePlug
        if nodePlug.isConnected:
            for i in iterDependencyGraph(nodePlug, plugSearchname, depthLimit=depthLimit - 1,
                                         transverseType=transverseType):
                yield i


def serializePlug(plug, includeSourceConnections=False, includeDestinationConnections=False):
    """Take's a plug and serializes all necessary information into a dict.
    :param plug: the valid MPlug to serialize
    :type plug: MPlug
    :param includeSourceConnections: if  True then we serialize any connections if this plug is the destination
    :type includeSourceConnections: bool
    :param includeDestinationConnections: if  True then we serialize any connections if this plug is the source
    :type includeDestinationConnections: bool
    :return: with out connection data {name: str, "isDynamic": bool, "default": type,
                                      "min": type, "max": type, "softMin": type, "softMax": type}
    :rtype: dict
    """
    data = {"name": plug.partialName(includeNonMandatoryIndices=True, useLongNames=True)}
    if plug.isDynamic:
        data.update({"isDynamic": True, "default": plugDefault(plug), "min": getPlugMin(plug), "max": getPlugMax(plug),
                     "softMin": getSoftMin(plug), "softMax": getSoftMax(plug)})
    else:
        data["isDynamic"] = False
    data.update({"channelBox": plug.isChannelBox, "keyable": plug.isKeyable,
                 "locked": plug.isLocked, "type": plugType(plug), "value": getPythonTypeFromPlugValue(plug)})
    if includeSourceConnections and plug.isDestination:
        source = plug.source()
        node = source.node()
        if node.hasFn(om2.MFn.kDagNode):
            nodeName = om2.MFnDagNode(node).fullPathName()
        else:
            nodeName = om2.MFnDependencyNode(node).name()
        data["inConnections"] = (nodeName, source.partialName(includeNonMandatoryIndices=True, useLongNames=True))
    if includeDestinationConnections and plug.isSource:
        destinations = plug.destinations()
        outConnections = []
        for conn in destinations:
            node = conn.node()
            if node.hasFn(om2.MFn.kDagNode):
                nodeName = om2.MFnDagNode(node).fullPathName()
            else:
                nodeName = om2.MFnDependencyNode(node).name()
            outConnections.append((nodeName, conn.partialName(includeNonMandatoryIndices=True, useLongNames=True)))
        if outConnections:
            data["outConnections"] = outConnections
    return data


def enumNames(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return [attr.fieldName(i) for i in xrange(attr.getMax())]
    return []


def enumIndices(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return [attr.fieldValue(i) for i in xrange(attr.getMax())]


def plugDefault(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        return attr.default
    elif obj.hasFn(om2.MFn.kTypedAttribute):
        attr = om2.MFnTypedAttribute(obj)
        default = attr.default
        if default.apiType() == om2.MFn.kInvalid:
            return None
        elif default.apiType() == om2.MFn.kStringData:
            return om2.MFnStringData(default).string()
        return default
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        return attr.default
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return attr.default
    return None


def setPlugDefault(plug, default):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        attr.default = default
        return True
    elif obj.hasFn(om2.MFn.kTypedAttribute):
        if not isinstance(default, om2.MObject):
            raise ValueError(
                "Wrong type passed to MFnTypeAttribute must be on type MObject, received : {}".format(type(default)))
        attr = om2.MFnTypedAttribute(obj)
        attr.default = default
        return True
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        if not isinstance(default, (om2.MAngle, om2.MDistance, om2.MTime)):
            raise ValueError(
                "Wrong type passed to MFnUnitAttribute must be on type MAngle,MDistance or MTime, received : {}".format(
                    type(default)))
        attr = om2.MFnUnitAttribute(obj)
        attr.default = default
        return True
    elif obj.hasFn(om2.MFn.kMatrixAttribute):
        if not isinstance(default, (om2.MMatrix, om2.MFloatMatrix)):
            raise ValueError(
                "Wrong type passed to MFnMatrixAttribute must be on type MMatrix or MFloatMatrix, received : {}".format(
                    type(default)))
        attr = om2.MFnMatrixAttribute(obj)
        attr.default = default
        return True
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        if not isinstance(default, (int, str)):
            raise ValueError(
                "Wrong type passed to MFnEnumAttribute must be on type int or float, received : {}".format(
                    type(default)))
        attr = om2.MFnEnumAttribute(obj)
        if isinstance(default, int):
            attr.default = default
        else:
            attr.setDefaultByName(default)
        return True
    return False


def hasPlugMin(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        return attr.hasMin()
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        return attr.hasMin()
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return attr.hasMin()
    return False


def hasPlugMax(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        return attr.hasMax()
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        return attr.hasMax()
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return attr.hasMax()
    return False


def hasPlugSoftMin(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        return attr.hasSoftMin()
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        return attr.hasSoftMin()
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return attr.hasSoftMin()
    return False


def hasPlugSoftMax(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        return attr.hasSoftMin()
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        return attr.hasSoftMin()
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return attr.hasSoftMin()
    return False


def getPlugMin(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        if attr.hasMin():
            return attr.getMin()
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        if attr.hasMin():
            return attr.getMin()
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return attr.getMin()


def getPlugMax(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        if attr.hasMax():
            return attr.getMax()
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        if attr.hasMax():
            return attr.getMax()
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        attr = om2.MFnEnumAttribute(obj)
        return attr.getMax()


def getSoftMin(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        if attr.hasSoftMin():
            return attr.getSoftMin()
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        if attr.hasSoftMin():
            return attr.getSoftMin()


def setSoftMin(plug, value):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        attr.setSoftMin(value)
        return True
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        attr.setSoftMin(value)
        return True
    return False


def getSoftMax(plug):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        if attr.hasSoftMax():
            return attr.getSoftMax()
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        if attr.hasSoftMax():
            return attr.getSoftMax()


def setSoftMax(plug, value):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        attr.setSoftMax(value)
        return True
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        attr.setSoftMax(value)
        return True
    return False


def setMin(plug, value):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        attr.setMin(value)
        return True
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        attr.setMin(value)
        return True
    return False


def setMax(plug, value):
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        attr.setMax(value)
        return True
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        attr.setMax(value)
        return True
    return False


def getPlugValue(plug):
    return getPlugAndType(plug)[1]


def getPlugAndType(plug):
    """Given an MPlug, get its value

    :param plug: MPlug
    :return the dataType of the given plug. Will return standard python types where necessary eg. float else maya type
    """
    obj = plug.attribute()

    if plug.isArray:
        count = plug.evaluateNumElements()
        res = [None] * count, [None] * count
        data = [getPlugAndType(plug.elementByPhysicalIndex(i)) for i in xrange(count)]
        for i in xrange(len(data)):
            res[0][i] = data[i][0]
            res[1][i] = data[i][1]
        return res

    if obj.hasFn(om2.MFn.kNumericAttribute):
        return getNumericValue(plug)

    elif obj.hasFn(om2.MFn.kUnitAttribute):
        uAttr = om2.MFnUnitAttribute(obj)
        ut = uAttr.unitType()
        if ut == om2.MFnUnitAttribute.kDistance:
            return attrtypes.kMFnUnitAttributeDistance, plug.asMDistance()
        elif ut == om2.MFnUnitAttribute.kAngle:
            return attrtypes.kMFnUnitAttributeAngle, plug.asMAngle()
        elif ut == om2.MFnUnitAttribute.kTime:
            return attrtypes.kMFnUnitAttributeTime, plug.asMTime()
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        return attrtypes.kMFnkEnumAttribute, plug.asInt()
    elif obj.hasFn(om2.MFn.kTypedAttribute):
        return getTypedValue(plug)
    elif obj.hasFn(om2.MFn.kMessageAttribute):
        return attrtypes.kMFnMessageAttribute, None

    if plug.isCompound:
        count = plug.numChildren()
        res = [None] * count, [None] * count
        data = [getPlugAndType(plug.child(i)) for i in xrange(count)]
        for i in xrange(len(data)):
            res[0][i] = data[i][0]
            res[1][i] = data[i][1]
        return res

    return None, None


def getNumericValue(plug):
    obj = plug.attribute()
    nAttr = om2.MFnNumericAttribute(obj)
    dataType = nAttr.numericType()
    if dataType == om2.MFnNumericData.kBoolean:
        return attrtypes.kMFnNumericBoolean, plug.asBool()
    elif dataType == om2.MFnNumericData.kByte:
        return attrtypes.kMFnNumericByte, plug.asBool()
    elif dataType == om2.MFnNumericData.kShort:
        return attrtypes.kMFnNumericShort, plug.asShort()
    elif dataType == om2.MFnNumericData.kInt:
        return attrtypes.kMFnNumericInt, plug.asInt()
    elif dataType == om2.MFnNumericData.kLong:
        return attrtypes.kMFnNumericLong, plug.asInt()
    elif dataType == om2.MFnNumericData.kDouble:
        return attrtypes.kMFnNumericDouble, plug.asDouble()
    elif dataType == om2.MFnNumericData.kFloat:
        return attrtypes.kMFnNumericFloat, plug.asFloat()
    elif dataType == om2.MFnNumericData.kAddr:
        return attrtypes.kMFnNumericAddr, plug.asAddr()
    elif dataType == om2.MFnNumericData.kChar:
        return attrtypes.kMFnNumericChar, plug.asChar()
    elif dataType == om2.MFnNumericData.k2Double:
        return attrtypes.kMFnNumeric2Double, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k2Float:
        return attrtypes.kMFnNumeric2Float, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k2Int:
        return attrtypes.kMFnNumeric2Int, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k2Long:
        return attrtypes.kMFnNumeric2Long, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k2Short:
        return attrtypes.kMFnNumeric2Short, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k3Double:
        return attrtypes.kMFnNumeric3Double, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k3Float:
        return attrtypes.kMFnNumeric3Float, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k3Int:
        return attrtypes.kMFnNumeric3Int, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k3Long:
        return attrtypes.kMFnNumeric3Long, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k3Short:
        return attrtypes.kMFnNumeric3Short, om2.MFnNumericData(plug.asMObject()).getData()
    elif dataType == om2.MFnNumericData.k4Double:
        return attrtypes.kMFnNumeric4Double, om2.MFnNumericData(plug.asMObject()).getData()
    return None, None


def getTypedValue(plug):
    """Returns the maya type from the given typedAttributePlug

    :param plug: MPLug
    :return: maya type
    """
    tAttr = om2.MFnTypedAttribute(plug.attribute())
    dataType = tAttr.attrType()
    if dataType == om2.MFnData.kInvalid:
        return None, None
    elif dataType == om2.MFnData.kString:
        return attrtypes.kMFnDataString, plug.asString()
    elif dataType == om2.MFnData.kNumeric:
        return getNumericValue(plug)
    elif dataType == om2.MFnData.kMatrix:
        return attrtypes.kMFnDataMatrix, om2.MFnMatrixData(plug.asMObject()).matrix()
    elif dataType == om2.MFnData.kFloatArray:
        return attrtypes.kMFnDataFloatArray, om2.MFnFloatArrayData(plug.asMObject()).array()
    elif dataType == om2.MFnData.kDoubleArray:
        return attrtypes.kMFnDataDoubleArray, om2.MFnDoubleArrayData(plug.asMObject()).array()
    elif dataType == om2.MFnData.kIntArray:
        return attrtypes.kMFnDataIntArray, om2.MFnIntArrayData(plug.asMObject()).array()
    elif dataType == om2.MFnData.kPointArray:
        return attrtypes.kMFnDataPointArray, om2.MFnPointArrayData(plug.asMObject()).array()
    elif dataType == om2.MFnData.kVectorArray:
        return attrtypes.kMFnDataVectorArray, om2.MFnVectorArrayData(plug.asMObject()).array()
    elif dataType == om2.MFnData.kStringArray:
        return attrtypes.kMFnDataStringArray, om2.MFnStringArrayData(plug.asMObject()).array()
    elif dataType == om2.MFnData.kMatrixArray:
        return attrtypes.kMFnDataMatrixArray, om2.MFnMatrixArrayData(plug.asMObject()).array()
    return None, None


def setAttr(plug, value):
    """
    Sets the given plug's value to the passed in value.

    :param plug: MPlug, The node plug.
    :param value: type, Any value of any data type.
    """

    if plug.isArray:
        for i in range(plug.evaluateNumElements()):
            setAttr(plug.elementByPhysicalIndex(i), value[i])
        return
    elif plug.isCompound:
        for i in range(plug.numChildren()):
            setAttr(plug.child(i), value[i])
        return
    obj = plug.attribute()
    if obj.hasFn(om2.MFn.kUnitAttribute):
        attr = om2.MFnUnitAttribute(obj)
        ut = attr.unitType()
        if ut == om2.MFnUnitAttribute.kDistance:
            plug.setMDistance(om2.MDistance(value))
        elif ut == om2.MFnUnitAttribute.kTime:
            plug.setMTime(om2.MTime(value))
        elif ut == om2.MFnUnitAttribute.kAngle:
            plug.setMAngle(om2.MAngle(value))
    elif obj.hasFn(om2.MFn.kNumericAttribute):
        attr = om2.MFnNumericAttribute(obj)
        at = attr.numericType()
        if at in (om2.MFnNumericData.k2Double, om2.MFnNumericData.k2Float, om2.MFnNumericData.k2Int,
                  om2.MFnNumericData.k2Long, om2.MFnNumericData.k2Short, om2.MFnNumericData.k3Double,
                  om2.MFnNumericData.k3Float, om2.MFnNumericData.k3Int, om2.MFnNumericData.k3Long,
                  om2.MFnNumericData.k3Short, om2.MFnNumericData.k4Double):
            data = om2.MFnNumericData().create(value)
            plug.setMObject(data.object())
        elif at == om2.MFnNumericData.kDouble:
            plug.setDouble(value)
        elif at == om2.MFnNumericData.kFloat:
            plug.setFloat(value)
        elif at == om2.MFnNumericData.kBoolean:
            plug.setBool(value)
        elif at == om2.MFnNumericData.kChar:
            plug.setChar(value)
        elif at in (om2.MFnNumericData.kInt, om2.MFnNumericData.kInt64, om2.MFnNumericData.kLong,
                    om2.MFnNumericData.kLast):
            plug.setInt(value)
        elif at == om2.MFnNumericData.kShort:
            plug.setInt(value)

    elif obj.hasFn(om2.MFn.kEnumAttribute):
        plug.setInt(value)

    elif obj.hasFn(om2.MFn.kTypedAttribute):
        attr = om2.MFnTypedAttribute(obj)
        at = attr.attrType()
        if at == om2.MFnData.kMatrix:
            mat = om2.MFnMatrixData(plug.asMObject())
            newMat = mat.create(value)
            plug.setMObject(newMat)
        elif at == om2.MFnData.kString:
            plug.setString(value)

    elif obj.hasFn(om2.MFn.kMessageAttribute) and isinstance(value, om2.MPlug):
        # connect the message attribute
        connectPlugs(plug, value)
    else:
        raise ValueError(
            "Currently we don't support dataType ->%s contact the developers to get this implemented" % obj.apiTypeStr)


def getPlugFn(obj):
    """
    :param obj: MObject that has the MFnAttribute functionset
    :type obj: MObject
    """
    if obj.hasFn(om2.MFn.kCompoundAttribute):
        return om2.MFnCompoundAttribute
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        return om2.MFnEnumAttribute
    elif obj.hasFn(om2.MFn.kGenericAttribute):
        return om2.MFnGenericAttribute
    elif obj.hasFn(om2.MFn.kLightDataAttribute):
        return om2.MFnLightDataAttribute
    elif obj.hasFn(om2.MFn.kMatrixAttribute):
        return om2.MFnMatrixAttribute
    elif obj.hasFn(om2.MFn.kMessageAttribute):
        return om2.MFnMessageAttribute
    elif obj.hasFn(om2.MFn.kNumericAttribute):
        return om2.MFnNumericAttribute
    elif obj.hasFn(om2.MFn.kTypedAttribute):
        return om2.MFnTypedAttribute
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        return om2.MFnUnitAttribute
    return om2.MFnAttribute


def iterChildren(plug):
    if plug.isArray:
        for p in xrange(plug.evaluateNumElements()):
            child = plug.elementByPhysicalIndex(p)
            for leaf in iterChildren(child):
                yield leaf
    elif plug.isCompound:
        for p in xrange(plug.numChildren()):
            child = plug.child(p)
            for leaf in iterChildren(child):
                yield leaf
    yield plug


def plugType(plug):
    obj = plug.attribute()

    if obj.hasFn(om2.MFn.kNumericAttribute):
        nAttr = om2.MFnNumericAttribute(obj)
        dataType = nAttr.numericType()
        if dataType == om2.MFnNumericData.kBoolean:
            return attrtypes.kMFnNumericBoolean
        elif dataType == om2.MFnNumericData.kByte:
            return attrtypes.kMFnNumericByte
        elif dataType == om2.MFnNumericData.kShort:
            return attrtypes.kMFnNumericShort
        elif dataType == om2.MFnNumericData.kInt:
            return attrtypes.kMFnNumericInt
        elif dataType == om2.MFnNumericData.kLong:
            return attrtypes.kMFnNumericLong
        elif dataType == om2.MFnNumericData.kDouble:
            return attrtypes.kMFnNumericDouble
        elif dataType == om2.MFnNumericData.kFloat:
            return attrtypes.kMFnNumericFloat
        elif dataType == om2.MFnNumericData.kAddr:
            return attrtypes.kMFnNumericAddr
        elif dataType == om2.MFnNumericData.kChar:
            return attrtypes.kMFnNumericChar
        elif dataType == om2.MFnNumericData.k2Double:
            return attrtypes.kMFnNumeric2Double
        elif dataType == om2.MFnNumericData.k2Float:
            return attrtypes.kMFnNumeric2Float
        elif dataType == om2.MFnNumericData.k2Int:
            return attrtypes.kMFnNumeric2Int
        elif dataType == om2.MFnNumericData.k2Long:
            return attrtypes.kMFnNumeric2Long
        elif dataType == om2.MFnNumericData.k2Short:
            return attrtypes.kMFnNumeric2Short
        elif dataType == om2.MFnNumericData.k3Double:
            return attrtypes.kMFnNumeric3Double
        elif dataType == om2.MFnNumericData.k3Float:
            return attrtypes.kMFnNumeric3Float
        elif dataType == om2.MFnNumericData.k3Int:
            return attrtypes.kMFnNumeric3Int
        elif dataType == om2.MFnNumericData.k3Long:
            return attrtypes.kMFnNumeric3Long
        elif dataType == om2.MFnNumericData.k3Short:
            return attrtypes.kMFnNumeric3Short
        elif dataType == om2.MFnNumericData.k4Double:
            return attrtypes.kMFnNumeric4Double
    elif obj.hasFn(om2.MFn.kUnitAttribute):
        uAttr = om2.MFnUnitAttribute(obj)
        ut = uAttr.unitType()
        if ut == om2.MFnUnitAttribute.kDistance:
            return attrtypes.kMFnUnitAttributeDistance
        elif ut == om2.MFnUnitAttribute.kAngle:
            return attrtypes.kMFnUnitAttributeAngle
        elif ut == om2.MFnUnitAttribute.kTime:
            return attrtypes.kMFnUnitAttributeTime
    elif obj.hasFn(om2.MFn.kEnumAttribute):
        return attrtypes.kMFnkEnumAttribute
    elif obj.hasFn(om2.MFn.kTypedAttribute):
        tAttr = om2.MFnTypedAttribute(obj)
        dataType = tAttr.attrType()
        if dataType == om2.MFnData.kString:
            return attrtypes.kMFnDataString
        elif dataType == om2.MFnData.kMatrix:
            return attrtypes.kMFnDataMatrix
        elif dataType == om2.MFnData.kFloatArray:
            return attrtypes.kMFnDataFloatArray
        elif dataType == om2.MFnData.kDoubleArray:
            return attrtypes.kMFnDataDoubleArray
        elif dataType == om2.MFnData.kIntArray:
            return attrtypes.kMFnDataIntArray
        elif dataType == om2.MFnData.kPointArray:
            return attrtypes.kMFnDataPointArray
        elif dataType == om2.MFnData.kVectorArray:
            return attrtypes.kMFnDataVectorArray
        elif dataType == om2.MFnData.kStringArray:
            return attrtypes.kMFnDataStringArray
        elif dataType == om2.MFnData.kMatrixArray:
            return attrtypes.kMFnDataMatrixArray

    elif obj.hasFn(om2.MFn.kMessageAttribute):
        return attrtypes.kMFnMessageAttribute
    return None


def getPythonTypeFromPlugValue(plug):
    dataType, value = getPlugAndType(plug)
    types = (attrtypes.kMFnDataMatrix, attrtypes.kMFnDataFloatArray,
             attrtypes.kMFnDataFloatArray, attrtypes.kMFnDataDoubleArray,
             attrtypes.kMFnDataIntArray, attrtypes.kMFnDataPointArray, attrtypes.kMFnDataStringArray,
             attrtypes.kMFnNumeric2Double, attrtypes.kMFnNumeric2Float, attrtypes.kMFnNumeric2Int,
             attrtypes.kMFnNumeric2Long, attrtypes.kMFnNumeric2Short, attrtypes.kMFnNumeric3Double,
             attrtypes.kMFnNumeric3Int, attrtypes.kMFnNumeric3Long, attrtypes.kMFnNumeric3Short,
             attrtypes.kMFnNumeric4Double)

    if dataType is None:
        return None
    elif isinstance(dataType, (list, tuple)):
        res = []
        for idx, dt in enumerate(dataType):
            if dt == attrtypes.kMFnDataMatrix:
                res.append([i for i in value[idx]])
            elif dt in (
                    attrtypes.kMFnUnitAttributeDistance, attrtypes.kMFnUnitAttributeAngle,
                    attrtypes.kMFnUnitAttributeTime):
                res.append(value[idx].value)
        return res
    elif dataType in (attrtypes.kMFnDataMatrixArray, attrtypes.kMFnDataVectorArray):
        return [[i for i in subValue] for subValue in value]
    elif dataType in (
            attrtypes.kMFnUnitAttributeDistance, attrtypes.kMFnUnitAttributeAngle, attrtypes.kMFnUnitAttributeTime):
        return value.value
    elif dataType in types:
        return [i for i in value]

    return value


def pythonTypeToMayaType(dataType, value):
    if dataType == attrtypes.kMFnDataMatrixArray:
        return [om2.MMatrix(subValue) for subValue in value]
    elif attrtypes.kMFnDataVectorArray:
        return [om2.MVector(subValue) for subValue in value]
    elif dataType == attrtypes.kMFnUnitAttributeDistance:
        return om2.MDistance(value)
    elif dataType == attrtypes.kMFnUnitAttributeAngle:
        return om2.MAngle(value, om2.MAngle.kDegrees)
    elif dataType == attrtypes.kMFnUnitAttributeTime:
        return om2.MTime(value)
    return value

from maya.api import OpenMaya as om2
from maya import cmds
from zoo.libs.maya.api import plugs
from zoo.libs.maya.api import attrtypes


def asMObject(name):
    """ Returns the MObject from the given name

    :param name: The name to get from maya to convert to an mobject
    :type name: str or MObjectHandle or MDagPath
    :return: The mobject for the given str
    :rtype: MObject

    """
    if isinstance(name, basestring):
        sel = om2.MSelectionList()
        sel.add(name)
        try:
            return sel.getDagPath(0).node()
        except TypeError:
            return sel.getDependNode(0)
    elif isinstance(name, om2.MObject):
        return name
    elif isinstance(name, om2.MObjectHandle):
        return name.object()
    elif isinstance(name, om2.MDagPath):
        return name.node()


def nameFromMObject(mobject, partialName=False):
    """This returns the full name or partial name for a given mobject, the mobject must be valid.

    :param mobject:
    :type mobject: MObject
    :param partialName: if False then this function will return the fullpath of the mobject.
    :type partialName: bool
    :return:  the name of the mobject
    :rtype: str

    Example::
        >>>from zoo.libs.maya.api import nodes
        >>>node = nodes.asMobject(cmds.polyCube())
        >>>print nodes.nameFromMObject(node, partial=False) # returns the fullpath, always prepends '|' eg '|polyCube'
        >>>print nodes.nameFromMObject(node, partial=True) # returns the partial name eg. polyCube1
    """
    if mobject.hasFn(om2.MFn.kDagNode):
        if partialName:
            return om2.MFnDagNode(mobject).partialPathName()
        return om2.MFnDagNode(mobject).fullPathName()
    # dependency node
    return om2.MFnDependencyNode(mobject).name()


def toApiObject(node):
    """
    Returns the appropriate mObject from the api 2.0

    :param node: str, the name of the node
    :type node: str, MObjectHandle
    :return: MFnDagNode, MPlug, MFnDependencyNode
    :rtype: MPlug or MFnDag or MFnDependencyNode

    Example::
        >>>from zoo.libs.maya.api import nodes
        >>>node = cmds.polyCube()[0] # str
        >>>nodes.toApiObject(node) # MFnDagNode
        >>>node = cmds.createNode("multiplyDivide")
        >>>nodes.toApiObject(node) # MFnDependencyNode
    """
    if isinstance(node, om2.MObjectHandle):
        node = node.object()
    elif isinstance(node, (om2.MFnDependencyNode, om2.MFnDagNode)):
        return node

    sel = om2.MSelectionList()
    sel.add(node)
    try:
        tmp = sel.getDagPath(0)
        tmp = om2.MFnDagNode(tmp)
    except TypeError:
        tmp = om2.MFnDependencyNode(sel.getDependNode(0))
    return tmp


def setNodeColour(node, colour):
    """Set the given node mobject override color can be a mobject representing a transform or shape

    :param node: the node which you want to change the override colour of
    :type node: mobject
    :param colour: The RGB colour to set
    :type colour: MColor or tuple
    """
    dependNode = om2.MFnDagNode(om2.MFnDagNode(node).getPath())
    plug = dependNode.findPlug("overrideColorRGB", False)
    enabledPlug = dependNode.findPlug("overrideEnabled", False)
    overrideRGBColors = dependNode.findPlug("overrideRGBColors", False)
    if not plugs.getPlugValue(enabledPlug):
        plugs.setAttr(enabledPlug, True)
    if not plugs.getPlugValue(overrideRGBColors):
        plugs.setAttr(dependNode.findPlug("overrideRGBColors", False), True)
    plugs.setAttr(plug, colour)


def getNodeColourData(node):
    """
    :param node: The maya node mobject that you want to get the override colour from

    :type node: MObject
    :return: {"overrideEnabled": bool,
            "overrideColorRGB": plugs.getAttr(plug),
            "overrideRGBColors": plugs.getAttr(overrideRGBColors)}

    :rtype: dict
    """

    dependNode = om2.MFnDagNode(om2.MFnDagNode(node).getPath())
    plug = dependNode.findPlug("overrideColorRGB", False)
    enabledPlug = dependNode.findPlug("overrideEnabled", False)
    overrideRGBColors = dependNode.findPlug("overrideRGBColors", False)
    return {"overrideEnabled": plugs.getPlugValue(enabledPlug),
            "overrideColorRGB": plugs.getPlugValue(plug),
            "overrideRGBColors": plugs.getPlugValue(overrideRGBColors)}


def createDagNode(name, nodeType, parent=None):
    """Create's a new dag node and if theres a parent specified then parent the new node

    :param name: The new name of the created node
    :type name: str
    :param nodeType: The node type to create
    :type nodeType: str
    :param parent: The node the parent the new node to, if the parent is none or MObject.kNullObj then it will parent
    to the world, defaults to world
    :type parent: MObject or MObject.kNullObj
    :return:The newly create nodes mobject
    :rtype: MObject
    """
    if parent is None or parent.isNull() or parent.apiType() in (om2.MFn.kInvalid, om2.MFn.kWorld):
        parent = om2.MObject.kNullObj
    command = om2.MDagModifier()
    node = command.createNode(nodeType)
    command.renameNode(node, name)
    command.reparentNode(node, parent)
    command.doIt()
    return node


def createDGNode(name, nodeType):
    """Creates and dependency graph node and returns the nodes mobject

    :param name: The newname of the node
    :type name: str
    :param nodeType: the node type to create
    :type nodeType: str
    :return: The mobject of the newly created node
    :rtype: MObject
    """
    dg = om2.MDGModifier()
    node = dg.createNode(nodeType)
    dg.renameNode(node, name)
    dg.doIt()
    return node


def lockNode(mobject, state=True):
    """Set the lock state of the node

    :param mobject: the node mobject to set the lock state on
    :type mobject: MObject
    :param state: the lock state for the node
    :type state: bool
    """
    if om2.MFnDependencyNode(mobject).isLocked != state:
        mod = om2.MDGModifier()
        mod.setNodeLockState(mobject, state)
        mod.doIt()


def unlockConnectedAttributes(mobject):
    for thisNodeP, otherNodeP in iterConnections(mobject, source=True, destination=True):
        if thisNodeP.isLocked:
            thisNodeP.isLocked = False


def unlockedAndDisconnectConnectedAttributes(mobject):
    for thisNodeP, otherNodeP in iterConnections(mobject, source=True, destination=True):
        plugs.disconnectPlug(thisNodeP, otherNodeP)


def childPathAtIndex(path, index):
    """From the given MDagPath return a new MDagPath for the child node at the given index.

    :param path: MDagPath
    :type index: int
    :return: MDagPath, this path's child at the given index"""
    existingChildCount = path.childCount()
    if existingChildCount < 1:
        return None
    if index < 0:
        index = path.childCount() - abs(index)
    copy = om2.MDagPath(path)
    copy.push(path.child(index))
    return copy


def childPaths(path):
    """Returns all the MDagPaths that are a child of path.

    :param path: MDagPath
    :return: list(MDagPaths), child MDagPaths which have path as parent
    """
    outPaths = [childPathAtIndex(path, i) for i in range(path.childCount())]
    return outPaths


def childPathsByFn(path, fn):
    """Get all children below path supporting the given MFn.type

    :param path: MDagpath
    :param fn: member of MFn
    :return: list(MDagPath), all matched paths below this path
    """
    return [p for p in childPaths(path) if p.hasFn(fn)]


def shapes(path):
    """

    :param path: MDagPath
    :return: list(MDagPath), all shapes below path
    """
    paths = []
    for i in range(path.numberOfShapesDirectlyBelow()):
        dagPath = om2.MDagPath(path)
        dagPath.extendToShape(i)
        paths.append(dagPath)
    return paths


def shapeAtIndex(path, index):
    if index in range(path.numberOfShapesDirectlyBelow()):
        return om2.MDagPath(path).extendToShape(index)


def childTransforms(path):
    """Returns all the child transform from the given DagPath

    :type path: MDagPath
    :return: list(MDagPath) to all transforms below path
    """
    return childPathsByFn(path, om2.MFn.kTransform)


def setParent(mobject, newParent, maintainOffset=False):
    """Sets the parent for the given mobject, this is undoable

    :param mobject: MObject
    :param newParent: MObject
    :param maintainOffset:
    :type maintainOffset: bool
    :rtype bool
    """
    if mobject == newParent:
        return False
    newParent = newParent if newParent is not None else om2.MObject.kNullObj
    dag = om2.MDagModifier()
    if maintainOffset:
        start = getWorldMatrix(newParent)
        end = getWorldMatrix(mobject)
        offset = end * start.inverse()
    dag.reparentNode(mobject, newParent)
    dag.doIt()
    if maintainOffset:
        om2.MFnTransform(mobject).setTransformation(om2.MTransformationMatrix(offset))
    return True


def hasParent(mobject):
    parent = getParent(mobject)
    if parent is None or parent.isNull():
        return False
    return True


def rename(mobject, newName):
    """Renames the given mobject node, this is undoable

    :param mobject: MObject
    :param newName: str
    """
    dag = om2.MDGModifier()
    dag.renameNode(mobject, newName)
    dag.doIt()


def parentPath(path):
    """

    :param path:
    :type path: MDagpath
    :return: MDagPath, parent of path or None if path is in the scene root.
    """
    parent = om2.MDagPath(path)
    parent.pop(1)
    if parent.length() == 0:  # ignore world !
        return
    return parent


def isValidMDagPath(dagPath):
    """ Determines if the given MDagPath is valid

    :param dagPath: MDagPath
    :return: bool
    """
    return dagPath.isValid() and dagPath.fullPathName()


def iterParents(mobject):
    parent = getParent(mobject=mobject)
    while parent is not None:
        yield parent
        parent = getParent(parent)


def isSceneRoot(node):
    fn = om2.MFnDagNode(node)
    return fn.object().hasFn(om2.MFn.kDagNode) and fn.name() == "world"


def isUnderSceneRoot(node):
    fn = om2.MFnDagNode(node)
    par = fn.parent(0)
    return isSceneRoot(par)


def iterChildren(mObject, recursive=False, filter=None):
    """Generator function that can recursive iterate over the children of the given mobject.

    :param mObject: The mobject to traverse must be a mobject that points to a transform
    :type mObject: MObject
    :param recursive: Whether to do a recursive search
    :type recursive: bool
    :param filter: om.MFn or 'all', the node type to find, can be either 'all' for returning everything or a om.MFn type constant
                    does not include shapes
    :type filter: str or int
    :return: om.MObject
    """
    dagNode = om2.MFnDagNode(mObject)
    childCount = dagNode.childCount()
    if not childCount:
        return

    for index in xrange(childCount):
        childObj = dagNode.child(index)
        if childObj.apiType() == filter or filter is None:
            yield childObj
            if recursive:
                for x in iterChildren(childObj, recursive, filter):
                    yield x


def getChildren(mObject, recursive=False, filter=om2.MFn.kTransform):
    """This function finds and returns all children mobjects under the given transform, if recursive then including subchildren.

    :param mObject: om.MObject, the mObject of the transform to search under
    :param recursive: bool
    :param filter: int(om.MFn.kTransform), the node type to filter by
    :return: list(MFnDagNode)
    """
    return [i for i in iterChildren(mObject, recursive, filter)]


def iterAttributes(node):
    dep = om2.MFnDependencyNode(node)
    for idx in xrange(dep.attributeCount()):
        attr = dep.attribute(idx)
        plug = om2.MPlug(node, attr)
        if "]" in plug.name() or plug.isChild:
            continue
        for child in plugs.iterChildren(plug):
            yield child


def iterExtraAttributes(node, filteredType=None):
    dep = om2.MFnDependencyNode(node)
    for idx in xrange(dep.attributeCount()):
        attr = dep.attribute(idx)
        plug = om2.MPlug(node, attr)
        if plug.isDynamic:
            if filteredType is None or plugs.plugType(plug) == filteredType:
                yield plug


def iterConnections(node, source=True, destination=True):
    dep = om2.MFnDependencyNode(node)
    for pl in iter(dep.getConnections()):
        if source and pl.isDestination:
            yield pl, pl.connectedTo(True, False)[0]
        if destination and pl.isSource:
            for i in iter(pl.connectedTo(False, True)):
                yield pl, i


def iterKeyablePlugs(node):
    dep = om2.MFnDependencyNode(node)
    for i in xrange(dep.attributeCount()):
        attr = dep.attribute(i)
        plug = om2.MPlug(node, attr)
        if plug.isKeyable:
            yield plug


def iterChannelBoxPlugs(node):
    dep = om2.MFnDependencyNode(node)
    for i in xrange(dep.attributeCount()):
        attr = dep.attribute(i)
        plug = om2.MPlug(node, attr)
        if plug.isKeyable and plug.isChannelBox:
            yield plug


def getRoots(nodes):
    roots = set()
    for node in nodes:
        root = getRoot(node)
        if root:
            roots.add(root)
    return list(roots)


def getRoot(mobject):
    """Traversals the objects parent until the root node is found and returns the MObject

    :param mobject: MObject
    :return: MObject
    """
    current = mobject
    for node in iterParents(mobject):
        if node is None:
            return current
        current = node
    return current


def getParent(mobject):
    """Returns the parent MFnDagNode if it has a parent else None

    :param mobject: MObject
    :return: MObject or None
    """
    if mobject.hasFn(om2.MFn.kDagNode):
        dagpath = om2.MDagPath.getAPathTo(mobject)
        if dagpath.node().apiType() == om2.MFn.kWorld:
            return None
        dagNode = om2.MFnDagNode(dagpath).parent(0)
        if dagNode.apiType() == om2.MFn.kWorld:
            return None
        return dagNode


def isValidMObject(node):
    mo = om2.MObjectHandle(node)
    if not mo.isValid() or not mo.isAlive():
        return False
    return True


def delete(node):
    """Delete the given nodes

    :param node:
    """
    if not isValidMObject(node):
        return
    lockNode(node, False)
    unlockedAndDisconnectConnectedAttributes(node)
    mod = om2.MDagModifier()
    mod.deleteNode(node)
    mod.doIt()


def getOffsetMatrix(startObj, endObj):
    start = getParentInverseMatrix(startObj)
    end = getWorldMatrix(endObj)
    mOutputMatrix = om2.MTransformationMatrix(end * start)
    return mOutputMatrix.asMatrix()


def getObjectMatrix(mobject):
    """ Returns the MMatrix of the given mobject

    :param mobject: MObject
    :return:MMatrix
    """
    dag = om2.MFnDagNode(mobject).getPath()
    return om2.MFnTransform(dag).transformation().asMatrix()


def getWorldMatrix(mobject):
    """Returns the worldMatrix value as an MMatrix.

    :param mobject: MObject, the MObject that points the dagNode
    :return: MMatrix
    """
    dag = om2.MFnDagNode(mobject).getPath()

    return dag.inclusiveMatrix()


def getWorldInverseMatrix(mobject):
    """Returns the world inverse matrix of the given MObject

    :param mobject: MObject
    :return: MMatrix
    """
    dag = om2.MFnDagNode(mobject).getPath()
    return dag.inclusiveMatrixInverse()


def getParentMatrix(mobject):
    """Returns the parent matrix of the given MObject

    :param mobject: MObject
    :return: MMatrix
    """
    dag = om2.MFnDagNode(mobject).getPath()

    return dag.exclusiveMatrix()


def getParentInverseMatrix(mobject):
    """Returns the parent inverse matrix from the Mobject

    :param mobject: MObject
    :return: MMatrix
    """
    dag = om2.MFnDagNode(mobject).getPath()

    return dag.exclusiveMatrixInverse()


def hasAttribute(node, name):
    """Searches the node for a give a attribute name and returns True or False

    :param node: MObject, the nodes MObject
    :param name: str, the attribute name to find
    :return: bool
    """
    return om2.MFnDependencyNode(node).hasAttribute(name)


def setMatrix(mobject, matrix):
    dag = om2.MFnDagNode(mobject)
    trans = om2.MFnTransform(dag.getPath())
    trans.setTransformation(om2.MTransformationMatrix(matrix))


def setTranslation(obj, position, space=None):
    path = om2.MFnDagNode(obj).getPath()
    space = space or om2.MSpace.kTransform
    trans = om2.MFnTransform(path)
    trans.setTranslation(position, space)


def getTranslation(obj, space=None):
    space = space or om2.MSpace.kTransform
    path = om2.MFnDagNode(obj).getPath()
    trans = om2.MFnTransform(path)
    return trans.translation(space)


def cvPositions(shape, space=None):
    space = space or om2.MSpace.kObject
    curve = om2.MFnNurbsCurve(shape)
    return curve.cvPositions(space)


def setCurvePositions(shape, points, space=None):
    space = space or om2.MSpace.kObject
    curve = om2.MFnNurbsCurve(shape)
    if len(points) != curve.numCVs:
        raise ValueError("Mismatched current curves cv count and the length of points to modify")
    curve.setCVPositions(points, space)


def setRotation(node, rotation, space=om2.MSpace.kTransform):
    path = om2.MFnDagNode(node).getPath()
    trans = om2.MFnTransform(path)
    if isinstance(rotation, (list, tuple)):
        rotation = om2.MEulerRotation([om2.MAngle(i, om2.MAngle.kDegrees).asRadians() for i in rotation]).asQuaternion()
    trans.setRotation(rotation, space)


def addAttribute(node, longName, shortName, attrType=attrtypes.kMFnNumericDouble):
    """This function uses the api to create attributes on the given node, currently WIP but currently works for
    string,int, float, bool, message. if the attribute exists a ValueError will be raised.

    :param node: MObject
    :param longName: str, the long name for the attribute
    :param shortName: str, the shortName for the attribute
    :param attrType: attribute Type, attrtypes constants
    :rtype: om.MObject
    """
    if hasAttribute(node, longName):
        raise ValueError("Node -> '%s' already has attribute -> '%s'" % (nameFromMObject(node), longName))
    aobj = None
    attr = None
    if attrType == attrtypes.kMFnNumericDouble:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kDouble)
    elif attrType == attrtypes.kMFnNumericFloat:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kFloat)
    elif attrType == attrtypes.kMFnNumericBoolean:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kBoolean)
    elif attrType == attrtypes.kMFnNumericInt:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kInt)
    elif attrType == attrtypes.kMFnNumericShort:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kShort)
    elif attrType == attrtypes.kMFnNumericLong:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kLong)
    elif attrType == attrtypes.kMFnNumericByte:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kByte)
    elif attrType == attrtypes.kMFnNumericChar:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kChar)
    elif attrType == attrtypes.kMFnNumericAddr:
        attr = om2.MFnNumericAttribute()
        aobj = attr.createAddr(longName, shortName)
    elif attrType == attrtypes.kMFnkEnumAttribute:
        attr = om2.MFnEnumAttribute()
        aobj = attr.create(longName, shortName)
    elif attrType == attrtypes.kMFnCompoundAttribute:
        attr = om2.MFnCompoundAttribute()
        aobj = attr.create(longName, shortName)
    elif attrType == attrtypes.kMFnMessageAttribute:
        attr = om2.MFnMessageAttribute()
        aobj = attr.create(longName, shortName)
    elif attrType == attrtypes.kMFnDataString:
        attr = om2.MFnTypedAttribute()
        stringData = om2.MFnStringData().create("")
        aobj = attr.create(longName, shortName, om2.MFnData.kString, stringData)
    elif attrType == attrtypes.kMFnUnitAttributeDistance:
        attr = om2.MFnUnitAttribute()
        aobj = attr.create(longName, shortName, om2.MDistance())
    elif attrType == attrtypes.kMFnUnitAttributeAngle:
        attr = om2.MFnUnitAttribute()
        aobj = attr.create(longName, shortName, om2.MAngle())
    elif attrType == attrtypes.kMFnUnitAttributeTime:
        attr = om2.MFnUnitAttribute()
        aobj = attr.create(longName, shortName, om2.MTime())
    elif attrType == attrtypes.kMFnDataMatrix:
        attr = om2.MFnMatrixAttribute()
        aobj = attr.create(longName, shortName)
    elif attrType == attrtypes.kMFnDataFloatArray:
        attr = om2.MFnFloatArray()
        aobj = attr.create(longName, shortName)
    elif attrType == attrtypes.kMFnDataDoubleArray:
        data = om2.MFnDoubleArrayData().create(om2.MDoubleArray())
        attr = om2.MFnTypedAttribute()
        aobj = attr.create(longName, shortName, om2.MFnData.kDoubleArray, data)
    elif attrType == attrtypes.kMFnDataIntArray:
        data = om2.MFnIntArrayData().create(om2.MIntArray())
        attr = om2.MFnTypedAttribute()
        aobj = attr.create(longName, shortName, om2.MFnData.kIntArray, data)
    elif attrType == attrtypes.kMFnDataPointArray:
        data = om2.MFnPointArrayData().create(om2.MPointArray())
        attr = om2.MFnTypedAttribute()
        aobj = attr.create(longName, shortName, om2.MFnData.kPointArray, data)
    elif attrType == attrtypes.kMFnDataVectorArray:
        data = om2.MFnVectorArrayData().create(om2.MVectorArray())
        attr = om2.MFnTypedAttribute()
        aobj = attr.create(longName, shortName, om2.MFnData.kVectorArray, data)
    elif attrType == attrtypes.kMFnDataStringArray:
        data = om2.MFnStringArrayData().create(om2.MStringArray())
        attr = om2.MFnTypedAttribute()
        aobj = attr.create(longName, shortName, om2.MFnData.kStringArray, data)
    elif attrType == attrtypes.kMFnDataMatrixArray:
        data = om2.MFnMatrixArrayData().create(om2.MMatrixArray())
        attr = om2.MFnTypedAttribute()
        aobj = attr.create(longName, shortName, om2.MFnData.kMatrixArray, data)
    elif attrType == attrtypes.kMFnNumericInt64:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kInt64)
    elif attrType == attrtypes.kMFnNumericLast:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.kLast)
    elif attrType == attrtypes.kMFnNumeric2Double:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k2Double)
    elif attrType == attrtypes.kMFnNumeric2Float:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k2Float)
    elif attrType == attrtypes.kMFnNumeric2Int:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k2Int)
    elif attrType == attrtypes.kMFnNumeric2Long:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k2Long)
    elif attrType == attrtypes.kMFnNumeric2Short:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k2Short)
    elif attrType == attrtypes.kMFnNumeric3Double:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k3Double)
    elif attrType == attrtypes.kMFnNumeric3Float:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k3Float)
    elif attrType == attrtypes.kMFnNumeric3Int:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k3Int)
    elif attrType == attrtypes.kMFnNumeric3Long:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k3Long)
    elif attrType == attrtypes.kMFnNumeric3Short:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k3Short)
    elif attrType == attrtypes.kMFnNumeric4Double:
        attr = om2.MFnNumericAttribute()
        aobj = attr.create(longName, shortName, om2.MFnNumericData.k4Double)

    if aobj is not None:
        mod = om2.MDGModifier()
        mod.addAttribute(node, aobj)
        mod.doIt()
    return attr


def getNodesCreatedBy(function, *args, **kwargs):
    """returns a 2-tuple containing all the nodes created by the passed function, and
    the return value of said function

    :param function: func, the function to call and inspect
    :return tuple, list(MObject), function return type
    """

    # construct the node created callback
    newNodeHandles = set()

    def newNodeCB(newNode, data):
        newNodeHandles.add(om2.MObjectHandle(newNode))

    def remNodeCB(remNode, data):
        remNodeHandle = om2.MObjectHandle(remNode)
        if remNodeHandle in newNodeHandles:
            newNodeHandles.remove(remNodeHandle)

    newNodeCBMsgId = om2.MDGMessage.addNodeAddedCallback(newNodeCB)
    remNodeCBMsgId = om2.MDGMessage.addNodeRemovedCallback(remNodeCB)

    try:
        ret = function(*args, **kwargs)
    finally:
        om2.MMessage.removeCallback(newNodeCBMsgId)
        om2.MMessage.removeCallback(remNodeCBMsgId)

    newNodes = [h.object() for h in newNodeHandles]

    return newNodes, ret


def serializeNode(node):
    dep = om2.MFnDagNode(node) if node.hasFn(om2.MFn.kDagNode) else om2.MFnDependencyNode(node)

    data = {"name": dep.fullPathName() if node.hasFn(om2.MFn.kDagNode) else dep.name(),
            "type": dep.typeName,
            }
    req = dep.pluginName
    if req:
        data["requirements"] = req
    if node.hasFn(om2.MFn.kDagNode):
        data["parent"] = nameFromMObject(dep.parent(0))
    attributes = {}
    for pl in iterAttributes(node):
        attrData = {}
        if pl.isDestination:
            source = pl.source()
            nodeName = nameFromMObject(source.node())
            attrData["connections"] = (nodeName, source.partialName(includeNonMandatoryIndices=True, useLongNames=True))

        if not pl.isDynamic:
            if pl.isDefaultValue():
                continue
        else:
            # standard data
            attrData.update({"isDynamic": True, "channelBox": pl.isChannelBox, "keyable": pl.isKeyable,
                             "locked": pl.isLocked, "type": plugs.plugType(pl), "default": plugs.plugDefault(pl),
                             "min": plugs.getPlugMin(pl), "max": plugs.getPlugMax(pl),
                             "softMin": plugs.getSoftMin(pl), "softMax": plugs.getSoftMax(pl)})
            if pl.attribute().hasFn(om2.MFn.kEnumAttribute):
                attrData["enums"] = plugs.enumNames(pl)
        value = plugs.getPythonTypeFromPlugValue(pl)
        # could be 0.0, False, True which is a valid result so we need to explicitly check
        if value not in (None, [], {}):
            attrData["value"] = value

        if attrData:
            attributes[pl.partialName(includeNonMandatoryIndices=True, useLongNames=True)] = attrData

    if attributes:
        data["attributes"] = attributes

    return data


def createAnnotation(rootObj, endObj, text=None, name=None):
    name = name or "annotation"
    rootDag = om2.MFnDagNode(rootObj)
    boundingBox = rootDag.boundingBox
    center = om2.MVector(boundingBox.center)
    locator = asMObject(cmds.createNode("locator"))
    locatorTransform = getParent(locator)
    rename(locatorTransform, "_".join([name, "loc"]))
    setTranslation(locatorTransform, getTranslation(rootObj, om2.MSpace.kWorld), om2.MSpace.kWorld)
    annotationNode = asMObject(cmds.annotate(nameFromMObject(locatorTransform), tx=text))
    annParent = getParent(annotationNode)
    rename(annParent, name)
    plugs.setAttr(om2.MFnDagNode(annotationNode).findPlug("position", False), center)
    setParent(locatorTransform, rootObj, True)
    setParent(annParent, endObj, False)
    return annotationNode, locatorTransform


def setlockStateOnAttributes(node, attributes, state=True):
    dep = om2.MFnDependencyNode(node)
    for attr in attributes:
        plug = dep.findPlug(attr, False)
        if plug.isLocked != state:
            plug.isLocked = state
    return True


def showHideAttributes(node, attributes, state=True):
    dep = om2.MFnDependencyNode(node)
    for attr in attributes:
        plug = dep.findPlug(attr, False)
        if plug.isChannelBox != state:
            plug.isChannelBox = state
    return True
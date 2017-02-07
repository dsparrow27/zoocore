from contextlib import contextmanager

from maya.api import OpenMaya as om2


def removeFromActiveSelection(node):
    """remove the node from the selection forcefully
    Otherwise maya can crash if someone deletes that node afterwards"""

    currentSelectionList = om2.MGlobal.getActiveSelectionList()
    newList = om2.MSelectionList()
    for i in range(currentSelectionList.length()):
        try:
            currentNode = currentSelectionList.getDagPath(i).node()
        except TypeError:
            currentNode = currentSelectionList.getDependNode(i)
        if currentNode != node:
            newList.add(currentNode)
    om2.MGlobal.setActiveSelectionList(newList, om2.MGlobal.kReplaceList)


def getSelectedNodes():
    """Returns the selected nodes

    :return: list(MObject)
    """
    sel = om2.MGlobal.getActiveSelectionList()
    nodes = []
    for i in range(sel.length()):
        try:
            nodes.append(sel.getDagPath(i).node())
        except TypeError:
            nodes.append(sel.getDependNode(i))
    return nodes


@contextmanager
def keepSelection():
    sel = om2.MSelectionList()
    om2.MGlobal.getActiveSelectionList(sel)
    try:
        yield
    finally:
        om2.MGlobal.setActiveSelectionList(sel)


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


def iterDag(root, includeRoot=True, nodeType=None):
    """Generator function to walk the node hierarchy, if a nodeType is provided then the function will only return
    that mobject apitype.
    :param root: the root dagnode to loop
    :type root: MObject
    :param includeRoot: if true include the root mobject
    :type includeRoot: bool
    :param nodeType: defaults to none which will return everything an example user specified type om2.MFn.kTransform
    :type nodeType: int
    :return: yields the mobject
    :rtype: Generator(mobject)
    """
    stack = [om2.MFnDagNode(root)]
    if includeRoot:
        yield stack[0]
    while stack:
        child = stack.pop(0)
        if child.childCount() > 0:
            for i in range(child.childCount()):
                subChild = child.child(i)
                stack.append(om2.MFnDagNode(subChild))
                if nodeType is not None and subChild.apiType() != nodeType:
                    continue
                yield subChild


def worldPositionToScreen(camera, point, width, height):
    cam = om2.MFnCamera(camera)
    projMat = om2.MMatrix(cam.projectionMatrix().matrix())
    transMat = cam.getPath().inclusiveMatrix().inverse()

    point = om2.MPoint(point)

    fullMat = point * transMat * projMat
    return [(fullMat[0] / fullMat[3] * 0.5 + 0.5) * width,
            (fullMat[1] / fullMat[3] * 0.5 + 0.5) * height]


def isPointInView(camera, point, width, height):
    x, y = worldPositionToScreen(camera, point, width, height)
    if x > width or x < 0.0 or y > height or y < 0.0:
        return False
    return True
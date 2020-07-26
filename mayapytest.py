from maya import standalone, cmds
standalone.initialize()
cmds.file(new=True)
cmds.polySphere(radius=2)
print(cmds.ls())

class Object:
    def __init__(self, name, shapeDataSize, aisShape):
        self.name = name
        self.shapeDataSize = shapeDataSize
        self.aisShape = aisShape
        self.forceUpdate = False
        self.stale = False
        self.new = True

    def checkID(self, newID):
        return self.id == newID

    def updateShape(self, newShape):
        self.aisShape.SetShape(newShape)

        return self.aisShape

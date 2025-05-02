class Object:
    def __init__(self, name, id, aisShape):
        self.name = name
        self.id = id
        self.aisShape = aisShape
        self.forceUpdate = False
        self.stale = False

    def checkID(self, newID):
        return self.id == newID

    def updateShape(self, newShape):
        self.aisShape.SetShape(newShape)

        return self.aisShape

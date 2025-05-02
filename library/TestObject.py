from build123d import *
from ViewerLib import *

with BuildPart() as part:
    Box(30, 15, 15)

part.part.edges()

# addObject("cube1", part)
addObject("cube2", part)

update()
from build123d import *
from ViewerLib import *

with BuildPart() as part:
    Box(15, 15, 15)

# addObject("cube1", part)
addObject("cube2", part)

update()

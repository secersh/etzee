import pcbnew
import math

class Fillet:
    def __init__(self, x: double, y: double, radius: double):
        self.a = pcbnew.VECTOR2D(x, y)
        self.b = pcbnew.VECTOR2D -> None
        self.c = pcbnew.VECTOR2D -> None
        self.d = pcbnew.VECTOR2D -> None
        self.radius = radius

class Segment:
    def __init__(self, high: Fillet, low: Fillet):
        self.high = high
        self.low = low

board = pcbnew.GetBoard()

# Parameters
C = 18
T = 20
ro = 50
ri = 20
tw = 0.15
origin = (0, 0)

# [Slot][Side][Track][Segment]
points = [int][String][int][int]

def pointsCloud():
    spacing = 2 * tw
    localPoints = [][]
    for t in T:
        localPoints[t][i] = (origin[0], ri + spacing * t)
        localPoints[t][i] = (origin[0], ro - spacing * t)

pcbnew.Refresh()

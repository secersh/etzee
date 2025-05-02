import math
import pcbnew

board = pcbnew.GetBoard()

# Parameters
number_of_slots = 5
number_of_tracks = 30
outer_radius = 59
inner_radius = 35
track_width = 0.15
origin = (450, 0)

def rotate_point(x, y, cx, cy, angle_degrees):
    theta = math.radians(angle_degrees)

    dx = x - cx
    dy = y - cy

    x_rot = dx * math.cos(theta) + dy * math.sin(theta)
    y_rot = -dx * math.sin(theta) + dy * math.cos(theta)

    return pcbnew.VECTOR2I(pcbnew.FromMM(x_rot + cx), pcbnew.FromMM(y_rot + cy))

def add_track(start_point, end_point):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(start_point)
    track.SetEnd(end_point)
    track.SetWidth(pcbnew.FromMM(track_width))
    track.SetLayer(pcbnew.F_Cu)
    board.Add(track)

def add_arc(start_point, mid_point, end_point):
    arc = pcbnew.PCB_ARC(board)
    arc.SetStart(start_point)
    arc.SetMid(mid_point)
    arc.SetEnd(end_point)
    arc.SetWidth(pcbnew.FromMM(track_width))
    arc.SetLayer(pcbnew.F_Cu)
    board.Add(arc)

def draw(phase):
    track_spacing = 2 * track_width
    tracks_angle = 360 / number_of_slots
    ox = origin[0]
    oy = origin[1]

    previous_slot_outer_points = [None] * number_of_tracks

    for slot in range(number_of_slots):

        slot_angle = tracks_angle * slot + phase

        left_angle = slot_angle - tracks_angle / 4
        right_angle = slot_angle + tracks_angle / 4

        for track_number in range(number_of_tracks):

            calulated_track_spacing = track_spacing * track_number
            track_inner_radius = inner_radius + calulated_track_spacing
            track_outer_radius = outer_radius + track_spacing * number_of_tracks + calulated_track_spacing
            fillet_radius = track_width * 2 * track_number

            track_offset = track_spacing * track_number - (track_spacing * (number_of_tracks - 1) / 2)

            al1 = rotate_point(ox + track_offset, oy + track_inner_radius, ox, oy, left_angle)
            bl1 = rotate_point(ox + track_offset, oy + track_inner_radius + fillet_radius, ox, oy, left_angle)
            cl1 = rotate_point(ox + track_offset + fillet_radius, oy + track_inner_radius + fillet_radius, ox, oy, left_angle)
            dl1 = rotate_point(ox + track_offset + fillet_radius, oy + track_inner_radius, ox, oy, left_angle)

            al2 = rotate_point(ox + track_offset, oy + track_outer_radius, ox, oy, left_angle)
            bl2 = rotate_point(ox + track_offset, oy + track_outer_radius - fillet_radius, ox, oy, left_angle)
            cl2 = rotate_point(ox + track_offset - fillet_radius, oy + track_outer_radius - fillet_radius, ox, oy, left_angle)
            dl2 = rotate_point(ox + track_offset - fillet_radius, oy + track_outer_radius, ox, oy, left_angle)

            ar1 = rotate_point(ox - track_offset, oy + track_inner_radius, ox, oy, right_angle)
            br1 = rotate_point(ox - track_offset, oy + track_inner_radius + fillet_radius, ox, oy, right_angle)
            cr1 = rotate_point(ox - track_offset + fillet_radius, oy + track_inner_radius + fillet_radius, ox, oy, right_angle)
            dr1 = rotate_point(ox - track_offset + fillet_radius, oy + track_inner_radius, ox, oy, right_angle)

            ar2 = rotate_point(ox - track_offset, oy + track_outer_radius, ox, oy, right_angle)
            br2 = rotate_point(ox - track_offset, oy + track_outer_radius - fillet_radius, ox, oy, right_angle)
            cr2 = rotate_point(ox - track_offset - fillet_radius, oy + track_outer_radius - fillet_radius, ox, oy, right_angle)
            dr2 = rotate_point(ox - track_offset - fillet_radius, oy + track_outer_radius, ox, oy, right_angle)

            mi = rotate_point(ox + track_offset, oy + track_inner_radius, ox, oy, slot_angle)
            mo = rotate_point(ox - track_offset, oy + track_outer_radius, ox, oy, slot_angle)

            add_arc(al1, mi, ar1)

            if previous_slot_outer_points[track_number] is not None:
                add_arc(previous_slot_outer_points[track_number], mo, al2)

            previous_slot_outer_points[track_number] = ar2

            add_track(al1, al2)
            add_track(ar1, ar2)

draw(0)
# draw(24)
# draw(48)
pcbnew.Refresh()

import math
import pcbnew

board = pcbnew.GetBoard()

# Parameters
number_of_slots = 5
number_of_tracks = 17
outer_radius = 63 / 2
inner_radius = 39 / 2
track_width = 0.15
origin = (402.375, 47.875)

def rotate_point(x, y, cx, cy, angle_degrees):
    theta = math.radians(angle_degrees)

    dx = x - cx
    dy = y - cy

    x_rot = dx * math.cos(theta) + dy * math.sin(theta)
    y_rot = -dx * math.sin(theta) + dy * math.cos(theta)

    return pcbnew.VECTOR2I(pcbnew.FromMM(x_rot + cx), pcbnew.FromMM(y_rot + cy))

def add_track(start_point, end_point, layer):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(start_point)
    track.SetEnd(end_point)
    track.SetWidth(pcbnew.FromMM(track_width))
    track.SetLayer(layer)
    board.Add(track)

def add_arc(start_point, mid_point, end_point, layer):
    arc = pcbnew.PCB_ARC(board)
    arc.SetStart(start_point)
    arc.SetMid(mid_point)
    arc.SetEnd(end_point)
    arc.SetWidth(pcbnew.FromMM(track_width))
    arc.SetLayer(layer)
    board.Add(arc)

def add_circle(radius):
    circle = pcbnew.PCB_SHAPE(board)
    circle.SetShape(pcbnew.S_CIRCLE)
    circle.SetCenter(pcbnew.VECTOR2I(pcbnew.FromMM(origin[0]), pcbnew.FromMM(origin[1])))
    circle.SetWidth(pcbnew.FromMM(track_width))
    circle.SetLayer(pcbnew.F_SilkS)
    circle.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(origin[0] + radius), pcbnew.FromMM(origin[1])))
    board.Add(circle)

def draw(phase, layer):
    track_spacing = 2 * track_width
    tracks_width = track_spacing * number_of_tracks
    half_width = tracks_width / 2
    tracks_angle = 360 / number_of_slots
    ox = origin[0]
    oy = origin[1]

    starting_slot_outer_points = [None] * number_of_tracks
    previous_slot_outer_points = [None] * number_of_tracks

    for slot in range(number_of_slots):

        slot_angle = tracks_angle * slot + phase

        left_angle = slot_angle - tracks_angle / 4
        right_angle = slot_angle + tracks_angle / 4

        for track_number in range(number_of_tracks):

            calculated_width = track_width * track_number
            calculated_width_i = track_width * (number_of_tracks - track_number)
            calculated_track_spacing = track_spacing * track_number
            track_inner_radius = inner_radius - tracks_width + track_width + calculated_track_spacing
            track_outer_radius = outer_radius + calculated_track_spacing

            track_offset = track_spacing * track_number - half_width

            left_line_str = rotate_point(ox + track_offset, oy + inner_radius - calculated_width_i, ox, oy, left_angle)
            left_line_end = rotate_point(ox + track_offset, oy + outer_radius + calculated_width, ox, oy, left_angle)

            right_line_str = rotate_point(ox - track_offset, oy + inner_radius- calculated_width_i, ox, oy, right_angle)
            right_line_end = rotate_point(ox - track_offset, oy + outer_radius + calculated_width, ox, oy, right_angle)

            inner_arc_str = rotate_point(ox + half_width - calculated_width_i - track_width, oy + track_inner_radius, ox, oy, left_angle)
            inner_arc_mid = rotate_point(ox, oy + track_inner_radius, ox, oy, slot_angle)
            inner_arc_end = rotate_point(ox - half_width + calculated_width_i + track_width, oy + track_inner_radius, ox, oy, right_angle)

            outer_arc_str = rotate_point(ox - half_width + calculated_width, oy + track_outer_radius, ox, oy, left_angle)
            outer_arc_mid = rotate_point(ox, oy + track_outer_radius, ox, oy, slot_angle)
            outer_arc_end = rotate_point(ox + half_width - calculated_width, oy + track_outer_radius, ox, oy, right_angle)

            add_arc(inner_arc_str, inner_arc_mid, inner_arc_end, layer)

            if previous_slot_outer_points[track_number] is not None:
                add_arc(previous_slot_outer_points[track_number], outer_arc_mid, outer_arc_str, layer)

            previous_slot_outer_points[track_number] = outer_arc_end

            if slot == 0:
                starting_slot_outer_points[track_number] = outer_arc_str

            add_track(left_line_str, left_line_end, layer)
            add_track(right_line_str, right_line_end, layer)

            add_track(left_line_end, outer_arc_str, layer)
            add_track(right_line_end, outer_arc_end, layer)

            add_track(left_line_str, inner_arc_str, layer)
            add_track(right_line_str, inner_arc_end, layer)

    for track_number in range(number_of_tracks):

        track_outer_radius = outer_radius + calculated_track_spacing

        outer_arc_mid = rotate_point(ox, oy + track_outer_radius, ox, oy, slot_angle)

        if track_number + 1 < number_of_tracks:
            add_arc(starting_slot_outer_points[track_number], outer_arc_mid, previous_slot_outer_points[track_number + 1], layer)

add_circle(inner_radius)
add_circle(outer_radius)

draw(0, pcbnew.F_Cu)
draw(24, pcbnew.In1_Cu)
draw(48, pcbnew.In2_Cu)

pcbnew.Refresh()

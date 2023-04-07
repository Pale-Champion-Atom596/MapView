import argparse
import copy
import json
import numpy as np
import pygame
import pygame_gui
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


class MapData:
    def __init__(self):
        self.countries = []

    def add_country(self, country):
        self.countries.append(country)


class Region:
    def __init__(self, country_data):
        self.name = country_data["name"]
        self.prefix = country_data["prefix"]
        self.suffix = country_data["suffix"]
        if country_data["color"] is not None:
            self.color = country_data["color"]
        else:
            self.color = list(np.random.choice(range(256), size=3))  # Generates a random color value, will change later
        self.government = country_data["government"]
        self.leader = country_data["leader"]
        self.consts = []
        self.coords = []

    def add_const(self, constituency):
        self.consts.append(constituency)

    def add_coord(self, coordinate):
        self.coords.append(coordinate)


parser = argparse.ArgumentParser()
parser.add_argument("-f", "--filename", type=str)


BACKGROUND = (31, 128, 128)


def coords_alterer(coords, o_x, o_y, zoom):
    for i in range(len(coords)):
        coords[i] = (coords[i][0] * 10 * zoom + o_x, coords[i][1] * 10 * zoom + o_y)
    return coords


def indexi(array, item, start=0, finish=0):
    if finish == 0:
        finish = len(array)
    try:
        return array.index(item, start, finish)
    except ValueError:
        return -1


def get_next_segment(segments, segment):
    for i in range(len(segments)):
        if segments[i][0] == segment[1]:
            return [segments[i], i]
        elif segments[i][1] == segment[1]:
            return [[segments[i][1], segments[i][0]], i]


def get_common_outline(consts):
    segments = []
    for const in consts:
        coords = get_coords(const)[0]
        for i in range(len(coords)):
            if i < len(coords) - 1:
                segments.append([coords[i], coords[i + 1]])
            else:
                segments.append([coords[i], coords[0]])

    i = 0
    while i < len(segments):
        next_pos = indexi(segments, segments[i], i + 1)
        if next_pos > 0:
            segments = segments[0: i] + segments[i + 1: len(segments)]
        else:
            i += 1

    ordered_segments = [segments[0]]
    for i in range(len(segments)):
        thing = get_next_segment(segments, ordered_segments[i])
        ordered_segments.append(thing[0])
        segments = segments[0: i] + segments[i + 1: len(segments)]

    coords = []
    for seg in ordered_segments:
        coords.append(seg[0])

    return [coords]


def get_coords(country):
    if len(country.coords) > 1:
        return [copy.deepcopy(country.coords)]
    else:
        return get_common_outline(country.consts)


def draw_map(clicked, screen, countries, o_x, o_y, zoom):
    if clicked[0] != 0:
        draw_map(clicked[1::len(clicked)], screen, countries[clicked], o_x, o_y, zoom)
    else:
        for i in range(0, len(countries)):
            coord_set = get_coords(countries[i])
            color = countries[i].color
            for coords in coord_set:
                pygame.draw.polygon(screen, color, coords_alterer(coords, o_x, o_y, zoom))
                pygame.draw.polygon(screen, (0, 0, 0), coords, zoom)


def country_clicked_getter(countries, x, y, o_x, o_y, zoom):
    for i in range(0, len(countries)):
        for coords in get_coords(countries[i]):
            if Polygon(coords_alterer(coords, o_x, o_y, zoom)).contains(Point(x, y)):
                return i
    return 0


def init_gui(manager):
    gui_dict = {"quit": pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((700, 550), (100, 50)),
        text="Quit",
        manager=manager
    )}
    return gui_dict


def map_handler(md):
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption(f"MapView {json.load(open('properties.json'))['version']}")

    manager = pygame_gui.UIManager((800, 600))
    gui_dict = init_gui(manager)

    clock = pygame.time.Clock()
    running = True
    panning = False
    o_x, o_tx, o_y, o_ty = 0, 0, 0, 0
    clicked_list = [0]
    zoom = 2
    while running:
        time_delta = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == gui_dict["quit"]:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:  # Middle Click
                panning = True
                o_tx, o_ty = event.pos

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                panning = False

            elif event.type == pygame.MOUSEMOTION and panning:
                o_x += (event.pos[0] - o_tx)
                o_y += (event.pos[1] - o_ty)
                o_tx, o_ty = event.pos

            elif event.type == pygame.MOUSEWHEEL:  # Mouse Wheel
                zoom += event.y * 2
                if zoom <= 2:
                    zoom = 2

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left Click
                clicked = country_clicked_getter(md.countries, event.pos[0], event.pos[1], o_x, o_y, zoom)
                if clicked != 0:
                    clicked_list.append(clicked)
                    clicked_on = md.countries[clicked]
                    full_name = clicked_on.name
                    if clicked_on.prefix is not None:
                        full_name = clicked_on.prefix + full_name
                    if clicked_on.suffix is not None:
                        full_name += clicked_on.suffix
                    print("Name:", full_name)
                else:
                    clicked_list = [0]

            elif event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == gui_dict["hello_button"]:
                    print('Hello World!')

            manager.process_events(event)

        manager.update(time_delta)

        screen.fill(BACKGROUND)
        draw_map(clicked_list, screen, md.countries, o_x, o_y, zoom)
        manager.draw_ui(screen)
        pygame.display.update()


def read_country(count):
    count_data = {"name": None, "prefix": None, "suffix": None, "color": None, "government": None, "leader": None}
    for key, value in count.items():
        try:
            count_data[key] = count[key]
        except KeyError:
            pass
    country = Region(count_data)
    try:
        for coords in count["coordinates"]:
            country.add_coord((coords[0], coords[1]))
    except KeyError:
        for ct in count["constituencies"]:
            country.add_const(read_country(ct))
    return country


def read_map(fn):
    if fn is None:
        fn = input("File to be opened: ")
    file = json.load(open("map/" + fn))
    md = MapData()
    for count in file["map_data"]:
        md.add_country(read_country(count))
    return md


if __name__ == "__main__":
    args = parser.parse_args()
    file_name = args.filename

    map_data = read_map(file_name)
    map_handler(map_data)

    pygame.quit()

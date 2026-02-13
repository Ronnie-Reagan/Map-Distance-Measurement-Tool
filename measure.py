import sys
import math
import pygame
import tkinter as tk
from tkinter import simpledialog, filedialog

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
BACKGROUND_COLOR = (30, 30, 30)
LINE_COLOR = (0, 255, 0)
POINT_COLOR = (255, 50, 50)
CALIBRATION_COLOR = (50, 150, 255)
TEXT_COLOR = (255, 255, 255)

UNIT_FACTORS = {
    "pixels": 1.0,
    "m": 1.0,
    "cm": 100.0,
    "mm": 1000.0,
    "km": 0.001,
    "in": 39.3701,
    "ft": 3.28084,
    "mi": 0.000621371,
    "pc": 3.24078e-17
}

def distance(p1, p2):
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

class MeasureApp:
    def __init__(self, image_path):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Map Distance Measurement Tool")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)

        self.image_original = pygame.image.load(image_path).convert()
        self.zoom = 1.0
        self.offset = [0.0, 0.0]
        self.dragging = False
        self.drag_start = (0, 0)

        self.mode = "calibrate"
        self.calibration_points = []
        self.current_polyline = []
        self.finished_polylines = []

        self.meters_per_pixel = None
        self.display_unit = "m"

        # GUI dialogs for known distance
        self.known_distance_value, self.known_distance_unit = self.ask_known_distance()
        self.known_distance_meters = self.known_distance_value / UNIT_FACTORS[self.known_distance_unit]

        # Fit image to window initially
        img_w, img_h = self.image_original.get_size()
        scale_w = WINDOW_WIDTH / img_w
        scale_h = WINDOW_HEIGHT / img_h
        self.zoom = min(scale_w, scale_h, 1.0)
        self.offset = [(WINDOW_WIDTH - img_w * self.zoom) / 2,
                       (WINDOW_HEIGHT - img_h * self.zoom) / 2]

    def ask_known_distance(self):
        root = tk.Tk()
        root.withdraw()  # hide main window
        while True:
            try:
                val = simpledialog.askfloat("Calibration", "Enter known distance (e.g., 12.5):")
                if val is None:  # user cancelled
                    pygame.quit()
                    sys.exit(0)
                break
            except ValueError:
                continue

        while True:
            unit = simpledialog.askstring("Calibration", f"Enter unit ({', '.join(UNIT_FACTORS.keys())}):")
            if unit is None:
                pygame.quit()
                sys.exit(0)
            unit = unit.strip().lower()
            if unit in UNIT_FACTORS:
                break
        return val, unit

    # Coordinate transforms
    def world_to_screen(self, pos):
        return (pos[0] * self.zoom + self.offset[0], pos[1] * self.zoom + self.offset[1])

    def screen_to_world(self, pos):
        return ((pos[0] - self.offset[0]) / self.zoom, (pos[1] - self.offset[1]) / self.zoom)

    # Distance
    def polyline_pixel_length(self, polyline):
        return sum(distance(polyline[i-1], polyline[i]) for i in range(1, len(polyline)))

    def polyline_meter_length(self, polyline):
        if not self.meters_per_pixel:
            return 0
        return self.polyline_pixel_length(polyline) * self.meters_per_pixel

    def total_meter_length(self):
        total = sum(self.polyline_meter_length(pl) for pl in self.finished_polylines)
        total += self.polyline_meter_length(self.current_polyline)
        return total

    # Drawing
    def draw_polyline(self, polyline, color):
        if len(polyline) > 1:
            for i in range(1, len(polyline)):
                pygame.draw.line(self.screen, color,
                                 self.world_to_screen(polyline[i-1]),
                                 self.world_to_screen(polyline[i]), 2)
        for p in polyline:
            pygame.draw.circle(self.screen, POINT_COLOR, (int(self.world_to_screen(p)[0]),
                                                          int(self.world_to_screen(p)[1])), 4)

    def draw_ui(self):
        lines = [
            f"Mode: {self.mode.upper()}",
            f"Zoom: {self.zoom:.2f}x",
            f"Display Unit: {self.display_unit}"
        ]
        if self.meters_per_pixel:
            factor = UNIT_FACTORS[self.display_unit]
            current = self.polyline_meter_length(self.current_polyline) * factor
            total = self.total_meter_length() * factor
            lines.append(f"Current: {current:.4f} {self.display_unit}")
            lines.append(f"Total:   {total:.4f} {self.display_unit}")
            lines.append(f"Scale: 1 pixel = {self.meters_per_pixel:.6f} m")

        lines += [
            "",
            "Left Click: Add Point",
            "Right Click: Finish Line",
            "Middle Drag: Pan",
            "Mouse Wheel: Zoom",
            "C: Calibrate | U: Undo | R: Reset All | ESC: Quit",
            "Number keys 1-9: Change display unit"
        ]

        x_margin, y_margin = 10, 10
        y = y_margin
        for line in lines:
            text = self.font.render(line, True, TEXT_COLOR)
            self.screen.blit(text, (x_margin, y))
            y += 22

    # Calibration
    def finish_calibration(self):
        if len(self.calibration_points) == 2:
            px = distance(self.calibration_points[0], self.calibration_points[1])
            if px > 0:
                self.meters_per_pixel = self.known_distance_meters / px
            self.calibration_points.clear()
            self.mode = "measure"

    # Main loop
    def run(self):
        running = True
        while running:
            self.clock.tick(60)
            self.screen.fill(BACKGROUND_COLOR)

            scaled = pygame.transform.smoothscale(
                self.image_original,
                (int(self.image_original.get_width() * self.zoom),
                 int(self.image_original.get_height() * self.zoom))
            )
            self.screen.blit(scaled, self.offset)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_c:
                        self.mode = "calibrate"
                        self.calibration_points.clear()
                    elif event.key == pygame.K_u and self.current_polyline:
                        self.current_polyline.pop()
                    elif event.key == pygame.K_r:
                        self.current_polyline.clear()
                        self.finished_polylines.clear()
                    elif event.key in map(ord, "123456789"):
                        units = list(UNIT_FACTORS.keys())
                        index = int(chr(event.key)) - 1
                        if index < len(units):
                            self.display_unit = units[index]

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        world = self.screen_to_world(event.pos)
                        if self.mode == "calibrate":
                            self.calibration_points.append(world)
                            if len(self.calibration_points) == 2:
                                self.finish_calibration()
                        else:
                            self.current_polyline.append(world)
                    elif event.button == 3:
                        if self.mode == "measure" and len(self.current_polyline) > 1:
                            self.finished_polylines.append(self.current_polyline.copy())
                            self.current_polyline.clear()
                    elif event.button == 2:
                        self.dragging = True
                        self.drag_start = event.pos
                    elif event.button in (4, 5):
                        mouse_pos = event.pos
                        zoom_factor = 1.1 if event.button == 4 else 1/1.1
                        mouse_world = self.screen_to_world(mouse_pos)
                        self.zoom = min(max(self.zoom * zoom_factor, 0.1), 10.0)
                        mouse_screen_after = self.world_to_screen(mouse_world)
                        self.offset[0] += mouse_pos[0] - mouse_screen_after[0]
                        self.offset[1] += mouse_pos[1] - mouse_screen_after[1]

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                    self.dragging = False

                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    dx = event.pos[0] - self.drag_start[0]
                    dy = event.pos[1] - self.drag_start[1]
                    self.offset[0] += dx
                    self.offset[1] += dy
                    self.drag_start = event.pos

                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            for pl in self.finished_polylines:
                self.draw_polyline(pl, LINE_COLOR)

            if self.mode == "calibrate":
                self.draw_polyline(self.calibration_points, CALIBRATION_COLOR)
            else:
                self.draw_polyline(self.current_polyline, LINE_COLOR)

            self.draw_ui()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    image_path = filedialog.askopenfilename(title="Select Map Image")
    if not image_path:
        sys.exit(0)

    app = MeasureApp(image_path)
    app.run()

import pygame as pg
from logic import GameLogic
import sys
import random



class Game:
    def __init__(self):
        pg.init()
        self.size = self.width, self.height = 500, 500
        self.screen = pg.display.set_mode(self.size)
        self.clock = pg.time.Clock()
        self.grid_size = 4
        self.game_logic = GameLogic(self.grid_size)
        self.cell_size = self.width // self.grid_size
        self.font = pg.font.Font('freesansbold.ttf', self.cell_size // 2)
        self.grid = self.game_logic.set_board()
    
    def draw_grid(self):
        self.grid = self.game_logic.set_board()
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                value = self.grid[y][x]
                rect = (x * self.cell_size + 3, y * self.cell_size + 3, self.cell_size - 6, self.cell_size - 6)

                # Choose color per value (examples — tweak as you like)
                if value == 0:
                    tile_color = (205, 193, 180)
                    text_str = ''
                elif value == 2:
                    tile_color = (238, 228, 218)
                    text_str = '2'
                elif value == 4:
                    tile_color = (237, 224, 200)
                    text_str = '4'
                elif value == 8:
                    tile_color = (242, 177, 121)
                    text_str = '8'
                elif value == 16:
                    tile_color = (245, 149, 99)
                    text_str = '16'
                elif value == 32:
                    tile_color = (246, 124, 95)
                    text_str = '32'
                elif value == 64:
                    tile_color = (246, 94, 59)
                    text_str = '64'
                elif value == 128:
                    tile_color = (237, 207, 114)
                    text_str = '128'
                elif value == 256:
                    tile_color = (237, 204, 97)
                    text_str = '256'
                elif value == 512:
                    tile_color = (237, 200, 80)
                    text_str = '512'
                elif value == 1024:
                    tile_color = (237, 197, 63)
                    text_str = '1024'
                elif value == 2048:
                    tile_color = (237, 194, 46)
                    text_str = '2048'
                else:
                    tile_color = (60, 58, 50)
                    text_str = str(value)

                # Draw the tile first (filled)
                pg.draw.rect(self.screen, tile_color, rect, 0)

                # Pick a text color that has contrast with the tile
                # Light tiles -> dark text; dark tiles -> white text
                if value in (0, 2, 4, 8, 16, 32, 64):
                    text_color = (119, 110, 101)  # dark gray for light tiles
                else:
                    text_color = (255, 255, 255)  # white for darker tiles

                # Render and blit text if not empty
                if text_str:
                    text = self.font.render(text_str, True, text_color)
                    text_rect = text.get_rect(center=(x * self.cell_size + self.cell_size // 2,
                                                      y * self.cell_size + self.cell_size // 2))
                    self.screen.blit(text, text_rect)
        
    def run(self):
        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()
                elif event.type == pg.KEYDOWN:
                    self.game_logic.print_board()
                    if event.key == pg.K_UP:
                        self.game_logic.move('up')
                    elif event.key == pg.K_DOWN:
                        self.game_logic.move('down')
                    elif event.key == pg.K_LEFT:
                        self.game_logic.move('left')
                    elif event.key == pg.K_RIGHT:
                        self.game_logic.move('right')
                    self.game_logic.add_random_tile()

            self.screen.fill((90, 173, 160))
            self.draw_grid()
            pg.display.flip()
            self.clock.tick(60)

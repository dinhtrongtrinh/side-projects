from move import Move

class GameLogic:
    def __init__(self, size=4):
        self.size = size
        self.board = [[0] * size for _ in range(size)]
        self.score = 0
        self.move_handler = Move()
        self.reset()

    def set_board(self):
        return self.board

    def reset(self):
        self.board = [[0] * self.size for _ in range(self.size)]
        self.score = 0
        self.add_random_tile()
        self.add_random_tile()

    def add_random_tile(self):
        import random
        empty_cells = [(r, c) for r in range(self.size) for c in range(self.size) if self.board[r][c] == 0]
        if empty_cells:
            r, c = random.choice(empty_cells)
            self.board[r][c] = 2 if random.random() < 0.9 else 4
    
    def print_board(self):
        for row in self.board:
            print('\t'.join(str(num) for num in row))
        print(f"Score: {self.score}\n")


    def move(self, direction):
        if direction == 'up':
            self.move_handler.move_up(self.board)
        elif direction == 'down':
            self.move_handler.move_down(self.board)
        elif direction == 'left':
            self.move_handler.move_left(self.board)
    
        elif direction == 'right':
            self.move_handler.move_right(self.board)

    def can_move(self):
        # Check if any moves are possible
        pass

    def is_game_over(self):
        return not self.can_move()
class Move:
    def __init__(self):
        pass

    def move_up(self, board):
        size = len(board)
        for c in range(size):
            col = [board[r][c] for r in range(size) if board[r][c] != 0]
            merged_col = []
            skip = False
            for i in range(len(col)):
                if skip:
                    skip = False
                    continue
                if i + 1 < len(col) and col[i] == col[i + 1]:
                    merged_col.append(col[i] * 2)
                    skip = True
                else:
                    merged_col.append(col[i])
            merged_col += [0] * (size - len(merged_col))
            for r in range(size):
                board[r][c] = merged_col[r]
    
    def move_down(self, board):
        size = len(board)
        for c in range(size):
            col = [board[r][c] for r in range(size) if board[r][c] != 0]
            merged_col = []
            skip = False
            for i in range(len(col) - 1, -1, -1):
                if skip:
                    skip = False
                    continue
                if i - 1 >= 0 and col[i] == col[i - 1]:
                    merged_col.append(col[i] * 2)
                    skip = True
                else:
                    merged_col.append(col[i])
            merged_col += [0] * (size - len(merged_col))
            merged_col.reverse()
            for r in range(size):
                board[r][c] = merged_col[r]

    def move_left(self, board):
        size = len(board)
        for r in range(size):
            row = [board[r][c] for c in range(size) if board[r][c] != 0]
            merged_row = []
            skip = False
            for i in range(len(row)):
                if skip:
                    skip = False
                    continue
                if i + 1 < len(row) and row[i] == row[i + 1]:
                    merged_row.append(row[i] * 2)
                    skip = True
                else:
                    merged_row.append(row[i])
            merged_row += [0] * (size - len(merged_row))
            for c in range(size):
                board[r][c] = merged_row[c]


    def move_right(self, board):
        size = len(board)
        for r in range(size):
            row = [board[r][c] for c in range(size) if board[r][c] != 0]
            merged_row = []
            skip = False
            for i in range(len(row) - 1, -1, -1):
                if skip:
                    skip = False
                    continue
                if i - 1 >= 0 and row[i] == row[i - 1]:
                    merged_row.append(row[i] * 2)
                    skip = True
                else:
                    merged_row.append(row[i])
            merged_row += [0] * (size - len(merged_row))
            merged_row.reverse()
            for c in range(size):
                board[r][c] = merged_row[c]

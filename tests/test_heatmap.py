import torch

from pagesight.retrieval.colsmol import tile_grid

TAGS = {100: (1, 1), 101: (1, 2)}  # token id -> (row, col) of the tile it opens


def test_tiles_are_placed_side_by_side_and_the_global_tile_is_left_out():
    # 2 tiles of 4 tokens (2 x 2 each), then a downscaled global tile that must be ignored
    ids = [9, 100, 5, 5, 5, 5, 101, 5, 5, 5, 5, 7, 5, 5, 5, 5]
    scores = torch.arange(len(ids), dtype=torch.float)

    grid = tile_grid(ids, scores, TAGS, seq_len=4)

    assert grid.tolist() == [[2, 3, 7, 8], [4, 5, 9, 10]]


def test_tiles_in_two_rows_stack_vertically():
    tags = {100: (1, 1), 101: (2, 1)}
    ids = [100, 5, 5, 5, 5, 101, 5, 5, 5, 5]

    grid = tile_grid(ids, torch.arange(len(ids), dtype=torch.float), tags, seq_len=4)

    assert grid.tolist() == [[1, 2], [3, 4], [6, 7], [8, 9]]

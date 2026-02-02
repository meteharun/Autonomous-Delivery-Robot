import numpy as np
from typing import Tuple, List, Set

class GridWorld:
    """
    Simulates a 2D grid environment for the delivery robot.
    """
    
    def __init__(self, width: int = 22, height: int = 15):
        self.width = width
        self.height = height
        self.grid = np.zeros((height, width), dtype=int)
        
        # Grid cell types
        self.EMPTY = 0
        self.OBSTACLE = 1
        self.BASE = 2
        self.DELIVERY_LOCATION = 3
        self.ROBOT = 4
        self.DYNAMIC_OBSTACLE = 5
        
        # Base location (robot starts and returns here)
        self.base_location = (1, 1)
        # Mark 2x2 area for supermarket visual (0,0), (0,1), (1,0), (1,1)
        self.grid[0, 0] = self.BASE
        self.grid[0, 1] = self.BASE
        self.grid[1, 0] = self.BASE
        self.grid[1, 1] = self.BASE
        
        # Delivery locations (12 houses spread across the map)
        self.delivery_locations = [
            # Left section
            (4, 4), (8, 2), (12, 4),
            # Middle section
            (2, 10), (6, 12), (10, 10), (13, 12),
            # Right section (moved from columns 22-24)
            (0, 15), (14, 2), (14, 18),
            # Additional
            (3, 19), (11, 20)
        ]
        
        for loc in self.delivery_locations:
            if 0 <= loc[0] < self.height and 0 <= loc[1] < self.width:
                if self.grid[loc] == self.EMPTY:
                    self.grid[loc] = self.DELIVERY_LOCATION
        
        # Static obstacles (trees)
        self._create_static_obstacles()
        
        # Dynamic obstacles (temporary blockages)
        self.dynamic_obstacles: Set[Tuple[int, int]] = set()
        
    def _create_static_obstacles(self):
        """Create static obstacles (trees) on the map - complex layout."""
        obstacles = [
            # === Left section (columns 0-8) ===
            # Vertical tree line near base
            (4, 0), (5, 0),
            # Tree cluster top-left
            (0, 3), (0, 4),
            # Scattered trees
            (2, 3), (3, 3),
            (5, 2), (6, 2),
            (2, 6), (3, 6),
            (6, 5), (7, 5), (7, 6),
            (9, 1), (10, 1), (10, 2),
            (9, 4), (9, 5),
            (12, 1), (13, 1),
            (11, 6), (12, 6),
            (5, 7), (6, 7),
            (14, 4), (14, 5),
            
            # === Middle section (columns 9-16) ===
            # Tree clusters
            (0, 9), (1, 9),
            (3, 9), (4, 9),
            (0, 13), (1, 13),
            (3, 13), (4, 13),
            (7, 9), (8, 9),
            (7, 14), (8, 14),
            (5, 10), (5, 11),
            (9, 12), (9, 13),
            (11, 8), (12, 8),
            (11, 14), (12, 14),
            (14, 9), (14, 10),
            (14, 13), (14, 14),
            # Middle area
            (6, 15), (6, 16),
            (10, 15), (10, 16),
            
            # === Right section (columns 17-21) ===
            # Tree clusters
            (0, 17), (1, 17),
            (0, 21), (1, 21),
            (2, 17), (2, 18),
            (4, 20), (4, 21),
            (6, 18), (6, 19),
            (8, 17), (9, 17),
            (8, 21), (9, 21),
            (12, 17), (12, 18),
            (12, 20), (12, 21),
        ]
        
        for pos in obstacles:
            if 0 <= pos[0] < self.height and 0 <= pos[1] < self.width:
                if self.grid[pos] == self.EMPTY:
                    self.grid[pos] = self.OBSTACLE
    
    def is_valid_position(self, pos: Tuple[int, int]) -> bool:
        """Check if a position is valid and not blocked."""
        row, col = pos
        if not (0 <= row < self.height and 0 <= col < self.width):
            return False
        
        cell_type = self.grid[row, col]
        if cell_type == self.OBSTACLE or cell_type == self.DYNAMIC_OBSTACLE:
            return False
        
        return True
    
    def add_dynamic_obstacle(self, pos: Tuple[int, int]) -> bool:
        """Add a temporary blockage at the given position."""
        if self.is_valid_position(pos) and pos != self.base_location:
            if pos not in self.delivery_locations:
                self.dynamic_obstacles.add(pos)
                self.grid[pos] = self.DYNAMIC_OBSTACLE
                return True
        return False
    
    def remove_dynamic_obstacle(self, pos: Tuple[int, int]) -> bool:
        """Remove a temporary blockage."""
        if pos in self.dynamic_obstacles:
            self.dynamic_obstacles.remove(pos)
            self.grid[pos] = self.EMPTY
            return True
        return False
    
    def get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get valid neighboring positions (4-connected)."""
        row, col = pos
        neighbors = [
            (row - 1, col),  # up
            (row + 1, col),  # down
            (row, col - 1),  # left
            (row, col + 1)   # right
        ]
        
        return [n for n in neighbors if self.is_valid_position(n)]
    
    def get_grid_copy(self) -> np.ndarray:
        """Return a copy of the current grid state."""
        return self.grid.copy()
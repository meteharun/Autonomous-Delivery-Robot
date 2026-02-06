"""
Shared state models - all serializable to/from JSON for MQTT messages.
"""
import time
from typing import List, Tuple


def create_order(order_id: str, delivery_location: Tuple[int, int], timestamp: float = None) -> dict:
    """Create an order dictionary."""
    return {
        'order_id': order_id,
        'delivery_location': list(delivery_location),
        'timestamp': timestamp or time.time(),
        'status': 'pending'
    }


def create_initial_knowledge(base_location: Tuple[int, int], max_capacity: int = 3) -> dict:
    """Create initial knowledge state."""
    return {
        'base_location': list(base_location),
        'max_capacity': max_capacity,
        'robot_position': list(base_location),
        'robot_is_at_base': True,
        'pending_orders': [],
        'loaded_orders': [],
        'completed_orders': [],
        'current_plan': None,
        'current_plan_index': 0,
        'delivery_sequence': [],
        'original_last_delivery': None,
        'last_mission_start_time': time.time(),
        'mission_timeout': 30,
        'mission_in_progress': False,
        'is_stuck': False,
        'known_blockages': [],
        'total_distance_traveled': 0,
        'number_of_replans': 0,
        'delivery_times': []
    }


def create_initial_grid(width: int = 22, height: int = 15) -> dict:
    """Create initial grid state."""
    grid = [[0 for _ in range(width)] for _ in range(height)]
    
    EMPTY = 0
    OBSTACLE = 1
    BASE = 2
    DELIVERY_LOCATION = 3
    
    base_location = [1, 1]
    grid[0][0] = BASE
    grid[0][1] = BASE
    grid[1][0] = BASE
    grid[1][1] = BASE
    
    delivery_locations = [
        [4, 4], [8, 2], [12, 4],
        [2, 10], [6, 12], [10, 10], [13, 12],
        [0, 15], [14, 2], [14, 18],
        [3, 19], [11, 20]
    ]
    
    for loc in delivery_locations:
        if 0 <= loc[0] < height and 0 <= loc[1] < width:
            if grid[loc[0]][loc[1]] == EMPTY:
                grid[loc[0]][loc[1]] = DELIVERY_LOCATION
    
    obstacles = [
        [4, 0], [5, 0], [0, 3], [0, 4], [2, 3], [3, 3], [5, 2], [6, 2],
        [2, 6], [3, 6], [6, 5], [7, 5], [7, 6], [9, 1], [10, 1], [10, 2],
        [9, 4], [9, 5], [12, 1], [13, 1], [11, 6], [12, 6], [5, 7], [6, 7],
        [14, 4], [14, 5], [0, 9], [1, 9], [3, 9], [4, 9], [0, 13], [1, 13],
        [3, 13], [4, 13], [7, 9], [8, 9], [7, 14], [8, 14], [5, 10], [5, 11],
        [9, 12], [9, 13], [11, 8], [12, 8], [11, 14], [12, 14], [14, 9], [14, 10],
        [14, 13], [14, 14], [6, 15], [6, 16], [10, 15], [10, 16], [0, 17], [1, 17],
        [0, 21], [1, 21], [2, 17], [2, 18], [4, 20], [4, 21], [6, 18], [6, 19],
        [8, 17], [9, 17], [8, 21], [9, 21], [12, 17], [12, 18], [12, 20], [12, 21],
    ]
    
    for pos in obstacles:
        if 0 <= pos[0] < height and 0 <= pos[1] < width:
            if grid[pos[0]][pos[1]] == EMPTY:
                grid[pos[0]][pos[1]] = OBSTACLE
    
    return {
        'width': width,
        'height': height,
        'grid': grid,
        'base_location': base_location,
        'delivery_locations': delivery_locations,
        'dynamic_obstacles': []
    }


def create_initial_robot(start_position: Tuple[int, int], max_capacity: int = 3) -> dict:
    """Create initial robot state."""
    return {
        'position': list(start_position),
        'max_capacity': max_capacity,
        'loaded_orders': [],
        'is_at_base': True
    }
from typing import List, Dict, Tuple, Optional
from environment.robot import Order
import time

class Knowledge:
    """
    Knowledge base that stores all system state and information.
    Shared by all MAPE components.
    This is pure storage - does NOT hold references to environment objects.
    """
    
    def __init__(self, base_location: Tuple[int, int], max_capacity: int = 3):
        # Base configuration
        self.base_location = base_location
        self.max_capacity = max_capacity
        
        # Robot state (updated by Monitor)
        self.robot_position: Tuple[int, int] = base_location
        self.robot_is_at_base: bool = True
        
        # Orders
        self.pending_orders: List[Order] = []
        self.loaded_orders: List[Order] = []
        self.completed_orders: List[Order] = []
        
        # Planning
        self.current_plan: Optional[List[Tuple[int, int]]] = None
        self.current_plan_index: int = 0
        self.delivery_sequence: List[Tuple[int, int]] = []
        self.original_last_delivery: Optional[Tuple[int, int]] = None
        
        # Timing
        self.last_mission_start_time: float = time.time()
        self.mission_timeout: float = 30  # 30 seconds
        self.mission_in_progress: bool = False
        
        # Stuck state
        self.is_stuck: bool = False
        
        # Dynamic obstacles (updated by Monitor)
        self.known_blockages: List[Tuple[int, int]] = []
        
        # Metrics
        self.total_distance_traveled: int = 0
        self.number_of_replans: int = 0
        self.delivery_times: List[float] = []
        
    def add_order(self, order: Order) -> None:
        """Add a new order to pending queue."""
        self.pending_orders.append(order)
        if len(self.pending_orders) == 1:
            self.last_mission_start_time = time.time()
    
    def should_start_mission(self) -> bool:
        """Determine if a delivery mission should start."""
        if self.mission_in_progress:
            return False
        
        if len(self.pending_orders) >= self.max_capacity:
            return True
        
        if self.pending_orders:
            time_elapsed = time.time() - self.last_mission_start_time
            if time_elapsed >= self.mission_timeout:
                return True
        
        return False
    
    def start_mission(self) -> None:
        """Mark the start of a delivery mission."""
        self.mission_in_progress = True
        self.last_mission_start_time = time.time()
    
    def set_delivery_sequence(self, sequence: List[Tuple[int, int]]) -> None:
        """Set delivery sequence and store the original last delivery."""
        self.delivery_sequence = sequence
        if sequence:
            self.original_last_delivery = sequence[-1]
    
    def end_mission(self) -> None:
        """Mark the end of a delivery mission."""
        self.mission_in_progress = False
        self.current_plan = None
        self.current_plan_index = 0
        self.delivery_sequence = []
        self.original_last_delivery = None
        self.loaded_orders = []
        self.is_stuck = False
    
    def update_robot_position(self, new_position: Tuple[int, int]) -> None:
        """Update robot position and tracking metrics."""
        self.robot_position = new_position
        self.robot_is_at_base = (new_position == self.base_location)
        if self.current_plan and self.current_plan_index < len(self.current_plan):
            self.current_plan_index += 1
            self.total_distance_traveled += 1
    
    def is_path_blocked(self, grid_world) -> bool:
        """Check if the current planned path is blocked."""
        if not self.current_plan:
            return False
        
        for i in range(self.current_plan_index, len(self.current_plan)):
            pos = self.current_plan[i]
            if not grid_world.is_valid_position(pos):
                return True
        
        return False
    
    def get_next_position(self) -> Optional[Tuple[int, int]]:
        """Get the next position in the current plan."""
        if not self.current_plan:
            return None
        
        if self.current_plan_index < len(self.current_plan):
            return self.current_plan[self.current_plan_index]
        
        return None
    
    def record_delivery(self, order: Order) -> None:
        """Record a completed delivery."""
        delivery_time = time.time() - order.timestamp
        self.delivery_times.append(delivery_time)
        self.completed_orders.append(order)
    
    def increment_replan_counter(self) -> None:
        """Increment the replan counter."""
        self.number_of_replans += 1
    
    def get_metrics(self) -> Dict:
        """Get current system metrics."""
        avg_delivery_time = (sum(self.delivery_times) / len(self.delivery_times) 
                            if self.delivery_times else 0)
        
        return {
            'total_deliveries': len(self.completed_orders),
            'pending_orders': len(self.pending_orders),
            'total_distance': self.total_distance_traveled,
            'replans': self.number_of_replans,
            'avg_delivery_time': avg_delivery_time
        }
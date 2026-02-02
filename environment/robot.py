from typing import Tuple, List, Optional
from dataclasses import dataclass

@dataclass
class Order:
    """Represents a delivery order."""
    order_id: str
    delivery_location: Tuple[int, int]
    timestamp: float
    status: str = "pending"  # pending, loaded, delivered

class Robot:
    """
    Represents the delivery robot with its sensors and effectors.
    """
    
    def __init__(self, start_position: Tuple[int, int], max_capacity: int = 5):
        self.position = start_position
        self.max_capacity = max_capacity
        self.loaded_orders: List[Order] = []
        self.is_at_base = True
        
    def get_position(self) -> Tuple[int, int]:
        """Sensor: Get current position."""
        return self.position
    
    def get_loaded_orders(self) -> List[Order]:
        """Sensor: Get currently loaded orders."""
        return self.loaded_orders.copy()
    
    def get_capacity_status(self) -> Tuple[int, int]:
        """Sensor: Get (current_load, max_capacity)."""
        return (len(self.loaded_orders), self.max_capacity)
    
    def is_capacity_full(self) -> bool:
        """Check if robot is at full capacity."""
        return len(self.loaded_orders) >= self.max_capacity
    
    def move(self, new_position: Tuple[int, int]) -> bool:
        """Effector: Move to a new position."""
        self.position = new_position
        self.is_at_base = False
        return True
    
    def load_order(self, order: Order) -> bool:
        """Effector: Load an order (must be at base)."""
        if not self.is_at_base:
            return False
        
        if len(self.loaded_orders) >= self.max_capacity:
            return False
        
        order.status = "loaded"
        self.loaded_orders.append(order)
        return True
    
    def deliver_order(self, order_id: str) -> Optional[Order]:
        """Effector: Deliver an order at current location."""
        for i, order in enumerate(self.loaded_orders):
            if order.order_id == order_id and order.delivery_location == self.position:
                order.status = "delivered"
                return self.loaded_orders.pop(i)
        return None
    
    def return_to_base(self, base_position: Tuple[int, int]) -> None:
        """Mark robot as being at base."""
        if self.position == base_position:
            self.is_at_base = True
    
    def clear_loaded_orders(self) -> None:
        """Clear all loaded orders (after delivery mission)."""
        self.loaded_orders.clear()
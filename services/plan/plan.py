from mape_k.knowledge import Knowledge
from utils.pathfinding import AStar, DeliveryPlanner
from environment.robot import Order
from typing import Dict, Any, List, Tuple, Optional
import time

class Plan:
    """
    Plan component of MAPE-K loop.
    Creates adaptation plans based on analysis results.
    Uses grid_world for pathfinding calculations.
    """
    
    def __init__(self, knowledge: Knowledge, grid_world):
        self.knowledge = knowledge
        self.grid_world = grid_world  # Needed for pathfinding
    
    def create_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create an adaptation plan based on analysis."""
        if not analysis['requires_adaptation']:
            return {'action': 'continue', 'details': None}
        
        adaptation_type = analysis['adaptation_type']
        
        if adaptation_type == 'start_mission':
            return self._plan_new_mission()
        elif adaptation_type == 'replan_path':
            return self._plan_path_adaptation()
        elif adaptation_type == 'deliver_order':
            return self._plan_delivery()
        elif adaptation_type == 'end_mission':
            return {'action': 'end_mission', 'details': None}
        
        return {'action': 'continue', 'details': None}
    
    def _plan_new_mission(self) -> Dict[str, Any]:
        """Plan a new delivery mission."""
        orders_to_load = self.knowledge.pending_orders[:self.knowledge.max_capacity]
        
        if not orders_to_load:
            return {'action': 'continue', 'details': None}
        
        delivery_locations = [order.delivery_location for order in orders_to_load]
        
        sequence = DeliveryPlanner.plan_delivery_sequence(
            self.grid_world,
            self.knowledge.base_location,
            delivery_locations,
            self.knowledge.base_location
        )
        
        full_path = DeliveryPlanner.create_full_path(
            self.grid_world,
            self.knowledge.base_location,
            sequence,
            self.knowledge.base_location
        )
        
        if full_path is None:
            print("Warning: Could not create valid path for mission")
            return {'action': 'continue', 'details': None}
        
        return {
            'action': 'start_mission',
            'details': {
                'orders_to_load': orders_to_load,
                'delivery_sequence': sequence,
                'full_path': full_path
            }
        }
    
    def _plan_path_adaptation(self) -> Dict[str, Any]:
        """Replan the path due to blockage or other obstacle."""
        self.knowledge.increment_replan_counter()
        
        robot_pos = self.knowledge.robot_position
        remaining_deliveries = [order.delivery_location 
                              for order in self.knowledge.loaded_orders]
        
        new_sequence = []
        
        if not remaining_deliveries:
            new_path = AStar.find_path(
                self.grid_world,
                robot_pos,
                self.knowledge.base_location
            )
        else:
            new_sequence = DeliveryPlanner.plan_delivery_sequence(
                self.grid_world,
                robot_pos,
                remaining_deliveries,
                self.knowledge.base_location
            )
            
            new_path = DeliveryPlanner.create_full_path(
                self.grid_world,
                robot_pos,
                new_sequence,
                self.knowledge.base_location
            )
        
        if new_path is None:
            print("Warning: Could not find alternative path - robot is stuck")
            return {'action': 'wait', 'details': {'reason': 'no_valid_path'}}
        
        return {
            'action': 'replan',
            'details': {
                'new_path': new_path,
                'new_sequence': new_sequence
            }
        }
    
    def _plan_delivery(self) -> Dict[str, Any]:
        """Plan to deliver an order at the current location."""
        robot_pos = self.knowledge.robot_position
        
        order_to_deliver = None
        for order in self.knowledge.loaded_orders:
            if order.delivery_location == robot_pos:
                order_to_deliver = order
                break
        
        if order_to_deliver is None:
            return {'action': 'continue', 'details': None}
        
        return {
            'action': 'deliver',
            'details': {
                'order': order_to_deliver
            }
        }
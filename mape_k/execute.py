from mape_k.knowledge import Knowledge
from typing import Dict, Any
import time

class Execute:
    """
    Execute component of MAPE-K loop.
    Executes adaptation plans by commanding robot and environment through effectors.
    """
    
    def __init__(self, knowledge: Knowledge, grid_world, robot):
        self.knowledge = knowledge
        self.grid_world = grid_world  # Effector access to environment
        self.robot = robot  # Effector access to robot
    
    def execute_plan(self, plan: Dict[str, Any]) -> bool:
        """Execute the given adaptation plan."""
        action = plan['action']
        details = plan['details']
        
        if action == 'continue':
            return self._execute_continue()
        elif action == 'start_mission':
            return self._execute_start_mission(details)
        elif action == 'replan':
            return self._execute_replan(details)
        elif action == 'deliver':
            return self._execute_delivery(details)
        elif action == 'end_mission':
            return self._execute_end_mission()
        elif action == 'wait':
            return self._execute_wait(details)
        
        return False
    
    def _execute_continue(self) -> bool:
        """Continue executing the current plan (move to next position)."""
        if self.knowledge.is_stuck:
            return True
        
        if not self.knowledge.current_plan:
            return True
        
        next_pos = self.knowledge.get_next_position()
        
        if next_pos is None:
            return True
        
        # Check with environment if position is valid
        if not self.grid_world.is_valid_position(next_pos):
            return True
        
        # Command robot effector to move
        success = self.robot.move(next_pos)
        
        if success:
            # Update knowledge with new state
            self.knowledge.update_robot_position(next_pos)
            
            if next_pos == self.knowledge.base_location:
                self.robot.return_to_base(self.knowledge.base_location)
        
        return success
    
    def _execute_start_mission(self, details: Dict[str, Any]) -> bool:
        """Start a new delivery mission: load orders and begin execution."""
        orders_to_load = details['orders_to_load']
        delivery_sequence = details['delivery_sequence']
        full_path = details['full_path']
        
        # Command robot effector to load orders
        for order in orders_to_load:
            success = self.robot.load_order(order)
            if success:
                self.knowledge.pending_orders.remove(order)
        
        # Update knowledge with plan
        self.knowledge.current_plan = full_path
        self.knowledge.current_plan_index = 0
        self.knowledge.set_delivery_sequence(delivery_sequence)
        self.knowledge.loaded_orders = self.robot.get_loaded_orders()
        self.knowledge.start_mission()
        
        print(f"Started mission with {len(orders_to_load)} orders")
        print(f"Delivery sequence: {delivery_sequence}")
        
        return True
    
    def _execute_replan(self, details: Dict[str, Any]) -> bool:
        """Execute a replanned path."""
        new_path = details['new_path']
        new_sequence = details.get('new_sequence', [])
        
        self.knowledge.is_stuck = False
        self.knowledge.current_plan = new_path
        self.knowledge.current_plan_index = 0
        
        if new_sequence:
            self.knowledge.set_delivery_sequence(new_sequence)
            print(f"Replanned path, new length: {len(new_path)}, new sequence: {new_sequence}")
        else:
            print(f"Replanned path, new length: {len(new_path)}")
        
        return True
    
    def _execute_wait(self, details: Dict[str, Any]) -> bool:
        """Robot waits because no valid path exists."""
        reason = details.get('reason', 'unknown')
        self.knowledge.is_stuck = True
        print(f"Robot is waiting - reason: {reason}")
        return True
    
    def _execute_delivery(self, details: Dict[str, Any]) -> bool:
        """Execute a delivery at the current location."""
        order = details['order']
        
        # Command robot effector to deliver
        delivered_order = self.robot.deliver_order(order.order_id)
        
        if delivered_order:
            # Update knowledge
            self.knowledge.record_delivery(delivered_order)
            self.knowledge.loaded_orders = self.robot.get_loaded_orders()
            
            if order.delivery_location in self.knowledge.delivery_sequence:
                self.knowledge.delivery_sequence.remove(order.delivery_location)
            
            print(f"Delivered order {order.order_id} at {order.delivery_location}")
            return True
        
        return False
    
    def _execute_end_mission(self) -> bool:
        """End the current delivery mission."""
        # Command robot effector to clear orders
        self.robot.clear_loaded_orders()
        
        # Update knowledge
        self.knowledge.end_mission()
        print("Mission completed, robot returned to base")
        
        return True
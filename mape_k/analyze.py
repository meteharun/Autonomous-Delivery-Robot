from mape_k.knowledge import Knowledge
from typing import Dict, Any

class Analyze:
    """
    Analyze component of MAPE-K loop.
    Analyzes data from Knowledge to detect situations requiring adaptation.
    """
    
    def __init__(self, knowledge: Knowledge):
        self.knowledge = knowledge
    
    def analyze_situation(self, monitoring_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the current situation based on monitoring data."""
        analysis = {
            'requires_adaptation': False,
            'adaptation_type': None,
            'reason': None,
            'estimated_remaining_distance': 0
        }
        
        # Check if new mission should start
        if monitoring_results['needs_new_mission'] and not self.knowledge.mission_in_progress:
            analysis['requires_adaptation'] = True
            analysis['adaptation_type'] = 'start_mission'
            analysis['reason'] = 'Capacity full or timeout reached'
            return analysis
        
        # Check if path is blocked
        if monitoring_results['path_blocked']:
            analysis['requires_adaptation'] = True
            analysis['adaptation_type'] = 'replan_path'
            analysis['reason'] = 'Current path blocked by dynamic obstacle'
            return analysis
        
        # Check if obstacle was removed
        if monitoring_results.get('obstacle_removed', False) and self.knowledge.mission_in_progress:
            analysis['requires_adaptation'] = True
            analysis['adaptation_type'] = 'replan_path'
            if self.knowledge.is_stuck:
                analysis['reason'] = 'Obstacle removed - attempting to resume'
            else:
                analysis['reason'] = 'Obstacle removed - recalculating optimal path'
            return analysis
        
        # Check if at delivery location
        if monitoring_results['at_delivery_location'] and self.knowledge.loaded_orders:
            analysis['requires_adaptation'] = True
            analysis['adaptation_type'] = 'deliver_order'
            analysis['reason'] = 'Reached delivery location'
            return analysis
        
        # Check if mission complete
        if (self.knowledge.mission_in_progress and 
            monitoring_results['at_base'] and 
            len(self.knowledge.loaded_orders) == 0):
            analysis['requires_adaptation'] = True
            analysis['adaptation_type'] = 'end_mission'
            analysis['reason'] = 'All deliveries completed, returned to base'
            return analysis
        
        # Calculate estimated remaining distance
        if self.knowledge.current_plan:
            remaining = len(self.knowledge.current_plan) - self.knowledge.current_plan_index
            analysis['estimated_remaining_distance'] = remaining
        
        return analysis
    
    def assess_order_priority(self) -> list:
        """Assess and prioritize pending orders."""
        return sorted(self.knowledge.pending_orders, key=lambda x: x.timestamp)
    
    def detect_anomalies(self) -> Dict[str, Any]:
        """Detect any anomalies in system behavior."""
        anomalies = {
            'stuck': False,
            'excessive_replanning': False,
            'unreachable_locations': []
        }
        
        if self.knowledge.number_of_replans > 20:
            anomalies['excessive_replanning'] = True
        
        return anomalies
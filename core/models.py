from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class Processor:
    id: int
    name: str
    f: float
    C0: float
    C1: float
    C2: float
    R: float
    C: float
    T_lim: float
    T_a: float = 25.0
    
    # State variables
    avail: float = 0.0  
    T_cur: float = 25.0 

    @property
    def B_n(self) -> float:
        """Calculate Thermal Constant (B_n) based on physical parameters"""
        return (1.0 - self.R * self.C2 * self.f) / (self.C * self.R)

@dataclass
class Task:
    id: str
    execution_times: Dict[int, float]  
    T_ss: Dict[int, float]             
    successors: List[str] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)
    
    # Computed metrics
    OFT: Dict[int, float] = field(default_factory=dict)
    rank: float = 0.0
    
    # Scheduling results
    AST: float = 0.0
    AFT: float = 0.0
    assigned_core: int = -1
    schedule_segments: List[Dict[str, float]] = field(default_factory=list)

class DAG:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.communication: Dict[Tuple[str, str], float] = {}

    def get_topological_order(self) -> List[str]:
        """Returns task IDs in topological order using Kahn's Algorithm"""
        in_degree = {t_id: len(task.predecessors) for t_id, task in self.tasks.items()}
        queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
        topo_order = []
        
        while queue:
            curr = queue.pop(0)
            topo_order.append(curr)
            for succ in self.tasks[curr].successors:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)
        return topo_order
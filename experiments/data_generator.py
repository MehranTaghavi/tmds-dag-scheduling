import os
import sys
import numpy as np
from typing import Dict, Tuple

# افزودن مسیر ریشه به مسیر جستجوی پایتون
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.models import DAG, Task, Processor

class TMDSDataGenerator:
    def __init__(self, seed: int = None):
        """Initialize generator with an optional seed for reproducibility (Rigorous Engineering)"""
        if seed is not None:
            np.random.seed(seed)

    def generate_gaussian_dag(self, v: int) -> DAG:
        """Generates Gaussian Elimination DAG. |V| = (v^2 + v - 2)/2"""
        dag = DAG()
        tasks_count = int((v ** 2 + v - 2) / 2)
        
        for i in range(1, tasks_count + 1):
            dag.tasks[f"t_{i}"] = Task(id=f"t_{i}", execution_times={}, T_ss={})

        current_task_id = 1
        for new_tasks in range(v, 1, -1):
            for successor_id in range(current_task_id + 1, current_task_id + new_tasks):
                if successor_id <= tasks_count:
                    u = f"t_{current_task_id}"
                    v_node = f"t_{successor_id}"
                    dag.tasks[u].successors.append(v_node)
                    dag.tasks[v_node].predecessors.append(u)
                    
                    if new_tasks != 2:
                        next_level = successor_id + new_tasks - 1
                        if next_level <= tasks_count:
                            u_next = f"t_{successor_id}"
                            v_next = f"t_{next_level}"
                            dag.tasks[u_next].successors.append(v_next)
                            dag.tasks[v_next].predecessors.append(u_next)
            current_task_id += new_tasks
            
        return dag

    def generate_laplace_dag(self, phi: int) -> DAG:
        """Generates Laplace Equation Solver DAG. |V| = phi^2"""
        dag = DAG()
        tasks_count = phi * phi
        
        for i in range(1, tasks_count + 1):
            dag.tasks[f"t_{i}"] = Task(id=f"t_{i}", execution_times={}, T_ss={})
            
        grid = np.arange(1, tasks_count + 1).reshape((phi, phi))
        for r in range(phi):
            for c in range(phi):
                u = f"t_{grid[r, c]}"
                if c < phi - 1: # یال به سمت راست
                    v_node = f"t_{grid[r, c+1]}"
                    dag.tasks[u].successors.append(v_node)
                    dag.tasks[v_node].predecessors.append(u)
                if r < phi - 1: # یال به سمت پایین
                    v_node = f"t_{grid[r+1, c]}"
                    dag.tasks[u].successors.append(v_node)
                    dag.tasks[v_node].predecessors.append(u)
                    
        return dag

    def setup_experimental_environment(self, dag: DAG, num_processors: int, 
                                       omega_dag_mean: float, sigma: float, beta: float, 
                                       ccr: float, B_mean: float) -> Tuple[Dict[int, Processor], dict]:
        """
        Implementation strictly based on Section 6.2 (Experimental Setup) of the TMDS paper.
        Extracts parameters precisely as formulated in the provided text snapshot.
        """
        # =====================================================================
        # (5) Temperature parameters (Processor Initialization)
        # =====================================================================
        processors = {}
        for n in range(1, num_processors + 1):
            # Thermal constant: B_n ~ N(0.008, 0.004)
            B_n = max(0.001, np.random.normal(0.008, 0.004))
            
            # Temperature threshold: Gamma_n_lim ~ U[60, 100]
            T_lim = np.random.uniform(60.0, 100.0)
            
            # Mathematical override to satisfy internal computed property B_n = 1/C
            p = Processor(
                id=n, name=f"p{n}", f=3.0, C0=1.0, C1=1.0, C2=0.0, R=1.0, C=(1.0 / B_n), 
                T_lim=T_lim, T_a=25.0
            )
            p.T_cur = 25.0
            processors[n] = p

        # =====================================================================
        # (4) Communication-to-Computation Ratio (CCR) - Link Bandwidths
        # =====================================================================
        transfer_matrix = {}
        raw_bandwidths = {}
        sum_b_mn = 0.0
        
        for m in range(1, num_processors + 1):
            transfer_matrix[(str(m), str(m))] = float('inf')  # ارتباط داخلی هزینه ندارد
            
            # Exact formula from paper: sum_{m=1}^{|P|} sum_{n=1}^{m-1} b_{m,n}
            for n in range(1, m): 
                # b_{m,n} ~ N(B_mean, 0.2 * B_mean)
                b_mn = max(0.1, np.random.normal(B_mean, 0.2 * B_mean))
                raw_bandwidths[(m, n)] = b_mn
                sum_b_mn += b_mn
                
        # Scaled appropriately such that sum becomes |P| * (|P| - 1) / 2 * B_mean
        target_bw_sum = num_processors * (num_processors - 1) / 2.0 * B_mean
        bw_scale = target_bw_sum / sum_b_mn if sum_b_mn > 0 else 1.0
        
        for (m, n), b_mn in raw_bandwidths.items():
            scaled_b_mn = b_mn * bw_scale
            transfer_matrix[(str(m), str(n))] = scaled_b_mn
            transfer_matrix[(str(n), str(m))] = scaled_b_mn # گراف دوطرفه متقارن

        # =====================================================================
        # (3) Task execution times & (5) Steady-state temperature
        # =====================================================================
        for t_id, task in dag.tasks.items():
            # Average execution time of task: omega_j ~ N(omega_dag_mean, sigma)
            omega_j = max(1.0, np.random.normal(omega_dag_mean, sigma))
            
            for n in range(1, num_processors + 1):
                # Exec time on proc p_n: omega_{j,n} ~ N(omega_j, omega_j * beta)
                omega_jn = max(0.1, np.random.normal(omega_j, omega_j * beta))
                task.execution_times[n] = omega_jn
                
                # Steady-state temp: Gamma_{j,n}^{ss} ~ U[40, 120]
                task.T_ss[n] = np.random.uniform(40.0, 120.0)

        # =====================================================================
        # (4) Communication-to-Computation Ratio (CCR) - Data Sizes
        # =====================================================================
        num_edges = sum(len(t.successors) for t in dag.tasks.values())
        if num_edges > 0:
            # data_DAG = CCR * omega_dag_mean * B_mean
            data_dag = ccr * omega_dag_mean * B_mean
            target_data_sum = num_edges * data_dag
            
            raw_data = {}
            sum_data_ij = 0.0
            
            for t_id, task in dag.tasks.items():
                for succ_id in task.successors:
                    # Output message size: data_{i,j} ~ N(data_DAG, 0.2 * data_DAG)
                    data_ij = max(0.1, np.random.normal(data_dag, 0.2 * data_dag))
                    raw_data[(t_id, succ_id)] = data_ij
                    sum_data_ij += data_ij
                    
            # Scaled such that sum over all edges equals |E| * data_DAG
            data_scale = target_data_sum / sum_data_ij if sum_data_ij > 0 else 1.0
            
            for edge, data_ij in raw_data.items():
                dag.communication[edge] = data_ij * data_scale
                
        return processors, transfer_matrix
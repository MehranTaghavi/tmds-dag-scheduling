from core.models import DAG, Processor, Task
from algorithms.thermal_math import MDE_scalar, coolT_scalar, T_cur_scalar, T_heat, T_cool, find_optimal_cutoff
from typing import List, Dict, Tuple

class TMDS:
    def __init__(self, dag: DAG, processors: Dict[int, Processor], transfer_matrix: dict, OV: float = 0.000080):
        self.dag = dag
        self.processors = processors
        self.transfer_matrix = transfer_matrix
        self.OV = OV
        self.iteration_trace = [] # For generating Table 3

    def _compute_OFT_and_Rank(self):
        topo_order = self.dag.get_topological_order()
        for t_id in reversed(topo_order):
            task = self.dag.tasks[t_id]
            for p_id, p in self.processors.items():
                if not task.successors:
                    task.OFT[p_id] = task.execution_times[p_id]
                else:
                    max_oft = 0
                    for succ_id in task.successors:
                        succ = self.dag.tasks[succ_id]
                        min_succ = float('inf')
                        for pr_id in self.processors.keys():
                            c_cost = 0.0
                            if p_id != pr_id:
                                comm_data = self.dag.communication.get((t_id, succ_id), 0)
                                bw = self.transfer_matrix.get((str(p_id), str(pr_id)), 1.0)
                                c_cost = comm_data / bw
                            cost = succ.OFT[pr_id] + task.execution_times[p_id] + c_cost
                            if cost < min_succ:
                                min_succ = cost
                        if min_succ > max_oft:
                            max_oft = min_succ
                    task.OFT[p_id] = max_oft
            task.rank = sum(task.OFT.values()) / len(self.processors)

    def _TETT(self, task: Task, p: Processor, curT: float, T_est: float) -> Tuple[List[dict], float, float]:
        WCET = task.execution_times[p.id]
        T_ss = task.T_ss[p.id]
        allowET = MDE_scalar(T_est, T_ss, p.T_lim, p.B_n)
        schedule_segments = []
        
        if WCET <= allowET:
            schedule_segments.append({"Start": round(curT, 4), "End": round(curT + WCET, 4)})
            final_temp = T_heat(T_ss, T_est, WCET, p.B_n)
            return schedule_segments, curT + WCET, final_temp
            
        remET = WCET - allowET
        schedule_segments.append({"Start": round(curT, 4), "End": round(curT + allowET, 4)})
        curT += allowET
        
        cutoff_params = find_optimal_cutoff(WCET, T_est, T_ss, p.T_lim, p.T_a, p.B_n, self.OV)
        if not cutoff_params:
            return schedule_segments, curT + remET, p.T_lim
            
        idleT = cutoff_params['idle_time_full']
        allowET_cycle = cutoff_params['val_mde']
        
        while remET > 1e-5:
            if remET >= allowET_cycle:
                curT += idleT + 2 * self.OV
                schedule_segments.append({"Start": round(curT, 4), "End": round(curT + allowET_cycle, 4)})
                curT += allowET_cycle
                remET -= allowET_cycle
            else:
                T_cur_val = T_cur_scalar(T_ss, p.T_lim, p.B_n, remET)
                idleT_last = coolT_scalar(max(T_cur_val, p.T_a), p.T_lim, p.T_a, p.B_n)
                curT += idleT_last + 2 * self.OV
                schedule_segments.append({"Start": round(curT, 4), "End": round(curT + remET, 4)})
                curT += remET
                remET = 0
                
        return schedule_segments, curT, p.T_lim

    def schedule(self) -> float:
        self._compute_OFT_and_Rank()
        task_list = sorted(self.dag.tasks.values(), key=lambda t: t.rank, reverse=True)
        unassigned_tasks = [t.id for t in task_list]
        
        for task in task_list:
            best_p_id = -1
            min_SCT = float('inf')
            best_EFT = 0.0
            best_AST = 0.0
            best_segments = []
            best_final_temp = 0.0
            
            # Trace data for Table 3
            trace_row = {
                "taskList": ",".join([t.replace("task_", "t") for t in unassigned_tasks]),
                "t_j": task.id.replace("task_", "t"),
                "R": round(task.rank, 2),
                "OFT": {}, "EST": {}, "EFT": {}, "SCT": {}
            }
            
            for p_id, p in self.processors.items():
                max_pred_arrival = 0.0
                for pred_id in task.predecessors:
                    pred = self.dag.tasks[pred_id]
                    c_cost = 0.0
                    if pred.assigned_core != p_id:
                        comm_data = self.dag.communication.get((pred_id, task.id), 0)
                        bw = self.transfer_matrix.get((str(pred.assigned_core), str(p_id)), 1.0)
                        c_cost = comm_data / bw
                    arrival = pred.AFT + c_cost
                    if arrival > max_pred_arrival:
                        max_pred_arrival = arrival
                        
                EST = max(p.avail, max_pred_arrival)
                idle_duration = EST - p.avail
                T_est = T_cool(p.T_a, p.T_cur, idle_duration, p.B_n)
                
                schedule_segments, EFT, final_temp = self._TETT(task, p, EST, T_est)
                
                # Formula used in paper (EFT + OFT - WCET)
                SCT = EFT + task.OFT[p_id] - task.execution_times[p_id]
                
                # Log iteration trace
                trace_row["OFT"][p_id] = round(task.OFT[p_id], 2)
                trace_row["EST"][p_id] = round(EST, 2)
                trace_row["EFT"][p_id] = round(EFT, 2)
                trace_row["SCT"][p_id] = round(SCT, 2)
                
                if SCT < min_SCT:
                    min_SCT = SCT
                    best_p_id = p_id
                    best_EFT = EFT
                    best_AST = EST
                    best_segments = schedule_segments
                    best_final_temp = final_temp

            # Assign and Update state
            task.assigned_core = best_p_id
            task.AST = best_AST
            task.AFT = best_EFT
            task.schedule_segments = best_segments
            
            p_selected = self.processors[best_p_id]
            p_selected.avail = best_EFT
            p_selected.T_cur = best_final_temp
            
            # Log final assignment for Table 3
            trace_row["AFT"] = round(best_EFT, 2)
            trace_row["p_n"] = f"p{best_p_id}"
            trace_row["T_cur"] = round(best_final_temp, 1)
            self.iteration_trace.append(trace_row)
            
            unassigned_tasks.remove(task.id)
            
        makespan = max(p.avail for p in self.processors.values())
        return makespan
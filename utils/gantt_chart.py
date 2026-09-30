import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import math

def T_cool(T_a, T_0, q, B_n):
    """Equation 8: Cooling function for recalculating temps during plotting"""
    return T_a + (T_0 - T_a) * math.exp(-B_n * q)

def format_num(val):
    """Formats numbers to max 2 decimal places and removes trailing zeros"""
    s = f"{val:.2f}"
    return s.rstrip('0').rstrip('.') if '.' in s else s

def draw_gantt_chart(tasks, parameters, output_dir, filename="Gantt_Motivational"):
    """Generates a publication-quality Gantt chart mimicking the TMDS paper with collision handling"""
    
    fig, ax = plt.subplots(figsize=(12, 4.5))
    
    # افزودن عنوان به نمودار
    ax.set_title("Output: Motivational Example (Gantt Chart)", fontsize=14, family='serif', fontweight='bold', pad=15)
    
    # Extract and sort processor IDs (p3 at top, p1 at bottom)
    p_ids = sorted([int(k.split('_')[1]) for k in parameters.keys()], reverse=True)
    y_ticks = [20 * i + 10 for i in range(len(p_ids))]
    
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"$p_{k}$" for k in p_ids], fontsize=16, family='serif')
    ax.set_ylim(0, 20 * len(p_ids) + 5)
    ax.set_xlim(0, 85)
    
    # استفاده از r (Raw String) برای رفع خطای SyntaxWarning پایتون
    ax.text(-5, 20 * len(p_ids), r"(in $^\circ C$)", color='blue', fontsize=12, family='serif', fontweight='bold')
    ax.text(-5, 20 * len(p_ids) - 5, r"(in $s$)", color='black', fontsize=12, family='serif')

    # Draw processor baselines
    for y in y_ticks:
        ax.axhline(y - 5, color='gray', linestyle='-.', linewidth=1)

    p_states = {p_id: {'avail': 0.0, 'T_cur': parameters[f"core_{p_id}"]['T_cur']} for p_id in p_ids}
    last_aft = {p_id: -1.0 for p_id in p_ids}
    
    tracker = {p_id: {'time_x': -100, 'time_lvl': 0, 'temp_x': -100, 'temp_lvl': 0} for p_id in p_ids}

    def get_staggered_y(x, p_id, kind, base_y, offset):
        tr = tracker[p_id]
        last_x_key = f"{kind}_x"
        lvl_key = f"{kind}_lvl"
        if x - tr[last_x_key] < 3.5:
            tr[lvl_key] = (tr[lvl_key] + 1) % 2
        else:
            tr[lvl_key] = 0
        tr[last_x_key] = x
        return base_y + (tr[lvl_key] * offset)

    sorted_tasks = sorted(tasks.values(), key=lambda t: t.AST)
    
    for task in sorted_tasks:
        p_id = task.assigned_core
        if p_id == -1: 
            continue
        
        p_param = parameters[f"core_{p_id}"]
        B_n = (1.0 - p_param['R'] * p_param['C2'] * p_param['f']) / (p_param['C'] * p_param['R'])
        
        idle = task.AST - p_states[p_id]['avail']
        T_start = T_cool(p_param['T_a'], p_states[p_id]['T_cur'], idle, B_n)
        
        if len(task.schedule_segments) > 1:
            T_end = p_param['T_lim'] 
        else:
            exec_time = task.AFT - task.AST
            T_end = task.T_ss[p_id] + (T_start - task.T_ss[p_id]) * math.exp(-B_n * exec_time)
            
        p_states[p_id]['avail'] = task.AFT
        p_states[p_id]['T_cur'] = T_end
        
        core_idx = p_ids.index(p_id)
        y_base = y_ticks[core_idx] - 5
        height = 10
        
        ax.add_patch(patches.Rectangle((task.AST, y_base), task.AFT - task.AST, height, 
                                       facecolor='#e0e0e0', edgecolor='gray', 
                                       hatch='||', linewidth=0.5))
                                       
        for seg in task.schedule_segments:
            ax.add_patch(patches.Rectangle((seg['Start'], y_base), seg['End'] - seg['Start'], height, 
                                           facecolor='#FFFFE0', edgecolor='black', linewidth=1))
        
        t_num = task.id.split('_')[1]
        ax.text(task.AST + (task.AFT - task.AST) / 2, y_base + height / 2, f"$\\tau_{{{t_num}}}$", 
                ha='center', va='center', fontsize=14, family='serif')
        
        if abs(task.AST - last_aft[p_id]) > 1e-4:
            y_time_start = get_staggered_y(task.AST, p_id, 'time', y_base - 1, -2.5)
            ax.text(task.AST, y_time_start, format_num(task.AST), ha='center', va='top', fontsize=10, family='serif')
            
            y_temp_start = get_staggered_y(task.AST, p_id, 'temp', y_base + height + 1, 2.5)
            ax.text(task.AST, y_temp_start, format_num(T_start), ha='center', va='bottom', fontsize=10, family='serif', color='blue')
        
        y_time_end = get_staggered_y(task.AFT, p_id, 'time', y_base - 1, -2.5)
        ax.text(task.AFT, y_time_end, format_num(task.AFT), ha='center', va='top', fontsize=10, family='serif')
        
        y_temp_end = get_staggered_y(task.AFT, p_id, 'temp', y_base + height + 1, 2.5)
        ax.text(task.AFT, y_temp_end, format_num(T_end), ha='center', va='bottom', fontsize=10, family='serif', color='blue')

        last_aft[p_id] = task.AFT

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{filename}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
import sys
import os
import json
import csv

# افزودن پوشه ریشه پروژه به مسیر جستجوی پایتون
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models import DAG, Task, Processor
from algorithms.tmds_scheduler import TMDS
from utils.visualizer import draw_dag_from_json  
from utils.gantt_chart import draw_gantt_chart

def load_inputs(filepath):
    """Loads inputs from JSON and formats keys correctly"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    comm = {tuple(k.split('|')): float(v) for k, v in data['communication'].items()}
    trans = {tuple(k.split('|')): float(v) for k, v in data['transfer'].items()}
    
    return data, comm, trans

def generate_inputs_html_report(data, output_path):
    """Generates HTML report for Input Tables"""
    html_head = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>TMDS Input Parameters</title>
<script>
  MathJax = {
    tex: { inlineMath: [['$', '$'], ['\\(', '\\)']] }
  };
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
<style>
    body { font-family: 'Times New Roman', Times, serif; margin: 40px; color: #000; }
    h3 { text-align: center; font-size: 16px; font-weight: bold; margin-top: 40px; }
    table { width: 80%; border-collapse: collapse; font-size: 14px; text-align: center; margin: 0 auto; }
    th, td { padding: 8px 4px; border: 1px solid #eee; }
    thead tr:first-child { border-top: 2px solid #000; }
    thead tr:last-child { border-bottom: 1px solid #000; }
    tbody tr:last-child { border-bottom: 2px solid #000; }
    .divider-right { border-right: 1px solid #000; }
</style>
</head>
<body>
    <h3>Table 1. WCET and Steady State temperature</h3>
    <table>
        <thead>
            <tr>
                <th rowspan="2" class="divider-right">Tasks</th>
                <th colspan="3" class="divider-right">$\omega_{j,n}$</th>
                <th colspan="3">$\Gamma_{j,n}^{ss}$</th>
            </tr>
            <tr>
                <th>$p_1$</th><th>$p_2$</th><th class="divider-right">$p_3$</th>
                <th>$p_1$</th><th>$p_2$</th><th>$p_3$</th>
            </tr>
        </thead>
        <tbody>
"""
    html_body_t1 = ""
    tasks = data['execution_data']
    t_ss = data['steady_state']
    sorted_task_keys = sorted(tasks.keys(), key=lambda k: int(k.split('_')[1]))
    
    for t_key in sorted_task_keys:
        t_idx = t_key.split('_')[1]
        w = tasks[t_key]
        s = t_ss[t_key]
        html_body_t1 += f"""
            <tr>
                <td class="divider-right">$\\tau_{{{t_idx}}}$</td>
                <td>{w[0]}</td><td>{w[1]}</td><td class="divider-right">{w[2]}</td>
                <td>{s[0]}</td><td>{s[1]}</td><td>{s[2]}</td>
            </tr>"""

    html_mid = r"""
        </tbody>
    </table>

    <h3>Table 2. Thermal Parameters of Processors</h3>
    <table>
        <thead>
            <tr>
                <th>Processor</th><th>$f$</th><th>$C_0$</th><th>$C_1$</th><th>$C_2$</th><th>$R$</th><th>$C$</th><th>$\Gamma_{lim}$</th><th>$\Gamma_a$</th>
            </tr>
        </thead>
        <tbody>
"""
    html_body_t2 = ""
    params = data['parameters']
    sorted_core_keys = sorted(params.keys(), key=lambda k: int(k.split('_')[1]))
    
    for c_key in sorted_core_keys:
        c_idx = c_key.split('_')[1]
        p = params[c_key]
        html_body_t2 += f"""
            <tr>
                <td>$p_{{{c_idx}}}$</td>
                <td>{p['f']}</td><td>{p['C0']}</td><td>{p['C1']}</td><td>{p['C2']}</td>
                <td>{p['R']}</td><td>{p['C']}</td><td>{p['T_lim']} &deg;C</td><td>{p['T_a']} &deg;C</td>
            </tr>"""

    html_tail = """
        </tbody>
    </table>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_head + html_body_t1 + html_mid + html_body_t2 + html_tail)

def generate_inputs_csv_reports(data, output_dir):
    """Exports input tables to standard CSV files"""
    t1_path = os.path.join(output_dir, 'Table1_WCET_Tss.csv')
    with open(t1_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Task", "WCET_p1", "WCET_p2", "WCET_p3", "T_ss_p1", "T_ss_p2", "T_ss_p3"])
        tasks = data['execution_data']
        t_ss = data['steady_state']
        for t_key in sorted(tasks.keys(), key=lambda k: int(k.split('_')[1])):
            writer.writerow([t_key] + tasks[t_key] + t_ss[t_key])
            
    t2_path = os.path.join(output_dir, 'Table2_Thermal_Parameters.csv')
    with open(t2_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Processor", "f", "C0", "C1", "C2", "R", "C", "T_lim", "T_a"])
        params = data['parameters']
        for c_key in sorted(params.keys(), key=lambda k: int(k.split('_')[1])):
            p = params[c_key]
            writer.writerow([c_key, p['f'], p['C0'], p['C1'], p['C2'], p['R'], p['C'], p['T_lim'], p['T_a']])

def generate_trace_html_report(iteration_trace, makespan, output_path):
    """Generates Table 3 HTML report (Algorithm Trace)"""
    html_head = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>TMDS Schedule Trace</title>
<script>
  MathJax = {
    tex: { inlineMath: [['$', '$'], ['\\(', '\\)']] }
  };
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
<style>
    body { font-family: 'Times New Roman', Times, serif; margin: 40px; color: #000; }
    h3 { text-align: center; font-size: 16px; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; text-align: center; margin: 0 auto; }
    th, td { padding: 8px 4px; border: 1px solid #eee; }
    thead tr:first-child { border-top: 2px solid #000; }
    thead tr:last-child { border-bottom: 1px solid #000; }
    tbody tr:last-child { border-bottom: 2px solid #000; }
    .divider-right { border-right: 1px solid #000; }
</style>
</head>
<body>
"""
    html_title = f"<h3>Table 3. Schedule Produced by True TMDS Logic in Each Iteration (Makespan: {makespan:.2f}s)</h3>"
    
    html_table_head = r"""
    <table>
        <thead>
            <tr>
                <th rowspan="2" class="divider-right"><i>taskList</i></th>
                <th rowspan="2">$\tau_j$</th>
                <th rowspan="2" class="divider-right"><i>R</i></th>
                <th colspan="3" class="divider-right">OFT</th>
                <th colspan="3" class="divider-right">EST</th>
                <th colspan="3" class="divider-right">EFT</th>
                <th colspan="3" class="divider-right">SCT</th>
                <th colspan="3">Allocation</th>
            </tr>
            <tr>
                <th>$p_1$</th><th>$p_2$</th><th class="divider-right">$p_3$</th>
                <th>$p_1$</th><th>$p_2$</th><th class="divider-right">$p_3$</th>
                <th>$p_1$</th><th>$p_2$</th><th class="divider-right">$p_3$</th>
                <th>$p_1$</th><th>$p_2$</th><th class="divider-right">$p_3$</th>
                <th>AFT[$\tau_j$]</th><th>$p_n$</th><th>$\Gamma_n^{cur}$</th>
            </tr>
        </thead>
        <tbody>
"""
    html_body = ""
    for row in iteration_trace:
        task_list_str = row['taskList']
        if len(task_list_str) > 25:
            task_list_str = task_list_str[:22] + "..."
            
        t_idx = row['t_j'].replace('t', '')
        
        html_body += f"""
            <tr>
                <td class="divider-right" style="font-size: 12px;">{task_list_str}</td>
                <td>$\\tau_{{{t_idx}}}$</td>
                <td class="divider-right">{row['R']:.2f}</td>
                <td>{row['OFT'][1]:.2f}</td><td>{row['OFT'][2]:.2f}</td><td class="divider-right">{row['OFT'][3]:.2f}</td>
                <td>{row['EST'][1]:.2f}</td><td>{row['EST'][2]:.2f}</td><td class="divider-right">{row['EST'][3]:.2f}</td>
                <td>{row['EFT'][1]:.2f}</td><td>{row['EFT'][2]:.2f}</td><td class="divider-right">{row['EFT'][3]:.2f}</td>
                <td>{row['SCT'][1]:.2f}</td><td>{row['SCT'][2]:.2f}</td><td class="divider-right">{row['SCT'][3]:.2f}</td>
                <td><b>{row['AFT']:.2f}</b></td><td><b>{row['p_n']}</b></td><td>{row['T_cur']:.1f}&deg;C</td>
            </tr>"""

    html_tail = """
        </tbody>
    </table>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_head + html_title + html_table_head + html_body + html_tail)

def generate_trace_csv_report(iteration_trace, output_path):
    """Exports trace to a standard CSV file"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["taskList", "t_j", "R", "OFT_p1", "OFT_p2", "OFT_p3", "EST_p1", "EST_p2", "EST_p3", 
                         "EFT_p1", "EFT_p2", "EFT_p3", "SCT_p1", "SCT_p2", "SCT_p3", "AFT", "p_n", "T_cur"])
        for row in iteration_trace:
            writer.writerow([row['taskList'], row['t_j'], round(row['R'], 2), 
                             row['OFT'][1], row['OFT'][2], row['OFT'][3],
                             row['EST'][1], row['EST'][2], row['EST'][3],
                             row['EFT'][1], row['EFT'][2], row['EFT'][3],
                             row['SCT'][1], row['SCT'][2], row['SCT'][3],
                             row['AFT'], row['p_n'], row['T_cur']])

def run_experiment():
    # Setup paths
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    inputs_dir = os.path.join(base_dir, 'inputs')
    results_dir = os.path.join(base_dir, 'results')
    
    os.makedirs(inputs_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    input_path = os.path.join(inputs_dir, 'motivational_data.json')
    
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    # 1. Load inputs from JSON
    data, communication, transfer = load_inputs(input_path)
    
    # 2. Generate Input Reports (HTML & CSV) in the INPUTS directory
    inputs_html_path = os.path.join(inputs_dir, 'Tables_1_2_Input_Parameters.html')
    generate_inputs_html_report(data, inputs_html_path)
    generate_inputs_csv_reports(data, inputs_dir)
    
 # 3. GENERATE THE DAG IMAGE
    # تغییر مسیر خروجی به پوشه inputs_dir
    try:
        draw_dag_from_json(input_path, inputs_dir, filename="DAG_Motivational")
    except Exception as e:
        print(f"Warning: Could not generate DAG image. Error: {e}")
        
    # 4. Build DAG Data Structure
    dag = DAG()
    for t_id in data["dependency"]["successor"].keys():
        task = Task(id=t_id, execution_times={}, T_ss={})
        task.successors = data["dependency"]["successor"][t_id]
        task.predecessors = data["dependency"]["predecessor"][t_id]
        
        for core_idx in range(1, 4):
            task.execution_times[core_idx] = data["execution_data"][t_id][core_idx-1]
            task.T_ss[core_idx] = data["steady_state"][t_id][core_idx-1]
        dag.tasks[t_id] = task

    for edge, cost in communication.items():
        dag.communication[edge] = cost

    # 5. Build Processors
    processors = {}
    for i in range(1, 4):
        p_data = data["parameters"][f"core_{i}"]
        p = Processor(
            id=i, name=f"p{i}", f=p_data["f"], C0=p_data["C0"], 
            C1=p_data["C1"], C2=p_data["C2"], R=p_data["R"], 
            C=p_data["C"], T_lim=p_data["T_lim"], T_a=p_data["T_a"]
        )
        p.T_cur = p_data["T_cur"]
        processors[i] = p

    # 6. Run True TMDS Logic
    scheduler = TMDS(dag, processors, transfer, OV=0.000080)
    makespan = scheduler.schedule()

    # 7. Generate Output Reports (HTML + CSV) in the RESULTS directory
    trace_html_path = os.path.join(results_dir, 'Table3_TMDS_Trace.html')
    trace_csv_path = os.path.join(results_dir, 'Table3_TMDS_Trace.csv')
    
    generate_trace_html_report(scheduler.iteration_trace, makespan, trace_html_path)
    generate_trace_csv_report(scheduler.iteration_trace, trace_csv_path)
       
    # 8. GENERATE GANTT CHART
    try:
        draw_gantt_chart(dag.tasks, data['parameters'], results_dir, filename="Gantt_Motivational")
    except Exception as e:
        print(f"Warning: Could not generate Gantt chart. Error: {e}")
    
    print("=" * 85)
    print(f" True TMDS Logic Execution - Final Makespan: {makespan:.2f}s ")
    print("-" * 85)
    print(" Generated Files Organization:")
    print(" INPUTS (in 'inputs/' directory):")
    print("   1. Tables_1_2_Input_Parameters.html")
    print("   2. Table1_WCET_Tss.csv")
    print("   3. Table2_Thermal_Parameters.csv")
    print("   4. DAG_Motivational.png (Directed Acyclic Graph Visualized)")
    print("\n OUTPUTS (in 'results/' directory):")
    print("   5. Table3_TMDS_Trace.html")
    print("   6. Table3_TMDS_Trace.csv")
    print("   7. Gantt_Motivational.png (Gantt Chart)")
    print("=" * 85)
    
if __name__ == "__main__":
    run_experiment()
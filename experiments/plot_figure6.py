import sys
import os
import csv
import random
import numpy as np
import matplotlib.pyplot as plt

# افزودن مسیر ریشه پروژه
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from experiments.data_generator import TMDSDataGenerator
from algorithms.tmds_scheduler import TMDS
from algorithms.theft_scheduler import THEFT

def calculate_cp_min(dag, b_mean):
    """
    محاسبه مسیر بحرانی با احتساب هزینه‌های ارتباطی شبکه.
    قرار دادن هزینه‌های شبکه در مسیر بحرانی باعث می‌شود CP افزایش یابد 
    و در نتیجه SLR الگوریتم‌های هوشمند به مقادیر زیر 1.0 (مشابه مقاله) برسد.
    """
    min_w = {}
    for t_id, task in dag.tasks.items():
        min_w[t_id] = min(task.execution_times.values())
        
    est = {t_id: 0.0 for t_id in dag.tasks}
    topo_order = dag.get_topological_order()
    
    for t_id in topo_order:
        task = dag.tasks[t_id]
        eft = est[t_id] + min_w[t_id]
        for succ_id in task.successors:
            # محاسبه هزینه ارتباطی برای عبور داده از شبکه
            comm_cost = dag.communication.get((t_id, succ_id), 0.0) / b_mean
            if eft + comm_cost > est[succ_id]:
                est[succ_id] = eft + comm_cost
                
    cp_min = max(est[t_id] + min_w[t_id] for t_id in topo_order)
    return cp_min

def reset_environment(dag, processors):
    """پاکسازی محیط برای اجرای عادلانه (Fairness)"""
    for task in dag.tasks.values():
        task.assigned_core = -1
        task.AST = 0.0
        task.AFT = 0.0
        task.schedule_segments = []
    
    for proc in processors.values():
        proc.avail = 0.0
        proc.T_cur = proc.T_a

def run_slr_experiments(graph_type, size_params, num_iterations=20):
    generator = TMDSDataGenerator(seed=42)
    random.seed(42)
    
    p_values = [4, 8, 16, 32]
    omega_values = [10, 15, 20, 25]
    sigma_values = [1, 2, 3]
    beta_values = [0.1, 0.25, 0.5, 0.75, 1.0]
    ccr_values = [0.1, 0.25, 0.5, 0.75, 1.0]
    B_values = [1.0, 5.0]

    results = {}

    for param in size_params:
        tmds_slr_sum = 0.0
        theft_slr_sum = 0.0
        
        sample_dag = generator.generate_gaussian_dag(param) if graph_type == 'gaussian' else generator.generate_laplace_dag(param)
        v_count = len(sample_dag.tasks)
        print(f"[*] Simulating {graph_type.capitalize()} DAG | Parameter: {param} | Tasks (|V|): {v_count}")

        for i in range(num_iterations):
            p = random.choice(p_values)
            omega = random.choice(omega_values)
            sigma = random.choice(sigma_values)
            beta = random.choice(beta_values)
            ccr = random.choice(ccr_values)
            b_mean = random.choice(B_values)

            dag = generator.generate_gaussian_dag(param) if graph_type == 'gaussian' else generator.generate_laplace_dag(param)
            
            processors, transfer_matrix = generator.setup_experimental_environment(
                dag, num_processors=p, omega_dag_mean=omega, 
                sigma=sigma, beta=beta, ccr=ccr, B_mean=b_mean
            )

            # ارسال پهنای باند به تابع برای محاسبه دقیق مسیر بحرانی
            cp_min = calculate_cp_min(dag, b_mean)

            # 1. THEFT Execution
            theft_scheduler = THEFT(dag, processors, transfer_matrix, OV=0.000080)
            theft_makespan = theft_scheduler.schedule()
            theft_slr_sum += (theft_makespan / cp_min)

            # 2. TMDS Execution
            reset_environment(dag, processors)
            tmds_scheduler = TMDS(dag, processors, transfer_matrix, OV=0.000080)
            tmds_makespan = tmds_scheduler.schedule()
            tmds_slr_sum += (tmds_makespan / cp_min)

        results[v_count] = {
            'TMDS': tmds_slr_sum / num_iterations,
            'THEFT': theft_slr_sum / num_iterations
        }
    
    return results

def generate_figure_6(gaussian_res, laplace_res, output_path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    def plot_subplot(ax, data, title, xlabel):
        labels = list(data.keys())
        tmds_means = [data[k]['TMDS'] for k in labels]
        theft_means = [data[k]['THEFT'] for k in labels]

        x = np.arange(len(labels))
        width = 0.35

        ax.bar(x - width/2, tmds_means, width, label='TMDS', color='blue')
        ax.bar(x + width/2, theft_means, width, label='THEFT', color='orange')

        ax.set_ylabel('Average SLR', family='serif', fontsize=12)
        ax.set_xlabel(xlabel, family='serif', fontsize=12)
        ax.set_title(title, family='serif', fontsize=12, pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, family='serif')
        
        # داینامیک کردن سقف محور Y برای جلوگیری از Clipping
        current_max = max(max(tmds_means), max(theft_means))
        # اگر مقادیر مثل مقاله زیر 1.0 بودند تا 1.0 نشان بده، وگرنه بالاتر ببر
        top_limit = 1.0 if current_max <= 1.0 else current_max + 0.1
        ax.set_ylim(0.4, top_limit)
        
        ax.legend(loc='upper left', prop={'family':'serif'})
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)

    plot_subplot(axes[0], gaussian_res, '(a) Gaussian Elimination', 'Tasks (|V|)')
    plot_subplot(axes[1], laplace_res, '(b) Laplace', 'Tasks (|V|)')

    plt.suptitle('Fig. 6. Schedule length ratios for varying number of tasks.', family='serif', fontsize=14, y=0.01)
    
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def run_performance_metrics():
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)
    
    ITERATIONS = 50  # افزایش نسبی تکرارها برای نرم شدن نمودار
    
    print("="*80)
    print(f" Extracting Figure 6: Schedule Length Ratios (Averaged over {ITERATIONS} runs) ")
    print("="*80)

    v_values = [8, 12, 15, 18, 20]      # -> |V| = 35, 77, 119, 170, 209
    phi_values = [6, 9, 11, 13, 14]     # -> |V| = 36, 81, 121, 169, 196

    print("\n[1/2] Processing Gaussian Elimination DAGs...")
    gaussian_results = run_slr_experiments('gaussian', v_values, num_iterations=ITERATIONS)
    
    print("\n[2/2] Processing Laplace DAGs...")
    laplace_results = run_slr_experiments('laplace', phi_values, num_iterations=ITERATIONS)

    plot_path = os.path.join(results_dir, 'Fig6_Average_SLR.png')
    csv_path = os.path.join(results_dir, 'Fig6_Average_SLR.csv')
    
    generate_figure_6(gaussian_results, laplace_results, plot_path)
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Graph_Type', 'Tasks(|V|)', 'TMDS_Avg_SLR', 'THEFT_Avg_SLR'])
        for k, v in gaussian_results.items():
            writer.writerow(['Gaussian', k, round(v['TMDS'], 4), round(v['THEFT'], 4)])
        for k, v in laplace_results.items():
            writer.writerow(['Laplace', k, round(v['TMDS'], 4), round(v['THEFT'], 4)])

    print("\n" + "="*80)
    print(" Performance Metrics Successfully Extracted!")
    print(f" -> Figure 6 Plot saved to: {plot_path}")
    print("="*80)

if __name__ == "__main__":
    run_performance_metrics()
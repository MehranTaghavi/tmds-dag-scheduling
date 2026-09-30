import sys
import os
import csv
import random
import numpy as np

# افزودن پوشه ریشه به مسیر جستجوی پایتون
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from experiments.data_generator import TMDSDataGenerator
from algorithms.tmds_scheduler import TMDS
from algorithms.theft_scheduler import THEFT

def reset_environment(dag, processors):
    """پاکسازی کامل گراف و پردازنده‌ها برای اجرای عادلانه الگوریتم بعدی"""
    for task in dag.tasks.values():
        task.assigned_core = -1
        task.AST = 0.0
        task.AFT = 0.0
        task.schedule_segments = []
    
    for proc in processors.values():
        proc.avail = 0.0
        proc.T_cur = proc.T_a

def generate_table4_html(better_pct, equal_pct, worse_pct, output_path):
    """تولید فایل HTML دقیقاً مطابق استایل Table 4 مقاله"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <title>Table 4. Pair-wise Comparison</title>
    <style>
        body {{ font-family: 'Times New Roman', Times, serif; margin: 40px; color: #000; }}
        h3 {{ text-align: center; font-size: 16px; font-weight: normal; margin-bottom: 5px; }}
        .table-title {{ text-align: center; font-size: 16px; margin-bottom: 15px; }}
        table {{ border-collapse: collapse; font-size: 14px; text-align: center; margin: 0 auto; }}
        th, td {{ padding: 6px 12px; }}
        /* IEEE Table Borders */
        thead tr:first-child th {{ border-top: 2px solid #000; border-bottom: 1px solid #000; }}
        tbody tr:last-child td {{ border-bottom: 2px solid #000; }}
        .col-divider {{ border-right: 1px solid #000; }}
    </style>
    </head>
    <body>

    <h3>Table 4. Pair-wise Comparison of Algorithms</h3>
    <div class="table-title">Using Gaussian Elimination</div>
    
    <table>
        <thead>
            <tr>
                <th colspan="2" class="col-divider"></th>
                <th><i>THEFT</i></th>
                <!-- سایر الگوریتم‌ها مانند TPEFT در آینده اینجا اضافه می‌شوند -->
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="3" class="col-divider" style="vertical-align: middle;"><i>TMDS</i></td>
                <td>better</td>
                <td>{better_pct:.1f}%</td>
            </tr>
            <tr>
                <td>equal</td>
                <td>{equal_pct:.1f}%</td>
            </tr>
            <tr>
                <td>worse</td>
                <td>{worse_pct:.1f}%</td>
            </tr>
        </tbody>
    </table>
    </body>
    </html>
    """
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_content)

def run_monte_carlo_simulation():
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)
    html_output = os.path.join(results_dir, 'Table4_Pairwise_Comparison.html')
    csv_output = os.path.join(results_dir, 'Table4_Pairwise_Comparison.csv')
    
    generator = TMDSDataGenerator(seed=42)
    random.seed(42)
    
    # فضاهای پارامتری دقیقاً مطابق بخش 6.2 مقاله
    v_values = [8, 12, 15, 18, 20]
    p_values = [4, 8, 16, 32]
    omega_values = [10, 15, 20, 25]
    sigma_values = [1, 2, 3]
    beta_values = [0.1, 0.25, 0.5, 0.75, 1.0]
    ccr_values = [0.1, 0.25, 0.5, 0.75, 1.0]
    B_values = [1.0, 5.0]
    
    # تنظیم تعداد تکرارهای شبیه‌سازی (مونت-کارلو)
    NUM_ITERATIONS = 500
    
    better = 0
    equal = 0
    worse = 0
    epsilon = 0.01 # تلورانس برای برابری محاسبات اعشاری (Floating-point precision)

    print("="*80)
    print(f" Starting Statistical Pair-wise Evaluation (Table 4) - {NUM_ITERATIONS} Iterations ")
    print("="*80)

    for i in range(1, NUM_ITERATIONS + 1):
        # 1. انتخاب تصادفی پارامترها از فضای مسئله برای پوشش تمام حالات
        v = random.choice(v_values)
        p = random.choice(p_values)
        omega = random.choice(omega_values)
        sigma = random.choice(sigma_values)
        beta = random.choice(beta_values)
        ccr = random.choice(ccr_values)
        b_mean = random.choice(B_values)
        
        # 2. تولید گراف و پلتفرم
        dag = generator.generate_gaussian_dag(v)
        processors, transfer_matrix = generator.setup_experimental_environment(
            dag, num_processors=p, omega_dag_mean=omega, 
            sigma=sigma, beta=beta, ccr=ccr, B_mean=b_mean
        )
        
        # 3. اجرای THEFT (Baseline)
        theft_scheduler = THEFT(dag, processors, transfer_matrix, OV=0.000080)
        makespan_theft = theft_scheduler.schedule()
        
        # 4. پاکسازی و اجرای TMDS (Proposed)
        reset_environment(dag, processors)
        tmds_scheduler = TMDS(dag, processors, transfer_matrix, OV=0.000080)
        makespan_tmds = tmds_scheduler.schedule()
        
        # 5. ارزیابی Pair-wise
        if makespan_tmds < makespan_theft - epsilon:
            better += 1
        elif makespan_tmds > makespan_theft + epsilon:
            worse += 1
        else:
            equal += 1
            
        # نمایش لاگ پیشرفت (برای جلوگیری از توقف ظاهری برنامه در گراف‌های بزرگ)
        if i % 10 == 0 or i == NUM_ITERATIONS:
            print(f" [Progress] Iteration {i}/{NUM_ITERATIONS} completed. Current Stats -> Better: {better}, Equal: {equal}, Worse: {worse}")

    # محاسبه درصدها
    better_pct = (better / NUM_ITERATIONS) * 100
    equal_pct = (equal / NUM_ITERATIONS) * 100
    worse_pct = (worse / NUM_ITERATIONS) * 100

    # تولید فایل HTML
    generate_table4_html(better_pct, equal_pct, worse_pct, html_output)

    # تولید فایل CSV برای نگهداری مقادیر خام
    with open(csv_output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Algorithm_Pair', 'Better(%)', 'Equal(%)', 'Worse(%)', 'Total_Iterations'])
        writer.writerow(['TMDS_vs_THEFT', round(better_pct, 2), round(equal_pct, 2), round(worse_pct, 2), NUM_ITERATIONS])

    print("\n" + "="*80)
    print(" Simulation Complete! Pair-wise Results (TMDS vs THEFT):")
    print(f" -> Better: {better_pct:.1f}%")
    print(f" -> Equal:  {equal_pct:.1f}%")
    print(f" -> Worse:  {worse_pct:.1f}%")
    print(f"\n Professional IEEE HTML Table generated at: \n -> {html_output}")
    print("="*80)

if __name__ == "__main__":
    run_monte_carlo_simulation()
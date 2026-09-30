import sys
import os

# Ensure the root directory is in the Python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from experiments.motivational_test import run_experiment as run_motivational
from experiments.run_benchmarks import run_monte_carlo_simulation
from experiments.plot_figure6 import run_performance_metrics

def main():
    print("=" * 85)
    print(" TMDS Algorithm: Full Reproduction and Evaluation Pipeline ".center(85))
    print("=" * 85)

    print("\n[Phase 1] Executing Motivational Example (Section 4)...")
    try:
        run_motivational()
    except Exception as e:
        print(f"[-] Error in Phase 1: {e}")

    print("\n[Phase 2] Executing Large-Scale Benchmarks - Table 4 (Section 6.2)...")
    try:
        run_monte_carlo_simulation()
    except Exception as e:
        print(f"[-] Error in Phase 2: {e}")

    print("\n[Phase 3] Extracting Performance Metrics - Figure 6 (Section 6.3)...")
    try:
        run_performance_metrics()
    except Exception as e:
        print(f"[-] Error in Phase 3: {e}")

    print("\n" + "=" * 85)
    print(" All execution phases completed. Check 'inputs/' and 'results/' directories.".center(85))
    print("=" * 85)

if __name__ == "__main__":
    main()
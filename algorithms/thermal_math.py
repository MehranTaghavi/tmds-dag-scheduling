import numpy as np
import math

def T_heat(T_ss, T_0, q, B_n):
    """Equation 7: Heating function"""
    return T_ss + (T_0 - T_ss) * math.exp(-B_n * q)

def T_cool(T_a, T_0, q, B_n):
    """Equation 8: Cooling function"""
    return T_a + (T_0 - T_a) * math.exp(-B_n * q)

def MDE_scalar(T_ini, T_ss, T_lim, B_n):
    """Equation 22: Maximum Duration of continuous Execution"""
    if T_ss <= T_lim:
        return float('inf')
    if T_ini >= T_lim:
        return 0.0
    return (-1.0 / B_n) * math.log((T_lim - T_ss) / (T_ini - T_ss))

def coolT_scalar(T_fin, T_ini, T_a, B_n):
    """Equation 23: Cooling time required to drop from T_ini to T_fin"""
    if T_fin >= T_ini:
        return 0.0
    if T_fin <= T_a:
        return float('inf')
    return (-1.0 / B_n) * math.log((T_fin - T_a) / (T_ini - T_a))

def T_cur_scalar(T_ss, T_lim, B_n, remET):
    """Corrected Equation 26: Max starting temp for remaining execution"""
    return T_ss + (T_lim - T_ss) * math.exp(B_n * remET)

def find_optimal_cutoff(WCET, T_est, T_ss, T_lim, T_a, B_n, OV):
    """Finds optimal cutoff temperature (Gamma_oc) minimizing TE (Equation 21)"""
    temps = np.linspace(T_a + 0.1, T_lim - 0.1, 2000)
    
    mde_start = MDE_scalar(T_est, T_ss, T_lim, B_n)
    if WCET <= mde_start:
        return None 
        
    rem_exec = WCET - mde_start
    val_mde = (-1.0 / B_n) * np.log((T_lim - T_ss) / (temps - T_ss))
    
    I_float = rem_exec / val_mde
    I_floor = np.floor(I_float)
    remET_last = rem_exec - (I_floor * val_mde)
    
    # Corrected Eq 26 implementation (Vectorized)
    T_cur_req = T_ss + (T_lim - T_ss) * np.exp(B_n * remET_last)
    T_cur_actual = np.maximum(T_cur_req, T_a + 0.1) 
    
    idle_time_full = (-1.0 / B_n) * np.log((temps - T_a) / (T_lim - T_a))
    idle_time_last = (-1.0 / B_n) * np.log((T_cur_actual - T_a) / (T_lim - T_a))
    
    # Calculate Total Execution Time (TE) - Equation 21
    total_time = mde_start + I_floor * (idle_time_full + val_mde + 2*OV)
    mask = remET_last > 0
    total_time[mask] += idle_time_last[mask] + remET_last[mask] + 2*OV
    
    best_idx = np.argmin(total_time)
    
    return {
        'optimal_Tc': temps[best_idx],
        'idle_time_full': idle_time_full[best_idx],
        'val_mde': val_mde[best_idx]
    }
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import animation
from matplotlib import rc
import plotly.express as px
from plotly import graph_objects as go
plt.rcParams['animation.ffmpeg_path'] = r'ffmpeg'

#----Part 1: specify constants for behavior of drone agents, obstacles, and targets----#
#Set number of agents, objects, targets
N_m = 15
N_o = 25
N_t = 100

#Set physical parameters
A_i = 1 #Agent area
C_d = 0.25 #Coefficient of drag
m = 10 #Agent mass
v_a = np.array([0, 0, 0]) #Air velocity
rho_a = 1.225 #Air density
F_p = 200 #Propulsion force magnitude

#Set time-stepping parameters
dt = 0.2 #Time step size
tf = 60 #Maximum task time

#Set object interaction parameters
agent_sight = 5 #Target mapping distance
crash_range = 2 #Agent collision distance

#Set GA parameters
C = 6 #Children per generation
P = 6 #Parents per generation
S = 20 #Designs per generation
G = 100 #Total generations
DV = 15 #Design variables
Lam_min = 0
Lam_max = 2
w_1 = 70 #Weight of mapping in cost
w_2 = 10 #Weight of time usage in cost
w_3 = 20 #Weight of agent losses in cost

#Set domain parameters
x_max = 150
x_min = -150
y_max = 150
y_min = -150
z_max = 60
z_min = 0

loc_x = 100
loc_y = 100
loc_z = 10

#----Part 2: define physics engine for simulation----#
def drone_sim(N_m, N_o, N_t, w_1, w_2, w_3, LAM, dt, tf, agents, obstacles, targets):
    """
    Simulates flight paths of drones in swarm
    :param int N_m: Number of drone members in swarm
    :param int N_o: Number of obstacles to be avoided by drones in simulation space
    :param int N_t: Number of targets to be collected by drones
    :param float w_1: Weight assigned to uncollected targets in cost function
    :param float w_2: Weight assigned to time usage in cost function
    :param float w_3: Weight assigned to loss of agents to obstacles in cost function
    :param arr LAM: Array of optimal parameter guesses generated by genetic algorithm
    :param float dt: Time increment of simulation
    :param float tf: Total time of flight
    :param arr agents: Starting coordinates of all drones in swarm
    :param arr obstacles: Starting coordinates of all obstacles in swarm
    :param arr targets: Starting coordinates of all targets in swarm
    :return: Tuple containing cost function and final coordinates of drones and targets after simulation run
    """
    obs = obstacles.copy()
    tar = targets.copy()
    pos = agents.copy()
    vel = np.zeros(agents.shape)
    posData, tarData = [], []
    posData.append(pos.copy())
    tarData.append(tar.copy())
    initial_N_m, initial_N_t = N_m, N_t
    mtDiff, mmDiff, moDiff = np.zeros((N_m, N_t, 3)), np.zeros((N_m, N_m, 3)), np.zeros((N_m, N_o, 3))
    mtDist, mmDist, moDist = np.zeros((N_m, N_t)), np.zeros((N_m, N_m)), np.zeros((N_m, N_o))
    W_mt, W_mo, W_mm, wt_1, wt_2, wo_1, wo_2, wm_1, wm_2, a_1, a_2, b_1, b_2, c_1, c_2 = LAM
    for i in range(int(tf/dt)): 
        for j in range(N_m):
            mtDiff[j, :, :] = tar - pos[j]
            mmDiff[j, :, :] = pos - pos[j]
            mmDiff[j, j, :] = np.nan
            moDiff[j, :, :] = obs - pos[j]
            mtDist[j, :] = np.linalg.norm(pos[j] - tar, ord=2, axis=1)
            mmDist[j, :] = np.linalg.norm(pos[j] - pos, ord=2, axis=1)
            mmDist[j, j] = np.nan
            moDist[j, :] = np.linalg.norm(pos[j] - obs, ord=2, axis=1)
        mt_hit = np.where(mtDist <= agent_sight)
        mm_hit = np.where(mmDist <= crash_range)
        mo_hit = np.where(moDist <= crash_range)
        x_lost = np.where(x_max < np.abs(pos[:, 0]))
        y_lost = np.where(y_max < np.abs(pos[:, 1]))
        z_lost = np.where(z_max < np.abs(pos[:, 2]))
        m_lost = np.unique(np.hstack([x_lost[0], y_lost[0], z_lost[0]]))
        t_hit = np.unique(mt_hit[1])
        m_crash = np.unique(np.hstack([mm_hit[0], mo_hit[0], m_lost]))
        N_m, N_t = N_m - len(m_crash), N_t - len(t_hit)
        pos[m_crash, :] = np.nan
        vel[m_crash, :] = np.nan
        tar[t_hit, :] = np.nan
        mtDist[m_crash, :], mtDiff[m_crash, :, :] = np.nan, np.nan
        mtDist[:, t_hit], mtDiff[:, t_hit, :] = np.nan, np.nan
        mmDist[m_crash, :], mmDiff[m_crash, :, :] = np.nan, np.nan
        mmDist[:, m_crash], mmDiff[:, m_crash, :] = np.nan, np.nan
        moDist[m_crash, :], moDiff[:, m_crash, :] = np.nan, np.nan
        if not (~np.isnan(tar)).any() or not (~np.isnan(pos)).any():
            break
        n_mt = mtDiff/mtDist[:, :, np.newaxis]
        n_mo = moDiff/moDist[:, :, np.newaxis]
        n_mm = mmDiff/mmDist[:, :, np.newaxis]
        n_mt_hat = (wt_1*np.exp(-a_1*mtDist[:, :, np.newaxis]) - wt_2*np.exp(-a_2*mtDist[:, :, np.newaxis]))*n_mt
        n_mo_hat = (wo_1*np.exp(-b_1*moDist[:, :, np.newaxis]) - wo_2*np.exp(-b_2*moDist[:, :, np.newaxis]))*n_mo
        n_mm_hat = (wm_1*np.exp(-c_1*mmDist[:, :, np.newaxis]) - wm_2*np.exp(-c_2*mmDist[:, :, np.newaxis]))*n_mm
        N_mt, N_mo, N_mm = np.nansum(n_mt_hat, axis=1), np.nansum(n_mo_hat, axis=1), np.nansum(n_mm_hat, axis=1)
        N = W_mt*N_mt + W_mo*N_mo + W_mm*N_mm
        n_prop = N/np.linalg.norm(N)
        f_prop = F_p*n_prop
        f_drag = 0.5*rho_a*C_d*A_i*np.linalg.norm(v_a - vel, 2, axis=1)[:, np.newaxis]*(v_a - vel)
        f_tot = f_prop + f_drag
        vel = vel + dt*f_tot/m
        pos = pos + dt*vel
        posData.append(pos.copy())
        tarData.append(tar.copy())
    M_star = N_t/initial_N_t
    T_star = (i*dt)/tf
    L_star = (initial_N_m - N_m)/initial_N_m
    PI = w_1*M_star + w_2*T_star + w_3*L_star
    return (PI, posData, tarData, i, M_star, T_star, L_star)

#----Part 3: implement genetic algorithm to select parameters for optimal drone flight behavior----#
def genetic(S, G, P, Lam_min, Lam_max, numLAM, N_m, N_t, N_o, w_1, w_2, w_3, dt, tf, agents, obstacles, targets):
    """
    Runs genetic algorithm to select ideal drone behavior parameters by iteratively breeding generations of genetic strings
    :param int S: Number of parameters to generate per genetic string
    :param int G: Number of generations for which to run algorithm
    :param int P: Number of parent strings to retain for breeding between generations
    :param float Lam_min: Minimum value of parameters to trial
    :param float Lam_max: Maximum value of parameters to trial
    :param int numLAM: Number of unique parameters to be optimized
    :param int N_m: Number of drone members in swarm
    :param int N_o: Number of obstacles to be avoided by drones in simulation space
    :param int N_t: Number of targets to be collected by drones
    :param float w_1: Weight assigned to uncollected targets in cost function
    :param float w_2: Weight assigned to time usage in cost function
    :param float w_3: Weight assigned to loss of agents to obstacles in cost function
    :param float dt: Time increment of simulation
    :param float tf: Total time of flight
    :param arr agents: Starting coordinates of all drones in swarm
    :param arr obstacles: Starting coordinates of all obstacles in swarm
    :param arr targets: Starting coordinates of all targets in swarm
    :return: Dictionary containing best genetic string, history of attempted strings, and components of cost function across generations
    """
    Lambda = np.random.rand(numLAM, S) * (Lam_max - Lam_min) + Lam_min
    C = P
    randGen = S - P - C
    Lambda_hist = np.zeros((G, numLAM))
    overallMean, parentMean, best = np.zeros(G), np.zeros(G), np.zeros(G)
    overall_M, parent_M, best_M = np.zeros(G), np.zeros(G), np.zeros(G)
    overall_T, parent_T, best_T = np.zeros(G), np.zeros(G), np.zeros(G)
    overall_L, parent_L, best_L = np.zeros(G), np.zeros(G), np.zeros(G)
    costs, M_star, T_star, L_star = np.zeros(S), np.zeros(S), np.zeros(S), np.zeros(S)
    start = 0
    for i in range(G):
        for j in range(start, S):
            costs[j], pos, tar, timesteps, M_star[j], T_star[j], L_star[j] = drone_sim(N_m, N_o, N_t, w_1, w_2, w_3, Lambda[:, j], dt, tf, agents, obstacles, targets)
        ranks = np.argsort(costs)
        costs = np.sort(costs)
        M_star, T_star, L_star = M_star[ranks], T_star[ranks], L_star[ranks]
        overallMean[i], parentMean[i], best[i] = np.mean(costs), np.mean(costs[:P]), costs[0]
        overall_M[i], parent_M[i], best_M[i] = np.mean(M_star), np.mean(M_star[ranks][:P]), M_star[0]
        overall_T[i], parent_T[i], best_T[i] = np.mean(T_star), np.mean(T_star[ranks][:P]), T_star[0]
        overall_L[i], parent_L[i], best_L[i] = np.mean(L_star), np.mean(L_star[ranks][:P]), L_star[0]
        Lambda = Lambda[:, ranks]
        Lambda_hist[i, :] = Lambda[:, 0]
        first_children, second_children = range(0, C, 2), range(1, C, 2)
        phis_1, phis_2 = np.random.random(len(first_children)), np.random.random(len(first_children))
        children = np.c_[phis_1*Lambda[:, first_children] + (1-phis_1)*Lambda[:, second_children], \
                         phis_2*Lambda[:, first_children] + (1-phis_2)*Lambda[:, second_children]]
        Lambda[:, P:P+C] = children
        Lambda[:, (P+C):] = np.random.rand(numLAM, randGen) * (Lam_max - Lam_min) + Lam_min
        start = P
    return {"Lambda":Lambda[:, 0], "Best Lambda History":Lambda_hist, \
            "Best Cost":best, "Mean Parent Cost":parentMean, "Mean Cost":overallMean, \
            "Best M_Star":best_M, "Mean Parent M_Star":parent_M, "Mean M_Star":overall_M, \
            "Best T_Star":best_T, "Mean Parent T_Star":parent_T, "Mean T_Star":overall_T, \
            "Best L_Star":best_L, "Mean Parent L_Star":parent_L, "Mean L_Star":overall_L}
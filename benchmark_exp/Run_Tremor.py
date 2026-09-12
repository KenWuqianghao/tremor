# -*- coding: utf-8 -*-
# Tremor for TSB-AD: confidence-weighted rank fusion of MMPAD, Sub-PCA and a point-anomaly score (CPU-only).
# Layout follows benchmark_exp/Run_Custom_Detector.py.  License: Apache-2.0.
#
# Registration in TSB_AD (for Run_Detector_U.py / Run_Detector_M.py):
#   * copy `tremor/` next to TSB_AD/models/ (or `pip install -e .` of this repo)
#   * model_wrapper.py: add 'Tremor' to Unsupervise_AD_Pool and
#         def run_Tremor(data, **HP):
#             from tremor import run_Tremor_Unsupervised
#             return run_Tremor_Unsupervised(data, **HP)
#   * HP_list.py: Optimal_Uni_algo_HP_dict['Tremor'] = Optimal_Multi_algo_HP_dict['Tremor'] = Tremor_HP
import os, sys, time, argparse
import pandas as pd
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tremor import Tremor, run_Tremor_Unsupervised   # noqa: F401

# Hyper-parameters (chosen on the TSB-AD Tuning sets only)
Tremor_HP = {'stat': 'kurt', 'power': 'hard', 'prior': (1.0, 0.0, 0.0), 'zfloor': 3.0, 'tau': 0.5, 'flat': 'zmax', 'zprior': 0.0,
             'point_window': 'period', 'flat_only': (2,), 'override': ('pz', 'agree', 'spikes'), 'pzmin': 7.0, 'kfrac': 0.01,
             'athr': 0.5, 'sthr': 10.0, 'cthr': 5, 'fuse_multivariate': False, 'n_job': 1}

if __name__ == '__main__':
    from TSB_AD.evaluation.metrics import get_metrics
    from TSB_AD.utils.slidingWindows import find_length_rank
    parser = argparse.ArgumentParser(description='Running Tremor')
    parser.add_argument('--filename', type=str, default='001_NAB_id_1_Facility_tr_1007_1st_2014.csv')
    parser.add_argument('--data_direc', type=str, default='../Datasets/TSB-AD-U/')
    parser.add_argument('--AD_Name', type=str, default='Tremor')
    args = parser.parse_args()

    df = pd.read_csv(args.data_direc + args.filename).dropna()
    data = df.iloc[:, 0:-1].values.astype(float)
    label = df['Label'].astype(int).to_numpy()
    print('data: ', data.shape); print('label: ', label.shape)
    slidingWindow = find_length_rank(data, rank=1)

    start_time = time.time()
    output = run_Tremor_Unsupervised(data, **Tremor_HP)
    run_time = time.time() - start_time

    pred = output > (np.mean(output) + 3 * np.std(output))
    evaluation_result = get_metrics(output, label, slidingWindow=slidingWindow, pred=pred)
    print('Evaluation Result: ', evaluation_result, 'runtime: %.1fs' % run_time)

#!/usr/bin/env bash

current_date=$(date +'%Y-%m-%d/%H-%M')
experiment='kaggle_home_credit'
root='/Users/bede01/Documents/work/phd-papers/published/ml-workload-optimization'
result_path=${root}'/experiment_results/local/materialization/kaggle_home_credit/'${current_date}'.csv'

python /Users/bede01/Documents/work/phd-papers/published/ml-workload-optimization/code/collaborative-optimizer/paper/experiments/materialization/run_experiment.py \
  'root='${root} 'result='${result_path} 'experiment='${experiment} \
  'mat_budget=5.0' 'method=optimized' 'materializer=simple' 'reuse_type=all_compute'

python /Users/bede01/Documents/work/phd-papers/published/ml-workload-optimization/code/collaborative-optimizer/paper/experiments/materialization/run_experiment.py \
  'root='${root} 'result='${result_path} 'experiment='${experiment} \
  'mat_budget=5.0' 'method=optimized' 'materializer=storage_aware' 'reuse_type=all_compute'
#
#python /Users/bede01/Documents/work/phd-papers/published/ml-workload-optimization/code/collaborative-optimizer/paper/experiments/materialization/run_experiment.py \
#'root='${root} 'result='${result_path} 'experiment='${experiment} \
#'mat_budget=5.0' 'method=mock_optimized' 'materializer=simple'
#
#python /Users/bede01/Documents/work/phd-papers/published/ml-workload-optimization/code/collaborative-optimizer/paper/experiments/materialization/run_experiment.py \
#'root='${root} 'result='${result_path} 'experiment='${experiment} \
#'mat_budget=5.0' 'method=mock_optimized' 'materializer=storage_aware'
#
#python /Users/bede01/Documents/work/phd-papers/published/ml-workload-optimization/code/collaborative-optimizer/paper/experiments/materialization/run_experiment.py \
#'root='${root} 'result='${result_path} 'experiment='${experiment} \
#'mat_budget=10.0' 'method=mock_optimized' 'materializer=simple'
#
#python /Users/bede01/Documents/work/phd-papers/published/ml-workload-optimization/code/collaborative-optimizer/paper/experiments/materialization/run_experiment.py \
#'root='${root} 'result='${result_path} 'experiment='${experiment} \
#'mat_budget=10.0' 'method=mock_optimized' 'materializer=storage_aware'
#
#python /Users/bede01/Documents/work/phd-papers/published/ml-workload-optimization/code/collaborative-optimizer/paper/experiments/materialization/run_experiment.py \
#'root='${root} 'result='${result_path} 'experiment='${experiment} \
#'mat_budget=20.0' 'method=mock_optimized' 'materializer=simple'
#
#python /Users/bede01/Documents/work/phd-papers/ml-workload-optimization/code/collaborative-optimizer/paper/experiments/materialization/run_experiment.py \
#'root='${root} 'result='${result_path} 'experiment='${experiment} \
#'mat_budget=20.0' 'method=mock_optimized' 'materializer=storage_aware'

#!/usr/bin/env bash

file_name=$1

current_date=$(date +'%Y-%m-%d')
experiment='kaggle_home_credit'
root='/home/behrouz/collaborative-optimization'
result_path=${root}'/experiment_results/remote/execution_time/different_workloads/kaggle_home_credit/'${file_name}'/'${current_date}'.csv'


python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/execution_time/different_workloads/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} \
'mat_budget=32.0' 'method=optimized'


python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/execution_time/different_workloads/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} \
 'mat_budget=0.0' 'method=baseline'

 python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/execution_time/different_workloads/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} \
'mat_budget=32.0' 'method=optimized'


python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/execution_time/different_workloads/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} \
 'mat_budget=0.0' 'method=baseline'


python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/execution_time/different_workloads/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} \
'mat_budget=32.0' 'method=optimized'


python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/execution_time/different_workloads/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} \
 'mat_budget=0.0' 'method=baseline'



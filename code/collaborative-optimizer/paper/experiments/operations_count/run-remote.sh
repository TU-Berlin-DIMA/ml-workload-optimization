#!/usr/bin/env bash

file_name=$1

current_date=$(date +'%Y-%m-%d/%H-%M')
experiment='openml'
root='/home/behrouz/collaborative-optimization'
result_path=${root}'/experiment_results/remote/operations_count/openml/'${file_name}'/'${current_date}'.csv'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'mat_budget=0.1' \
'method=optimized' 'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'method=baseline' \
'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'mat_budget=0.1' \
'method=optimized' 'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup' 'warmstart=0'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'mat_budget=0.1' \
'method=optimized' 'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'method=baseline' \
'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'mat_budget=0.1' \
'method=optimized' 'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup' 'warmstart=0'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'mat_budget=0.1' \
'method=optimized' 'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'method=baseline' \
'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup'

python ~/collaborative-optimization/code/collaborative-optimizer/paper/experiments/operations_count/run_experiment.py \
${root}'/code/collaborative-optimizer/' 'root='${root} 'result='${result_path} 'experiment='${experiment} 'mat_budget=0.1' \
'method=optimized' 'limit=2000' 'profile='${root}'/data/profiles/cloud-41-dedup' 'warmstart=0'
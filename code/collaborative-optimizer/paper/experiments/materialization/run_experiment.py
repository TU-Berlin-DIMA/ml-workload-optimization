#!/usr/bin/env python



"""Execution Time Experiment

Run a list of workloads in sequence and report the execution time for each one

"""
import errno
import os
import sys
import uuid
from datetime import datetime

# Somehow someone hard codes this to be on top of the sys path and I cannot get rid of it
if '/home/zeuchste/git/scikit-learn' in sys.path:
    sys.path.remove('/home/zeuchste/git/scikit-learn')
from paper.experiments.scenario import get_kaggle_optimized_scenario
from experiment_graph.executor import CollaborativeExecutor, HelixExecutor
from experiment_graph.data_storage import DedupedStorageManager
from paper.experiment_helper import Parser
from experiment_graph.storage_managers import storage_profiler
from experiment_graph.optimizations.Reuse import LinearTimeReuse

parser = Parser(sys.argv)
verbose = parser.get('verbose', 0)
DEFAULT_ROOT = '/Users/bede01/Documents/work/phd-papers/ml-workload-optimization'
ROOT = parser.get('root', DEFAULT_ROOT)

# Experiment Graph
from experiment_graph.execution_environment import ExecutionEnvironment
from experiment_graph.materialization_algorithms.materialization_methods import StorageAwareMaterializer, \
    HeuristicsMaterializer, AllMaterializer, HelixMaterializer

EXPERIMENT = parser.get('experiment', 'kaggle_home_credit')
ROOT_DATA_DIRECTORY = ROOT + '/data'

method = parser.get('method', 'optimized')
materializer_type = parser.get('materializer', 'helix')

EXPERIMENT_TIMESTAMP = datetime.now()

mat_budget = float(parser.get('mat_budget', '8.0')) * 1024.0 * 1024.0

# unique identifier for the experiment run
e_id = uuid.uuid4().hex.upper()[0:8]

result_file = parser.get('result', ROOT + '/experiment_results/local/materialization/mock/test.csv')
profile = storage_profiler.get_profile(parser.get('profile', ROOT_DATA_DIRECTORY + '/profiles/local-dedup'))

if not os.path.exists(os.path.dirname(result_file)):
    try:
        os.makedirs(os.path.dirname(result_file))
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise

ee = ExecutionEnvironment(DedupedStorageManager(), reuse_type=LinearTimeReuse.NAME)
if materializer_type == 'storage_aware':
    materializer = StorageAwareMaterializer(storage_budget=mat_budget)
elif materializer_type == 'simple':
    materializer = HeuristicsMaterializer(storage_budget=mat_budget)
elif materializer_type == 'helix':
    materializer = HelixMaterializer(storage_budget=mat_budget)
elif materializer_type == 'all':
    materializer = AllMaterializer()
else:
    raise Exception('Invalid materializer type: {}'.format(materializer_type))

if materializer_type == 'helix':
    executor = HelixExecutor(budget=mat_budget)
else:
    executor = CollaborativeExecutor(execution_environment=ee, materializer=materializer)

workloads = get_kaggle_optimized_scenario(package=method)
for workload in workloads:
    workload_name = workload.__class__.__name__
    start = datetime.now()
    print('{} Start-workload: {}, mat_type: {}, budget: {}'.format(start, workload_name, materializer_type,
                                                                   mat_budget))
    success = executor.run_workload(workload=workload, root_data=ROOT_DATA_DIRECTORY, verbose=verbose)
    end = datetime.now()
    print('{} End-workload: {}, mat_type: {}, budget: {}'.format(end, workload_name, materializer_type,
                                                                 mat_budget))

    elapsed = (end - start).total_seconds()

    executor.local_process()
    executor.global_process()
    executor.cleanup()

    if not success:
        elapsed = 'Failed!'
    graph = executor.execution_environment.experiment_graph
    total_mat = graph.get_total_materialized_size()
    total_size = graph.get_total_size()
    with open(result_file, 'a') as the_file:
        # get_benchmark_results has the following order:
        the_file.write(
            '{},{},{},{},{},{},{},{},{}\n'.format(EXPERIMENT_TIMESTAMP.strftime("%H:%M:%S"), e_id,
                                                  EXPERIMENT, workload_name, materializer_type, mat_budget, total_mat,
                                                  total_size, elapsed))

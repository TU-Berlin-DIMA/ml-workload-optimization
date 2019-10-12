#!/usr/bin/env python

"""Execution Time Experiment

Run a list of workloads in sequence and report the execution time for each one

"""
import errno
import os
import sys
import uuid
from datetime import datetime

from openml import config

if len(sys.argv) > 1:
    SOURCE_CODE_ROOT = sys.argv[1]
else:
    SOURCE_CODE_ROOT = '/Users/bede01/Documents/work/phd-papers/ml-workload-optimization/code/collaborative' \
                       '-optimizer/ '
sys.path.append(SOURCE_CODE_ROOT)
# Somehow someone hard codes this to be on top of the sys path and I cannot get rid of it
if '/home/zeuchste/git/scikit-learn' in sys.path:
    sys.path.remove('/home/zeuchste/git/scikit-learn')

from paper.experiment_helper import Parser
from experiment_graph.data_storage import StorageManagerFactory, DedupedStorageManager
from experiment_graph.executor import CollaborativeExecutor, BaselineExecutor
from experiment_graph.execution_environment import ExecutionEnvironment
from experiment_graph.materialization_algorithms.materialization_methods import AllMaterializer, \
    StorageAwareMaterializer, HeuristicsMaterializer
from experiment_graph.optimizations.Reuse import LinearTimeReuse
from experiment_graph.storage_managers import storage_profiler
from experiment_graph.openml_helper.openml_connectors import get_setup_and_pipeline
from experiment_graph.workloads.openml_optimized import OpenMLOptimizedWorkload
from experiment_graph.workloads.openml_baseline import OpenMLBaselineWorkload

e_id = uuid.uuid4().hex.upper()[0:8]
EXPERIMENT_TIMESTAMP = datetime.now()

parser = Parser(sys.argv)
verbose = parser.get('verbose', 0)

DEFAULT_ROOT = '/Users/bede01/Documents/work/phd-papers/ml-workload-optimization'
ROOT = parser.get('root', DEFAULT_ROOT)
ROOT_DATA_DIRECTORY = ROOT + '/data'

mat_budget = float(parser.get('mat_budget', '1.0')) * 1024.0 * 1024.0

materializer_type = parser.get('materializer', 'storage_aware')
storage_type = parser.get('storage_type', 'dedup')
if materializer_type == 'storage_aware':
    materializer = StorageAwareMaterializer(storage_budget=mat_budget)
elif materializer_type == 'simple':
    materializer = HeuristicsMaterializer(storage_budget=mat_budget)
elif materializer_type == 'all':
    materializer = AllMaterializer()
else:
    raise Exception('invalid materializer: {}'.format(materializer_type))

storage_manager = StorageManagerFactory.get_storage(parser.get('storage_type', 'dedup'))

EXPERIMENT = parser.get('experiment', 'openml')
limit = int(parser.get('limit', 20))
openml_task = int(parser.get('task', 31))
OPENML_DIR = ROOT_DATA_DIRECTORY + '/openml/'
config.set_cache_directory(OPENML_DIR + '/cache')
OPENML_DATASET = ROOT_DATA_DIRECTORY + '/openml/task_id={}'.format(openml_task)

result_file = parser.get('result', ROOT + '/experiment_results/local/model_materialization/openml/test.csv')
profile = storage_profiler.get_profile(parser.get('profile', ROOT_DATA_DIRECTORY + '/profiles/local-dedup'))

if not os.path.exists(os.path.dirname(result_file)):
    try:
        os.makedirs(os.path.dirname(result_file))
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise

method = parser.get('method', 'optimized')

OPENML_DIR = ROOT_DATA_DIRECTORY + '/openml/'
OPENML_DATASET = ROOT_DATA_DIRECTORY + '/openml/task_id={}'.format(openml_task)
setup_and_pipelines = get_setup_and_pipeline(OPENML_DATASET + '/all_runs.csv', limit)

if method == 'optimized':
    ee = ExecutionEnvironment(DedupedStorageManager(), reuse_type=LinearTimeReuse.NAME)
    materializer = StorageAwareMaterializer(storage_budget=mat_budget)
    executor = CollaborativeExecutor(ee, cost_profile=profile, materializer=materializer)
elif method == 'baseline':
    executor = BaselineExecutor()
else:
    raise Exception('invalid method name: {}'.format(method))


def get_workload(method, setup, pipeline):
    if method == 'optimized':
        return OpenMLOptimizedWorkload(setup, pipeline, task_id=openml_task)
    else:
        return OpenMLBaselineWorkload(setup, pipeline, task_id=openml_task)


def run(executor, workload):
    if method == 'optimized' or method == 'mock_optimized':
        return executor.run_workload(workload=workload, root_data=ROOT_DATA_DIRECTORY, verbose=verbose)
    elif method == 'baseline':
        return executor.end_to_end_run(workload=workload, root_data=ROOT_DATA_DIRECTORY)
    elif method == 'mock':
        return executor.end_to_end_run(workload=workload, root_data=ROOT_DATA_DIRECTORY)


best_workload = None
best_score = -1
for setup, pipeline in setup_and_pipelines:

    workload = get_workload(method, setup, pipeline)
    start = datetime.now()
    # print '{}-Start of {} with pipeline {}, execution'.format(start, workload_name)
    success = run(executor, workload)
    # success = executor.run_workload(workload=workload, root_data=ROOT_DATA_DIRECTORY)
    current_score = workload.get_score()
    if best_score == -1:
        best_score = current_score
    print 'current score: {}'.format(current_score)
    print 'best score: {}'.format(best_score)
    if best_workload is not None:
        success = run(executor, workload)
        if current_score > best_score:
            print 'changing the baseline workload'
            best_score = current_score
            best_workload = workload
    else:
        best_workload = workload
        best_score = current_score
    end = datetime.now()

    elapsed = (end - start).total_seconds()

    executor.local_process()
    executor.global_process()
    executor.cleanup()

    if not success:
        elapsed = 'Failed!'
    # graph = executor.execution_environment.experiment_graph
    # total_mat = graph.get_total_materialized_size()
    # total_size = graph.get_total_size()
    with open(result_file, 'a') as the_file:
        # get_benchmark_results has the following order:
        the_file.write(
            '{},{},{},{},{},{},{},{},{}\n'.format(EXPERIMENT_TIMESTAMP.strftime("%H:%M:%S"), e_id,
                                                  EXPERIMENT, setup.flow_id, setup.setup_id, method,
                                                  elapsed, current_score, best_score))

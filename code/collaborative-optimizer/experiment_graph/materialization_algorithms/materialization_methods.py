from abc import abstractmethod

from experiment_graph.graph.graph_representations import ExperimentGraph
from experiment_graph.graph.graph_representations import WorkloadDag

ALPHA = 0.5


class Materializer(object):
    def __init__(self, storage_budget, modify_graph=False):
        """

        :type modify_graph: bool for debugging the utility values, set this to true
        """
        self.storage_budget = storage_budget
        self.modify_graph = modify_graph

    def compute_rhos(self, e_graph, w_dag):
        rhos = []
        for node in e_graph.nodes(data=True):
            if node[1]['root']:
                rho = float('inf')

            elif node[1]['type'] == 'SuperNode':
                rho = 0
            elif node[1]['type'] == 'GroupBy':
                # we are not materializing group by nodes at any cost
                rho = 0
                # node[1]['data'].clear_content()
            elif node[1]['load_cost'] > node[1]['recreation_cost']:
                print 'skipping node since the load cost is greater than the recreation cost: {}'.format(node[0])
                rho = 0
            else:
                # only compute the utility for the vertices which are already
                # materialized or are in the workload graph
                if node[1]['mat'] or node[0] in w_dag.nodes():
                    node_info = NodeInfo(node[0], node[1]['n_recreation_cost'],
                                         node[1]['n_potential'],
                                         node[1]['size'])
                    rhos.append(node_info)
                    rho = node_info.utility_value
                else:
                    rho = 0

            if self.modify_graph:
                node[1]['rho'] = rho

        rhos.sort(reverse=True)
        return rhos

    @staticmethod
    def select_nodes_to_materialize(rhos, remaining_budget, materialized_so_far):
        to_mat = list(materialized_so_far)
        current_budget = remaining_budget
        remaining = []

        while len(rhos) > 0:
            top = rhos.pop(0)
            if top.node_id in to_mat:
                continue
            if current_budget - top.size >= 0:
                to_mat.append(top.node_id)
                current_budget -= top.size
            else:
                remaining.append(top)

        return to_mat, remaining

    @staticmethod
    def materialize(experiment_graph, workload_dag, should_materialize):
        """
        materializes the list of vertices in the @should_materialize
        After calling this method, the data manager and history graph of the execution environment will be modified
        :type workload_dag: WorkloadDag
        :type experiment_graph: ExperimentGraph
        :param should_materialize: list of vertices to materialize (vertex ids)
        """
        # print 'should_materialize: {}'.format(should_materialize)
        for node_id, attributes in experiment_graph.graph.nodes(data=True):
            if node_id in should_materialize:
                if not attributes['mat']:
                    artifact = workload_dag.graph.nodes[node_id]['data']
                    experiment_graph.materialize(node_id=node_id,
                                                 artifact=artifact)
            else:
                if attributes['mat']:
                    print 'unmaterialize node {}'.format(node_id)
                    experiment_graph.unmaterialize(node_id)

    @abstractmethod
    def run(self, experiment_graph, workload_dag, verbose):
        """
        the code for finding the nodes to materialize
        this function does not and should not perform the actual materialization
        it only returns the list of the nodes that should be materialized
        :return: a list of (vertex_ids) to be materialized
        """
        pass

    def run_and_materialize(self, experiment_graph, workload_dag, verbose=0):
        """
        calls run and then the materialize function
        it 'materializes' the nodes specified by the run method. After calling this method,
        the data manager and history graph of the execution environment will be modified
        """
        should_materialize = self.run(experiment_graph, workload_dag, verbose)
        self.materialize(experiment_graph, workload_dag, should_materialize)


class AllMaterializer(Materializer):
    """
    This class materializes everything (except for SuperNode which cannot be materialized)
    We will use this as a baseline
    """

    def __init__(self):
        super(AllMaterializer, self).__init__(0)

    def run(self, experiment_graph, workload_dag, verbose=0):
        return list(set([n for n, t in workload_dag.graph.nodes(data='type') if
                         t != 'SuperNode' and t != 'GroupBy'] +
                        [n for n, d in experiment_graph.graph.nodes(data='mat') if d]))


class HeuristicsMaterializer(Materializer):

    def run(self, experiment_graph, workload_dag, verbose=0):
        """
        simple heuristics based materialization.
        First, it computes all the rhos (feasibility ratio) based on the formula in the paper
        Then, starting fro the highest rhos it starts to materialize until the storage budget is met
        :return:
        """

        graph = experiment_graph.graph
        rhos = self.compute_rhos(experiment_graph.graph, workload_dag.graph)
        root_size = 0.0
        to_mat = []
        for n in graph.nodes(data=True):
            if n[1]['root']:
                root_size += n[1]['size']
                to_mat.append(n[0])
        should_materialize, remaining = self.select_nodes_to_materialize(rhos, self.storage_budget,
                                                                         to_mat)

        total_node_size = experiment_graph.get_size_of(should_materialize)
        remaining_budget = self.storage_budget - total_node_size
        if verbose:
            print 'state after heuristics based materialization'
            print 'total size of materialized nodes: {}'.format(total_node_size)
            print 'remaining budget: {}, number of nodes to materialize: {}'.format(remaining_budget,
                                                                                    len(should_materialize))

        return should_materialize


class StorageAwareMaterializer(Materializer):

    def run(self, experiment_graph, workload_dag, verbose=0):

        rhos = self.compute_rhos(experiment_graph.graph, workload_dag.graph)
        root_size = 0.0
        materialization_candidates = []

        for n in experiment_graph.graph.nodes(data=True):
            if n[1]['root']:
                root_size += n[1]['size']
                materialization_candidates.append(n[0])

        remaining_budget = self.storage_budget
        i = 1
        while remaining_budget >= 0:
            start_list = list(materialization_candidates)

            materialization_candidates, rhos = self.select_nodes_to_materialize(rhos, remaining_budget,
                                                                                materialization_candidates)
            print 'current size: {}'.format(experiment_graph.get_size_of(materialization_candidates))
            # if node new node is materialized, end the process
            if start_list == materialization_candidates:
                break
            current_size = self.recompute_sizes(experiment_graph, workload_dag, materialization_candidates, rhos)
            remaining_budget = self.storage_budget - current_size
            if verbose:
                total_node_size = experiment_graph.get_size_of(materialization_candidates)
                print 'state after iteration {}'.format(i)
                print 'total size of materialized nodes: {}, actual on disk size: {}'.format(total_node_size,
                                                                                             current_size)
                print 'remaining budget: {}, number of nodes to materialize: {}'.format(remaining_budget,
                                                                                        len(materialization_candidates))

            i += 1
        return materialization_candidates

    @staticmethod
    def recompute_sizes(experiment_graph, workload_dag, materialization_candidates, remaining_rhos):
        """
        First, this method checks all the columns in the artifacts in materialization_candidates.
        Then, the total size of the experiment graph, considering the column redundancy is computed.
        Finally, the sizes of the remaining vertices are recomputed based on how much more storage do they need to
        materialize.
        :param experiment_graph:
        :param workload_dag:
        :param materialization_candidates:
        :param remaining_rhos:
        :return:
        """
        current_size = 0.0
        all_columns = set()
        for node_id in materialization_candidates:
            node = experiment_graph.graph.nodes[node_id]
            if not node['mat']:
                node = workload_dag.graph.nodes[node_id]
                if node['type'] == 'Dataset':
                    underlying_data = node['data'].underlying_data
                    for column_hash in underlying_data.get_column_hash():
                        if column_hash not in all_columns:
                            current_size += underlying_data.column_sizes[column_hash]
                            all_columns.add(column_hash)
                elif node['type'] == 'Feature':
                    underlying_data = node['data'].underlying_data
                    column_hash = underlying_data.get_column_hash()
                    if column_hash not in all_columns:
                        current_size += underlying_data.get_size()
                        all_columns.add(column_hash)
                else:
                    current_size += node['size']

        for rho in remaining_rhos:
            node = experiment_graph.graph.nodes[rho.node_id]
            if not node['mat']:
                node = workload_dag.graph.nodes[rho.node_id]
                if node['type'] == 'Feature':
                    underlying_data = node['data'].underlying_data
                    column_hash = underlying_data.get_column_hash()
                    if column_hash in all_columns:
                        rho.size = 0.0
                elif node['type'] == 'Dataset':
                    underlying_data = node['data'].underlying_data
                    for ch in underlying_data.get_column_hash():
                        if ch in all_columns:
                            rho.size -= underlying_data.column_sizes[ch]

        return current_size


class NodeInfo(object):
    def __init__(self, node_id, normalized_cost, normalized_potential, size):
        self.node_id = node_id
        self.normalized_cost = normalized_cost
        self.normalized_potential = normalized_potential
        self.size = size
        self.utility_value = self.compute_rho()

    def compute_rho(self):
        return (ALPHA * self.normalized_potential + (1 - ALPHA) * self.normalized_cost) / self.size

    def __lt__(self, other):
        return self.utility_value < other.utility_value

    def __repr__(self):
        return 'node: {}, cost: {:.3f}, potential: {:.3f}, size: {:.3f}, utility: {:.5f}' \
            .format(self.node_id[0:12],  # 32 is too long to show
                    self.normalized_cost,
                    self.normalized_potential,
                    self.size,
                    self.utility_value)

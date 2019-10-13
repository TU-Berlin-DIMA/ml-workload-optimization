import copy
from abc import abstractmethod
from collections import deque

import networkx as nx


class Reuse:
    NAME = 'BASE_REUSE'

    def __init__(self):
        self.history_reads = 0

    @staticmethod
    def get_reuse(reuse_type):
        if reuse_type == AllMaterializedReuse.NAME:
            return AllMaterializedReuse()
        elif reuse_type == LinearTimeReuse.NAME:
            return LinearTimeReuse()
        elif reuse_type == AllComputeReuse.NAME:
            return AllComputeReuse()
        elif reuse_type == BottomUpReuse.NAME:
            return BottomUpReuse()
        else:
            raise Exception('Undefined Reuse type: {}'.format(reuse_type))

    @abstractmethod
    def run(self, vertex, workload, history, verbose):
        """
        method for implementing the reuse algorithm.
        It returns a tuple (materialize_vertices, execution_vertices, history_reads):
            materialize_vertices: set of already materialized vertices from history
            execution_vertices: set of vertices that must be in the execution path
            history_reads: number of reads from history graph
        :param history: history graph
        :param workload: current workload graph
        :param vertex: queried vertex
        :param verbose: verbosity level (0 or 1)
        :return:
        """
        pass

    def is_mat(self, history, vertex):
        self.history_reads += 1
        try:
            return history.nodes[vertex]['mat']
        except KeyError:
            return False

    def in_history_and_mat(self, history, vertex):
        """
        checks if a nodes is in history and if it is materialized and returns the following
        0: if the node is not in history
        1: if the node is in history but it is not materialized
        2: if the node is in history and it is materialized
        :param history:
        :param vertex:
        :return:
        """
        self.history_reads += 1
        try:
            node = history.nodes[vertex]
        except KeyError:
            # the node does not exist in history
            return 0
        if node['mat']:
            # the node is materialized
            return 2
        else:
            # the node exists but it is not materialized
            return 1

    def check_for_warmstarting(self, history, workload, all_models):
        warmstarting_candidates = set()
        for m in all_models:
            training_datasets = list(workload.predecessors(m))
            assert len(training_datasets) == 1
            training_dataset = training_datasets[0]
            if self.in_history_and_mat(history, training_dataset):
                workload_training_edge = workload.edges[training_dataset, m]
                if not workload_training_edge['warm_startable']:
                    continue
                if not workload_training_edge['should_warmstart']:
                    continue
                results = set()
                for _, hm, history_training_edge in history.out_edges(training_dataset, data=True):
                    history_node = history.nodes[hm]
                    if history_node['type'] == 'SK_Model':
                        if not history_training_edge['warm_startable']:
                            continue
                        elif history_training_edge['no_random_state_model'] == \
                                workload_training_edge['no_random_state_model']:
                            results.add((history_training_edge['args']['model'], history_node['score']))
                if results:
                    best_model = -1
                    best_score = -1
                    for model, score in results:
                        if score > best_score:
                            best_score = score
                            best_model = model
                    model_to_warmstart = copy.deepcopy(best_model)
                    model_to_warmstart.random_state = workload_training_edge['random_state']
                    warmstarting_candidates.add((training_dataset, m, model_to_warmstart))
        return warmstarting_candidates


class AllComputeReuse(Reuse):
    """
    A naive reuse which recomputes every materialized vertex. Since by default we compute everything, this class
    does nothing just returns the list of all the vertices of workload dag which to be executed
    """
    NAME = 'all_compute'

    def __init__(self):
        Reuse.__init__(self)

    def run(self, vertex, workload, history, verbose):
        workload_subgraph = workload.compute_execution_subgraph(vertex)

        return set(), set(workload_subgraph.nodes()), set()


class AllMaterializedReuse(Reuse):
    """
    A naive reuse which loads all the materialized vertices into the workload DAG
    """
    NAME = 'all_mat'

    def __init__(self):
        Reuse.__init__(self)

    def run(self, vertex, workload, history, verbose):
        workload_subgraph = workload.compute_execution_subgraph(vertex)
        materialized_vertices, execution_vertices, all_models = self.naive_all_load(workload_subgraph=workload_subgraph,
                                                                                    e_graph=history.graph,
                                                                                    verbose=verbose)

        warmstarting_candidates = self.check_for_warmstarting(history.graph, workload_subgraph, all_models)
        if verbose == 1:
            print 'materialized_vertices: {}'.format(materialized_vertices)
            print 'warmstarting_candidates: {}'.format(warmstarting_candidates)
        return materialized_vertices, execution_vertices, warmstarting_candidates

    @staticmethod
    def naive_all_load(workload_subgraph, e_graph, verbose):
        """
        add every materialized vertex for loading into workload DAG
        """
        materialized_vertices = set()
        warmstarting_candidates = set()
        execution_set = set()
        for n in nx.topological_sort(workload_subgraph):
            execution_set.add(n)
            if not e_graph.has_node(n):
                # for sk models that are not in experiment graph, we add them to warmstarting candidate
                if workload_subgraph.nodes[n]['type'] == 'SK_Model':
                    warmstarting_candidates.add(n)
                continue
            elif e_graph.nodes[n]['mat']:
                materialized_vertices.add(n)
            else:
                if workload_subgraph.nodes[n]['type'] == 'SK_Model':
                    warmstarting_candidates.add(n)

        if verbose:
            print 'After forward pass mat_set={}, warm_set={}'.format(materialized_vertices, warmstarting_candidates)
        return materialized_vertices, execution_set, warmstarting_candidates


class LinearTimeReuse(Reuse):
    """
    Our novel reuse method that addresses the load cost/recreation cost trade off when deciding what materialized nodes
    to load into the workload DAG.
    """
    NAME = 'linear'

    def __init__(self):
        Reuse.__init__(self)

    def run(self, vertex, workload, history, verbose):
        workload_subgraph = workload.compute_execution_subgraph(vertex)
        materialized_vertices, to_warmstart = self.forward_pass(workload_subgraph=workload_subgraph,
                                                                e_graph=history.graph, verbose=verbose)
        materialized_vertices, execution_vertices, to_warmstart = self.backward_pass(
            terminal=vertex,
            workload_subgraph=workload_subgraph,
            materialized_vertices=materialized_vertices,
            to_warmstart=to_warmstart,
            verbose=verbose)

        warmstarting_candidates = self.check_for_warmstarting(history.graph, workload_subgraph, to_warmstart)
        if verbose == 1:
            print 'materialized_vertices: {}'.format(materialized_vertices)
            print 'warmstarting_candidates: {}'.format(warmstarting_candidates)
        return materialized_vertices, execution_vertices, warmstarting_candidates

    @staticmethod
    def forward_pass(workload_subgraph, e_graph, verbose):
        """
        performs a conditional search from the root nodes of the subgraph
        unlike reverse_conditional_bfs, the workload subgraph must be previously computed and is guaranteed not to
        contain any nodes that has materialized data
        :param verbose:
        :param workload_subgraph:
        :param e_graph:
        :return:
        """
        materialized_vertices = set()
        to_warmstart = set()
        recreation_costs = {node: -1 for node in workload_subgraph.nodes}
        for n in nx.topological_sort(workload_subgraph):
            if not e_graph.has_node(n):
                # for sk models that are not in experiment graph, we add them to warmstarting candidate
                if workload_subgraph.nodes[n]['type'] == 'SK_Model':
                    to_warmstart.add(n)
                continue

            if workload_subgraph.nodes[n]['data'].computed:
                recreation_costs[n] = 0
            else:
                node = e_graph.nodes[n]
                p_costs = sum([recreation_costs[source] for source, _ in e_graph.in_edges(n)])
                execution_cost = node['compute_cost'] + p_costs
                if not node['mat']:

                    recreation_costs[n] = execution_cost
                    # for sk models that are in experiment graph but are not materialized, we add them to materialized
                    # candidates to see if we can warmstart them with a model that is materialized
                    # TODO is this valid?
                    if workload_subgraph.nodes[n]['type'] == 'SK_Model':
                        to_warmstart.add(n)
                elif node['load_cost'] < execution_cost:

                    recreation_costs[n] = node['load_cost']
                    materialized_vertices.add(n)
                else:
                    recreation_costs[n] = execution_cost
        if verbose == 1:
            print 'After forward pass mat_set={}, warm_set={}'.format(materialized_vertices, to_warmstart)
        return materialized_vertices, to_warmstart

    @staticmethod
    def backward_pass(terminal, workload_subgraph, materialized_vertices, to_warmstart, verbose):

        execution_set = set()
        prevs = workload_subgraph.predecessors
        final_materialized_vertices = set()
        final_to_warmstart = set()
        queue = deque([(terminal, prevs(terminal))])
        while queue:
            current, prev_nodes_list = queue.pop()
            execution_set.add(current)
            if current in materialized_vertices:
                final_materialized_vertices.add(current)
            elif not workload_subgraph.nodes[current]['data'].computed:
                if current in to_warmstart:
                    final_to_warmstart.add(current)

                for prev_node in prev_nodes_list:
                    if prev_node not in execution_set:
                        queue.append((prev_node, prevs(prev_node)))

        if verbose == 1:
            print 'After backward pass mat_set={}, warm_set={}'.format(materialized_vertices, to_warmstart)

        return final_materialized_vertices, execution_set, final_to_warmstart


class BottomUpReuse(Reuse):
    """
    This is a better baseline which only returns the materialized node that are needed and prunes the rest.
    Our Linear time should still perform better than this because in the linear time reuse, if a vertex has higher
    load cost, we choose to recompute it. However, in Bottom Up we always return the materialized vertex.
    Bottom Up is faster than AllMaterialized, because in Bottom Up we only return the materialized node which are needed.
    Essentially, bottom up reuse is very similar to the the backward-pass of the reuse algorithm which
    stops traversing the vertex of a materialized node.
    """
    NAME = 'bottomup'

    def __init__(self):
        Reuse.__init__(self)

    def run(self, vertex, workload, history, verbose):
        e_subgraph = workload.compute_execution_subgraph(vertex)
        materialized_vertices, execution_vertices, model_candidates = self.reverse_bfs(terminal=vertex,
                                                                                       workload_subgraph=e_subgraph,
                                                                                       history=history.graph)
        warmstarting_candidates = self.check_for_warmstarting(history.graph, e_subgraph, model_candidates)
        return materialized_vertices, execution_vertices, warmstarting_candidates, self.history_reads

    def reverse_bfs(self, terminal, workload_subgraph, history):
        """
        perform a reverse bfs on workload stop searching further if the node exist in history
        the search doesn't continue on parents of a node which exists in the history
        :param terminal:
        :param workload_subgraph:
        :param history:
        :return:
        """

        materialized_set = set()
        model_candidates = set()
        warmstarting_candidates = set()
        execution_set = {terminal}
        if workload_subgraph.nodes[terminal]['data'].computed:
            return materialized_set, execution_set, warmstarting_candidates
        if self.is_mat(history, terminal):
            return {terminal}, execution_set, warmstarting_candidates
        if workload_subgraph.nodes[terminal]['type'] == 'SK_Model':
            model_candidates.add(terminal)

        prevs = workload_subgraph.predecessors

        queue = deque([(terminal, prevs(terminal))])
        while queue:
            current, prev_nodes_list = queue[0]
            try:

                prev_node = next(prev_nodes_list)
                if prev_node not in execution_set:
                    # The next node should always be added to the execution set even if it is materialized in the
                    # history which results as the first node in the execution path
                    execution_set.add(prev_node)
                    workload_node = workload_subgraph.nodes[prev_node]

                    if workload_node['data'].computed:
                        pass
                    elif self.is_mat(history, prev_node):
                        materialized_set.add(prev_node)
                    else:
                        if workload_node['type'] == 'SK_Model':
                            model_candidates.add(prev_node)
                        queue.append((prev_node, prevs(prev_node)))

            except StopIteration:
                queue.popleft()
        return materialized_set, execution_set, model_candidates

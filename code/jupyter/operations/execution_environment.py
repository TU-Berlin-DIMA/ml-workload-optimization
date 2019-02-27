import uuid

import pandas as pd
import numpy as np

from execution_graph import ExecutionGraph


class ExecutionEnvironment(object):
    graph = ExecutionGraph()

    @staticmethod
    def load(loc, nrows=None):
        nextnode = ExecutionEnvironment.Dataset(loc, pd.read_csv(loc, nrows=nrows))
        ExecutionEnvironment.graph.roots.append(loc)
        ExecutionEnvironment.graph.add_node(loc, **{'root': True, 'type': 'Dataset', 'data': nextnode, 'loc': loc})
        return nextnode

    class Node(object):
        def __init__(self, id, data):
            self.id = id
            self.data = data
            self.meta = {}

        # TODO: when params are a dictionary with multiple keys the order may not be the same in str conversion
        def e_hash(self, oper, params=''):
            return oper + '(' + str(params).replace(' ', '') + ')'

        def v_uuid(self):
            return uuid.uuid4().hex.upper()[0:8]

        def get(self):
            # compute and return the result
            # graph.compute_result(self.id)
            if self.is_empty():
                ExecutionEnvironment.graph.compute_result(self.id)
                self.reapply_meta()
            return self.data

        def update_meta(self):
            raise Exception('Node object has no meta data')

        def reapply_meta(self):
            raise Exception('Node class should not have been instantiated')

        def getNotNone(self, nextnode, exist):
            if exist is not None:
                return exist
            else:
                return nextnode

        def is_empty(self):
            return self.data is None or 0 == len(self.data)

        def generate_agg_node(self, oper, args={}, v_id=None):
            if v_id is None:
                v_id = self.id
            nextid = self.v_uuid()
            nextnode = ExecutionEnvironment.Agg(nextid, None)
            exist = ExecutionEnvironment.graph.add_edge(v_id, nextid, nextnode,
                                                        {'name': oper,
                                                         'oper': 'p_' + oper,
                                                         'args': args,
                                                         'hash': self.e_hash(oper, args)},
                                                        ntype=ExecutionEnvironment.Agg.__name__)
            return self.getNotNone(nextnode, exist)

        def generate_sklearn_node(self, oper, args={}, v_id=None):
            if v_id is None:
                v_id = self.id
            nextid = self.v_uuid()
            nextnode = ExecutionEnvironment.SK_Model(nextid, None)
            exist = ExecutionEnvironment.graph.add_edge(v_id, nextid, nextnode,
                                                        {'name': oper,
                                                         'oper': 'p_' + oper,
                                                         'args': args,
                                                         'hash': self.e_hash(oper, args)},
                                                        ntype=ExecutionEnvironment.Agg.__name__)
            return self.getNotNone(nextnode, exist)

        def generate_dataset_node(self, oper, args={}, v_id=None):
            if v_id is None:
                v_id = self.id
            nextid = self.v_uuid()
            nextnode = ExecutionEnvironment.Dataset(nextid, pd.DataFrame())
            exist = ExecutionEnvironment.graph.add_edge(v_id, nextid, nextnode,
                                                        {'name': oper,
                                                         'oper': 'p_' + oper,
                                                         'args': args,
                                                         'hash': self.e_hash(oper, args)},
                                                        ntype=ExecutionEnvironment.Dataset.__name__)
            return self.getNotNone(nextnode, exist)

        def generate_feature_node(self, oper, args={}, v_id=None):
            if v_id is None:
                v_id = self.id
            nextid = self.v_uuid()
            nextnode = ExecutionEnvironment.Feature(nextid, pd.Series())
            exist = ExecutionEnvironment.graph.add_edge(v_id, nextid, nextnode,
                                                        {'name': oper,
                                                         'oper': 'p_' + oper,
                                                         'args': args,
                                                         'hash': self.e_hash(oper, args)},
                                                        ntype=type(nextnode).__name__)
            return self.getNotNone(nextnode, exist)

        def generate_super_node(self, nodes, args={}):
            nextid = ''
            for n in nodes:
                nextid += n.id

            if not ExecutionEnvironment.graph.has_node(nextid):
                nextnode = ExecutionEnvironment.SuperNode(nextid, nodes)
                ExecutionEnvironment.graph.add_node(nextid,
                                                    **{'type': type(nextnode).__name__,
                                                       'root': False,
                                                       'data': nextnode})
                for n in nodes:
                    # this is to make sure each merge edge is a unique name
                    args['uuid'] = self.v_uuid()
                    ExecutionEnvironment.graph.add_edge(n.id, nextid, nextnode,
                                                        {'name': 'merge',
                                                         'oper': 'merge',
                                                         'args': {},
                                                         'hash': self.e_hash('merge', args)},
                                                        ntype=type(nextnode).__name__)
                return nextnode
            else:
                # TODO: add the update rule (even though it has no effect)
                return ExecutionEnvironment.graph.graph.nodes[nextid]['data']

    class Feature(Node):
        """ Feature class representing one (and only one) column of a data.
        This class is analogous to pandas.core.series.Series 

        Todo:
            * Integration with the graph library
            * Add support for every operations that Pandas Series supports
            * Support for Python 3.x

        """

        def __init__(self, id, data):
            ExecutionEnvironment.Node.__init__(self, id, data)
            if len(data) > 0:
                self.update_meta()

        def update_meta(self):
            self.meta = {'name': self.data.name, 'dtype': self.data.dtype}

        def reapply_meta(self):
            if not self.is_empty() and 'name' in self.meta.keys():
                self.data.name = self.meta['name']
            self.update_meta()

        def setname(self, name):
            self.meta['name'] = name
            self.reapply_meta()

        # Overriding math operators
        def __mul__(self, other):
            return self.generate_feature_node('__mul__', {'other': other})

        def p___mul__(self, other):
            return self.data * other

        def __rmul__(self, other):
            return self.generate_feature_node('__rmul__', {'other': other})

        def p___rmul__(self, other):
            return other * self.data

        # TODO: When switching to python 3 this has to change to __floordiv__ and __truediv__
        def __div__(self, other):
            return self.generate_feature_node('__div__', {'other': other})

        def p___div__(self, other):
            return self.data / other

        def __rdiv__(self, other):
            return self.generate_feature_node('__rdiv__', {'other': other})

        def p___rdiv__(self, other):
            return other / self.data

        def __add__(self, other):
            return self.generate_feature_node('__add__', {'other': other})

        def p___add__(self, other):
            return self.data + other

        def __radd__(self, other):
            return self.generate_feature_node('__radd__', {'other': other})

        def p___radd__(self, other):
            return other + self.data

        def __sub__(self, other):
            return self.generate_feature_node('__sub__', {'other': other})

        def p___sub__(self, other):
            return self.data - other

        def __rsub__(self, other):
            return self.generate_feature_node('__rsub__', {'other': other})

        def p___rsub__(self, other):
            return other - self.data

        def __lt__(self, other):
            return self.generate_feature_node('__lt__', {'other': other})

        def p___lt__(self, other):
            return self.data < other

        def __le__(self, other):
            return self.generate_feature_node('__le__', {'other': other})

        def p___le__(self, other):
            return self.data <= other

        def __eq__(self, other):
            return self.generate_feature_node('__eq__', {'other': other})

        def p___eq__(self, other):
            return self.data == other

        def __ne__(self, other):
            return self.generate_feature_node('__ne__', {'other': other})

        def p___ne__(self, other):
            return self.data != other

        def __gt__(self, other):
            return self.generate_feature_node('__gt__', {'other': other})

        def p___gt__(self, other):
            return self.data > other

        def __ge__(self, other):
            return self.generate_feature_node('__ge__', {'other': other})

        def p___ge__(self, other):
            return self.data >= other

        # End of overridden methods

        def isnull(self):
            ExecutionEnvironment.graph.add_edge(self.id,
                                                {'oper': self.edge('isnull'), 'hash': self.edge('isnull')},
                                                ntype=type(self).__name__)

        def notna(self):
            return self.generate_feature_node('notna')

        def p_notna(self):
            return self.data.notna()

        def sum(self):
            return self.generate_agg_node('sum')

        def p_sum(self):
            return self.data.sum()

        def nunique(self, dropna=True):
            return self.generate_agg_node('nunique', {'dropna': dropna})

        def p_nunique(self, dropna):
            return self.data.nunique(dropna=dropna)

        def describe(self):
            return self.generate_agg_node('describe')

        def p_describe(self):
            return self.data.describe()

        def mean(self):
            return self.generate_agg_node('mean')

        def p_mean(self):
            return self.data.mean()

        def min(self):
            return self.generate_agg_node('min')

        def p_min(self):
            return self.data.min()

        def max(self):
            return self.generate_agg_node('max')

        def p_max(self):
            return self.data.max()

        def count(self):
            return self.generate_agg_node('count')

        def p_count(self):
            return self.data.count()

        def std(self):
            return self.generate_agg_node('std')

        def p_std(self):
            return self.data.std()

        def quantile(self, values):
            return self.generate_agg_node('quantile', {'values': values})

        def p_quantile(self, values):
            return self.data.quantile(values=values)

        def value_counts(self):
            return self.generate_agg_node('value_counts')

        def p_value_counts(self):
            return self.data.value_counts()

        def abs(self):
            return self.generate_feature_node('abs')

        def p_abs(self):
            return self.data.abs()

        def unique(self):
            return self.generate_feature_node('unique')

        def p_unique(self):
            return self.data.unique()

        def dropna(self):
            return self.generate_feature_node('dropna')

        def p_dropna(self):
            return self.data.dropna()

        def binning(self, start_value, end_value, num):
            return self.generate_feature_node('binning',
                                              {'start_value': start_value, 'end_value': end_value, 'num': num})

        def p_binning(self, start_value, end_value, num):
            return pd.cut(self.data, bins=np.linspace(start_value, end_value, num=num))

        def replace(self, to_replace):
            return self.generate_feature_node('replace', {'to_replace': to_replace})

        def p_replace(self, to_replace):
            return self.data.replace(to_replace, inplace=False)

        def onehot_encode(self):
            ExecutionEnvironment.graph.add_edge(self.id,
                                                {'oper': self.edge('onehot'), 'hash': self.edge('onehot')},
                                                ntype=ExecutionEnvironment.Dataset.__name__)

        def corr(self, other):
            supernode = self.generate_super_node([self, other])
            return self.generate_agg_node('corr_with', v_id=supernode.id)

        def fit_sk_model(self, model):
            return self.generate_sklearn_node('fit_sk_model', {'model': model})

        def p_fit_sk_model(self, model):
            model.fit(self.data)
            return model

    class Dataset(Node):
        """ Dataset class representing a dataset (set of Features)
        This class is analogous to pandas.core.frame.DataFrame

        Todo:
            * Integration with the graph library
            * Add support for every operations that Pandas DataFrame supports
            * Support for Python 3.x

        """

        def __init__(self, id, data):
            ExecutionEnvironment.Node.__init__(self, id, data)
            if len(data) > 0:
                self.update_meta()

        def update_meta(self):
            self.meta = {'columns': self.data.columns, 'dtypes': self.data.dtypes}

        def reapply_meta(self):
            if 'columns' in self.meta.keys():
                self.data.columns = self.meta['columns']
            self.update_meta()

        def project(self, columns):
            if type(columns) is str:
                return self.generate_feature_node('project', {'columns': columns})
            if type(columns) is list:
                return self.generate_dataset_node('project', {'columns': columns})

        def p_project(self, columns):
            return self.data[columns]

        # overloading the indexing operator similar operation to project  
        def __getitem__(self, index):
            """ Overrides getitem method
            If the index argument is of type string or a list, we apply a projection operator (indexing columns)
            If the index argument is of type Feature, we apply a 'join' operator where we filter the data using values
            in the Feature. The data in the feature must be of the form (index, Boolean)
            TODO:
             check how to implement the set_column operation, i.e. dataset['new_column'] = new_feature
            """
            # project operator
            if type(index) in [str, list]:
                return self.project(index)
            # index operator using another Series of the form (index,Boolean)
            elif isinstance(index, ExecutionEnvironment.Feature):
                supernode = self.generate_super_node([self, index])
                return self.generate_dataset_node('filter_with', args={}, v_id=supernode.id)

            else:
                raise Exception('Unsupported operation. Only project (column index) is supported')

        def head(self, size=5):
            return self.generate_dataset_node('head', {'size': size})

        def p_head(self, size=5):
            return self.data.head(size)

        def shape(self):
            return self.generate_agg_node('shape', {})

        def p_shape(self):
            return self.data.shape

        def isnull(self):
            return self.generate_dataset_node('isnull')

        def p_isnull(self):
            return self.data.isnull()

        def sum(self):
            return self.generate_agg_node('sum')

        def p_sum(self):
            return self.data.sum()

        def nunique(self, dropna=True):
            return self.generate_agg_node('nunique', {'dropna': dropna})

        def p_nunique(self, dropna):
            return self.data.nunique(dropna=dropna)

        def describe(self):
            return self.generate_agg_node('describe')

        def p_describe(self):
            return self.data.describe()

        def abs(self):
            return self.generate_dataset_node('abs')

        def p_abs(self):
            return self.data.abs()

        def mean(self):
            return self.generate_agg_node('mean')

        def p_mean(self):
            return self.data.mean()

        def min(self):
            return self.generate_agg_node('min')

        def p_min(self):
            return self.data.min()

        def max(self):
            return self.generate_agg_node('max')

        def p_max(self):
            return self.data.max()

        def count(self):
            return self.generate_agg_node('count')

        def p_count(self):
            return self.data.count()

        def std(self):
            return self.generate_agg_node('std')

        def p_std(self):
            return self.data.std()

        def quantile(self, values):
            return self.generate_agg_node('quantile', {'values': values})

        def p_quantile(self, values):
            return self.data.quantile(values=values)

        def notna(self):
            return self.generate_dataset_node('notna')

        def p_notna(self):
            return self.data.notna()

        def select_dtypes(self, data_type):
            return self.generate_dataset_node('select_dtypes', {'data_type': data_type})

        def p_select_dtypes(self, data_type):
            return self.data.select_dtypes(data_type)

        # If drop column results in one column the return type should be a Feature
        def drop(self, columns):
            return self.generate_dataset_node('drop', {'columns': columns})

        def p_drop(self, columns):
            return self.data.drop(columns=columns)

        def dropna(self):
            return self.generate_dataset_node('dropna')

        def p_dropna(self):
            return self.data.dropna()

        def add_column(self, feature, col_name):
            supernode = self.generate_super_node([self, feature], {'col_name': col_name})
            return self.generate_dataset_node('add_column', {'col_name': col_name}, v_id=supernode.id)

        def onehot_encode(self):
            return self.generate_dataset_node('onehot_encode', {})

        def p_onehot_encode(self):
            return pd.get_dummies(self.data)

        def corr(self):
            return self.generate_agg_node('corr', {})

        def p_corr(self):
            return self.data.corr()

        # TODO: Do we need to create special grouped nodes?
        # For now Dataset node is good enough since aggregation operations that exist on group
        # also exist in the Dataset
        def groupby(self, col_names):
            return self.generate_dataset_node('groupby', {'col_names': col_names})

        def p_groupby(self, col_names):
            return self.data.groupby(col_names)

        # merge node
        def concat(self, nodes):
            if type(nodes) == list:
                supernode = self.generate_super_node([self] + nodes)
            else:
                supernode = self.generate_super_node([self] + [nodes])
            return self.generate_dataset_node('concat', v_id=supernode.id)

        def fit_sk_model(self, model):
            return self.generate_sklearn_node('fit_sk_model', {'model': model})

        def p_fit_sk_model(self, model):
            model.fit(self.data)
            return model

    class Agg(Node):
        def __init__(self, id, data):
            ExecutionEnvironment.Node.__init__(self, id, data)

        def is_empty(self):
            return self.data is None

        def update_meta(self):
            self.meta = {'type': 'aggregation'}

        def reapply_meta(self):
            self.update_meta()

        def show(self):
            return self.id + " :" + self.data.__str__()

    class SK_Model(Node):
        def __init__(self, id, data):
            ExecutionEnvironment.Node.__init__(self, id, data)

        def is_empty(self):
            return self.data is None

        def update_meta(self):
            self.meta = {'model_class': self.data.get_params.im_class}

        def reapply_meta(self):
            self.update_meta()

        # The matching physical operator is in the supernode class
        def transform_col(self, node, col_name):
            supernode = self.generate_super_node([self, node])
            return self.generate_feature_node('transform_col', args={'col_name': col_name}, v_id=supernode.id)

        def transform(self, node):
            supernode = self.generate_super_node([self, node])
            return self.generate_dataset_node('transform', v_id=supernode.id)

    class SuperNode(Node):
        """SuperNode represents a (sorted) collection of other nodes
        Its only purpose is to allow operations that require multiple nodes to fit 
        in our data model
        """

        def __init__(self, id, nodes):
            ExecutionEnvironment.Node.__init__(self, id, None)
            self.nodes = nodes
            self.meta = {'count': len(self.nodes)}

        def update_meta(self):
            self.meta = {'count': len(self.nodes)}

        def reapply_meta(self):
            self.update_meta()

        def p_transform_col(self, col_name):
            return pd.Series(self.nodes[0].data.transform(self.nodes[1].data), name=col_name)

        def p_transform(self):
            return self.nodes[0].data.transform(self.nodes[1].data)

        def p_filter_with(self):
            return self.nodes[0].data[self.nodes[1].data]

        def p_add_column(self, col_name):
            t = self.nodes[0].data
            t[col_name] = self.nodes[1].data
            return t

        def p_corr_with(self):
            return self.nodes[0].data.corr(self.nodes[1].data)

        def p_concat(self):
            ds = []
            for d in self.nodes:
                ds.append(d.data)
            return pd.concat(ds, axis=1)

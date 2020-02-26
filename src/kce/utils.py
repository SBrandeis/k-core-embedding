import time
import networkx as nx
import numpy as np
from copy import deepcopy


def timeit(var_name):
    def wrapper(func):
        def timed_f(self, *args, **kwargs):
            start = time.time()
            res = func(self, *args, **kwargs)
            end = time.time()
            self.times[var_name] = end - start
            return res
        return timed_f
    return wrapper


def preprocess(graph: nx.Graph): # Doing it inplace to reduce memory usage
    selfloop_edges = nx.selfloop_edges(graph)
    graph.remove_edges_from(selfloop_edges)  # Remove self-loops
    isolated_nodes = nx.isolates(graph)
    graph.remove_nodes_from(isolated_nodes)  # Remove orphan nodes
    return isolated_nodes, selfloop_edges

def downstream_specific_preprocessing(graph: nx.Graph, downstream_task_name, **downstream_task_args):
    """
    Simply returns unchanged graph when downstream task is node classification.
    When downstream task is link prediction, first coarsen graph and return edges to consider for training/testing
    """
    if downstream_task_name == "node_classification":
        return graph, {}
    elif downstream_task_name == "link_prediction":
        cut_ratio, test_size = downstream_task_args["cut_ratio"], downstream_task_args["test_size"]

        # Coarsen graph
        # Select edges to cut
        index_cut = np.random.choice(graph.number_of_edges(), size=int(graph.number_of_edges() * cut_ratio),
                                     replace=False)
        edges = np.array(list(graph.edges))
        nb_edges = edges.shape[0]
        non_edges = np.array(list(nx.non_edges(graph)))
        edges_cut = edges[index_cut]

        # Remove those edges from graph
        _graph = deepcopy(graph)
        [_graph.remove_edge(u, v) for u, v in edges_cut] # use TODO: graph.remove_edges_from(list) if faster

        # Create train set : select pairs of nodes not connected
        index_neg = np.random.choice(non_edges.shape[0], size=nb_edges)
        index_train_neg, index_test_neg = index_neg[:-int(nb_edges * test_size)], index_neg[-int(nb_edges * test_size):]
        non_edges_train, non_edges_test = non_edges[index_train_neg], non_edges[index_test_neg]
        index_pos = np.arange(nb_edges)
        np.random.shuffle(index_pos)
        index_train_pos, index_test_pos = index_pos[:-int(nb_edges * test_size)], index_pos[-int(nb_edges * test_size):]
        edges_train, edges_test = edges[index_train_pos], edges[index_test_pos]

        return _graph, {"non_edges_train": non_edges_train, "non_edges_test": non_edges_test,
                       "edges_train": edges_train, "edges_test": edges_test}

def link_pred_train_test_split(embeddings, node2id, non_edges_train, non_edges_test, edges_train, edges_test, **kwargs):

    # Retreive corresponding embedding a create train test sets
    X_neg_train = np.array(
        [np.concatenate((embeddings[node2id[u]], embeddings[node2id[v]])) for u, v
         in non_edges_train])
    X_neg_test = np.array(
        [np.concatenate((embeddings[node2id[u]], embeddings[node2id[v]])) for u, v
         in non_edges_test])
    X_pos_train = np.array(
        [np.concatenate((embeddings[node2id[u]], embeddings[node2id[v]])) for u, v
         in edges_train])
    X_pos_test = np.array(
        [np.concatenate((embeddings[node2id[u]], embeddings[node2id[v]])) for u, v
         in edges_test])
    X_train, X_test = np.concatenate([X_neg_train, X_pos_train]), np.concatenate([X_neg_test, X_pos_test])
    Y_train, Y_test = np.concatenate([np.zeros(X_neg_train.shape[0]), np.ones(X_pos_train.shape[0])]), np.concatenate([np.zeros(X_neg_test.shape[0]), np.ones(X_pos_test.shape[0])])
    return X_train, X_test, Y_train, Y_test


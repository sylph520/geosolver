import re
import itertools
from geosolver.diagram.get_instances import get_all_instances
from geosolver.grounding.states import MatchParse
from geosolver.ontology.ontology_semantics import evaluate
from geosolver.text2.ontology import VariableSignature, signatures, FormulaNode, SetNode, types, is_singular, Node
import numpy as np

__author__ = 'minjoon'

def ground_formula_node(match_parse, formula_node):
    core_parse = match_parse.graph_parse.core_parse
    singular_variable_nodes = _get_singular_variable_nodes(formula_node)
    grounded_node_sets = []
    for node in singular_variable_nodes:
        grounded_node = _ground_leaf(match_parse, node)
        if isinstance(grounded_node, FormulaNode):
            grounded_node_sets.append([grounded_node])
        else:
            grounded_node_sets.append(grounded_node.children)
    scores = []
    combinations = list(itertools.product(*grounded_node_sets))
    final_formulas = []
    for combination in combinations:
        var_dict = {variable_node.signature: combination[idx]
                    for idx, variable_node in enumerate(singular_variable_nodes)}
        grounded_formula = _assign_variables(formula_node, var_dict)
        final_formula = _apply_distribution(grounded_formula)
        final_formulas.append(final_formula)
        if final_formula.has_signature("What"):
            score = 1
        elif isinstance(final_formula, Node):
            score = evaluate(final_formula, core_parse.variable_assignment).conf
        else:
            raise Exception()
        scores.append(score)

    pairs = zip(scores, final_formulas)
    argmax_grounded_formula = max(pairs, key=lambda pair: pair[0])[1]
    return argmax_grounded_formula

def _assign_variables(formula_node, var_dict):
    tester = lambda node: isinstance(node, FormulaNode) and node.is_leaf() and node.signature in var_dict
    getter = lambda node: var_dict[node.signature]
    assert isinstance(formula_node, FormulaNode)
    out_node = formula_node.replace_node(tester, getter)
    return out_node






def _ground_formula_node_helper(match_parse, formula_node):
    if not isinstance(formula_node, FormulaNode) and not isinstance(formula_node, SetNode):
        return formula_node
    elif isinstance(formula_node, FormulaNode) and formula_node.is_leaf():
        if formula_node.signature.id in signatures:
            return formula_node
        return _ground_leaf(match_parse, formula_node, formula_node.return_type)
    elif isinstance(formula_node, FormulaNode):
        children = [_ground_formula_node_helper(match_parse, child) for child in formula_node.children]
        return FormulaNode(formula_node.signature, children)
    elif isinstance(formula_node, SetNode):
        members = [_ground_formula_node_helper(match_parse, member) for member in formula_node.children]
        return SetNode(members)


def _infer_return_type(match_parse, atoms, variable_signature):
    pass

def _get_singular_variable_nodes(formula_node):
    singular_variable_nodes = []
    for each_node in formula_node:
        if isinstance(each_node, FormulaNode) and each_node.is_leaf() and \
                isinstance(each_node.signature, VariableSignature) and is_singular(each_node.signature.return_type):
            singular_variable_nodes.append(each_node)
    return singular_variable_nodes



def _ground_leaf(match_parse, leaf):
    """

    :param match_parse:
    :param leaf:
    :return FormulaNode or SetNode:
    """
    assert isinstance(leaf, FormulaNode)
    assert isinstance(match_parse, MatchParse)
    return_type = leaf.return_type
    graph_parse = match_parse.graph_parse
    variable_signature = leaf.signature

    if variable_signature.id in signatures:
        return leaf
    elif return_type == 'number':
        if re.match("^\d+(\.\d+)?$", variable_signature.name):
            return leaf
        elif len(variable_signature.name) == 1:
            return FormulaNode(variable_signature, [])
        elif len(variable_signature.name) == 2:
            new_leaf = FormulaNode(VariableSignature(leaf.signature.id, "line", name=leaf.signature.name), [])
            return FormulaNode(signatures['LengthOf'], [_ground_leaf(match_parse, new_leaf)])
    elif return_type == 'point':
        if variable_signature.name == 'point':
            points = get_all_instances(graph_parse, 'point', True)
            return SetNode(points.values())
        elif len(variable_signature.name) == 1:
            return match_parse.match_dict[variable_signature.name][0]
    elif return_type == 'line':
        if variable_signature.name == 'line':
            lines = get_all_instances(graph_parse, 'line', True)
            return SetNode(lines.values())
        elif len(variable_signature.name) == 1:
            line = match_parse.match_dict[variable_signature.name][0]
            return line
        elif len(variable_signature.name) == 2:
            label_a, label_b = variable_signature.name
            point_a = match_parse.match_dict[label_a][0]
            point_b = match_parse.match_dict[label_b][0]
            return FormulaNode(signatures['Line'], [point_a, point_b])
    elif return_type == 'lines':
        lines = get_all_instances(graph_parse, 'line', True)
        return SetNode(lines.values())
    elif return_type == 'circle':
        if len(variable_signature.name) == 1:
            center_label = variable_signature.name
            center = match_parse.match_dict[center_label][0]
            center_idx = int(center.signature.name.split("_")[1])
            return graph_parse.circle_dict[center_idx][0]['variable']
            # radius = match_parse.graph_parse.core_parse.radius_variables[center_idx][0]
        elif variable_signature.name == 'circle':
            circles = get_all_instances(graph_parse, 'circle', True)
            return SetNode(circles.values())
        else:
            raise Exception()
    elif return_type == 'angle':
        # TODO :
        if len(variable_signature.name) == 3:
            label_a, label_b, label_c = variable_signature.name
            point_a = match_parse.match_dict[label_a][0]
            point_b = match_parse.match_dict[label_b][0]
            point_c = match_parse.match_dict[label_c][0]
            return FormulaNode(signatures['Angle'], [point_a, point_b, point_c])
        else:
            raise Exception()
    elif return_type == 'triangle':
        if len(variable_signature.name) == 3:
            label_a, label_b, label_c = variable_signature.name
            point_a = match_parse.match_dict[label_a][0]
            point_b = match_parse.match_dict[label_b][0]
            point_c = match_parse.match_dict[label_c][0]
            return FormulaNode(signatures['Triangle'], [point_a, point_b, point_c])
        elif variable_signature.name == 'triangle':
            triangles = get_all_instances(graph_parse, 'triangle', True)
            return SetNode(triangles.values())
    elif return_type == 'triangles':
        triangles = get_all_instances(graph_parse, 'triangle', True)
        return SetNode(triangles.values())
    elif return_type == 'quad':
        if len(variable_signature.name) == 4:
            points = [match_parse.match_dict[label][0] for label in variable_signature.name]
            return FormulaNode(signatures['Quad'], points)
        else:
            quads = get_all_instances(graph_parse, 'quad', True)
            return SetNode(quads.values())
    elif return_type == 'quads':
        quads = get_all_instances(graph_parse, 'quad', True)
        for quad in get_all_instances(graph_parse, 'quad', False).values():
            graph_parse.display_instances([quad])
        return SetNode(quads.values())
    elif return_type == 'hexagon':
        if len(variable_signature.name) == 6:
            points = [match_parse.match_dict[label][0] for label in variable_signature.name]
            return FormulaNode(signatures['Hexagon'], points)
        else:
            quads = get_all_instances(graph_parse, 'hexagon', True)
            return SetNode(quads.values())

    elif return_type == 'polygon':
        points = [match_parse.match_dict[label][0] for label in variable_signature.name]
        return FormulaNode(signatures['Polygon'], points)

    raise Exception(repr(leaf))

def _apply_distribution(node):
    if not isinstance(node, FormulaNode) or len(node.children) == 0:
        return node
    node = FormulaNode(node.signature, [_apply_distribution(child) for child in node.children])
    if len(node.children) == 1:
        child_node = node.children[0]
        if isinstance(child_node, SetNode) and node.signature.arg_types[0][0] != '*':
            children = [FormulaNode(node.signature, [child]) for child in child_node.children]
            return SetNode(children)
    elif len(node.children) == 2:
        a_node, b_node = node.children
        if isinstance(a_node, SetNode) and node.signature.arg_types[0][0] != '*' and isinstance(b_node, SetNode) and node.signature.arg_types[1][0] != '*':
            assert len(a_node.children) == len(b_node.children)
            children = [FormulaNode(node.signature, [a_node.children[index], b_node.children[index]]) for index in range(len(a_node.children))]
            return SetNode(children)
        elif isinstance(a_node, SetNode) and node.signature.arg_types[0][0] != '*' and isinstance(b_node, FormulaNode):
            children = [FormulaNode(node.signature, [child, b_node]) for child in a_node.children]
            return SetNode(children)
        elif isinstance(a_node, FormulaNode) and isinstance(b_node, SetNode) and node.signature.arg_types[1][0] != '*':
            children = [FormulaNode(node.signature, [a_node, child]) for child in b_node.children]
            return SetNode(children)

    return node

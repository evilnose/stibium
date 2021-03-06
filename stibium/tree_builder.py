'''Functions that convert a Lark tree to an Antimony tree with the correct types, as seen in
stibium.ant_types.

Author: Gary Geng
'''


# Helper classes to hold name structures

from typing import Callable, Dict, Optional, Type, TypeVar, Union, cast

from lark.lexer import Token
from lark.tree import Tree

from stibium.ant_types import (Annotation, ArithmeticExpr, Assignment, Atom, DeclModifiers,
                               Declaration, DeclAssignment,
                               DeclItem, ErrorNode, ErrorToken,
                               FileNode, InComp, Keyword, LeafNode, NameMaybeIn,
                               Name, Newline, Number, Operator,
                               Power, Product, Reaction, ReactionName,
                               SimpleStmt, Species, SpeciesList, StringLiteral,
                               Sum, TreeNode, TrunkNode, TypeModifier, VarModifier,
                               VarName)
from stibium.symbols import AbstractScope, BaseScope
from stibium.types import ASTNode, SrcRange, SymbolType, Variability
from stibium.utils import get_tree_range, get_token_range

# Use None to indicate that this node should have exactly one child and should be skilled
TREE_MAP: Dict[str, Type[TreeNode]] = {
    'NAME': Name,
    'NUMBER': Number,
    'NEWLINE': Newline,
    'ERROR_TOKEN': ErrorToken,
    'VAR_MODIFIER': VarModifier,
    'TYPE_MODIFIER': TypeModifier,
    'ESCAPED_STRING': StringLiteral,
    'ANNOT_KEYWORD': Keyword,
    'SEMICOLON': Operator,
    # TODO need to add more operators
    'error_node': ErrorNode,
    'root': FileNode,
    'simple_stmt': SimpleStmt,
    'var_name': VarName,
    'in_comp': InComp,
    'namemaybein': NameMaybeIn,
    'reaction_name': ReactionName,
    'reaction': Reaction,
    'species': Species,
    'species_list': SpeciesList,
    'assignment': Assignment,
    'declaration': Declaration,
    'decl_item': DeclItem,
    'decl_assignment': DeclAssignment,
    'decl_modifiers': DeclModifiers,
    'annotation': Annotation,
    # TODO decl_modifiers need special handling
    'sum': Sum,
    'product': Product,
    'power': Power,
    'atom': Atom,
    # TODO more
}

OPERATORS = {'EQUAL', 'COLON', 'ARROW', 'SEMICOLON', 'LPAR', 'RPAR', 'STAR', 'PLUS', 'MINUS',
             'DOLLAR', 'CIRCUMFLEX', 'COMMA', 'SLASH'}
KEYWORDS = {'ANNOT_KEYWORD', 'IN'}

for name in OPERATORS:
    TREE_MAP[name] = Operator

for name in KEYWORDS:
    TREE_MAP[name] = Keyword


def transform_tree(tree: Optional[Union[Tree, str]]):
    '''Transform the entirely of a Lark tree to our Antimony tree and return it.'''
    if tree is None:
        return None

    if isinstance(tree, str):
        # assert isinstance(tree, Token)
        tree = cast(Token, tree)
        cls = TREE_MAP[tree.type]

        # assert issubclass(cls, LeafNode)
        return cls(get_token_range(tree), tree.value)  # type: ignore
    else:
        cls = TREE_MAP[tree.data]
        # assert issubclass(cls, TrunkNode)

        children = tuple(transform_tree(child) for child in tree.children)

        # special handling for DeclModifiers. For consistency, we always store two children, even
        # if one of them is None.
        if cls is DeclModifiers:
            var_mod = None
            type_mod = None
            for child in children:
                if isinstance(child, VarModifier):
                    var_mod = child
                else:
                    # assert isinstance(child, TypeModifier)
                    child = cast(TypeModifier, child)
                    type_mod = child
            children = (var_mod, type_mod)

        return cls(get_tree_range(tree), children)  # type: ignore


def set_parents(root: TreeNode):
    '''Set the parent pointer of all nodes in the tree. The tree is modified in-place'''
    if isinstance(root, LeafNode):
        return

    assert isinstance(root, TrunkNode)
    for child in root.children:
        if child:
            child.parent = root
            set_parents(child)


def set_leaf_pointers(root: Optional[TreeNode], last: Optional[LeafNode] = None):
    '''Set 'next' and 'prev' of leaf nodes so that all the leaf nodes are linked in order.
    '''
    if root is None:
        return None

    if isinstance(root, LeafNode):
        root.prev = last
        if last:
            last.next = root
        return root

    assert isinstance(root, TrunkNode)

    for child in root.children:
        # If last node is None, then keep the current last
        last = set_leaf_pointers(child, last) or last

    return last

import re
from collections import namedtuple
from typing import Any, List, NamedTuple

from lark import Lark, Tree

from .grammar import grammar
from .utils import squash_prefix

_lark_parser: Lark = Lark(grammar)  # Earley parser


class Parser(object):
    """A parser for the ArchieML language
    """

    _buffer: str
    _last_ref: Any
    _last_key: Any

    _skip: bool

    _depth: List[NamedTuple]
    _val: dict

    SomeList = namedtuple("SomeList", "id")
    ObjectList = namedtuple("ObjectList", "id first_key")
    StringList = namedtuple("StringList", "id")
    FreeformList = namedtuple("FreeformList", "id")

    Namespace = namedtuple("Namespace", "id")

    def __init__(self, *args, **kwargs):
        self._reset()
        super().__init__(*args, **kwargs)

    ### Helper Functions

    def _reset(self):
        self._depth = list()
        self._buffer = ""
        self._val = dict()
        self._last_ref = None
        self._last_key = None
        self._skip = False

    def _clear_buffer(self):
        self._buffer = ""
        self._last_ref = None
        self._last_key = None

    def _get_current_ref(self):
        ref = self._val
        in_freeform = False
        for scope in self._depth:
            if in_freeform:
                ref = ref[-1]
                assert ref.get("type") == scope.id
                ref = ref.get("value")
                in_freeform = False
            else:
                levels = scope.id.split(".")
                for level in levels:
                    if isinstance(ref, list):
                        ref = ref[-1]
                    ref = ref.get(level)
                if isinstance(scope, self.FreeformList):
                    in_freeform = True
        assert ref != None
        return ref

    def _access_or_create(self, key: str, thing):
        loc = None
        if isinstance(thing, dict):
            loc = thing.get(key)
            if loc is None or not isinstance(loc, dict):
                thing[key] = dict()
                loc = thing[key]
        elif isinstance(thing, list):
            if not len(thing):
                thing.append(dict())
            loc = thing[-1]
            loc[key] = dict()
            loc = loc[key]
        return loc

    def _set_value(self, path: List[str], value, replace=True):
        ref = self._get_current_ref()
        for nesting_key in path[:-1]:
            ref = self._access_or_create(nesting_key, ref)
        if isinstance(ref, list):
            if not len(ref):
                ref.append(dict())
            ref = ref[-1]
        if replace:
            ref[path[-1]] = value
        else:
            if not ref.get(path[-1]) or type(value) != type(ref.get(path[-1])):
                ref[path[-1]] = value
        return ref

    def _append_freeform_value(self, value, key="text"):
        ref = self._get_current_ref()
        assert isinstance(ref, list)
        ref.append(dict(type=key, value=value))
        return ref

    def _append_string_value(self, value: str):
        ref = self._get_current_ref()
        assert isinstance(ref, list)
        ref.append(value)
        return ref

    def _is_array_type(self) -> bool:
        return len(self._depth) > 0 and ("List" in type(self._depth[-1]).__name__)

    def _is_freeform_array(self) -> bool:
        return len(self._depth) > 0 and isinstance(self._depth[-1], self.FreeformList)

    ### Handlers

    def _handle_list_item(self, elements):
        value = filter(lambda t: isinstance(t, Tree), elements)
        value_ = "".join(list(value)[0].children)
        rest = "".join(elements[:-1])
        if self._is_array_type():
            if isinstance(self._depth[-1], self.SomeList):
                self._clear_buffer()
                old_list = self._depth.pop()
                self._depth.append(self.StringList(old_list.id))
                ref = self._append_string_value(value_.strip())
                self._last_ref = ref
                self._last_key = 0
                self._buffer += value_

            elif isinstance(self._depth[-1], self.StringList):
                self._clear_buffer()
                ref = self._append_string_value(value_.strip())
                self._last_ref = ref
                self._last_key = len(ref) - 1
                self._buffer += value_
            else:
                self._handle_comment(rest + value_)
        else:
            self._handle_comment(rest + value_)

    def _handle_pair(self, elements):
        important_values = list(filter(lambda t: isinstance(t, Tree), elements))
        key_ = important_values[0].children[0].value
        value_ = "".join(important_values[1].children)
        key_layers = key_.split(".")

        if len(self._depth) == 0 or isinstance(self._depth[-1], self.Namespace):
            self._clear_buffer()
            ref = self._set_value(key_layers, value_.strip())
            self._last_ref = ref
            self._last_key = key_layers[-1]
            self._buffer += value_
        else:
            list_context = self._depth[-1]
            ref = None
            if isinstance(list_context, self.SomeList):
                self._clear_buffer()
                self._depth.pop()
                self._depth.append(self.ObjectList(list_context.id, key_))
                ref = self._set_value(key_layers, value_.strip())
            elif isinstance(list_context, self.ObjectList):
                self._clear_buffer()
                if list_context.first_key == key_:
                    self._get_current_ref().append(dict())
                ref = self._set_value(key_layers, value_.strip())
            elif isinstance(list_context, self.FreeformList):
                self._clear_buffer()
                self._append_freeform_value(value_.strip(), key_)
            elif isinstance(list_context, self.StringList):
                # Flush to buffer
                self._handle_comment(
                    "".join(
                        [
                            "".join(t.children) if isinstance(t, Tree) else t
                            for t in elements
                        ]
                    )
                )

            if isinstance(ref, dict):
                # Rule of thumb - if this ref returns a dict, this can be multiline
                self._last_ref = ref
                self._last_key = key_layers[-1]
                self._buffer += value_
            # raise NotImplementedError()

    def _handle_end_multiline(self, _):
        if self._last_ref is not None and self._last_key is not None:
            self._last_ref[self._last_key] = self._buffer.strip()
            self._clear_buffer()

    def _handle_start_block(self, command):
        key = command.children[0].value
        # squash all prefixing "."s
        key = squash_prefix(".", key)
        key_list = key.split(".")

        self._clear_buffer()

        if key_list[0] == "":
            # blocks with preceding . only works in freeform arrays
            if self._is_freeform_array():
                self._append_freeform_value(dict(), key[1:])
                self._depth.append(self.Namespace(key[1:]))
            pass
        else:
            self._depth = list()
            self._set_value(key_list, dict(), replace=False)
            self._depth.append(self.Namespace(key))

    def _handle_end_block(self, command):
        if not self._depth:
            pass
        else:
            self._depth.pop()

    def _handle_start_array(self, command):
        is_freeform = "+" in command.children[0]
        key = command.children[0]
        if is_freeform:
            key = key.replace("+", "", 1)

        self._clear_buffer()

        key = squash_prefix(".", key)
        key_list = key.split(".")
        if key_list[0] == "":
            proper_key = ".".join(key_list[1:])
            if len(self._depth) > 0:
                current_context = self._depth[-1]
                if isinstance(current_context, self.SomeList):
                    self._set_value(key_list[1:], list())
                    parent_list = self._depth.pop()
                    self._depth.append(self.ObjectList(parent_list.id, proper_key))
                elif isinstance(current_context, self.ObjectList):
                    if current_context.first_key == proper_key:
                        self._get_current_ref().append(dict())
                    self._set_value(key_list[1:], list())
                elif isinstance(current_context, self.FreeformList):
                    self._append_freeform_value(list(), proper_key)
                elif isinstance(current_context, self.Namespace):
                    self._set_value(key_list[1:], list())
                else:  # StringList
                    self._depth.pop()
                    self._set_value(key_list[1:], list())
                if is_freeform:
                    self._depth.append(self.FreeformList(proper_key))
                else:
                    self._depth.append(self.SomeList(proper_key))
            else:
                self._set_value(key_list[1:], list())
                if is_freeform:
                    self._depth.append(self.FreeformList(proper_key))
                else:
                    self._depth.append(self.SomeList(proper_key))
        else:
            # ends this
            self._depth = list()
            self._set_value(key_list, list())
            if is_freeform:
                self._depth.append(self.FreeformList(key))
            else:
                self._depth.append(self.SomeList(key))

    def _handle_end_array(self, command):
        if self._is_array_type():
            self._depth.pop()

    def _handle_skip(self, command):
        self._skip = True
        self._clear_buffer()

    def _handle_end_skip(self, command):
        self._skip = False

    def _handle_comment(self, comment):
        comment_value = ""
        if isinstance(comment, str):
            comment_value = comment
        else:
            comment_value = "".join(comment.children)

        stripped_comment_value = comment_value.strip()

        if stripped_comment_value.startswith("\\"):
            comment_value = comment_value.replace("\\", "", 1)

        if self._is_freeform_array():
            if stripped_comment_value:
                self._append_freeform_value(comment_value.strip())
        else:
            self._buffer += comment_value

    def _handle_ignore(self, _):
        return "Done"

    def _handle_command(self, command):
        fn = {
            "start_block": self._handle_start_block,
            "end_block": self._handle_end_block,
            "end_multiline": self._handle_end_multiline,
            "start_array": self._handle_start_array,
            "end_array": self._handle_end_array,
            "skip": self._handle_skip,
            "end_skip": self._handle_end_skip,
            "ignore": self._handle_ignore,
        }.get(command.data)
        if not fn:
            raise NotImplementedError(command.data)
        if not self._skip or command.data == "end_skip":
            return fn(command)

    def tree_to_dict(self, node: Tree) -> dict:
        assert node.data == "start"
        self._reset()
        for stmt in node.children:
            stmt_ = stmt.children[0]
            if stmt_.data == "pair":
                if not self._skip:
                    self._handle_pair(stmt_.children)
            elif stmt_.data == "command":
                rv = self._handle_command(stmt_.children[0])
                if rv == "Done":
                    break
            elif stmt_.data == "comment":
                if not self._skip:
                    self._handle_comment(stmt_)
            elif stmt_.data == "list_item":
                if not self._skip:
                    self._handle_list_item(stmt_.children)
            else:
                raise NotImplementedError(stmt_.data)
        return self._val

    def parse(self, input_to_parse) -> dict:
        if isinstance(input_to_parse, str):
            tree = _lark_parser.parse(input_to_parse + "\n")
            return self.tree_to_dict(tree)
        else:
            raise NotImplementedError("The parser currently only supports strings!")

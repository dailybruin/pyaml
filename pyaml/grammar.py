grammar = """
start: _INSIGNIFICANT_WS* statement+ _INSIGNIFICANT_WS*

statement: pair
    | list_item
    | command (_INSIGNIFICANT_INLINE_WS+ VALUE* | _INSIGNIFICANT_INLINE_WS*) NEWLINE+
    | comment

!pair.9: WS_INLINE* key WS_INLINE* ":" WS_INLINE* value

list_item: WS_INLINE* STAR WS_INLINE* value

value.9: VALUE WS*

key.9: KEY

command.9: _INSIGNIFICANT_INLINE_WS* (start_block VALUE*
    | end_block VALUE*
    | start_array VALUE*
    | end_array VALUE*
    | skip VALUE*
    | end_skip VALUE*
    | ignore VALUE*
    | end_multiline)

start_block: "{" _INSIGNIFICANT_INLINE_WS* KEY _INSIGNIFICANT_INLINE_WS* "}"
end_block: "{" _INSIGNIFICANT_INLINE_WS* "}"

start_array: "[" _INSIGNIFICANT_INLINE_WS* ARRAYKEY _INSIGNIFICANT_INLINE_WS* "]"
end_array: "[" _INSIGNIFICANT_INLINE_WS* "]"

skip: ":skip"i 
end_skip.3: ":endskip"i

ignore: ":ignore"i

end_multiline.1: ":end"i VALUE*

comment.1: ( ESCAPED
    | NO_COLON 
    | NOT_KEYA
    | NOT_KEYB
    | START_COLON
    | WS_INLINE+ ) WS_INLINE* NEWLINE+

ARRAYKEY.9: /[a-zA-Z0-9_\-\.+]+/
KEY.9: /[a-zA-Z0-9_\-\.]+/
STAR: "*"
_INSIGNIFICANT_WS.10: WS
_INSIGNIFICANT_INLINE_WS.10: WS_INLINE
VALUE.9: /[\S \\t]+/
FREEFORM: "+"
ESCAPED.2: _BACKSLASH VALUE
NO_COLON.1: (WS_INLINE* /[^{\s:*\[][^\s:]*/)+
NOT_KEYA.1: /[a-zA-Z0-9_\-\.]*[^a-zA-Z0-9_\-\. \\t\\n:]+[a-zA-Z0-9_\-\.]*:.*/ //debugging
NOT_KEYB.1: /.*[ \\t]+[^\s]+:.*/ //debugging
START_COLON.1: WS_INLINE* ":" VALUE
_BACKSLASH: /\\\\/

NEWLINE: /[\\r\\n\\f]+/

%import common.WS_INLINE
%import common.WS
"""

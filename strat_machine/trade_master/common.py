import copy
from typing import Any, Collection, Mapping, Union, get_type_hints, Tuple


def _asdict_raw(obj, encode_json=False):
    """
    A re-implementation of `asdict` (based on the original in the `dataclasses`
    source) to support arbitrary Collection and Mapping types.
    """

    if isinstance(obj, Mapping):
        return dict((_asdict(k, encode_json=encode_json),
                     _asdict(v, encode_json=encode_json)) for k, v in
                    obj.items())
    elif isinstance(obj, Collection) and not isinstance(obj, str) \
            and not isinstance(obj, bytes):
        return list(_asdict(v, encode_json=encode_json) for v in obj)
    else:
        return copy.deepcopy(obj)


def _asdict(obj, encode_json=False):
    """
    A re-implementation of `asdict` (based on the original in the `dataclasses`
    source) to support arbitrary Collection and Mapping types.
    """
    map = {}
    for field in obj.__dict__:
        print(field)
        value = getattr(obj, field)
        print(value)
        if isinstance(value, Mapping) or isinstance(value, Collection) or isinstance(value, str):
            map[field] =_asdict_raw(value, encode_json=encode_json)
    return map



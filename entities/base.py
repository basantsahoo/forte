"""
from typing import Any, Dict, List, Optional, Tuple, Type, Union, overload

from haystack.nodes.base import BaseComponent
from haystack.nodes.prompt.invocation_layer import PromptModelInvocationLayer
from haystack.schema import Document, MultiLabel
from haystack.lazy_imports import LazyImport
"""


class BaseEntity:
    name:str


class BaseSignal:
    name: str
    asset: str
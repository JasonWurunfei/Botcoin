"""This module contains the dataclasses used in the botcoin project."""

import re
import json
from abc import ABC
from enum import Enum

from datetime import datetime
from dataclasses import fields, dataclass
from types import NoneType


def is_iso_format(value: str) -> bool:
    """
    Check if a string is in ISO format.
        Example: 2025-05-11T13:02:21.384360-04:00
    """
    iso_format_regex = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}[-+]\d{2}:\d{2}$"
    return re.match(iso_format_regex, value) is not None


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Serializable(ABC):
    """
    Abstract base dataclass for serializable objects.
    """

    def serialize(self) -> dict:
        """
        Convert the object to a JSON-compatible dictionary.
        """
        cached_data = getattr(self, "_serialized_data", None)
        if cached_data is not None:
            return cached_data

        res = {}
        for f in fields(self):
            if f.type == datetime:
                res[f.name] = getattr(self, f.name).isoformat()
                continue

            attr = getattr(self, f.name)
            if isinstance(attr, (str, int, float, bool, NoneType)):
                # If the field is a basic type, use its value
                res[f.name] = attr

            elif issubclass(f.type, Serializable):
                # If the field is a subclass of Serializable, call its serialize method
                res[f.name] = attr.serialize()
            elif isinstance(attr, Enum):
                # If the field is an Enum, use its value
                res[f.name] = attr.value
            elif isinstance(attr, list):
                # If the field is a list, serialize each item in the list
                res[f.name] = [
                    item.serialize() if isinstance(item, Serializable) else item for item in attr
                ]
            elif isinstance(attr, dict):
                # If the field is a dictionary, serialize each value in the dictionary
                res[f.name] = {
                    k: v.serialize() if isinstance(type(v), Serializable) else v
                    for k, v in attr.items()
                }
            else:
                raise TypeError(f"Field {f.name} of type: {f.type} is not serializable. ")

        # Cache the serialized data for future use
        object.__setattr__(self, "_serialized_data", res)

        return res

    @classmethod
    def from_dict(cls, dict_data: dict) -> "Serializable":
        """
        Populate the object from a dictionary representation.
        """
        kwargs = {}
        for k, v in dict_data.items():
            # Check if the value is an ISO formatted datetime string
            if isinstance(v, str) and is_iso_format(v):
                # Convert ISO formatted string to datetime object
                kwargs[k] = datetime.fromisoformat(v)
            else:
                kwargs[k] = v
        return cls(**kwargs)


def is_serializable(type_: type) -> bool:
    """
    Check if a class is the subclass of Serializable.
    """
    return issubclass(type_, Serializable)


class JSONSerializable(Serializable, ABC):
    """
    Abstract base class for serializable objects.
    """

    def to_json(self) -> str:
        """
        Convert the object to a JSON string representation.
        """
        return json.dumps(self.serialize())

    @classmethod
    def from_json(cls, json_str: str) -> "JSONSerializable":
        """
        Populate the object from a JSON string representation.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

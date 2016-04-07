#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function, absolute_import

import logging

from django.db.models.fields.related import ForeignObject

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class CompositeForeignKey(ForeignObject):
    def __init__(self, to, **kwargs):
        """
        create the ForeignObject, but use the to_fields as a dict which will later used as form_fields and to_fields
        """
        to_fields = kwargs["to_fields"]
        self._raw_fields = self.compute_to_fields(to_fields)
        kwargs["to_fields"], kwargs["from_fields"] = zip(*(
            (k, v.value)
            for k, v in self._raw_fields.items()
            if v.is_local_field
        ))

        super(CompositeForeignKey, self).__init__(to, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(CompositeForeignKey, self).deconstruct()
        del kwargs["from_fields"]
        kwargs["to_fields"] = self._raw_fields
        return name, path, args, kwargs

    def get_extra_descriptor_filter(self, instance):
        return {
            k: v.value for k, v in self._raw_fields.items()
            if isinstance(v, RawFieldValue)
            }


    @property
    def foreign_related_fields(self):
        try:
            remote_model = self.remote_field.model
        except AttributeError:
            remote_model = self.rel.to
        return tuple(
            remote_model._meta.get_field(rhs_field)
            for rhs_field in self._raw_fields.keys()
        )

    def compute_to_fields(self, to_fields):
        """
        compute the to_fields parameterse to make it uniformly a dict of CompositePart
        :return: the well formated to_field containing only subclasses of CompositePart
        :rtype: dict[str, CompositePart]
        """
        return {
            k: (v if isinstance(v, CompositePart) else LocalFieldValue(v))
            for k, v in to_fields.items()
            }

    def db_type(self, connection):
        # A ManyToManyField is not represented by a single column,
        # so return None.
        return None

    def db_parameters(self, connection):
        return {"type": None, "check": None}


class CompositePart(object):
    is_local_field = True

    def __init__(self, value):
        self.value = value

    def deconstruct(self):
        module_name = self.__module__
        name = self.__class__.__name__
        return (
            '%s.%s' % (module_name, name),
            (self.value,),
            {}
        )


class RawFieldValue(CompositePart):
    """
    represent a raw value for  a field.
    """
    is_local_field = False


class LocalFieldValue(CompositePart):
    """
    implicitly used, represent the value of a local field
    """
    is_local_field = True

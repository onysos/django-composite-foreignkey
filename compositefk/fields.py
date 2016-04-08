#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function, absolute_import

import logging
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields.related import ForeignObject

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class CompositeForeignKey(ForeignObject):
    requires_unique_target = False
    def __init__(self, to, **kwargs):
        """
        create the ForeignObject, but use the to_fields as a dict which will later used as form_fields and to_fields
        """
        to_fields = kwargs["to_fields"]
        self.null_if_equal = kwargs.pop("null_if_equal", [])
        # a list of tuple : (fieldnaem, value) . if fielname = value, then the field react as if fieldnaem_id = None
        self._raw_fields = self.compute_to_fields(to_fields)

        kwargs["to_fields"], kwargs["from_fields"] = zip(*(
            (k, v.value)
            for k, v in self._raw_fields.items()
            if v.is_local_field
        ))
        super(CompositeForeignKey, self).__init__(to, **kwargs)

    def check(self, **kwargs):
        errors = super(CompositeForeignKey, self).check(**kwargs)
        errors.extend(self._check_null_with_nullifequal())
        errors.extend(self._check_nullifequal_fields_exists())
        errors.extend(self._check_to_fields_local_valide())
        errors.extend(self._check_to_fields_remote_valide())
        return errors

    def _check_to_fields_local_valide(self):
        res = []
        for local_field in self._raw_fields.values():
            if isinstance(local_field, LocalFieldValue):
                try:
                    self.model._meta.get_field(local_field.value)
                except FieldDoesNotExist:
                    res.append(
                        checks.Error(
                            "the field %s does not exists on the model %s" % (local_field, self.model),
                            hint=None,
                            obj=self,
                            id='compositefk.E003',
                        )
                    )
        return res

    def _check_to_fields_remote_valide(self):
        res = []
        for remote_field in self._raw_fields.keys():
            try:
                self.related_model._meta.get_field(remote_field)
            except FieldDoesNotExist:
                res.append(
                    checks.Error(
                        "the field %s does not exists on the model %s" % (remote_field, self.model),
                        hint=None,
                        obj=self,
                        id='compositefk.E004',
                    )
                )
        return res


    def _check_null_with_nullifequal(self):
        if self.null_if_equal and not self.null:
            return [
                checks.Error(
                    "you must set null=True to field %s.%s if null_if_equal is given" % (self.model.__class__.__name__, self.name),
                    hint=None,
                    obj=self,
                    id='compositefk.E001',
                )
            ]
        return []

    def _check_nullifequal_fields_exists(self):
        res = []
        for field_name, value in self.null_if_equal:
            try:
                self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                res.append(
                    checks.Error(
                        "the field %s does not exists on the model %s" % (field_name, self.model),
                        hint=None,
                        obj=self,
                        id='compositefk.E002',
                    )
                )
        return res

    def deconstruct(self):
        name, path, args, kwargs = super(CompositeForeignKey, self).deconstruct()
        del kwargs["from_fields"]
        kwargs["to_fields"] = self._raw_fields
        kwargs["null_if_equal"] = self.null_if_equal
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
        # A CompositeForeignKey don't have a column in the database
        # so return None.
        return None

    def db_parameters(self, connection):
        return {"type": None, "check": None}

    def get_instance_value_for_fields(self, instance, fields):
        # we override this method to provide the feathur of converting
        # some special values of teh composite local fields into a
        # None pointing field.
        # ie, if company is '   ' and it mean that the current field
        # point to nothing (as if it was None) => we transform this
        # '   ' into a true None to let django das as if it was None
        res = super(CompositeForeignKey, self).get_instance_value_for_fields(instance, fields)
        if self.null_if_equal:
            cur_values_dict = dict(zip((f.name for f in fields), res))
            for field_name, exception_value in self.null_if_equal:
                # check framework check if all fields exists
                if cur_values_dict[field_name] == exception_value:
                    # we have field_name that is equal to the bad value
                    return (None,) # currently, it is enouth since the django implementation check at first if there is a None in the result
        return res

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

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.value)


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

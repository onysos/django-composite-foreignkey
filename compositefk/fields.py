#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function, absolute_import
from django.db.models import signals, Q

import logging
from django.core import checks
from django.db.models.fields import FieldDoesNotExist

from django.db.models.fields.related import ForeignKey, ForeignObject
from django.db.models.fields.reverse_related import ManyToOneRel, ForeignObjectRel
from django.utils import six
from django.utils.deconstruct import deconstructible
from django.utils.six import python_2_unicode_compatible

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class CompositeRelatedObject(object):
    """
    a ForeignKey that allow to link a model using multiple column of both models.
    """
    # Field flags
    auto_created = False
    concrete = False
    editable = False
    hidden = False
    primary_key = False

    is_relation = True
    many_to_many = True
    many_to_one = False
    one_to_many = False
    one_to_one = False
    related_model = None
    remote_field = None
    db_index = False

    rel_class = ForeignObjectRel

    def __init__(self, to, to_fields, related_name=None, related_query_name=None,
                 limit_choices_to=None, parent_link=False, on_delete=None):
        """
        create the field pointing to `to` model and linking it with `to_fields` dict
        :param django.db.models.Model to: the remote Model
        :param dict[str,  str|CompositePart] to_fields: the dict giving the columns corespondances.
            will be of the form : remote_field: local_field. with local_field (aka value of the dict) can be of different types :

            - str : will get the value from the local field
            - LocalFieldValue : idem as str (behind the scene, str is transformed into LocalFieldValue)
            - RawFieldValue : dont't use local value, will make the query filtering the remote field = the given value

        """
        if not isinstance(to_fields, dict):
            raise TypeError(
                'to_fields should be a dict[remote_field_name, local_field_name | RawFieldValue("Rawvalue")]')
        self.name = None
        self.to = to
        self.to_fields = self.compute_to_fields(to_fields)
        self.editable = False
        self.column = None
        self.remote_field = self.rel_class(
            self, to,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            parent_link=parent_link,
            on_delete=on_delete,
        )

    def deconstruct(self):
        return (
            self.name,
            self.__module__,
            tuple(),
            {
                "to": self.to,
                "to_fields": self.to_fields
            }
        )

    def clone(self):
        """
        Uses deconstruct() to clone a new copy of this Field.
        Will not preserve any class attachments/attribute names.
        """
        name, path, args, kwargs = self.deconstruct()
        return self.__class__(*args, **kwargs)

    def _get_local_fields(self):
        """
        return the list of local only field (skipping all no local field (Raw)
        :rtype: dict[str, CompositePart]
        """
        return {k: v for k,v in self.to_fields if v.is_local_field}

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

    def contribute_to_class(self, cls, name, **kwargs):
        self.name = name
        self.attname = name
        self.model = cls
        self.cache_attr = "_%s_cache" % name
        cls._meta.add_field(self, virtual=True)

        # Only run pre-initialization field assignment on non-abstract models
        if not cls._meta.abstract:
            signals.pre_init.connect(self.instance_pre_init, sender=cls)

        setattr(cls, name, self)

    def get_value_for(self, fieldValue, instance):
        """
        compute the fieldValue attr to get back either the local value, or the raw value if fieldValue is a RawFieldValue
        :param CompositePart fieldValue: the field value given in the to_fields attribute
        """
        return fieldValue.get_from(instance)

    def get_remote_queryset(self, obj):
        params = {
            remote_fname: self.get_value_for(local_fname, obj)
            for remote_fname, local_fname in self.to_fields.items()
        }
        return self.to._default_manager.filter(**params)

    def get_forward_related_filter(self, obj):
        """
        Return the keyword arguments that when supplied to
        self.model.object.filter(), would select all instances related through
        this field to the remote obj. This is used to build the querysets
        returned by related descriptors. obj is an instance of
        self.to
        """
        return {
            "%s__%s" % (self.name, remote_fname): self.get_value_for(local_fname, obj)
            for remote_fname, local_fname in self.to_fields
        }

    def get_filter_kwargs_for_object(self, obj):
        """
        Return a dict that when passed as kwargs to self.model.filter(), would
        yield all instances having the same value for this field as obj has.
        """
        return {
            local_fname.value: local_fname.get_from(obj)
            for local_fname in self.to_fields.values()
            if local_fname.is_local_field
        }

    def __str__(self):
        model = self.model
        app = model._meta.app_label
        return '%s.%s.%s' % (app, model._meta.object_name, self.name)

    def check(self, **kwargs):
        errors = []
        errors.extend(self._check_field_name())
        errors.extend(self._check_local_fields())
        errors.extend(self._check_remote_fields())
        return errors

    def _check_field_name(self):
        if self.name.endswith("_"):
            return [
                checks.Error(
                    'Field names must not end with an underscore.',
                    hint=None,
                    obj=self,
                    id='fields.E001',
                )
            ]
        else:
            return []

    def _check_local_fields(self):
        local_field = None
        try:
            for local_field in self.to_fields.values():
                local_field.get_field(self.model)
        except FieldDoesNotExist:
            return [
                checks.Error(
                    "The CompositeRelatedObject %s references the non-existent field '%s'." % (self.name, local_field),
                    hint=None,
                    obj=self,
                    id='compositefk.E001',
                )
            ]
        else:
            return []

    def _check_remote_fields(self):
        """
        Check if field named `field_name` in model `model` exists and is a
        valid content_type field (is a ForeignKey to ContentType).
        """
        remote = None
        try:
            for remote in self.to_fields.keys():
                self.to._meta.get_field(remote)
        except FieldDoesNotExist:
            return [
                checks.Error(
                    "The CompositeRelatedObject %s references the non-existent field '%s.%s'." % (
                        self.name, self.to, remote
                    ),
                    hint=None,
                    obj=self,
                    id='compositefk.E002',
                )
            ]
        return []

    def instance_pre_init(self, signal, sender, args, kwargs, **_kwargs):
        """
        Handle initializing an object with the generic FK instead of
        content_type and object_id fields.
        """
        if self.name in kwargs:
            value = kwargs.pop(self.name)
            if value is not None:
                for remote_f, local_f in self._get_local_fields().items():
                    kwargs[local_f.value] = getattr(value, self.to._meta.get_field(remote_f).get_attname())
            else:
                for local_f in self._get_local_fields().values():
                    kwargs[local_f.value] = None

    def get_prefetch_queryset(self, instances, queryset=None):
        raise NotImplementedError()
        if queryset is not None:
            raise ValueError("Custom queryset can't be used for this lookup.")

        # For efficiency, group the instances by content type and then do one
        # query per model
        fk_dict = defaultdict(set)
        # We need one instance for each group in order to get the right db:
        instance_dict = {}
        ct_attname = self.model._meta.get_field(self.ct_field).get_attname()
        for instance in instances:
            # We avoid looking for values if either ct_id or fkey value is None
            ct_id = getattr(instance, ct_attname)
            if ct_id is not None:
                fk_val = getattr(instance, self.fk_field)
                if fk_val is not None:
                    fk_dict[ct_id].add(fk_val)
                    instance_dict[ct_id] = instance

        ret_val = []
        for ct_id, fkeys in fk_dict.items():
            instance = instance_dict[ct_id]
            ct = self.get_content_type(id=ct_id, using=instance._state.db)
            ret_val.extend(ct.get_all_objects_for_this_type(pk__in=fkeys))

        # For doing the join in Python, we have to match both the FK val and the
        # content type, so we use a callable that returns a (fk, class) pair.
        def gfk_key(obj):
            ct_id = getattr(obj, ct_attname)
            if ct_id is None:
                return None
            else:
                model = self.get_content_type(id=ct_id,
                                              using=obj._state.db).model_class()
                return (model._meta.pk.get_prep_value(getattr(obj, self.fk_field)),
                        model)

        return (ret_val,
                lambda obj: (obj._get_pk_val(), obj.__class__),
                gfk_key,
                True,
                self.cache_attr)

    def is_cached(self, instance):
        return hasattr(instance, self.cache_attr)

    def db_type(self, connection):
        # A ManyToManyField is not represented by a single column,
        # so return None.
        return None

    def db_parameters(self, connection):
        return {"type": None, "check": None}


class CompositeForeignKey(CompositeRelatedObject):
    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        try:
            return getattr(instance, self.cache_attr)
        except AttributeError:
            rel_obj = None
            rel_obj = self.get_remote_queryset(instance).get()
            setattr(instance, self.cache_attr, rel_obj)
            return rel_obj

    def __set__(self, instance, value):
        ct = None
        fk = None
        if value is not None:
            for remote, local in self.to_fields.items():
                attr_name = self.to._meta.get_field(remote).get_attname()
                local.set_to(instance, getattr(value, attr_name))
        setattr(instance, self.cache_attr, value)


class CompositePart(object):
    is_local_field = True
    def __init__(self, value):
        self.value = value

    def deconstruct(self):
        module_name = self.__module__
        name = self.__class__.__name__
        return (
            '%s.%s' % (self.__class__.__module__, name),
            (self.value,),
            {}
        )

    def __str__(self):
        return self.value

    def get_from(self, instance):
        """
        get the final value from instance
        """
        raise NotImplementedError()

    def get_field(self, model):
        return model._meta.get_field(self.value)

    def set_to(self, instance, value):
        """
        set the given value to the local field if it mean somthing.
        :param instance: the current instance which we should update
        :param value: the value to set
        """
        raise NotImplementedError()


class RawFieldValue(CompositePart):
    """
    represent a raw value for  a field.
    """
    is_local_field = False

    def get_from(self, instance):
        return self.value

    def get_field(self, model):
        return None

    def set_to(self, instance, value):
        pass # do nothing since value is not for us


class LocalFieldValue(CompositePart):
    """
    implicitly used, represent the value of a local field
    """
    is_local_field = True


    def get_from(self, instance):
        return getattr(instance, self.value)


    def set_to(self, instance, value):
        setattr(instance, self.value, value)
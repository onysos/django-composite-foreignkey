#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import
import logging

try:
    from django.db.models.fields.related_descriptors import ReverseOneToOneDescriptor
except ImportError:
    from django.db.models.fields.related import SingleRelatedObjectDescriptor as ReverseOneToOneDescriptor

from django.db.models.fields.related import SingleRelatedObjectDescriptor as ReverseOneToOneDescriptor, ReverseSingleRelatedObjectDescriptor

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class CompositeReverseOneToOneDescriptor(ReverseOneToOneDescriptor):

    def __set__(self, instance, value):
        super(CompositeReverseOneToOneDescriptor, self).__set__(instance, value)

        if value is None:

            for lh_field_name, rh_field_name in self.field.get_extra_related_attributes_fields():
                setattr(instance, lh_field_name, None)

        # Set the values of the related field.
        else:
            for lh_field_name, rh_field_name in self.field.get_extra_related_attributes_fields():
                setattr(instance, lh_field_name, getattr(value, rh_field_name))


class CompositeReverseSingleRelatedObjectDescriptor(ReverseSingleRelatedObjectDescriptor):
    def __set__(self, instance, value):
        super(CompositeReverseSingleRelatedObjectDescriptor, self).__set__(instance, value)

        if value is None:
            for lh_field_name, rh_field_name in self.field.get_extra_attributes_fields():
                setattr(instance, lh_field_name, None)

        # Set the values of the related field.
        else:
            for lh_field_name, rh_field_name in self.field.get_extra_attributes_fields():
                setattr(instance, lh_field_name, getattr(value, rh_field_name))
        if value is not None and not self.field.rel.multiple:
            for lh_field_name, rh_field_name in self.field.get_extra_related_attributes_fields():
                setattr(value, lh_field_name, getattr(instance, rh_field_name))


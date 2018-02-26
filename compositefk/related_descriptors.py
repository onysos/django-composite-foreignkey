#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import
import logging

from compositefk.compat import (
    get_remote_field,
    set_cached_value_by_descriptor,
    set_cached_value_by_field,
    get_cached_value,
)

try:
    from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
except ImportError:
    from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor as ForwardManyToOneDescriptor

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class CompositeForwardManyToOneDescriptor(ForwardManyToOneDescriptor):
    def __set__(self, instance, value):
        if value is not None or not self.field.nullable_fields:
            super(CompositeForwardManyToOneDescriptor, self).__set__(instance, value)
        else:
            # we set only the asked fields to None, not all field as the default ForwardManyToOneDescriptor will

            # ### taken from original ForwardManyToOneDescriptor
            # Look up the previously-related object, which may still be available
            # since we've not yet cleared out the related field.
            # Use the cache directly, instead of the accessor; if we haven't
            # populated the cache, then we don't care - we're only accessing
            # the object to invalidate the accessor cache, so there's no
            # need to populate the cache just to expire it again.
            related = get_cached_value(instance, self, None)

            # If we've got an old related object, we need to clear out its
            # cache. This cache also might not exist if the related object
            # hasn't been accessed yet.
            if related is not None:
                related_field = get_remote_field(self.field)
                set_cached_value_by_field(related, related_field, None)

            # ##### only original part
            for lh_field_name, none_value in self.field.nullable_fields.items():
                setattr(instance, lh_field_name, none_value)

            # Set the related instance cache used by __get__ to avoid a SQL query
            # when accessing the attribute we just set.
            set_cached_value_by_descriptor(instance, self, None)

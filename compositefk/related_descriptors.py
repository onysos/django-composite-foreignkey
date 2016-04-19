#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import
import logging

from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor

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
            related = getattr(instance, self.cache_name, None)

            # If we've got an old related object, we need to clear out its
            # cache. This cache also might not exist if the related object
            # hasn't been accessed yet.
            if related is not None:
                setattr(related, self.field.remote_field.get_cache_name(), None)

            # ##### only original part

            for lh_field_name in self.field.nullable_fields:
                setattr(instance, lh_field_name, None)


            # Set the related instance cache used by __get__ to avoid a SQL query
            # when accessing the attribute we just set.
            setattr(instance, self.cache_name, value)

            # If this is a one-to-one relation, set the reverse accessor cache on
            # the related object to the current instance to avoid an extra SQL
            # query if it's accessed later on.
            if value is not None and not self.field.remote_field.multiple:
                setattr(value, self.field.remote_field.get_cache_name(), instance)
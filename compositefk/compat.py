import django


def get_remote_field(field):
    if django.VERSION < (1, 9):
        return field.rel
    else:
        return field.remote_field


def get_cached_value(instance, descriptor, default=None):
    if django.VERSION < (2, 0):
        return getattr(instance, descriptor.cache_name, default)
    else:
        return descriptor.field.get_cached_value(instance, default=default)


def set_cached_value_by_descriptor(instance, descriptor, value):
    if django.VERSION < (2, 0):
        setattr(instance, descriptor.cache_name, value)
    else:
        descriptor.field.set_cached_value(instance, value)


def set_cached_value_by_field(instance, field, value):
    if django.VERSION < (2, 0):
        setattr(instance, field.get_cache_name(), value)
    else:
        field.set_cached_value(instance, value)
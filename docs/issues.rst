known issues
============

since this fields use multiple fields as identifier, we don't have a field like `fieldname_id` like normal ForeignKey.
some libs assert this sort of field exists and sometimes, we can't tel them otherwise. so you mill need to hack a little some part
of your code to make sur your fields is well treated.




Django Rest Framework
---------------------


version
^^^^^^^
tested on django 1.8 and rest_framework 3.2.4

error
^^^^^


`TypeError: <MyModel: XXXXXXX> is not JSON serializable`

explication
^^^^^^^^^^^

the serializer will try to get the pk of the CompositeForeignKey. for a normal FK, it will git the `fieldname_id`, but for us, it is impossible.

fix
^^^

the best way of fixing this is to override the models `serializable_value`

from :

.. code:: python

    def serializable_value(self, field_name):
        """
        Returns the value of the field name for this instance. If the field is
        a foreign key, returns the id value, instead of the object. If there's
        no Field object with this name on the model, the model attribute's
        value is returned directly.

        Used to serialize a field's value (in the serializer, or form output,
        for example). Normally, you would just access the attribute directly
        and not use this method.
        """
        try:
            field = self._meta.get_field(field_name)
        except FieldDoesNotExist:
            return getattr(self, field_name)
        return getattr(self, field.attname)

to :

.. code:: python

    def serializable_value(self, field_name):
        try:
            field = self._meta.get_field(field_name)
        except FieldDoesNotExist:
            return getattr(self, field_name)
        if isinstance(field, CompositeForeignKey):
            return getattr(self, field.attname).pk
        return getattr(self, field.attname)


this will just, in case of a CompositeForeignKey, get the related model pk instead of falsly returning the original model.
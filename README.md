# django-composite-foreignkey



allow to create a django foreignkey that don't link with pk of other model, but with multi column matching local model columns or fixed values.


.. image:: https://img.shields.io/travis/onysos/django-composite-foreignkey/master.svg
    :target: https://travis-ci.org/onysos/django-composite-foreignkey

.. image:: https://img.shields.io/coveralls/onysos/django-composite-foreignkey/master.svg
  :target: https://coveralls.io/r/onysos/django-composite-foreignkey?branch=master

.. image:: https://img.shields.io/pypi/v/django-composite-foreignkey.svg
    :target: https://pypi.python.org/pypi/django-composite-foreignkey
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/django-composite-foreignkey.svg
    :target: https://pypi.python.org/pypi/django-composite-foreignkey
    :alt: Number of PyPI downloads per month

some databases have a composite Primary Key, leading to impossiblity for a django foreign key to be used.

today, Django don't support Composite Primary Key ([see ticket](https://code.djangoproject.com/wiki/MultipleColumnPrimaryKeys)) and thus don't support composite foreignkey.

this implementation of CompositeForeignKey skip the complexity of Composite Primary Key by forcing the providing of the corresponding column of the other model, not forcefully a PrimaryKey.

Installation
------------

1. Install using pip:

   ``pip install django-composite-foreignkey``

   Alternatively, you can install download or clone this repo and call ``pip install -e .``.

3. In your models, set up all your real field, then add a `virtual` one giving the foreignkey
```
customer = CompositeForeignKey(Customer, fields={"customer_code": "customer_id", "company_code": "company"})
```


Example template
----------------


you have this model :

.. code: python

    class Customer(models.Model):

        company = models.IntegerField()
        customer_id = models.IntegerField()
        name = models.CharField(max_length=255)

        class Meta:
            unique_togeteh = [
                ("company", "customer_id"),
            ]

    class Contact(models.Model):
        company_code = models.IntegerField()
        customer_code = models.IntegerField()
        surname = models.CharField(max_length=255)

        # virtual field
        customer = CompositeForeignKey(Customer, fields={"customer_code": "customer_id", "company_code": "company"})


you can use Contact.customer like any ForeignKey, but behinde the scene, it will query the Customer Table using company and customer id's.


Documentation
-------------

This readme provide the main doc : an working exemple and a demo app


Requirements
------------

- Python 2.7, 3.2, 3.3, 3.4
- Django >= 1.8

Contributions and pull requests for other Django and Python versions are welcome.


Bugs and requests
-----------------

If you have found a bug or if you have a request for additional functionality, please use the issue tracker on GitHub.

https://github.com/onysos/django-composite-foreignkey/issues


License
-------

You can use this under GPLv3. See `LICENSE
<LICENSE>`_ file for details.


Author
------

Original author & Development lead: `Darius BERNARD <https://github.com/ornoone>`_.


Thanks
------

Thanks to django for this amazing framework. And thanks to django-composite-foreignkey to the structure of the apps.
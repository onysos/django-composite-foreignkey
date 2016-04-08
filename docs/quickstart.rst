==========
Quickstart
==========

After :doc:`installation`, you can use ``django-composite-foreignkey`` in your models.:

Example simple composite ForeignKey models
------------------------------------------

.. code:: python

    class Customer(models.Model):

        company = models.IntegerField()
        customer_id = models.IntegerField()
        name = models.CharField(max_length=255)

        class Meta(object):
            unique_together = [
                ("company", "customer_id"),
            ]



    class Contact(models.Model):
        company_code = models.IntegerField()
        customer_code = models.IntegerField()
        surname = models.CharField(max_length=255)
        # virtual field
        customer = CompositeForeignKey(Customer, on_delete=CASCADE, related_name='contacts', to_fields={
            "customer_id": "customer_code",
            "company": "company_code"
        })

these 2 models is linked by a CompositeForeignKey on Contact.customer. there is no `customer_id` field, but it use
instead the shared fields company and customer_id. CompositeForeignKey support a advanced mapping which allow the fields
from both models to no beeing named identicaly.

in the prevous exemple, the folowing fields is linked :

+---------------+-----------------+
| Contact       | Customer        |
+===============+=================+
| company_code  | company         |
+---------------+-----------------+
| customer_code | company_code    |
+---------------+-----------------+

where a «normal» ForeignKey shoud be :

+---------------+-----------------+
| Contact       | Customer        |
+===============+=================+
| customer_id   | pk              |
+---------------+-----------------+


Example advanced composite ForeignKey models
--------------------------------------------



.. code:: python

    class Address(models.Model):
        company = models.IntegerField()
        tiers_id = models.IntegerField()
        type_tiers = models.CharField(max_length=1, choices=[("C", "Customer"), ("S", "supplier")])
        city = models.CharField(max_length=255)
        postcode = models.CharField(max_length=32)

        class Meta(object):
            unique_together = [
                ("company", "tiers_id", "type_tiers"),
            ]


    class Customer(models.Model):

        company = models.IntegerField()
        customer_id = models.IntegerField()
        name = models.CharField(max_length=255)
        address = CompositeForeignKey(Address, on_delete=CASCADE, to_fields={
            "tiers_id": "customer_id",
            "company": "company",
            "type_tiers": RawFieldValue("C")
        })

    class Supplier(models.Model):

        company = models.IntegerField()
        supplier_id = models.IntegerField()
        name = models.CharField(max_length=255)
        address = CompositeForeignKey(Address, on_delete=CASCADE, to_fields={
            "tiers_id": "supplier_id",
            "company": "company",
            "type_tiers": RawFieldValue("S")
        })


in this exemple, the Address Model can be used by either Supplier OR Customer.
the linked fields is for Customer :

+--------------------+-----------------+
| Customer           | Address         |
+====================+=================+
| company            | company         |
+--------------------+-----------------+
| customer_id        | customer_id     |
+--------------------+-----------------+
| RawFieldValue("C") | type_tiers      |
+--------------------+-----------------+

The model Address have a field named «type_tiers» that allow to dinstinguish if the «tiers_id» is for a Supplier or a
Customer. si the Customer model will always have an address with «S» in the «type_tiers» field. so be it via the
`RawFieldValue` which tel exactly that : don't search on the table, the value is always «C».

for convenience, a oposit version of `RawFieldValue` exists and mean «search on the table field X».
it is `LocalFieldValue("X")`.

so the class Supplier could be wrote:

.. code:: python

    class Supplier(models.Model):

        company = models.IntegerField()
        supplier_id = models.IntegerField()
        name = models.CharField(max_length=255)
        address = CompositeForeignKey(Address, on_delete=CASCADE, to_fields={
            "tiers_id": LocalFieldValue("supplier_id"),
            "company": LocalFieldValue("company"),
            "type_tiers": RawFieldValue("S")
        })


Treate specific values as None
------------------------------

sometimes, some database is broken and some values should be treated as None to make sur
no query will be made. ie if company code is «-1» instead of None, the query shall not seach for related model
with company = -1 since this is an old aplicative exception.

you just have one thing to do that : null_if_equal

.. code:: python

    class Customer(models.Model):

        company = models.IntegerField()
        customer_id = models.IntegerField()
        name = models.CharField(max_length=255)
        address = CompositeForeignKey(Address, on_delete=CASCADE, null=True, to_fields={
            "tiers_id": "customer_id",
            "company": LocalFieldValue("company"),
            "type_tiers": RawFieldValue("C")
        }, null_if_equal=[ # if either of the fields company or customer is -1, ther can't have address
            ("company", -1),
            ("customer_id", -1 )
        ])

in this exemple, if company is -1, OR customer_id is -1 too, no query will be made and custome.address will be equal to None.
it is the same behavior as if a normal foreignkey address had address_id = None.

.. note::

    you must allow null value to permit that (which will not have any impact on database).

.. note::

    these cases should not be possible on database that use ForeignKey constraint. but with some legacy database that won't,
    this feathure is mandatory to bypass the headarch comming with broken logic on special values.


Test application
----------------

The test application provides a number of useful examples.

https://github.com/onysos/django-composite-foreignkey/tree/master/testapp/


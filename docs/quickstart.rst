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


Test application
----------------

The test application provides a number of useful examples.

https://github.com/onysos/django-composite-foreignkey/tree/master/testapp/


#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import

import logging

import django.db.models as models
from django.db.models.deletion import CASCADE

from compositefk.fields import CompositeForeignKey, RawFieldValue, LocalFieldValue, CompositeOneToOneField

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


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
    address = CompositeForeignKey(Address, on_delete=CASCADE, null=True, to_fields={
        "tiers_id": "customer_id",
        "company": LocalFieldValue("company"),
        "type_tiers": RawFieldValue("C")
    }, null_if_equal=[  # if either of the fields company or customer is -1, ther can't have address
        ("company", -1),
        ("customer_id", -1)
    ])

    class Meta(object):
        unique_together = [
            ("company", "customer_id"),
        ]


class Supplier(models.Model):
    company = models.IntegerField()
    supplier_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address = CompositeForeignKey(Address, on_delete=CASCADE, to_fields={
        "tiers_id": "supplier_id",
        "company": LocalFieldValue("company"),
        "type_tiers": RawFieldValue("S")
    })

    class Meta(object):
        unique_together = [
            ("company", "supplier_id"),
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


class Extra(models.Model):
    """
    some wrongly analysed table that add extra column to existing one (not a django way of life)

    """
    company = models.IntegerField()
    customer_id = models.IntegerField()
    sales_revenue = models.FloatField()
    customer = CompositeOneToOneField(
        Customer,
        on_delete=CASCADE,
        related_name='extra',
        to_fields={"company", "customer_id"})


class AModel(models.Model):
    n = models.CharField(max_length=32)

class BModel(models.Model):
    a = models.ForeignKey(AModel, null=True, on_delete=CASCADE)

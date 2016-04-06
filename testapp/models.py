#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import

import logging

import django.db.models as models

from compositefk.fields import CompositeForeignKey, RawFieldValue, LocalFieldValue

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class Address(models.Model):
    company = models.IntegerField()
    tiers_id = models.IntegerField()
    type_tiers = models.CharField(max_length=1, choices=[("C", "Customer"), ("S", "supplier")])
    city = models.CharField(max_length=255)
    postcode = models.CharField(max_length=32)

class Customer(models.Model):

    company = models.IntegerField()
    customer_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address = CompositeForeignKey(Address, to_fields={"tiers_id": "customer_id", "company": LocalFieldValue("company"), "type_tiers": RawFieldValue("C")})

    class Meta:
        unique_together = [
            ("company", "customer_id"),
        ]


class Supplier(models.Model):

    company = models.IntegerField()
    supplier_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address = CompositeForeignKey(Address, to_fields={"tiers_id": "supplier_id", "company": LocalFieldValue("company"), "type_tiers": RawFieldValue("S")})

    class Meta:
        unique_together = [
            ("company", "supplier_id"),
        ]


class Contact(models.Model):
    company_code = models.IntegerField()
    customer_code = models.IntegerField()
    surname = models.CharField(max_length=255)

    # virtual field
    customer = CompositeForeignKey(Customer, to_fields={"customer_id": "customer_code", "company": "company_code"}, related_name='contacts')

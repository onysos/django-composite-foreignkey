#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
just a test app that is broken. used in tests.
"""

from __future__ import unicode_literals, print_function, absolute_import
import logging
from django.db import models
from django.db.models.deletion import CASCADE

from compositefk.fields import CompositeForeignKey, RawFieldValue
from testapp.models import Address

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class TempModel(models.Model):
    n = models.CharField(max_length=1)
    address = CompositeForeignKey(Address, on_delete=CASCADE, null=False, to_fields={
        "tiers_id": "customer_id",
        "company": "company",
        "not_an_addrress_field": RawFieldValue("C")
    }, null_if_equal=[  # if either of the fields company or customer is -1, ther can't have address
        ("don'texists", 37),
    ])


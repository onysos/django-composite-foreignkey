#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import
import logging

from django.db import connection
from django.test.testcases import TestCase

from testapp.models import Customer, Contact

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class TestQuery(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_model_fields(self):
        Contact._meta.get_field("customer")
        l = Contact._meta.get_fields()
        self.assertIn("customer", [f.name for f in l])

        l2 = Customer._meta.get_fields()
        self.assertIn("contacts", [f.name for f in l2])


    def test_foreignkey_getter(self):
        contact = Contact.objects.get(pk=1) # moiraine
        customer = Customer.objects.get(pk=3)
        with self.settings(DEBUG=True):
            self.assertEqual(contact.customer, customer)
            self.assertEqual(contact.customer.customer_id, contact.customer_code)
            self.assertEqual(contact.customer.company, contact.company_code)

            qs = connection.queries
            self.assertEqual(1, len(qs))


    def test_foreignkey_setter(self):
        contact = Contact.objects.get(pk=1)  # moiraine
        customer = Customer.objects.get(pk=2)
        self.assertNotEqual(contact.customer, customer)
        contact.customer = customer
        self.assertEqual(contact.customer, customer)

        self.assertEqual(contact.customer.customer_id, contact.customer_code)
        self.assertEqual(contact.customer.company, contact.company_code)
        contact.save()
        self.assertEqual(contact.customer.customer_id, contact.customer_code)
        self.assertEqual(contact.customer.company, contact.company_code)

    def test_foreignkey_lookup(self):
        contact = Contact.objects.get(pk=1)  # moiraine

        self.assertEqual(1, Customer.objects.filter(contacts=contact).count())
        self.assertEqual(1, Customer.objects.filter(contacts__surname="moiraine the witch").count())
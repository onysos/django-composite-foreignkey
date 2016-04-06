#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import
import logging

from django.apps import apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import NonInteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.test.testcases import TestCase

from compositefk.fields import CompositeForeignKey
from testapp.models import Customer, Contact, Address

logger = logging.getLogger(__name__)
__author__ = 'darius.bernard'


class TestGetterSetter(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_attr_set(self):
        contact = Contact.objects.get(pk=1)  # moiraine
        customer = Customer.objects.get(pk=2)
        self.assertNotEqual(contact.customer, customer)
        contact.customer = customer

        self.assertEqual(contact.customer, customer)
        # tests sub attrs changed
        self.assertEqual(contact.customer.customer_id, contact.customer_code)
        self.assertEqual(contact.customer.company, contact.company_code)
        # test nothing changed
        contact.save()
        self.assertEqual(contact.customer.customer_id, contact.customer_code)
        self.assertEqual(contact.customer.company, contact.company_code)

    def test_creation_inital_with_fk(self):
        customer = Customer.objects.get(pk=2)
        contact = Contact(surname="rand", customer=customer)
        self.assertEqual(contact.customer.customer_id, contact.customer_code)
        self.assertEqual(contact.customer.company, contact.company_code)
        self.assertEqual(contact.customer, customer)
        contact.save()
        self.assertEqual(contact.customer.customer_id, contact.customer_code)
        self.assertEqual(contact.customer.company, contact.company_code)
        self.assertEqual(contact.customer, customer)

    def test_creation_initial_with_attrs(self):
        customer = Customer.objects.get(pk=2)
        contact = Contact(surname="rand", company_code=customer.company, customer_code=customer.customer_id)

        self.assertEqual(contact.customer.customer_id, contact.customer_code)
        self.assertEqual(contact.customer.company, contact.company_code)
        self.assertEqual(contact.customer, customer)
        contact.save()
        self.assertEqual(contact.customer.customer_id, contact.customer_code)
        self.assertEqual(contact.customer.company, contact.company_code)
        self.assertEqual(contact.customer, customer)

    def test_foreignkey_getter(self):
        contact = Contact.objects.get(pk=1)  # moiraine
        customer = Customer.objects.get(pk=3)
        self.assertIsInstance(contact.customer, Customer)
        with self.settings(DEBUG=True):
            self.assertEqual(contact.customer, customer)
            self.assertEqual(contact.customer.customer_id, contact.customer_code)
            self.assertEqual(contact.customer.company, contact.company_code)


class TestForeignKeyStruct(TestCase):
    def test_model_fields(self):
        f = Contact._meta.get_field("customer")
        self.assertIsInstance(f, CompositeForeignKey)
        l = Contact._meta.get_fields()
        self.assertIn("customer", [field.name for field in l])

        f2 = Customer._meta.get_field("contacts")
        self.assertIsInstance(f2, ForeignObjectRel)
        l2 = Customer._meta.get_fields()
        self.assertIn("contacts", [field.name for field in l2])


class TestLookupQuery(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_forward_lookup(self):
        customer = Customer.objects.get(pk=1)
        self.assertEqual(1, Contact.objects.filter(customer=customer).count())
        self.assertEqual(1, Contact.objects.filter(customer__name="moiraine & cie").count())

    def test_backward_lookup(self):
        contact = Contact.objects.get(pk=1)  # moiraine
        self.assertEqual(1, Customer.objects.filter(contacts__surname=contact.surname).count())
        self.assertEqual(1, Customer.objects.filter(contacts=contact).count())


class TestExtraFilterRawValue(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_filtered_values(self):
        customer = Customer.objects.get(pk=1)
        address = Address.objects.get(pk=1)
        self.assertEqual(customer.address, address)


class TestDeconstuct(TestCase):
    def test_deconstruct(self):
        name, path, args, kwargs = Contact._meta.get_field("customer").deconstruct()
        self.assertEqual(name, "customer")
        self.assertEqual(path, "compositefk.fields.CompositeForeignKey")
        self.assertGreater(len(kwargs), 0)

    def test_reconstruct(self):
        name, path, args, kwargs = Contact._meta.get_field("customer").deconstruct()
        CompositeForeignKey(*args, **kwargs)

    def test_total_deconstruct(self):
        loader = MigrationLoader(None, load=True, ignore_no_migrations=True)
        loader.disk_migrations = {t: v for t, v in loader.disk_migrations.items() if t[0] != 'testapp'}
        app_labels = {"testapp"}
        questioner = NonInteractiveMigrationQuestioner(specified_apps=app_labels, dry_run=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(apps),
            questioner,
        )
        # Detect changes
        changes = autodetector.changes(
            graph=loader.graph,
            trim_to_apps=app_labels or None,
            convert_apps=app_labels or None,
            migration_name="my_fake_migration_for_test_deconstruct",
        )
        self.assertGreater(len(changes), 0)
        for app_label, app_migrations in changes.items():
            for migration in app_migrations:
                # Describe the migration
                writer = MigrationWriter(migration)

                migration_string = writer.as_string()
                self.assertNotEqual(migration_string, "")

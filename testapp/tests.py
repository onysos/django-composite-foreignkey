#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import

try:
    from unittest import mock
except ImportError:
    from mock import mock

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import logging

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader

try:
    from django.db.migrations.questioner import NonInteractiveMigrationQuestioner
except ImportError:
    from django.db.migrations.questioner import MigrationQuestioner as NonInteractiveMigrationQuestioner
from django.core import checks
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter
try:
    from django.db.models.fields.reverse_related import ForeignObjectRel
except ImportError:
    from django.db.models.fields.related import ForeignObjectRel

from django.test.testcases import TestCase
from compositefk.fields import CompositeForeignKey
from testapp.models import Customer, Contact, Address, Extra, AModel, BModel, PhoneNumber, Representant

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

        self.assertIsNone(f.db_type(None))


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

    def test_deep_forward(self):
        c = Customer.objects.get(pk=1)
        a = c.address
        self.assertEqual([c], list(Customer.objects.filter(address__in=[a])))

    def test_deep_backward(self):
        c = Customer.objects.get(pk=1)
        a = c.address
        l = list(Address.objects.filter(customer__in=[c]))
        self.assertEqual([a], l)

    def test_very_deep_mixed_forward(self):
        p = PhoneNumber.objects.get(pk=1)
        c = Contact.objects.get(pk=2)
        cu = Customer.objects.get(pk=1)
        a = Address.objects.get(pk=1)
        self.assertEqual([p], list(PhoneNumber.objects.filter(contact=c)))
        self.assertEqual([p], list(PhoneNumber.objects.filter(contact__customer=cu)))

    def test_very_deep_optimized_forward(self):
        # this query is optimized by django
        p = PhoneNumber.objects.get(pk=1)
        a = Address.objects.get(pk=1)
        q = PhoneNumber.objects.filter(contact__customer__address=a)

    def test_very_deep_optimized_backward(self):
        # this query is optimized by django
        p = PhoneNumber.objects.get(pk=1)
        a = Address.objects.get(pk=1)
        q = Address.objects.filter(customer__contacts__phonenumbers=p)
        self.assertEqual([a], list(q))


class TestExtraFilterRawValue(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_filtered_values(self):
        customer = Customer.objects.get(pk=1)
        address = Address.objects.get(pk=1)
        self.assertEqual(customer.address, address)


class TestExtraFilterFunctionBasedValue(TestCase):
    fixtures = ["all_fixtures.json"]

    @mock.patch.object(Customer.local_address.field._raw_fields['type_tiers'], '_func')
    def test_filtered_values(self, mock_get_local_type_tiers):
        mock_get_local_type_tiers.return_value = 'C'
        customer = Customer.objects.get(pk=1)
        address = Address.objects.get(pk=1)
        self.assertEqual(customer.local_address, address)

        mock_get_local_type_tiers.return_value = 'S'
        customer = Customer.objects.get(pk=1)
        address = Address.objects.get(pk=2)
        self.assertEqual(customer.local_address, address)


class TestNullIfEqual(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_exist_fq_null_if_company_bad(self):
        # test that fk is None even if addr exist,
        # but the company is '   ' and this is bad
        c = Customer.objects.get(pk=4)
        self.assertIsNone(c.address)

    def test_notexist_fq_null_if_company_bad(self):
        # test that fk is None. the addr don't exists in base
        # (bad but possible with bad database schema (legacy))

        c = Customer.objects.get(pk=5)
        self.assertIsNone(c.address)


class TestDeconstuct(TestCase):
    def test_deconstruct(self):
        name, path, args, kwargs = Contact._meta.get_field("customer").deconstruct()
        self.assertEqual(name, "customer")
        self.assertEqual(path, "compositefk.fields.CompositeForeignKey")
        self.assertGreater(len(kwargs), 0)

    def test_reconstruct(self):
        name, path, args, kwargs = Contact._meta.get_field("customer").deconstruct()
        CompositeForeignKey(*args, **kwargs)

    def test_models_check(self):
        self.maxDiff = None
        app_configs = [apps.get_app_config("testapp")]
        all_issues = checks.run_checks(
            app_configs=app_configs,
            tags=None,
            include_deployment_checks=False,
        )
        self.assertListEqual(all_issues, [])


    def test_field_check_errors(self):
        with self.settings(INSTALLED_APPS=settings.INSTALLED_APPS + ("broken_test_app",)):
            self.maxDiff = None
            app_configs = [apps.get_app_config("broken_test_app")]
            all_issues = checks.run_checks(
                app_configs=app_configs,
                tags=None,
                include_deployment_checks=False,
            )
            self.assertListEqual([issue.id for issue in all_issues], [
                'compositefk.E001', 'compositefk.E002', 'compositefk.E003',
                'compositefk.E003', 'compositefk.E004', 'compositefk.E006', 'compositefk.E005' ])

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


class TestOneToOne(TestCase):
    fixtures = ["all_fixtures.json"]
    def test_set(self):
        c = Customer.objects.all().get(pk=1)
        with self.assertRaises(Extra.DoesNotExist):
            self.assertIsNone(c.extra)
        e = Extra(sales_revenue=17.35, customer=c)
        e.save()
        c.refresh_from_db()

        self.assertEqual(c.extra, e)
        self.assertEqual(e.customer, c)


    def test_lookup(self):
        c = Customer.objects.all().get(pk=1)
        e = Extra(sales_revenue=17.35, customer=c)
        e.save()

        self.assertEqual(Extra.objects.get(customer__name=c.name), e)


class TestDeletion(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_one_delete(self):
        c = Customer.objects.get(pk=1)
        c.delete()

    def test_bulk_delete(self):
        Customer.objects.all().delete()

    def test_normal_delete(self):
        a = AModel.objects.create(n="plop")
        c = BModel.objects.create(a=a)

        self.assertTrue(AModel.objects.filter(pk=a.pk).exists())
        self.assertTrue(BModel.objects.filter(pk=c.pk).exists())
        a.delete()
        self.assertFalse(AModel.objects.filter(pk=a.pk).exists())
        self.assertFalse(BModel.objects.filter(pk=c.pk).exists())


    def test_ondelete_cascade(self):
        c = Customer.objects.get(pk=1)
        a = c.address
        self.assertTrue(Address.objects.filter(pk=a.pk).exists())
        self.assertTrue(Customer.objects.filter(pk=c.pk).exists())
        a.delete()
        self.assertFalse(Address.objects.filter(pk=a.pk).exists())
        self.assertFalse(Customer.objects.filter(pk=c.pk).exists())

class TestmanagementCommand(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_graph_data(self):
        out = StringIO()
        call_command("graph_datas", "testapp", stdout=out)

        result = out.getvalue()
        # print(result)
        self.assertEqual("""digraph items_in_db {
{ rank=same; address_1;address_2;address_3; }
{ rank=same; representant_1;representant_2; }
{ rank=same; customer_1;customer_2;customer_3;customer_4;customer_5; }
{ rank=same; contact_1;contact_2; }
{ rank=same; phonenumber_1; }
address_1;
address_2;
address_3;
representant_1;
representant_2;
customer_1;
customer_1  -> address_1;
customer_1  -> address_1;
customer_1  -> representant_1;
customer_2;
customer_3;
customer_3  -> representant_2;
customer_4;
customer_5;
contact_1;
contact_1  -> customer_3;
contact_2;
contact_2  -> customer_1;
phonenumber_1;
phonenumber_1  -> contact_2;
}
""", result)

    def test_app_not_exists(self):
        self.assertRaises(CommandError, call_command, "graph_datas", "doesnotexistsapp")

class TestToNone(TestCase):
    fixtures = ["all_fixtures.json"]

    def test_value_to_something(self):
        r = Representant.objects.get(pk=1)
        c = Customer.objects.get(pk=2)
        self.assertIsNone(c.representant)
        self.assertIsNone(c.cod_rep)
        c.representant = r
        c.save()
        self.assertEqual(c.representant, r)
        self.assertEqual(c.cod_rep, "DB")

    def test_value_to_none(self):
        r = Representant.objects.get(pk=1)
        c = Customer.objects.get(pk=1)

        self.assertEqual(c.representant, r)
        self.assertEqual(c.cod_rep, "DB")
        c.representant = None
        c.save()
        self.assertIsNotNone(c.company)
        self.assertIsNone(c.representant)
        self.assertEqual(c.cod_rep, "")

    def test_inital_value_to_related(self):
        r = Representant.objects.get(pk=1)
        c = Customer.objects.create(representant=r, name="test", customer_id=34)
        self.assertEqual(r.cod_rep, c.cod_rep)

    def test_inital_value_to_nullable(self):
        c = Customer.objects.create(representant=None, name="test", customer_id=34, company=1)
        self.assertEqual("", c.cod_rep)

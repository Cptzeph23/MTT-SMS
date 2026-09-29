from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.schools.models import School


class SchoolModelTests(TestCase):
    def test_code_is_trimmed_and_lowercased_on_save(self):
        school = School.objects.create(name="Alpha Academy", code="  ALPHA ")
        self.assertEqual(school.code, "alpha")

    def test_code_must_be_unique_regardless_of_case(self):
        School.objects.create(name="Alpha Academy", code="alpha")
        with self.assertRaises(IntegrityError), transaction.atomic():
            School.objects.create(name="Another", code="ALPHA")

    def test_new_school_is_active_by_default(self):
        self.assertTrue(School.objects.create(name="Alpha", code="alpha").is_active)

    def test_string_representation_is_the_name(self):
        self.assertEqual(str(School(name="Alpha Academy", code="alpha")), "Alpha Academy")

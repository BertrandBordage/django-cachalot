# coding: utf-8

from __future__ import unicode_literals
from unittest import skip
import datetime
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import (
    Model, CharField, ForeignKey, BooleanField,
    DateField, DateTimeField, Count)
from django.test import TestCase


class Test(Model):
    name = CharField(max_length=20)
    owner = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
    public = BooleanField(default=False)
    date = DateField(null=True, blank=True)
    datetime = DateTimeField(null=True, blank=True)

    class Meta(object):
        ordering = ('name',)

    def __str__(self):
        return self.name


class ReadTestCase(TestCase):
    """
    Tests if every SQL request that only reads data is cached.

    The only exception is for requests that don’t go through the ORM, using
    ``QuerySet.extra`` with ``select`` or ``where`` arguments,
     ``Model.objects.raw``, or ``cursor.execute``.
    """

    def setUp(self):
        self.user = User.objects.create_user('user')
        self.user__permissions = list(Permission.objects.all()[:3])
        self.user.user_permissions.add(*self.user__permissions)
        self.admin = User.objects.create_superuser('admin', 'admin@test.me',
                                                   'password')
        self.t1 = Test.objects.create(
            name='test1', owner=self.user,
            date='1789-07-14', datetime='1789-07-14T16:43:27')
        self.t2 = Test.objects.create(
            name='test2', owner=self.admin, public=True,
            date='1944-06-06', datetime='1944-06-06T06:35:00')
        # TODO: Move this to setUpClass when cachalot will handle transactions.
        cache.clear()

    def test_empty(self):
        with self.assertNumQueries(0):
            data1 = list(Test.objects.none())
        with self.assertNumQueries(0):
            data2 = list(Test.objects.none())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [])

    def test_exists(self):
        with self.assertNumQueries(1):
            n1 = Test.objects.exists()
        with self.assertNumQueries(0):
            n2 = Test.objects.exists()
        self.assertEqual(n2, n1)
        self.assertTrue(n2)

    def test_count(self):
        with self.assertNumQueries(1):
            n1 = Test.objects.count()
        with self.assertNumQueries(0):
            n2 = Test.objects.count()
        self.assertEqual(n2, n1)
        self.assertEqual(n2, 2)

    def test_get(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.get(name='test1')
        with self.assertNumQueries(0):
            data2 = Test.objects.get(name='test1')
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t1)

    def test_first(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.first()
        with self.assertNumQueries(0):
            data2 = Test.objects.first()
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t1)

    def test_last(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.last()
        with self.assertNumQueries(0):
            data2 = Test.objects.last()
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t2)

    def test_all(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

    def test_filter(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(public=True))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(public=True))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2])

        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(pk__in=range(2, 10)))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(pk__in=range(2, 10)))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2])

    def test_filter_empty(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(public=True,
                                             name='user'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(public=True,
                                             name='user'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [])

    def test_exclude(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.exclude(public=True))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.exclude(public=True))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1])

        with self.assertNumQueries(1):
            data1 = list(Test.objects.exclude(pk__in=range(2, 10)))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.exclude(pk__in=range(2, 10)))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1])

    def test_slicing(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all()[:1])
        with self.assertNumQueries(0):
            data2 = list(Test.objects.all()[:1])
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1])

    def test_order_by(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.order_by('pk'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.order_by('pk'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

        with self.assertNumQueries(1):
            data1 = list(Test.objects.order_by('-name'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.order_by('-name'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2, self.t1])

    def test_reverse(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.reverse())
        with self.assertNumQueries(0):
            data2 = list(Test.objects.reverse())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2, self.t1])

    def test_distinct(self):
        # We ensure that the query without distinct should return duplicate
        # objects, in order to have a real-world example.
        data1 = list(Test.objects.filter(
            owner__user_permissions__content_type__app_label='auth'))
        self.assertEqual(len(data1), 3)
        self.assertListEqual(data1, [self.t1] * 3)

        with self.assertNumQueries(1):
            data2 = list(Test.objects.filter(
                owner__user_permissions__content_type__app_label='auth'
            ).distinct())
        with self.assertNumQueries(0):
            data3 = list(Test.objects.filter(
                owner__user_permissions__content_type__app_label='auth'
            ).distinct())
        self.assertListEqual(data3, data2)
        self.assertEqual(len(data3), 1)
        self.assertListEqual(data3, [self.t1])

    def test_iterator(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.iterator())
        with self.assertNumQueries(0):
            data2 = list(Test.objects.iterator())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

    def test_in_bulk(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.in_bulk((7, 2, 5))
        with self.assertNumQueries(0):
            data2 = Test.objects.in_bulk((7, 2, 5))
        self.assertDictEqual(data2, data1)
        self.assertDictEqual(data2, {2: self.t2})

    def test_values(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values('name', 'public'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values('name', 'public'))
        self.assertEqual(len(data1), 2)
        self.assertEqual(len(data2), 2)
        for row1, row2 in zip(data1, data2):
            self.assertDictEqual(row2, row1)
        self.assertDictEqual(data2[0], {'name': 'test1', 'public': False})
        self.assertDictEqual(data2[1], {'name': 'test2', 'public': True})

    def test_values_list(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, ['test1', 'test2'])

    def test_earliest(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.earliest('date')
        with self.assertNumQueries(0):
            data2 = Test.objects.earliest('date')
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t1)

    def test_latest(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.latest('date')
        with self.assertNumQueries(0):
            data2 = Test.objects.latest('date')
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t2)

    def test_dates(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.dates('date', 'year'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.dates('date', 'year'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [datetime.date(1789, 1, 1),
                                     datetime.date(1944, 1, 1)])

    def test_datetimes(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.datetimes('datetime', 'hour'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.datetimes('datetime', 'hour'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [datetime.datetime(1789, 7, 14, 16),
                                     datetime.datetime(1944, 6, 6, 6)])

    def test_subquery(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(owner__in=User.objects.all()))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(owner__in=User.objects.all()))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

    def test_aggregate(self):
        Test.objects.create(name='test3', owner=self.user)
        with self.assertNumQueries(1):
            n1 = User.objects.aggregate(n=Count('test'))['n']
        with self.assertNumQueries(0):
            n2 = User.objects.aggregate(n=Count('test'))['n']
        self.assertEqual(n2, n1)
        self.assertEqual(n2, 3)

    def test_annotate(self):
        Test.objects.create(name='test3', owner=self.user)
        with self.assertNumQueries(1):
            data1 = list(User.objects.annotate(n=Count('test'))
                         .values_list('n', flat=True))
        with self.assertNumQueries(0):
            data2 = list(User.objects.annotate(n=Count('test'))
                         .values_list('n', flat=True))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [2, 1])

    def test_only(self):
        with self.assertNumQueries(1):
            t1 = Test.objects.only('name').first()
            t1.name
        with self.assertNumQueries(0):
            t2 = Test.objects.only('name').first()
            t2.name
        with self.assertNumQueries(1):
            t1.public
        with self.assertNumQueries(0):
            t2.public
        self.assertEqual(t2, t1)
        self.assertEqual(t2.name, t1.name)
        self.assertEqual(t2.public, t1.public)

    def test_defer(self):
        with self.assertNumQueries(1):
            t1 = Test.objects.defer('name').first()
            t1.public
        with self.assertNumQueries(0):
            t2 = Test.objects.defer('name').first()
            t2.public
        with self.assertNumQueries(1):
            t1.name
        with self.assertNumQueries(0):
            t2.name
        self.assertEqual(t2, t1)
        self.assertEqual(t2.name, t1.name)
        self.assertEqual(t2.public, t1.public)

    def test_select_related(self):
        with self.assertNumQueries(1):
            t1 = Test.objects.select_related('owner').get(name='test1')
            self.assertEqual(t1.owner, self.user)
        with self.assertNumQueries(0):
            t2 = Test.objects.select_related('owner').get(name='test1')
            self.assertEqual(t2.owner, self.user)
        self.assertEqual(t2, t1)
        self.assertEqual(t2, self.t1)

    def test_prefetch_related(self):
        with self.assertNumQueries(2):
            qs = (Test.objects.select_related('owner')
                  .prefetch_related('owner__user_permissions'))
            permissions1 = []
            for t in qs:
                permissions1.extend(t.owner.user_permissions.all())
        with self.assertNumQueries(0):
            qs = (Test.objects.select_related('owner')
                  .prefetch_related('owner__user_permissions'))
            permissions2 = []
            for t in qs:
                permissions2.extend(t.owner.user_permissions.all())
        self.assertListEqual(permissions2, permissions1)
        self.assertListEqual(permissions2, self.user__permissions)

    @skip(NotImplementedError)
    def test_using(self):
        pass

    @skip(NotImplementedError)
    def test_select_for_update(self):
        pass

    def test_extra_select(self):
        """
        Tests if ``QuerySet.extra(select=…)`` is not cached.
        """

        username_length_sql = """
        SELECT LENGTH(%(user_table)s.username)
        FROM %(user_table)s
        WHERE %(user_table)s.id = %(test_table)s.owner_id
        """ % {'user_table': User._meta.db_table,
               'test_table': Test._meta.db_table}

        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(
                select={'username_length': username_length_sql}))
        with self.assertNumQueries(1):
            data2 = list(Test.objects.extra(
                select={'username_length': username_length_sql}))
        self.assertListEqual(data2, data1)
        self.assertListEqual([o.username_length for o in data2],
                             [o.username_length for o in data1])
        self.assertListEqual([o.username_length for o in data2],
                             [4, 5])

    def test_extra_where(self):
        """
        Tests if ``QuerySet.extra(where=…)`` is not cached.

        The ``where`` list of a ``QuerySet.extra`` can contain subqueries,
        and since it’s unparsed pure SQL, it can’t be reliably invalidated.
        """

        sql_condition = ('owner_id IN '
                         '(SELECT id FROM auth_user WHERE username = "admin")')
        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(where=[sql_condition]))
        with self.assertNumQueries(1):
            data2 = list(Test.objects.extra(where=[sql_condition]))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2])

    def test_extra_tables(self):
        """
        Tests if ``QuerySet.extra(tables=…)`` is cached.

        ``tables`` can only define table names, so we can reliably invalidate
        such queries.
        """

        # QUESTION: Is there a way to access extra tables data without
        #           an extra select?
        with self.assertNumQueries(1):
            list(Test.objects.extra(tables=['auth_user']))
        with self.assertNumQueries(0):
            list(Test.objects.extra(tables=['auth_user']))
        with self.assertNumQueries(0):
            list(Test.objects.extra(tables=['"auth_user"']))

    def test_extra_order_by(self):
        """
        Tests if ``QuerySet.extra(order_by=…)`` is cached.

        As far as I know, the ``order_by`` list of a ``QuerySet.extra``
        can’t select data from other tables.
        """

        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(order_by=['-cachalot_test.name']))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.extra(order_by=['-cachalot_test.name']))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2, self.t1])

    def test_raw(self):
        """
        Tests if ``Model.objects.raw`` queries are not cached.
        """

        sql = 'SELECT * FROM %s;' % Test._meta.db_table

        with self.assertNumQueries(1):
            data1 = list(Test.objects.raw(sql))
        with self.assertNumQueries(1):
            data2 = list(Test.objects.raw(sql))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

    @skip('For an unknown reason, we can’t measure how many requests are '
          'executed by ``cursor.execute``.')
    def test_cursor_execute(self):
        """
        Tests if queries executed from a DB cursor are not cached.
        """

        sql = 'SELECT * FROM %s;' % Test._meta.db_table

        from django.db import connection
        cursor = connection.cursor()
        with self.assertNumQueries(1):
            cursor.execute(sql)
            data1 = cursor.fetchall()
        with self.assertNumQueries(1):
            cursor.execute(sql)
            data2 = cursor.fetchall()
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])


class WriteTestCase(TestCase):
    """
    Tests if every SQL request writing data is not cached and invalidates the
    implied data.
    """

    def setUp(self):
        # TODO: Move this to setUpClass when cachalot will handle transactions.
        cache.clear()

    def test_create(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            t2 = Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        with self.assertNumQueries(1):
            t3 = Test.objects.create(name='test3')
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all())
        self.assertListEqual(data2, [t1, t2])
        self.assertListEqual(data3, [t1, t2, t3])

    def test_get_or_create(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        # get_or_create has to try to find the object, then create it
        # inside a transaction.
        # This triggers 4 queries: SELECT, BEGIN, UPDATE, & COMMIT
        with self.assertNumQueries(4):
            t, created = Test.objects.get_or_create(name='test')
        self.assertTrue(created)

        with self.assertNumQueries(1):
            t_clone, created = Test.objects.get_or_create(name='test')
        self.assertFalse(created)
        self.assertEqual(t_clone, t)

        with self.assertNumQueries(0):
            t_clone, created = Test.objects.get_or_create(name='test')
        self.assertFalse(created)
        self.assertEqual(t_clone, t)

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [t])

    @skip(NotImplementedError)
    def test_update_or_create(self):
        pass

    def test_bulk_create(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            unsaved_tests = [Test(name='test%02d' % i) for i in range(1, 11)]
            Test.objects.bulk_create(unsaved_tests)
        self.assertEqual(Test.objects.count(), 10)

        with self.assertNumQueries(1):
            unsaved_tests = [Test(name='test%02d' % i) for i in range(11, 21)]
            Test.objects.bulk_create(unsaved_tests)
        self.assertEqual(Test.objects.count(), 20)

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertEqual(len(data2), 20)
        self.assertListEqual([t.name for t in data2],
                             ['test%02d' % i for i in range(1, 21)])

    def test_update(self):
        with self.assertNumQueries(1):
            t = Test.objects.create(name='test1')

        with self.assertNumQueries(1):
            t1 = Test.objects.get()
        with self.assertNumQueries(1):
            t.name = 'test2'
            t.save()
        with self.assertNumQueries(1):
            t2 = Test.objects.get()
        self.assertEqual(t1.name, 'test1')
        self.assertEqual(t2.name, 'test2')

        with self.assertNumQueries(1):
            Test.objects.update(name='test3')
        with self.assertNumQueries(1):
            t3 = Test.objects.get()
        self.assertEqual(t3.name, 'test3')

    def test_delete(self):
        with self.assertNumQueries(1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            t2 = Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
        with self.assertNumQueries(1):
            t2.delete()
        with self.assertNumQueries(1):
            data2 = list(Test.objects.values_list('name', flat=True))
        self.assertListEqual(data1, [t1.name, t2.name])
        self.assertListEqual(data2, [t1.name])

        with self.assertNumQueries(1):
            Test.objects.bulk_create([Test(name='test%s' % i)
                                      for i in range(2, 11)])
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 10)
        with self.assertNumQueries(1):
            Test.objects.all().delete()
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 0)

    def test_invalidate_exists(self):
        with self.assertNumQueries(1):
            self.assertFalse(Test.objects.exists())

        Test.objects.create(name='test')

        with self.assertNumQueries(1):
            self.assertTrue(Test.objects.create())

    def test_invalidate_count(self):
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 0)

        Test.objects.create(name='test1')

        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 1)

        Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 2)

    def test_invalidate_get(self):
        with self.assertNumQueries(1):
            with self.assertRaises(Test.DoesNotExist):
                Test.objects.get(name='test')

        Test.objects.create(name='test')

        with self.assertNumQueries(1):
            Test.objects.get(name='test')

        Test.objects.create(name='test')

        with self.assertNumQueries(1):
            with self.assertRaises(MultipleObjectsReturned):
                Test.objects.get(name='test')

    def test_invalidate_values(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values('name', 'public'))
        self.assertListEqual(data1, [])

        Test.objects.bulk_create([Test(name='test1'),
                                  Test(name='test2', public=True)])

        with self.assertNumQueries(1):
            data2 = list(Test.objects.values('name', 'public'))
        self.assertEqual(len(data2), 2)
        self.assertDictEqual(data2[0], {'name': 'test1', 'public': False})
        self.assertDictEqual(data2[1], {'name': 'test2', 'public': True})

        Test.objects.all()[0].delete()

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values('name', 'public'))
        self.assertEqual(len(data3), 1)
        self.assertDictEqual(data3[0], {'name': 'test2', 'public': True})

    @skip(NotImplementedError)
    def test_invalidate_aggregate(self):
        pass

    @skip(NotImplementedError)
    def test_invalidate_annotate(self):
        pass

    def test_invalidate_subquery(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(owner__in=User.objects.all()))

        u = User.objects.create_user('test')
        t = Test.objects.create(name='test', owner=u)

        with self.assertNumQueries(1):
            data2 = list(Test.objects.filter(owner__in=User.objects.all()))

        self.assertListEqual(data1, [])
        self.assertListEqual(data2, [t])

    @skip(NotImplementedError)
    def test_invalidate_select_related(self):
        pass

    @skip(NotImplementedError)
    def test_invalidate_prefetch_related(self):
        pass

    @skip(NotImplementedError)
    def test_invalidate_extra_select(self):
        pass

    @skip(NotImplementedError)
    def test_invalidate_extra_where(self):
        pass

    @skip(NotImplementedError)
    def test_invalidate_extra_tables(self):
        pass

    @skip(NotImplementedError)
    def test_invalidate_extra_order_by(self):
        pass

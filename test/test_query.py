import unittest

from sqlite_orm.db import Database
from sqlite_orm.fields import IntField, TextField, ForeignKeyField


class QueryingTest(unittest.TestCase):

    def setUp(self):
        # initialize in-memory database
        self.db = Database(verbose=False)

        class New(self.db.BaseModel):
            __tablename__ = 'new_table'
            field1 = TextField()
            field2 = IntField()
            field3 = IntField(pk=True)

        self.New = New

        class New2(self.db.BaseModel):
            __tablename__ = 'new_table_2'
            field4 = ForeignKeyField(to=New)
            field5 = TextField()

        self.New2 = New2

        self.db.create_all()

    def tearDown(self):
        self.db.close()

    def testModelRetrieval(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Bbbb', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m12, m21]]
        # check pks was set properly
        self.assertEqual(m11.pk, 3)
        self.assertEqual(m12.pk, 1)

        # check pk set automatically after model added
        self.assertEqual(m11.pk, 3)
        self.assertEqual(m12.pk, 1)

        # fetch models from db and check fetched pk's and data are the same
        m11_db = self.db.query(self.New).get(3)
        m12_db = self.db.query(self.New).get(1)
        self.assertEqual(m11_db.field1, m11.field1)
        self.assertEqual(m12_db.field1, m12.field1)
        self.assertEqual(m11_db.pk, m11.pk)
        self.assertEqual(m12_db.pk, m12.pk)

    def testFirstQuery(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Bbbb', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m12, m21]]

        m11_db = self.db.query(self.New).first()
        self.assertDictEqual(m12._data, m11_db._data)

    def testAllQuery(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Bbbb', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m12, m21]]

        m1_db = self.db.query(self.New).all()
        self.assertEqual(len(m1_db), 2)
        m12_db, m11_db = m1_db
        self.assertDictEqual(m12._data, m12_db._data)
        self.assertDictEqual(m11._data, m11_db._data)


    def testForeignKeyFieldRetrieval(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m21]]

        m21_db = self.db.query(self.New2).get(1)
        m11_db = m21_db.field4

        self.assertEqual(m11.pk, m11_db.pk)
        self.assertEqual(m11.field1, m11_db.field1)

    def testFilterQuery(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Aaaa', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m12, m21]]

        m11_m12_db = self.db.query(self.New).filter(field1='Aaaa').all()
        self.assertEqual(len(m11_m12_db), 2)
        pks = [m11.pk, m12.pk]
        self.assertIn(m11_m12_db[0].pk, pks)
        self.assertIn(m11_m12_db[1].pk, pks)
        self.assertEqual(m11_m12_db[0].field1, 'Aaaa')
        self.assertEqual(m11_m12_db[0].field1, 'Aaaa')

    def testChainFilterQuery(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Aaaa', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m12, m21]]

        m11_db = self.db.query(self.New).filter(field1='Aaaa').filter(field2=15).all()
        self.assertEqual(len(m11_db), 1)
        self.assertDictEqual(m11._data, m11_db[0]._data)

    def testFirstReturnNoneIfNoMatchedModels(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Aaaa', field2=30, field3=1)
        [self.db.add(model) for model in [m11, m12]]
        res = self.db.query(self.New).filter(field1='Eeee').first()
        self.assertIsNone(res)

    def testModelUpdate(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Bbbb', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m12, m21]]

        # change model
        m11.field1 = 'New data'
        # check its pk hasnt been reset
        self.assertEqual(m11.pk, 3)
        self.assertEqual(m11._data['_id'], 3)
        # add it again to issue update
        self.db.add(m11)
        # and check pk again
        self.assertEqual(m11.pk, 3)
        self.assertEqual(m11._data['_id'], 3)
        # fetch from db
        m11_db = self.db.query(self.New).get(3)

        self.assertDictEqual(m11._data, m11_db._data)
        self.assertEqual(m11_db.field1, 'New data')

    def testSelectNotAllColumns(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Bbbb', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m12, m21]]

        m11_db_dict = self.db.query(self.New).filter(field1='Aaaa').select(self.New, fields=['field2', 'field1']).first()
        self.assertDictEqual(m11_db_dict, {'new_table.field1': 'Aaaa', 'new_table.field2': 15})
        m11_db_dict = self.db.query(self.New).filter(field1='Aaaa').select(self.New, fields=['field2']).first()
        self.assertEqual(m11_db_dict, {'new_table.field2': 15})

    def testJoinTables(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Bbbb', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Cccc')
        [self.db.add(model) for model in [m11, m12, m21]]

        m21_db_dict = self.db.query(self.New).join(self.New2).select(self.New2, fields=['field5']).filter(field2=15).first()
        self.assertEqual(m21_db_dict, {'new_table_2.field5': 'Cccc'})

    def testJoinTablesOn(self):
        m11 = self.New(field1='Aaaa', field2=15, field3=3)
        m12 = self.New(field1='Bbbb', field2=30, field3=1)
        m21 = self.New2(field4=m11, field5='Aaaa')
        [self.db.add(model) for model in [m11, m12, m21]]

        m21_db_dict = self.db.query(self.New).join(self.New2, join_on=['field1', 'field5']).select(self.New2, fields=['field5']).first()
        self.assertEqual(len(m21_db_dict), 1)
        self.assertDictEqual(m21_db_dict, {'new_table_2.field5': 'Aaaa'})

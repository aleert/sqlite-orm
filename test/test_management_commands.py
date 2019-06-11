import unittest

from sqlite_orm.db import Database
from sqlite_orm.exceptions import QueryError, dbIntegrityError
from sqlite_orm.fields import IntField, TextField, ForeignKeyField


class CreationTest(unittest.TestCase):

    def setUp(self):
        # initialize in-memory database
        self.db = Database()

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

    def testDropTable(self):
        self.db.drop(self.New2)
        with self.assertRaises(QueryError):
            self.db.query(self.New2).first()

    def testRaiseIfExists(self):
        with self.assertRaises(dbIntegrityError):
            self.db.create_all(raise_if_exists=True)

    def testNamedModelField(self):
        class New3(self.db.BaseModel):
            __tablename__ = 'new_table_3'
            field1 = TextField(name='my_text_field')
            field2 = IntField()
            field3 = IntField(pk=True)

        self.db.create_all()
        m31 = New3(field1='yarr', field2=3)
        self.db.add(m31)
        m31_db = self.db.query(New3).get(1)
        self.assertDictEqual(m31._data, m31_db._data)
        self.assertEqual(m31_db.pk, m31.pk)
        self.assertEqual(m31_db.field1, m31.field1)

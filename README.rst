Simple sqlite orm. To install it clone this repo and run

.. code-block:: shell

    python setup.py install

Without further ado, let's jump staight to usage exapmles:

Usage
-----

Creating database
*****************

First you should create database:

.. code-block:: python

    from sqlite_orm.db import Database
    db = Database()

That will create in-memory database. To create a database file pass ``filename='mydb.sqlite3``
parameter to ``Database`` constructor.

You can also pass ``verbose=True`` to ``Database`` constructor and then it'll print
executed sql statements to console.

Creating models
***************

After you have database you can create some models.

.. code-block:: python

    from sqlite_orm.fields import IntField, TextField, ForeignKeyField

        class New(db.BaseModel):
            __tablename__ = 'new_table'
            field1 = TextField()
            field2 = IntField()
            field3 = IntField(pk=True)

        class New2(db.BaseModel):
            __tablename__ = 'new_table_2'
            field4 = ForeignKeyField(to=New)
            field5 = TextField()

That will register you models. Note that ``__tablename__`` class attribute is required.
You can also set custom field name to use in database table by passing ``name=myname``
parameter to field constructor.

Now you can actually add models to database. Just issue

.. code-block:: python

    db.create_all()

You can also pass ``raise_if_exists=True`` parameter to raise an exception if table with
such ``__tablename__`` already exists.

Adding model instances
**********************
Create some model instances and ``add`` them to database.

.. code-block:: python

        m11 = New(field1='Aaaa', field2=15, field3=3)
        m12 = New(field1='Aaaa', field2=30, field3=1)
        m21 = New2(field4=m11, field5='Cccc')
        [db.add(model) for model in [m11, m12, m21]]

``db.add(model)`` is a method responsible to actually run sql. After adding models
their primary keys will be set automatically and you can access them either by fieldname
or using special model attribute ``model.pk``.

To update a record in database just change the model and add it to database again:

.. code-block:: python

        m11.field1 = 'Some new text'
        db.add(m11)

Querying database
*****************

Methods that evaluate query
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Database has special method ``query`` that accepts model instance as its argument.
So to query model by its pk run

.. code-block:: python

        m11_db = db.query(New).get(3)

and that will return ``New`` instance.

To get all results use ``query.all()`` and to get first record use ``query.first()``:

.. code-block:: python

    m1_list = db.query(New).all()
    m1_model = db.query(New).first()

Methods that filter query without evaluating
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To filter result with WHERE sql condition use ``query.filter`` statement that
accepts keyword arguments corresponding to model fields. Currently only '='
comparisons available:

.. code-block:: python

        m11_m12_db = db.query(New).filter(field1='Aaaa').all()

Filter statements can be chained together:

.. code-block:: python

        m11_db = db.query(New).filter(field1='Aaaa').filter(field2=15).first()

There is also ``db.select`` method that allows you to select just specified fields.
``select`` accepts ``Model`` as first argument and ``fields=['field1', 'field']`` list of
fields to query. Returned dict is namespaced with ``.`` symbol so keys will be like
'``{tablename}.{field_name}``'.

.. code-block:: python

        m11_db_dict = db.query(New).filter(field1='Aaaa').select(New, fields=['field2', 'field1']).first()
        >>> m11_db_dict
        {'new_table.field2': 15, 'new_table.field1': 'Aaaa'}

Joins
^^^^^

If models related by foreign_key join will be made automatically by that field:

.. code-block:: python

        m21_db_dict = db.query(New).join(New2).select(New2, fields=['field5']).filter(field2=15).first()
        >>>m21_db_dict
        {'new_table_2.field5': 'Cccc'}


Otherwise you can join any tables

.. code-block:: python

        m13 = New(field1='Dddd', field2=30)
        m22 = New2(field4=m11, field5='Dddd')
        [db.add(model) for model in [m13, m22]]
        m22_db_dict = db.query(New).join(New2, join_on=['field1', 'field5']).select(New2, fields=['field5']).first()
        >>>m21_db_dict
        {'new_table_2.field5': 'Dddd'}

there join is made between ``New`` and ``New2`` tables based on condition ``New.field1=New2.field5``.


Closing database
----------------
To close connection to database run

.. code-block:: python

    db.close()

Running tests
-------------

There are few tests that demonstrate basic behaviour. To run them just

.. code-block:: shell

    python -m unittest

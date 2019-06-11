class BaseField:

    SQL_TYPE: str
    PYTHON_TYPE: type

    def __init__(self, name=None, pk=False, unique=False):
        """
        Base descriptor for fields that handles model _meta information update.
        :param name: custom table name
        :param pk: if field is pk
        :param unique: if field unique
        """
        self.model_name = ''
        self.db_name = name
        self.pk = pk
        self.unique = unique

    def __set_name__(self, owner, name):
        self.model_name = name
        self.db_name = self.db_name or name
        owner._meta['names'][self.model_name] = self.db_name
        owner._meta['types'].append(self.SQL_TYPE)
        if self.pk:
            owner._meta['pks'][self.model_name] = self.db_name
        if self.unique:
            owner._meta['uniques'][self.model_name] = self.db_name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance._data[self.db_name]

    def __set__(self, instance, value):
        # do some type checking
        if not isinstance(self, ForeignKeyField) and not isinstance(value, self.PYTHON_TYPE):
            raise ValueError('Cannot cast {0} to sql type {1} for {2} field.'.format(
                value, self.SQL_TYPE, self.model_name
            ))
        instance._data[self.db_name] = value
        if self.pk:
            instance._data['_id'] = value

        instance.needs_update_in_db = True

    def get_sql(self):
        """Field SQL to use for table creation."""
        sql = ' '.join([self.db_name, self.SQL_TYPE])
        if self.unique:
            sql += ' ' + 'UNIQUE'
        if self.pk:
            sql += ' PRIMARY KEY'
        return sql


class TextField(BaseField):
    SQL_TYPE = 'TEXT'
    PYTHON_TYPE = str


class IntField(BaseField):
    SQL_TYPE = 'INTEGER'
    PYTHON_TYPE = int


class FloatField(BaseField):
    SQL_TYPE = 'REAL'
    PYTHON_TYPE = float


class BytesField(BaseField):
    SQL_TYPE = 'BLOB'
    PYTHON_TYPE = bytes


class ForeignKeyField(BaseField):
    SQL_TYPE = ''
    PYTHON_TYPE = ''

    def __init__(self, to, name=None, on_delete='CASCADE'):
        self.to = to
        self.__class__.PYTHON_TYPE = getattr(self.to, [*self.to._meta['pks']][0]).PYTHON_TYPE
        self.__class__.SQL_TYPE = getattr(self.to, [*self.to._meta['pks']][0]).SQL_TYPE
        self.on_delete = on_delete
        super().__init__(name=name)

    def get_sql(self):
        sql = f'FOREIGN KEY({self.db_name}) REFERENCES {self.to.__tablename__}({self.to.pk_db_name()})'
        if self.on_delete:
            sql += f'ON DELETE {self.on_delete}'
        return sql

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        owner._meta['fks'][name] = self.db_name

    def __get__(self, instance, owner):
        # return descriptor itself if requested from class (no instance)
        if instance is None:
            return self
        # if model already have model fetched for fk field - return it without querying db each time
        if instance._data[self.db_name]:
            return instance._data[self.db_name]
        # else query model from db and add it to instance
        params = {
            self.to.pk_db_name(): instance._data['fk_to_id']
        }
        fk_instance = owner.db.query(self.to).join(owner).filter(**params).first()
        instance._data[self.db_name] = fk_instance
        return fk_instance

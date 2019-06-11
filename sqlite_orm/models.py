from sqlite_orm.exceptions import dbIntegrityError
from sqlite_orm.fields import ForeignKeyField
from sqlite_orm import NAMESPACE_SPLIT_KEY


class BaseModel:
    """Base class for models that keeps track of all subclassed models."""

    __tablename__ = ''
    _meta = {
        # model_field_name: db_name
        'names': {},
        'pks': {},
        'uniques': {},
        'fks': {},
        # sql types
        'types': [],
    }
    # registry of all models ever subclassed from BaseModel
    registered_models = []

    def __init__(self, **kwargs):
        if not self.__class__.__tablename__:
            raise ValueError(f'Please provide tablename for model {self.__class__}')
        # flags to distinguish between model fetched from db and not updated, fetched from db and modified
        # (needs update), newly created model (needs insert)
        self.fetched_from_db = False
        self.needs_update_in_db = True
        # sql field names for keys, values for values
        self._data = {name: None for name in self._meta['names'].values()}
        self._data['_id'] = None
        # there is also special data key 'fk_to_id' which is set by ForeignKeyField

        # initialize data fields
        for key, value in kwargs.items():
            if not key in self._meta['names'].keys():
                raise KeyError(f'Wrong parameter {key}')
            setattr(self, key, value)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._meta = BaseModel._meta.copy()
        BaseModel.registered_models.append(cls)
        # reset BaseModel  _meta state after every subclass initialization
        # or Fields in different subclasses will append to BaseModel _meta state
        BaseModel._meta = {
            'names': {},
            'types': [],
            'pks': {},
            'uniques': {},
            'fks': {},
        }

    @classmethod
    def from_query_result(cls, data):
        """Make instance from data where data is sqlite3 row."""
        reversed_names = {db_name: model_name for model_name, db_name in cls._meta['names'].items()}
        params = {}
        fk_id = ''
        for field in data.keys():
            # those are fields for different models
            if not field.startswith(cls.__tablename__):
                continue
            # remove namespacing
            stripped_field = field[len(cls.__tablename__)+len(NAMESPACE_SPLIT_KEY):]
            if stripped_field == 'rowid':
                continue
            if stripped_field in reversed_names.keys() and stripped_field not in cls._meta['fks'].values():
                params[reversed_names[stripped_field]] = data[field]
            if stripped_field in cls._meta['fks'].values():
                fk_id = data[field]
        new_instance = cls(**params)
        if 'rowid' in data.keys():
            new_instance._data['_id'] = data['rowid']
        if fk_id:
            new_instance._data['fk_to_id'] = fk_id
        return new_instance

    @property
    def pk(self):
        """Convinient property to set or retrieve model primary key."""
        pass

    @pk.getter
    def pk(self):
        return self._data['_id']

    @pk.setter
    def pk(self, value):
        self._data['_id'] = value
        pk_names = [*self._meta['pks'].keys()]
        if len(pk_names) > 1:
            raise dbIntegrityError('Composite primary keys not supported.')
        if pk_names:
            pk_name = pk_names[0]
            setattr(self, pk_name, value)

    @classmethod
    def pk_db_name(cls):
        """Return pk field name that is used in database for that model."""
        pk_name = ''
        if len(cls._meta['pks']) == 1:
            pk_name = [i for i in cls._meta['pks'].values()][0]
        elif len(cls._meta['pks']) == 0:
            pk_name = 'rowid'
        return pk_name

    @classmethod
    def pk_sql_type(cls):
        if len(cls._meta['pks']) == 1:
            pk_name = [i for i in cls._meta['pks'].keys()][0]
            pk_descriptor = getattr(cls, pk_name)
            return pk_descriptor.SQL_TYPE

    @classmethod
    def table_definition_sql(cls, raise_if_exists=False):
        """
        SQL to create table, by default IF NOT EXISTS statement used.
        :param raise_if_exists: if True IF NOT EXISTS not included.
        :return: str
        """
        sqls = []
        for fieldname in cls._meta['names'].keys():
            field = getattr(cls, fieldname)
            if isinstance(field, ForeignKeyField):
                fk_sql = ' '.join([field.db_name, field.SQL_TYPE])
                sqls.append(fk_sql)
                continue
            field_sql = field.get_sql()
            sqls.append(field_sql)

        # setting FOREIGN KEY .. REFERENCES .. condition
        for fieldname in cls._meta['fks'].keys():
            field = getattr(cls, fieldname)
            field_sql = field.get_sql()
            sqls.append(field_sql)

        fields_sql = ', '.join(sqls)
        condition = ''
        if not raise_if_exists:
            condition = 'IF NOT EXISTS '
        query = f'CREATE TABLE {condition}{cls.__tablename__} ({fields_sql});'
        return query

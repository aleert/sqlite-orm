import sqlite3
from typing import Iterable, List

from sqlite_orm.fields import ForeignKeyField
from sqlite_orm.models import BaseModel
from sqlite_orm.exceptions import dbIntegrityError, QueryError, NotFoundError, MultipleRowsReturnedError, \
    DatabaseClosedError
from sqlite_orm import NAMESPACE_SPLIT_KEY


class Query(object):
    """Base query class with methods to filter result and retrieve it."""

    def __init__(self, model):
        self.model = model
        self.pk_db_name = self.model.pk_db_name()
        self._base_query = 'SELECT {select_fields} FROM {select_from} '
        self._select_fields = {
            self.model.__tablename__: self.model._meta['names'].copy()
        }
        if self.pk_db_name == 'rowid':
            self._select_fields[self.model.__tablename__]['rowid'] = 'rowid'
        self.select_from = self.model.__tablename__
        # ['fieldname1=?', 'fieldname2=?'] strings
        self._select_where = []
        # params for ? in _select_where
        self._query_params = []
        self.limit = ''
        # return dicts instead of models (e.g. when we don't want to select all fields)
        self._return_dicts = False

    def make_query_with_params(self):
        """Combine all requests etc into sql query string and params."""
        select_where = 'AND '.join(self._select_where)
        select_fields = []
        for tablename in self._select_fields:
            # use AS for namespacing (e.g. querying from joined tables with same fields name)
            select_fields.extend(
                [
                    f'{tablename}.{field} AS {tablename}{NAMESPACE_SPLIT_KEY}{field}'
                    for field in self._select_fields[tablename].values()
                ]
            )
        query = self._base_query.format(
            select_fields=', '.join(select_fields),
            select_from=self.select_from,
        )
        if self._select_where:
            query += f'WHERE ({select_where})'
        return query, self._query_params

    def filter(self, **kwargs):
        """Filter results by kwargs where kwargs should be field for one of the queried models."""
        where_arg = '{tablename}.{fieldname}=?'
        where_params = []
        if 'db' in kwargs:
            where_params.append(kwargs.pop('db'))
            self._select_where.append(where_arg.format(
                tablename=self.model.__tablename__,
                fieldname=self.model.pk_db_name,
            ))
        for arg_name, value in kwargs.items():
            try:
                # get database field name for given kwarg
                self._select_where.append(where_arg.format(
                    tablename=self.model.__tablename__,
                    fieldname=self.model._meta['names'][arg_name]
                ))
                self._query_params.append(value)
            except KeyError:
                raise QueryError('No such field {0} on model {1}'.format(arg_name, self.model))
        return self

    def all(self) -> List:
        """Return all results as list with models or dicts."""
        query, params = self.make_query_with_params()
        rows = self.db._execute(query, params) or []
        if not self._return_dicts:
            fetched_models = [self.model.from_query_result(row) for row in rows]
            return fetched_models
        reverse_names = {}
        for table in self._select_fields.values():
            for table_name, db_name in table.items():
                reverse_names[db_name] = table_name
        dicts_to_return = []
        for row in rows:
            new_dict = {}
            for namespaced_name in row.keys():
                tablename, field_db_name = namespaced_name.split(NAMESPACE_SPLIT_KEY)
                new_name = tablename + '.' + reverse_names[field_db_name]
                new_dict[new_name] = row[namespaced_name]
            dicts_to_return.append(new_dict)
        return dicts_to_return

    def first(self):
        """Get first item as model or dict. Return None if no result."""
        self.limit = 'LIMIT 1'
        result = self.all()
        if not result:
            return None
        return result[0]

    def get(self, pk):
        """Return model with specified pk."""
        self._select_where.append(f'{self.pk_db_name}=?')
        self._query_params.append(pk)
        self.limit = 'LIMIT 1'
        query, params = self.make_query_with_params()
        rows = self.db._execute(query, params)
        if len(rows) > 1:
            raise MultipleRowsReturnedError(
                f'Expected 1 resulting row but {len(rows)} rows returned for {query} {params}'
            )
        elif len(rows) == 0:
            raise NotFoundError(f'No results for {query} {params}')
        row = rows[0]
        fetched_model = self.model.from_query_result(row)
        fetched_model.pk = pk
        fetched_model.fetched_from_db = True
        fetched_model.needs_update_in_db = False
        return fetched_model

    def join(self, join_with, **kwargs):
        """
        Join table with other model.
        Default behaviour is to join on fk, but `join_on` argument may be provided,
        where join_on should be a list with two fieldnames to make join for.
        """
        fk_dict = self.model._meta['fks'] or join_with._meta['fks']
        fk_name = [*fk_dict.keys()][0]
        fk_descriptor_left = getattr(self.model, fk_name, None)
        fk_descriptor_right = getattr(join_with, fk_name, None)
        left_side_db_name = fk_descriptor_left.db_name if fk_descriptor_left else self.model.pk_db_name()
        right_side_db_name = fk_descriptor_right.db_name if fk_descriptor_right else join_with.pk_db_name()

        if kwargs.get('join_on'):
            left_side_db_name = self.model._meta['names'][kwargs['join_on'][0]]
            right_side_db_name = join_with._meta['names'][kwargs['join_on'][1]]
        self.select_from = f'{self.model.__tablename__} JOIN {join_with.__tablename__} ON ' \
                           f'{self.model.__tablename__}.{left_side_db_name}={join_with.__tablename__}.{right_side_db_name}'
        return self

    def select(self, model, fields: Iterable):
        """Select kwargs fields from model."""
        if isinstance(fields, str):
            raise ValueError('fields cannot be a string, it must be a container with strings.')
        reverse_names = {db_name: model_name for model_name, db_name in model._meta['names'].items()}
        # reset fields if there was no select before
        if not self._return_dicts:
            self._select_fields = {}
        for field in fields:
            try:
                self._select_fields.setdefault(model.__tablename__, {})[field] = reverse_names[field]
            except KeyError:
                raise QueryError(f'No field {field} on model {model}.')
        self._return_dicts = True
        return self


class Database:
    """Class to hold connection and do db management (model creation, deletion etc.)."""

    def __init__(self, filename=':memory:', verbose=False):
        self.filename = filename
        self.query = Query
        self.query.db = self
        self.BaseModel = BaseModel
        # backref to db for foreign key support
        self.BaseModel.db = self
        self.con = sqlite3.connect(filename)
        self.con.row_factory = sqlite3.Row
        self.cursor = self.con.cursor()
        if verbose:
            self.con.set_trace_callback(lambda query: print(query))

    def create_all(self, raise_if_exists=False):
        """
        Create all tables for models registered in db.
        :param raise_if_exists: if True raises error if one of tables already exists in db
        """
        sql = ' '.join(
            model.table_definition_sql(raise_if_exists=raise_if_exists)
            for model in self.BaseModel.registered_models
        )
        try:
            self.cursor.executescript(sql)
        except sqlite3.OperationalError as e:
            raise dbIntegrityError(e)
        self.con.commit()

    def _execute(self, sql, params=None, commit=False):
        """
        Execute raw sql.
        :param sql: SQL string.
        :param params: params for ? in sql string
        :param commit: if True issue COMMIT after transaction
        """
        sql = sql+';' if not sql.endswith(';') else sql
        try:
            if not params:
                self.cursor.execute(sql)
                if commit:
                    self.con.commit()
                return self.cursor.fetchall()
            self.cursor.execute(sql, params)
            if commit:
                self.con.commit()
            return self.cursor.fetchall()
        except sqlite3.OperationalError as e:
            raise QueryError(e)

    def add(self, model):
        """Insert model to db or update it."""
        sql, values = self._get_add_sql(model)
        self._execute(sql, values, commit=True)
        pk = model.pk or self.cursor.lastrowid
        model.pk = pk
        model.fetched_from_db = True
        model.needs_update_in_db = False
        return model

    def _get_add_sql(self, model):
        """Get sql appropriate for given model (INSERT or UPDATE)."""
        sql, values = '', ''
        if model.fetched_from_db and model.needs_update_in_db:
            sql, values = self._update(model)
        elif model.needs_update_in_db:
            sql, values = self._insert(model)
        else:
            pass
        return sql, values

    def _update(self, model):
        values = []
        names = []
        for model_name, db_name in model._meta['names'].items():
            value = getattr(model, model_name)
            if isinstance(model.__class__.__dict__[model_name], ForeignKeyField):
                value = value.pk
            names.append(db_name)
            values.append(value)
            if model_name in model._meta['pks']:
                continue

        name_val_pairs = ['='.join([name, '?']) for name in names]
        field_values = ', '.join(name_val_pairs)

        sql = 'UPDATE {tablename} SET {field_values} WHERE {pk_field_name}={model_pk}'.format(
            tablename=model.__tablename__,
            field_values=field_values,
            pk_field_name=model.pk_db_name(),
            model_pk=model.pk,
        )
        return sql, values

    def _insert(self, model):
        values = []

        for model_name, db_name in model._meta['names'].items():
            value = getattr(model, model_name)
            if isinstance(model.__class__.__dict__[model_name], ForeignKeyField):
                value = value.pk
            values.append(value)

        q_marks = ['?' for _ in range(len(values))]
        values_escaped = '(' + ','.join(q_marks) + ')'
        sql = 'INSERT INTO {tablename} VALUES {values}'.format(
            tablename=model.__tablename__,
            values=values_escaped,
        )
        return sql, values

    def drop(self, model):
        """Drop table corresponding to model."""
        sql = f'DROP TABLE IF EXISTS {model.__tablename__}'
        return self._execute(sql, commit=True)

    def close(self):
        """Close cursor and connection."""
        try:
            self.cursor.close()
            self.con.close()
        except sqlite3.ProgrammingError:
            raise DatabaseClosedError('Database is already closed')


from superset.common.query_context import QueryContext
from superset.datasets.dao import DatasetDAO
from superset.superset_typing import AdhocColumn
from superset.utils.core import DatasourceDict

def get_table_data_from_history(id):
    table = DatasetDAO.find_by_id(id)
    return [{'id': a.id, 'expression': a.expression, 'changed_on': a.changed_on.isoformat(), 'description': a.description, 'type': a.type, 'column_name': a.column_name} for a in table.columns]
def get_table_from_name(table_name):
    table = DatasetDAO.find_table_by_name(table_name)
    return table

def get_column_from_name(column_name):
    column = DatasetDAO.find_column_by_name(column_name)
    return AdhocColumn(columnType=column.type, id=column.id, column_name = column.column_name, groupby = True)

def serialize_query_context(qc: QueryContext):
    datasource = DatasourceDict(type=qc.datasource.type, id=str(qc.datasource.id))
    return None


def get_time_column(table_name):
    table = DatasetDAO.find_table_by_name(table_name)
    return table.time_column_grains['time_columns'][0]


# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""
Datamanage model.

This model was introduced in SIP-68 (https://github.com/apache/superset/issues/14909),
and represents a "datamanage" -- either a physical table or a virtual. In addition to a
datamanage, new models for columns, metrics, and tables were also introduced.

These models are not fully implemented, and shouldn't be used yet.
"""

from typing import List

import sqlalchemy as sa
from flask_appbuilder import Model
from sqlalchemy.orm import backref, relationship

from superset import security_manager
from superset.columns.models import Column
from superset.models.core import Database
from superset.models.helpers import (
    AuditMixinNullable,
    ExtraJSONMixin,
    ImportExportMixin,
)
from superset.tables.models import Table

datamanage_column_association_table = sa.Table(
    "sl_datamanage_columns",
    Model.metadata,  # pylint: disable=no-member
    sa.Column(
        "datamanage_id",
        sa.ForeignKey("sl_datamanages.id"),
        primary_key=True,
    ),
    sa.Column(
        "column_id",
        sa.ForeignKey("sl_columns.id"),
        primary_key=True,
    ),
)

datamanage_table_association_table = sa.Table(
    "sl_datamanage_tables",
    Model.metadata,  # pylint: disable=no-member
    sa.Column("datamanage_id", sa.ForeignKey("sl_datamanages.id"), primary_key=True),
    sa.Column("table_id", sa.ForeignKey("sl_tables.id"), primary_key=True),
)

datamanage_user_association_table = sa.Table(
    "sl_datamanage_users",
    Model.metadata,  # pylint: disable=no-member
    sa.Column("datamanage_id", sa.ForeignKey("sl_datamanages.id"), primary_key=True),
    sa.Column("user_id", sa.ForeignKey("ab_user.id"), primary_key=True),
)


class Datamanage(Model, AuditMixinNullable, ExtraJSONMixin, ImportExportMixin):
    """
    A table/view in a database.
    """

    __tablename__ = "sl_datamanages"

    id = sa.Column(sa.Integer, primary_key=True)
    database_id = sa.Column(sa.Integer, sa.ForeignKey("dbs.id"), nullable=False)
    database: Database = relationship(
        "Database",
        backref=backref("datamanage", cascade="all, delete-orphan"),
        foreign_keys=[database_id],
    )
    # The relationship between datamanage and columns is 1:n, but we use a
    # many-to-many association table to avoid adding two mutually exclusive
    # columns(datamanage_id and table_id) to Column
    columns: List[Column] = relationship(
        "Column",
        secondary=datamanage_column_association_table,
        cascade="all, delete-orphan",
        single_parent=True,
        backref="datamanage",
    )
    owners = relationship(
        security_manager.user_model, secondary=datamanage_user_association_table
    )
    tables: List[Table] = relationship(
        "Table", secondary=datamanage_table_association_table, backref="datamanage"
    )

    # Does the datamanage point directly to a ``Table``?
    is_physical = sa.Column(sa.Boolean, default=False)

    # Column is managed externally and should be read-only inside Superset
    is_managed_externally = sa.Column(sa.Boolean, nullable=False, default=False)

    # We use ``sa.Text`` for these attributes because (1) in modern databases the
    # performance is the same as ``VARCHAR``[1] and (2) because some table names can be
    # **really** long (eg, Google Sheets URLs).
    #
    # [1] https://www.postgresql.org/docs/9.1/datatype-character.html
    name = sa.Column(sa.Text)
    expression = sa.Column(sa.Text)
    external_url = sa.Column(sa.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Datamanage id={self.id} database_id={self.database_id} {self.name}>"

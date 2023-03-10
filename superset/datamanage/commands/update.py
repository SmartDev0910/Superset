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
import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from flask_appbuilder.models.sqla import Model
from marshmallow import ValidationError

from superset import security_manager
from superset.commands.base import BaseCommand, UpdateMixin
from superset.connectors.sqla.models import SqlaTable
from superset.dao.exceptions import DAOUpdateFailedError
from superset.datamanage.commands.exceptions import (
    DatabaseChangeValidationError,
    DatamanageColumnNotFoundValidationError,
    DatamanageColumnsDuplicateValidationError,
    DatamanageColumnsExistsValidationError,
    DatamanageExistsValidationError,
    DatamanageForbiddenError,
    DatamanageInvalidError,
    DatamanageMetricsDuplicateValidationError,
    DatamanageMetricsExistsValidationError,
    DatamanageMetricsNotFoundValidationError,
    DatamanageNotFoundError,
    DatamanageUpdateFailedError,
)
from superset.datamanage.dao import DatamanageDAO
from superset.exceptions import SupersetSecurityException

logger = logging.getLogger(__name__)


class UpdateDatamanageCommand(UpdateMixin, BaseCommand):
    def __init__(
        self,
        model_id: int,
        data: Dict[str, Any],
        override_columns: Optional[bool] = False,
    ):
        self._model_id = model_id
        self._properties = data.copy()
        self._model: Optional[SqlaTable] = None
        self.override_columns = override_columns
        self._properties["override_columns"] = override_columns

    def run(self) -> Model:
        self.validate()
        if self._model:
            try:
                datamanage = DatamanageDAO.update(
                    model=self._model,
                    properties=self._properties,
                )
                return datamanage
            except DAOUpdateFailedError as ex:
                logger.exception(ex.exception)
                raise DatamanageUpdateFailedError() from ex
        raise DatamanageUpdateFailedError()

    def validate(self) -> None:
        exceptions: List[ValidationError] = []
        owner_ids: Optional[List[int]] = self._properties.get("owners")
        # Validate/populate model exists
        self._model = DatamanageDAO.find_by_id(self._model_id)
        if not self._model:
            raise DatamanageNotFoundError()
        # Check ownership
        try:
            security_manager.raise_for_ownership(self._model)
        except SupersetSecurityException as ex:
            raise DatamanageForbiddenError() from ex

        database_id = self._properties.get("database", None)
        table_name = self._properties.get("table_name", None)
        # Validate uniqueness
        if not DatamanageDAO.validate_update_uniqueness(
            self._model.database_id, self._model_id, table_name
        ):
            exceptions.append(DatamanageExistsValidationError(table_name))
        # Validate/Populate database not allowed to change
        if database_id and database_id != self._model:
            exceptions.append(DatabaseChangeValidationError())
        # Validate/Populate owner
        try:
            owners = self.populate_owners(owner_ids)
            self._properties["owners"] = owners
        except ValidationError as ex:
            exceptions.append(ex)

        # Validate columns
        columns = self._properties.get("columns")
        if columns:
            self._validate_columns(columns, exceptions)

        # Validate metrics
        metrics = self._properties.get("metrics")
        if metrics:
            self._validate_metrics(metrics, exceptions)

        if exceptions:
            exception = DatamanageInvalidError()
            exception.add_list(exceptions)
            raise exception

    def _validate_columns(
        self, columns: List[Dict[str, Any]], exceptions: List[ValidationError]
    ) -> None:
        # Validate duplicates on data
        if self._get_duplicates(columns, "column_name"):
            exceptions.append(DatamanageColumnsDuplicateValidationError())
        else:
            # validate invalid id's
            columns_ids: List[int] = [
                column["id"] for column in columns if "id" in column
            ]
            if not DatamanageDAO.validate_columns_exist(self._model_id, columns_ids):
                exceptions.append(DatamanageColumnNotFoundValidationError())

            # validate new column names uniqueness
            if not self.override_columns:
                columns_names: List[str] = [
                    column["column_name"] for column in columns if "id" not in column
                ]
                if not DatamanageDAO.validate_columns_uniqueness(
                    self._model_id, columns_names
                ):
                    exceptions.append(DatamanageColumnsExistsValidationError())

    def _validate_metrics(
        self, metrics: List[Dict[str, Any]], exceptions: List[ValidationError]
    ) -> None:
        if self._get_duplicates(metrics, "metric_name"):
            exceptions.append(DatamanageMetricsDuplicateValidationError())
        else:
            # validate invalid id's
            metrics_ids: List[int] = [
                metric["id"] for metric in metrics if "id" in metric
            ]
            if not DatamanageDAO.validate_metrics_exist(self._model_id, metrics_ids):
                exceptions.append(DatamanageMetricsNotFoundValidationError())
            # validate new metric names uniqueness
            metric_names: List[str] = [
                metric["metric_name"] for metric in metrics if "id" not in metric
            ]
            if not DatamanageDAO.validate_metrics_uniqueness(self._model_id, metric_names):
                exceptions.append(DatamanageMetricsExistsValidationError())

    @staticmethod
    def _get_duplicates(data: List[Dict[str, Any]], key: str) -> List[str]:
        duplicates = [
            name
            for name, count in Counter([item[key] for item in data]).items()
            if count > 1
        ]
        return duplicates

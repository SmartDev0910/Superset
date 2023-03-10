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
from typing import Optional

from flask_appbuilder.models.sqla import Model
from sqlalchemy.exc import SQLAlchemyError

from superset import security_manager
from superset.commands.base import BaseCommand
from superset.connectors.sqla.models import SqlaTable
from superset.dao.exceptions import DAODeleteFailedError
from superset.datamanage.commands.exceptions import (
    DatamanageDeleteFailedError,
    DatamanageForbiddenError,
    DatamanageNotFoundError,
)
from superset.datamanage.dao import DatamanageDAO
from superset.exceptions import SupersetSecurityException
from superset.extensions import db

logger = logging.getLogger(__name__)


class DeleteDatamanageCommand(BaseCommand):
    def __init__(self, model_id: int):
        self._model_id = model_id
        self._model: Optional[SqlaTable] = None

    def run(self) -> Model:
        self.validate()
        try:
            datamanage = DatamanageDAO.delete(self._model, commit=False)
            db.session.commit()
        except (SQLAlchemyError, DAODeleteFailedError) as ex:
            logger.exception(ex)
            db.session.rollback()
            raise DatamanageDeleteFailedError() from ex
        return datamanage

    def validate(self) -> None:
        # Validate/populate model exists
        self._model = DatamanageDAO.find_by_id(self._model_id)
        if not self._model:
            raise DatamanageNotFoundError()
        # Check ownership
        try:
            security_manager.raise_for_ownership(self._model)
        except SupersetSecurityException as ex:
            raise DatamanageForbiddenError() from ex

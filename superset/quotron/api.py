import datetime
import json
import logging

import requests
import sqlparse
from flask import g, request, Response
from flask_appbuilder.api import BaseApi, expose
from sql_metadata import Parser

from superset.charts.commands.create import CreateChartCommand
from superset.charts.schemas import ChartPostSchema
from superset.common.query_context import QueryContext
from superset.common.query_context_factory import QueryContextFactory
from superset.common.query_object import QueryObject
from superset.datasets.commands.exceptions import DatasetNotFoundError
from superset.datasets.dao import DatasetDAO
from superset.extensions import event_logger, cache_manager
from superset.quotron import firestore_db, utils
from superset.quotron.DataTypes import Autocomplete, QuotronChart, Params, Answer, \
    QuotronQueryContext
from superset.quotron.firestore_db import getColumnHistory, update_table
from superset.quotron.schemas import AutoCompleteSchema, QuestionSchema, AnswerSchema, \
    ColumnHistorySchema
import superset.quotron.utils
from superset.superset_typing import AdhocMetric, AdhocColumn
from superset.utils.core import DatasourceDict, AdhocFilterClause, \
    QueryObjectFilterClause
import re
logger = logging.getLogger(__name__)


def get_where_clause(sql):
    parsed_sql = sqlparse.parse(sql)
    for item in parsed_sql[0].tokens:
        if isinstance(item, sqlparse.sql.Where):
            clause = item.value
            stripped_clause = re.sub('WHERE', '', clause, flags=re.IGNORECASE)
            logger.debug(f'stripped clause: {stripped_clause}')
            return f'{stripped_clause}'



class QuotronRestApi(BaseApi):
    include_route_methods = {
        "auto_complete", "answer", "answer_debug", "column_history", "init_column_history"
    }
    resource_name = "quotron"
    openapi_spec_tag = "Quotron"
    openapi_spec_component_schemas = (AutoCompleteSchema, QuestionSchema,ColumnHistorySchema, AnswerSchema)

    @cache_manager.cache.memoize(timeout=60)
    @expose("/auto_complete/", methods=["GET"])
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.data",
        log_to_statsd=False,
    )
    def auto_complete(self) -> Response:
        """
                ---
                get:
                  description: Auto complete for questions
                  responses:
                    200:
                      description: Auto complete questions for currently logged in user
                      content:
                        application/json:
                            schema:
                                $ref: "#/components/schemas/AutoCompleteSchema"
                """
        logger.info(g.user)
        autoCompleteQuestions = firestore_db.getAutoComplete()
        logger.info(autoCompleteQuestions)
        autocomplete = Autocomplete(email=g.user.email,question="what is the highest revenue?", time=datetime.datetime.now())

        schema = AutoCompleteSchema()
        result = schema.dump(autocomplete)
        return self.response(200, result = [result])
    @expose("/answer/", methods=["POST"])
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.data",
        log_to_statsd=False,
    )
    def answer(self) -> Response:
        """
        Takes a natural langauge question and generate a corresponding graph/ slice
        ---
        post:
          description: >-
            Takes a natural langauge question and generate a corresponding graph/ slice
          requestBody:
            description: >-
              Question context that has natural langauge question and metadata
            required: true
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/QuestionSchema"
                example:
                    {
                    "question": "what is the highest revenue?"
                    }


          responses:
            200:
              description: Query result
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/AnswerSchema"

            400:
              $ref: '#/components/responses/400'
            401:
              $ref: '#/components/responses/401'
            500:
              $ref: '#/components/responses/500'
        """
        req = QuestionSchema().load(request.json)
        question = req['question']
        answer = Answer(question=question, answer='{placeholder}', slice_id=1322)
        schema = AnswerSchema()
        result = schema.dump(answer)
        return self.response(200, result=result)

    @expose("/answer_debug/", methods=["POST"])
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.data",
        log_to_statsd=False,
    )
    def answer_debug(self) -> Response:
        """
        Takes a natural langauge question and generate a corresponding graph/ slice
        ---
        post:
          description: >-
            Takes a natural langauge question and generate a corresponding graph/ slice
          requestBody:
            description: >-
              Question context that has natural langauge question and metadata
            required: true
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/QuestionSchema"
                example:
                    {
                    "question": "what is the highest revenue?"
                    }


          responses:
            200:
              description: Query result
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/AnswerSchema"

            400:
              $ref: '#/components/responses/400'
            401:
              $ref: '#/components/responses/401'
            500:
              $ref: '#/components/responses/500'
        """
        req = QuestionSchema().load(request.json)
        logger.info(g.user)
        question = req['question']
        data = {
  "email": "test@quotron.ai",
  "question": question
}
        #1. Get quotron SQL query
        resp =requests.post(f'https://nlp.quotron.ai/answer', data = json.dumps(data))

        #2. Parse quotron query
        sql = resp.json()['sql']['generated_code']
        where_clause = get_where_clause(sql)
        columns = Parser(sql).columns
        table = Parser(sql).tables[0]
        logger.info(columns)
        logger.info(table)
        add_model_schema = ChartPostSchema()
        time_column = utils.get_time_column(table)
        table = utils.get_table_from_name(table)
        superset_columns = []
        for column in columns:
            superset_columns.append(utils.get_column_from_name(column))

        superset_metrics = []
        for superset_column in superset_columns:
            superset_metrics.append(AdhocMetric(aggregate='AVG', column=superset_column, expressionType='SIMPLE'))

        series_limit_metric = AdhocMetric(aggregate='AVG', column=utils.get_column_from_name(time_column),expressionType='SIMPLE' )

        datasource = DatasourceDict(type="table",id=str(table.id))
        extras = {
			"having": "",
			"where": where_clause
		}

        queryObject = QueryObject(datasource=json.dumps(datasource),columns = superset_columns,
                                  metrics = superset_metrics, series_limit_metric = series_limit_metric, row_limit = 10000, extras=extras)

        qc = QueryContextFactory().create(
            datasource=datasource,
            queries=[],
            result_type='full',
            result_format='json'
        )
        qc.queries.append(queryObject)
        adhoc_filters = [{
		"expressionType": "SQL",
		"sqlExpression": where_clause,
		"clause": "WHERE",
	}]
        params = Params(datasource=datasource['id'] + '__' + datasource['type'], viz_type="dist_bar",
                        time_range="No Filter",
                        metrics=superset_metrics,groupby=[time_column],
                        timeseries_limit_metric=series_limit_metric,
                        order_desc=False,
                        adhoc_filters=adhoc_filters,
                        zoomable = True,
                        time_grain_sqla=None)
        quotronQueryContext = QuotronQueryContext(datasource=datasource, queries=qc.queries, result_format=qc.result_format, result_type=qc.result_type )
        quotronChart = QuotronChart(slice_name=question, viz_type="dist_bar",datasource_id=table.id, datasource_type="table",
                                    query_context=json.dumps(quotronQueryContext, default=lambda o: o.__dict__, indent=4),
                                    params =json.dumps(params.__dict__, default=lambda o: '<not serializable>'))
        result = add_model_schema.dump(quotronChart)
        new_model = CreateChartCommand(result).run()
        logger.info(new_model)
        answer = Answer(question=question, answer='{placeholder}', slice_id=new_model.id)
        schema = AnswerSchema()
        result = schema.dump(answer)
        return self.response(200, result = result)

    @expose("/column_history/<pk>", methods=["GET"])
    def column_history(self, pk: int) -> Response:
        """
                ---
                get:
                  description: get column history
                  parameters:
                      - in: path
                        name: pk
                        schema:
                          type: integer
                  responses:
                    200:
                      description: Column history of user's changes
                      content:
                        application/json:
                            schema:
                                $ref: "#/components/schemas/ColumnHistorySchema"
                    404:

        """
        try:
            column_history  = getColumnHistory(column_id=pk)
            logger.info(column_history)
            return self.response(200, result = column_history)
        except DatasetNotFoundError:
            response = self.response_404()
            return response


    @expose("/init_column_history", methods=["GET"])
    def init_column_history(self) -> Response:
        """
                ---
                get:
                  description: init column history API to initialize google firebase once.

                  responses:
                    200:
                      description: Gets column history
                      content:
                        application/json:
                    404:
                        description: returns 404 if history record is absent for given column id.


                """
        try:
            tables = DatasetDAO.find_all()
            for table in tables:
                update_table(table.id)
                logger.info(table.id)
        except DatasetNotFoundError:
            response = self.response_404()































































































































































































































































































































































































































































































































































































































































































































































































































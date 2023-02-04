import json
import string
from datetime import datetime
import superset.quotron.utils
from google.cloud import firestore
from loguru import logger

from superset.datasets.commands.exceptions import DatasetNotFoundError
from superset.quotron import settings
from superset.quotron.settings import firestore_settings

def update_table(table):
    data = superset.quotron.utils.get_table_data_from_history(table)
    db = firestore.Client()
    transaction = db.transaction()
    for column in data:
        column_id = column['id']
        column_changed_on = column['changed_on']
        question_ref = db.collection(
            firestore_settings.columns_collection_name + f'/{column_id}/{column_changed_on}').document(
            'column_data')
        try:
            question_ref.set(column)
        except Exception as e:
            logger.warning(
                f"error while trying to save to firestore: {data}, {e.with_traceback()}")



def update(question, email, answer):
    data = {
        u'question': question,
        u'time': datetime.utcnow(),
        u'email': email,
        u'answer': answer
    }
    db = firestore.Client()
    transaction = db.transaction()
    question_ref = db.collection(firestore_settings.query_collection_name).document(
        question.upper())
    try:
        question_ref.set(data)
    except Exception as e:
        logger.warning(
            f"error while trying to save to firestore: {data}, {e.with_traceback()}")


def getColumnHistory(column_id):
    try:
        db = firestore.Client()
        collections = db.collection(u'columns').document(f'{column_id}').collections()
        docs = []
        for collection in collections:
            for doc in collection.stream():
                docs.append(doc.to_dict())
        if docs:
            return docs
        else:
            raise DatasetNotFoundError()
    except Exception as ex:
        logger.exception(ex)
        raise Exception() from ex


def getAutoComplete():
    db = firestore.Client()
    # [START firestore_data_get_all_documents]

    docs = db.collection(settings.firestore.query_collection_name).order_by(
        u'time', direction=firestore.Query.DESCENDING).stream()
    q = []
    for doc in docs:
        full_dict = doc.to_dict()
        dict = {key: value for key, value in full_dict.items() if key != 'answer'}
        q.append(dict)

    return q


def getDocument(documentReference):
    db = firestore.Client()
    # [START firestore_data_get_all_documents]
    docs = []
    if documentReference is None:
        docs = db.collection(firestore_settings.document_collection_name).order_by(
            u'documentLastUpdated', direction=firestore.Query.DESCENDING).stream()
    else:
        docs.append(db.collection(firestore_settings.document_collection_name).document(
            documentReference).get())
    q = []
    for doc in docs:
        full_dict = doc.to_dict()
        q.append(full_dict)
    return q

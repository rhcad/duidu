#!/usr/bin/env python3
import pymongo
import fire
from pymongo.errors import OperationFailure

indexes = {
    'user': ['username:unique', 'nickname'],
    'proj': ['code', 'name', 'created_by', 'editors', 'published', 'cols'],
    'article': ['proj_id', 'code', 'name', 'type', 'created_by', 'sections'],
    'section': ['a_id', 'name'],
    'cb': ['name:unique']
}


def main(db_name='duidu', uri='localhost'):
    with pymongo.MongoClient(uri) as client:
        db = client[db_name]
        for coll, fields in indexes.items():
            for f in fields:
                f, kind = (f + ':').split(':', maxsplit=1)
                try:
                    db[coll].create_index(f, name=f, unique=kind == 'unique')
                except OperationFailure:
                    pass


if __name__ == '__main__':
    fire.Fire(main)

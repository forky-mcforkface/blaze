from __future__ import absolute_import, division, print_function

try:
    from pymongo.collection import Collection
except ImportError:
    Collection = None

from .dispatch import dispatch
from datashape import discover, isdimension, dshape
from collections import Iterator
from toolz import take, concat, partition_all
from .data.core import DataDescriptor
from .compute.mongo import *
import copy


@dispatch(Collection)
def discover(coll, n=50):
    items = list(take(n, coll.find()))
    for item in items:
        del item['_id']

    ds = discover(items)

    if isdimension(ds[0]):
        return coll.count() * ds.subshape[0]
    else:
        raise ValueError("Consistent datashape not found")


@dispatch(Collection, DataDescriptor)
def into(coll, dd, chunksize=1024):
    return into(coll, iter(dd), chunksize=chunksize, schema=dd.schema)


@dispatch(Collection, (tuple, list, Iterator))
def into(coll, seq, columns=None, schema=None, chunksize=1024):
    seq = iter(seq)
    item = next(seq)
    seq = concat([[item], seq])

    if isinstance(item, (tuple, list)):
        if not columns and schema:
            columns = dshape(schema)[0].names
        if not columns:
            raise ValueError("Inputs must be dictionaries. "
                "Or provide columns=[...] or schema=DataShape(...) keyword")
        seq = (dict(zip(columns, item)) for item in seq)

    for block in partition_all(1024, seq):
        coll.insert(copy.deepcopy(block))

    return coll


@dispatch(Collection, TableExpr)
def into(coll, t, **kwargs):
    from blaze import compute
    result = compute(t)
    return into(coll, result, schema=t.schema, **kwargs)


@dispatch((tuple, list), Collection)
def into(l, coll, columns=None, schema=None):
    seq = list(coll.find())
    for item in seq:
        del item['_id']

    return type(l)(seq)


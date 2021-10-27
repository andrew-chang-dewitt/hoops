"""A Model for Transaction data types."""

import datetime
from typing import List, Optional

from db_wrapper.client import SyncClient
from db_wrapper.model import (
    ModelData,
    SyncModel,
    SyncRead,
    sql,
)


class TransactionData(ModelData):
    """An example Item."""

    # Essentially a dataclass, has no methods
    # pylint: disable=too-few-public-methods

    amount: float
    description: str
    payee: str
    timestamp: datetime.datetime


class TransactionReader(SyncRead[TransactionData]):
    """Additional read methods."""

    def many(self, limit: Optional[int]) -> List[TransactionData]:
        """Return many transaction records."""
        query = sql.SQL(
            'SELECT * '
            'FROM {table} '
            'ORDER BY timestamp'
            'LIMIT {limit}'
        ).format(
            table=self._table,
            limit=limit,
        )

        return self._client.execute_and_return(query)


class Transaction(SyncModel[TransactionData]):
    """Build an Transaction Model instance."""

    read: TransactionReader

    def __init__(self, client: SyncClient) -> None:
        table = 'transaction'

        super().__init__(client, table)
        self.read = TransactionReader(client, table)
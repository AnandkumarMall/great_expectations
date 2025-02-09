from uuid import uuid4

import pytest

from great_expectations.compatibility.pydantic import ValidationError, errors
from great_expectations.metrics.domain import ColumnMap, Domain, Map

BATCH_ID = str(uuid4())
TABLE = "my_table"
COLUMN = "my_column"


class TestAbstractClasses:
    def test_domain_instantiation_raises(self):
        with pytest.raises(TypeError):
            Domain(batch_id=BATCH_ID)

    def test_map_instantiation_raises(self):
        with pytest.raises(TypeError):
            Map(batch_id=BATCH_ID, table=TABLE)


class TestColumnMap:
    def test_column_map_instantiation_success(self):
        ColumnMap(batch_id=BATCH_ID, table=TABLE, column=COLUMN)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"batch_id": "", "table": TABLE, "column": COLUMN},
            {"batch_id": BATCH_ID, "table": "", "column": COLUMN},
            {"batch_id": BATCH_ID, "table": TABLE, "column": ""},
        ],
    )
    def test_column_map_arguments_empty_string_raises(self, kwargs: dict):
        with pytest.raises(ValidationError) as e:
            ColumnMap(**kwargs)
        all_errors = e.value.raw_errors
        assert any(
            True if isinstance(error.exc, errors.AnyStrMinLengthError) else False
            for error in all_errors
        )

from great_expectations.expectations.expectation import Expectation


class ExpectSourceQueryToMatchTargetQuery(Expectation):
    source_query: str
    target_query: str

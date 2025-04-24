from __future__ import annotations

from collections import Counter

import requests

from great_expectations.compatibility.typing_extensions import override
from great_expectations.data_context.store import gx_cloud_store_backend


class TrackedSession(requests.Session):
    _requests: list[tuple[str, str]] = []

    @override
    def request(self, method, url, *args, **kwargs):
        self.track_request(method, url)
        return super().request(method, url, *args, **kwargs)

    def track_request(self, method: str, url: str) -> None:
        self._requests.append((method, url))

    def get_request_counts(self) -> Counter:
        return Counter(self._requests)

    def clear(self) -> None:
        self._requests.clear()

    def print_summary(self) -> None:
        print("\nRequest Statistics:")
        print("------------------")
        print("\nAll Requests:")
        for method, url in self._requests:
            print(f"{method} {url}")

        print("\nRequest Counts:")
        for (method, url), count in self.get_request_counts().items():
            print(f"{count}: {method} {url}")

    @classmethod
    def override_session(cls) -> TrackedSession:
        """Helper method to be used in custom scripts to override the requests.Session class.

        Prefer `mocker.patch("requests.Session", return_value=tracked_session)` over this for tests.
        """
        tracked_session = TrackedSession()
        gx_cloud_store_backend.requests.Session = lambda: tracked_session  # type: ignore[assignment]
        return tracked_session

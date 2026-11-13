"""Polite, cache-first client for the public NASA PSI repository API."""

import csv
import io
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PSIResponse:
    value: dict | list | str
    source_url: str
    cache_path: Path


class PSIClient:
    """Public PSI API client. Responses are cached as immutable raw artifacts."""

    base_url = "https://psi.nasa.gov/geode-py/ws"

    def __init__(self, raw_dir: Path, min_interval_seconds: float = 0.5):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval_seconds = min_interval_seconds
        self._last_request = 0.0

    def _request(self, url: str, *, data: bytes | None = None) -> bytes:
        wait = self.min_interval_seconds - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        headers = {"User-Agent": "nasa-fire-ai-mvp/0.1"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
        self._last_request = time.monotonic()
        return payload

    def _cached_json(self, investigation_id: str, kind: str, url: str, data: bytes | None = None):
        path = self.raw_dir / f"{investigation_id}_{kind}.json"
        if not path.exists():
            path.write_bytes(self._request(url, data=data))
        return PSIResponse(json.loads(path.read_text()), url, path)

    def get_investigation(self, investigation_id: str) -> PSIResponse:
        return self._cached_json(
            investigation_id,
            "metadata",
            f"{self.base_url}/studies/{urllib.parse.quote(investigation_id)}/metadata",
        )

    def get_versions(self, investigation_id: str) -> PSIResponse:
        return self._cached_json(
            investigation_id,
            "versions",
            f"{self.base_url}/repo/investigations/{urllib.parse.quote(investigation_id)}/versions",
        )

    def list_files(self, investigation_id: str) -> PSIResponse:
        metadata = self.get_investigation(investigation_id).value
        version = int(metadata.get("version", 0))
        payload = json.dumps(
            {
                "folder": "",
                "fileType": "study",
                "studyId": investigation_id,
                "version": version,
                "obfuscationcode": "",
            }
        ).encode()
        return self._cached_json(
            investigation_id, "files", f"{self.base_url}/files/v2", data=payload
        )

    def get_experimental_table(self, investigation_id: str) -> PSIResponse:
        listing = self.list_files(investigation_id).value
        candidates = [
            item
            for group in listing.get("files", [])
            if group.get("displayName", "").lower() == "experimental table"
            for item in group.get("files", [])
            if item.get("key", "").lower().endswith(".csv")
        ]
        if not candidates:
            raise LookupError(f"No CSV experimental table exposed by PSI for {investigation_id}")
        item = candidates[0]
        raw_path = self.raw_dir / f"{investigation_id}_experimental_table.csv"
        endpoint = f"{self.base_url}/studies/{urllib.parse.quote(investigation_id)}/download"
        filename = Path(item["key"]).name
        request_url = (
            endpoint
            + "?"
            + urllib.parse.urlencode(
                {"file": filename, "version": item.get("version", 0), "redirect": "false"},
                quote_via=urllib.parse.quote,
            )
        )
        if not raw_path.exists():
            signed_url = self._request(request_url).decode().strip()
            if not signed_url.startswith("https://"):
                raise RuntimeError(f"PSI did not return a public download URL: {signed_url[:160]}")
            raw_path.write_bytes(self._request(signed_url))
        try:
            table_text = raw_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            # Legacy PSI tables contain Windows punctuation. Preserve the bytes;
            # decode losslessly rather than replacing or deleting characters.
            table_text = raw_path.read_text(encoding="cp1252")
        return PSIResponse(table_text, request_url, raw_path)


def parse_experimental_table(csv_text: str) -> list[dict[str, str]]:
    """Parse PSI CSV exactly as reported; empty non-run rows remain distinguishable."""
    return [
        {key.strip(): value.strip() for key, value in row.items()}
        for row in csv.DictReader(io.StringIO(csv_text))
    ]

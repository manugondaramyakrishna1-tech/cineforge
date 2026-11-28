"""Hosted text-to-video generation through Replicate's HTTP API.

CineForge keeps provider credentials server-side (environment or Streamlit secrets).
The uploaded JSON template contains a model slug and that model's input schema.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_BASE = "https://api.replicate.com/v1"
_ALLOWED_FILE_HOSTS = ("replicate.delivery", "replicate.com", "replicateusercontent.com")


def replace_placeholders(value, replacements):
    if isinstance(value, dict):
        return {key: replace_placeholders(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_placeholders(item, replacements) for item in value]
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, str(new))
    return value


def validate_workflow(workflow):
    issues = []
    if not isinstance(workflow, dict):
        return ["Hosted model template must be a JSON object."]
    model = str(workflow.get("model", "")).strip()
    if model.count("/") != 1 or any(not part for part in model.split("/")):
        issues.append("Hosted template needs a model field in owner/model format.")
    if not isinstance(workflow.get("input"), dict) or not workflow.get("input"):
        issues.append("Hosted template needs a non-empty input object matching the selected model's API schema.")
    elif not any("__PROMPT__" in str(value) for value in _walk_values(workflow["input"])):
        issues.append("Add the __PROMPT__ placeholder to the model's prompt input field.")
    return issues


def _walk_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


class ReplicateVideo:
    """Replicate hosted video adapter with the same render interface as ComfyUI."""

    def __init__(self, token=None, timeout=60):
        self.token = (token or os.environ.get("REPLICATE_API_TOKEN", "")).strip()
        if not self.token:
            raise ValueError("REPLICATE_API_TOKEN is not configured in the server environment or Streamlit secrets.")
        self.timeout = max(5, int(timeout))

    @staticmethod
    def replace_placeholders(value, replacements):
        return replace_placeholders(value, replacements)

    def _request(self, url, data=None, timeout=None):
        if not url.startswith(API_BASE + "/"):
            raise ValueError("Refusing to call an unexpected hosted API URL.")
        body = None if data is None else json.dumps(data).encode("utf-8")
        headers = {"Authorization": "Bearer " + self.token, "Content-Type": "application/json"}
        request = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1200]
            raise RuntimeError(f"Hosted video API returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Could not reach hosted video API: {exc}") from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Hosted video API returned invalid JSON.") from exc

    def submit(self, workflow):
        issues = validate_workflow(workflow)
        if issues:
            raise ValueError(" ".join(issues))
        owner, model = workflow["model"].strip().split("/", 1)
        url = f"{API_BASE}/models/{urllib.parse.quote(owner)}/{urllib.parse.quote(model)}/predictions"
        result = self._request(url, {"input": workflow["input"]})
        prediction_id = result.get("id") if isinstance(result, dict) else None
        if not prediction_id:
            raise RuntimeError(f"Hosted video API did not return a prediction ID: {str(result)[:1000]}")
        return str(prediction_id)

    def wait_for_outputs(self, prediction_id, status_box, timeout=1800, poll_interval=3):
        url = f"{API_BASE}/predictions/{urllib.parse.quote(str(prediction_id))}"
        start = time.time()
        while time.time() - start < max(1, int(timeout)):
            result = self._request(url)
            state = str(result.get("status", "")).lower()
            if state in {"succeeded", "successful"}:
                if result.get("output") is None:
                    raise RuntimeError("Hosted model succeeded but returned no output.")
                return result
            if state in {"failed", "canceled", "cancelled"}:
                raise RuntimeError("Hosted video generation " + state + ": " + str(result.get("error") or result.get("logs") or "No details")[:1200])
            status_box.caption(f"Hosted AI generation · {state or 'waiting'} · {int(time.time() - start)}s elapsed")
            time.sleep(min(max(1, int(poll_interval)), max(1, int(timeout - (time.time() - start)))))
        raise TimeoutError(f"Hosted video generation timed out after {timeout} seconds. The prediction may still be visible in your provider dashboard.")

    @staticmethod
    def _output_urls(value):
        found = []
        if isinstance(value, str) and value.startswith("https://"):
            found.append(value)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in {"url", "video", "video_url", "output"} and isinstance(item, str) and item.startswith("https://"):
                    found.append(item)
                else:
                    found.extend(ReplicateVideo._output_urls(item))
        elif isinstance(value, list):
            for item in value:
                found.extend(ReplicateVideo._output_urls(item))
        return list(dict.fromkeys(found))

    def download_videos(self, prediction, folder):
        urls = self._output_urls(prediction.get("output") if isinstance(prediction, dict) else prediction)
        if not urls:
            raise RuntimeError("Hosted model output did not contain a downloadable HTTPS video URL.")
        folder = Path(folder).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        saved = []
        for url in urls:
            parsed = urllib.parse.urlparse(url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme != "https" or not any(host == suffix or host.endswith("." + suffix) for suffix in _ALLOWED_FILE_HOSTS):
                raise ValueError("Hosted model returned a file URL on an untrusted host; refusing to send credentials.")
            request = urllib.request.Request(url, headers={"Authorization": "Bearer " + self.token})
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = response.read()
                    media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                raise RuntimeError(f"Could not download hosted video output: {exc}") from exc
            suffix = Path(urllib.parse.unquote(parsed.path)).suffix.lower()
            if suffix not in {".mp4", ".webm", ".mov", ".mkv"}:
                suffix = ".webm" if "webm" in media_type else ".mp4" if media_type in {"video/mp4", "application/mp4"} else ""
            if not suffix:
                raise RuntimeError(f"Hosted output is not a recognized video file (Content-Type: {media_type or 'unknown'}).")
            if not data:
                raise RuntimeError("Hosted provider returned an empty video file.")
            target = folder / f"hosted_scene_{len(saved) + 1}{suffix}"
            index = 2
            while target.exists():
                target = folder / f"hosted_scene_{len(saved) + 1}_{index}{suffix}"
                index += 1
            temp = target.with_name(target.name + ".part")
            try:
                temp.write_bytes(data)
                temp.replace(target)
            finally:
                temp.unlink(missing_ok=True)
            saved.append(target)
        return saved

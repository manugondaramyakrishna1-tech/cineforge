import time, urllib.parse, urllib.request, json, uuid
from pathlib import Path

class ComfyUI:
    def __init__(self, base):
        self.base = base.rstrip('/')

    @staticmethod
    def replace_placeholders(obj, replacements):
        if isinstance(obj, dict):
            return {k: ComfyUI.replace_placeholders(v, replacements) for k, v in obj.items()}
        if isinstance(obj, list):
            return [ComfyUI.replace_placeholders(v, replacements) for v in obj]
        if isinstance(obj, str):
            for old, new in replacements.items():
                obj = obj.replace(old, new)
        return obj

    def _request(self, path, data=None):
        body = None if data is None else json.dumps(data).encode()
        req = urllib.request.Request(self.base + path, data=body, headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    def submit(self, workflow):
        payload = {'prompt': workflow, 'client_id': str(uuid.uuid4())}
        result = json.loads(self._request('/prompt', payload))
        return result['prompt_id']

    def wait_for_outputs(self, prompt_id, status_box, timeout=1800, poll_interval=3):
        """Poll ComfyUI history, surface execution failures and bound waiting time."""
        if not prompt_id:
            raise ValueError('ComfyUI did not return a prompt ID.')
        timeout = max(1, int(timeout))
        poll_interval = max(1, int(poll_interval))
        start = time.time()
        last_caption = None
        while time.time() - start < timeout:
            history = json.loads(self._request(f'/history/{prompt_id}'))
            entry = history.get(prompt_id, {})
            status = entry.get('status', {}) if isinstance(entry, dict) else {}
            messages = status.get('messages', []) if isinstance(status, dict) else []
            for message in messages:
                if isinstance(message, (list, tuple)) and message and str(message[0]).lower() in {'execution_error', 'execution_interrupted'}:
                    details = message[1] if len(message) > 1 else {}
                    raise RuntimeError(f'ComfyUI execution failed: {str(details)[:1200]}')
            if entry.get('outputs'):
                return entry['outputs']
            elapsed = int(time.time() - start)
            caption = f'Generation running · {elapsed}s elapsed · waiting for output…'
            if caption != last_caption:
                status_box.caption(caption)
                last_caption = caption
            time.sleep(min(poll_interval, max(1, timeout - elapsed)))
        raise TimeoutError(f'ComfyUI timed out after {timeout} seconds. Check the server queue and logs, then retry.')

    def download_videos(self, outputs, folder):
        folder.mkdir(parents=True, exist_ok=True)
        saved = []
        for _, node_output in outputs.items():
            for key in ('videos', 'gifs'):
                for item in node_output.get(key, []):
                    filename = item.get('filename')
                    sub = item.get('subfolder', '')
                    typ = item.get('type', 'output')
                    if not filename:
                        continue
                    qs = urllib.parse.urlencode({'filename': filename, 'subfolder': sub, 'type': typ})
                    with urllib.request.urlopen(self.base + '/view?' + qs, timeout=120) as r:
                        data = r.read()
                    out = folder / filename
                    out.write_bytes(data)
                    saved.append(out)
        return saved

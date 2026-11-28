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
            outputs = entry.get('outputs') if isinstance(entry, dict) else None
            completed = status.get('completed') is True or str(status.get('status_str', '')).lower() == 'success'
            if outputs and completed:
                return outputs
            elapsed = int(time.time() - start)
            caption = f'Generation running · {elapsed}s elapsed · waiting for output…'
            if caption != last_caption:
                status_box.caption(caption)
                last_caption = caption
            time.sleep(min(poll_interval, max(1, timeout - elapsed)))
        raise TimeoutError(f'ComfyUI timed out after {timeout} seconds. Check the server queue and logs, then retry.')

    @staticmethod
    def _safe_output_name(filename):
        """Return a single safe filename; reject paths and unsupported media."""
        name = str(filename or '')
        if not name or name in {'.', '..'} or '/' in name or chr(92) in name or chr(0) in name:
            raise ValueError('ComfyUI returned an unsafe output filename.')
        suffix = Path(name).suffix.lower()
        if suffix not in {'.mp4', '.webm', '.mov', '.mkv', '.avi', '.gif'}:
            raise ValueError(f'Unsupported generated video format: {suffix or "no extension"}')
        return name

    def download_videos(self, outputs, folder):
        folder = Path(folder).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        saved = []
        for _, node_output in outputs.items():
            if not isinstance(node_output, dict):
                continue
            for key in ('videos', 'gifs'):
                for item in node_output.get(key, []):
                    if not isinstance(item, dict):
                        continue
                    filename = self._safe_output_name(item.get('filename'))
                    sub = str(item.get('subfolder', '') or '')
                    typ = str(item.get('type', 'output') or 'output')
                    qs = urllib.parse.urlencode({'filename': filename, 'subfolder': sub, 'type': typ})
                    with urllib.request.urlopen(self.base + '/view?' + qs, timeout=120) as response:
                        data = response.read()
                    if not data:
                        raise RuntimeError(f'ComfyUI returned an empty video file: {filename}')
                    out = folder / filename
                    if out.exists():
                        stem, suffix = out.stem, out.suffix
                        index = 2
                        while (folder / f'{stem}_{index}{suffix}').exists():
                            index += 1
                        out = folder / f'{stem}_{index}{suffix}'
                    temp = out.with_name(out.name + '.part')
                    try:
                        temp.write_bytes(data)
                        temp.replace(out)
                    finally:
                        if temp.exists():
                            temp.unlink()
                    if out.parent != folder or not out.is_file() or out.stat().st_size == 0:
                        raise RuntimeError(f'Generated video could not be saved safely: {filename}')
                    saved.append(out)
        return saved

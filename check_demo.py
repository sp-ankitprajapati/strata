"""Check demo pages in a temporary snapshot without ignored workspace data."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from demo_assets import demo_asset


ROOT = Path(__file__).resolve().parent
CHECK = """
from pathlib import Path
from streamlit.testing.v1 import AppTest
from demo_assets import demo_asset
from pdf_processing import inspect_pdf_page

root = Path.cwd()
for name in ('raw', 'processed', 'reviews'):
    assert not (root / 'data' / name).exists()
assert not (root / '.models').exists()

def check_page(app, stage, expected_errors=()):
    exceptions = [element.message for element in app.exception]
    errors = [element.value for element in app.error]
    print(f'CHECK: {stage}', flush=True)
    print(f'  Exceptions: {exceptions!r}', flush=True)
    print(f'  Displayed error messages: {errors!r}', flush=True)
    assert not exceptions, f'{stage}: uncaught exceptions: {exceptions!r}'
    assert errors == list(expected_errors), (
        f'{stage}: expected displayed errors {list(expected_errors)!r}; '
        f'got {errors!r}'
    )

app = AppTest.from_file('streamlit_app.py', default_timeout=45).run()
check_page(app, 'Saved reviews / Drawing OCR')
app.radio(key='source').set_value('Synthetic examples').run()
assert app.selectbox(key='annotation_demo').value == 0
# The first synthetic example deliberately displays its asbestos reference
# status with st.error. That exact status alert is expected on this page.
check_page(
    app,
    'Saved reviews / Synthetic examples',
    expected_errors=('Reference status: asbestos-containing',),
)
app.switch_page('app_pages/process_pdf.py').run()
check_page(app, 'Process PDF / Project example')
assert len(app.selectbox) == 1
assert len(app.selectbox[0].options) == 39
scan, _ = inspect_pdf_page(demo_asset(root, 'synthetic_scan').read_bytes(), 1)
assert not scan['text'].strip()
assert 'torch' not in __import__('sys').modules
print('PASS: saved reviews and native PDF page loaded; 39 entries; image-only scan verified.')
print('PASS: no ignored workspace data or model cache was required; live OCR was not run.')
"""


def main():
    assets = [demo_asset(ROOT, name) for name in ("kmew_pdf", "drawing_crop", "synthetic_scan")]
    with TemporaryDirectory(prefix="strata-demo-check-") as folder:
        snapshot = Path(folder)
        for source in ROOT.glob("*.py"):
            shutil.copyfile(source, snapshot / source.name)
        for relative in ("app_pages", "reports/matching", "data/reference"):
            shutil.copytree(ROOT / relative, snapshot / relative)
        assets.append(ROOT / "assets/demo/manifest.json")
        for source in assets:
            destination = snapshot / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        subprocess.run([sys.executable, "-c", CHECK], cwd=snapshot,
                       env=environment, check=True)


if __name__ == "__main__":
    main()

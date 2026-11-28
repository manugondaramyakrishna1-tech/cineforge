# CineForge Free GPU Mode

Free GPU notebook providers (Kaggle/Colab) are temporary and may limit GPU access, session duration, networking, or inbound ports. This mode is intended for manual generation/testing, not always-on production.

## Kaggle
1. Open https://www.kaggle.com/code and create a notebook.
2. In notebook settings, select GPU if available.
3. Copy/run the code from `free_gpu_notebook.py` in notebook cells.
4. Run the notebook, wait for model download, enter a prompt.
5. Download the generated MP4 from the notebook output files.

## Colab
Open https://colab.research.google.com/ , select Runtime > Change runtime type > GPU if available, then run the same code.

## Limits
- Free GPU sessions can disconnect or have quotas and availability limits.
- CogVideoX-2B may be slow or fail depending on GPU memory.
- This is not a persistent public endpoint and does not automatically connect notebook GPU to CineForge mobile/API.
- Keep credentials private and don't expose notebook runtimes publicly without authentication and safeguards.
- Review model license and provider terms.

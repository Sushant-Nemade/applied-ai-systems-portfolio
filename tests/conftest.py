import os
import tempfile

os.environ["APP_ENV"] = "test"
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="ai-portfolio-tests-")

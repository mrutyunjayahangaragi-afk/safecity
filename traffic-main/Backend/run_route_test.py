import os
import sys
import pytest

os.chdir(r'c:\Users\mruty\Downloads\SafeRoute-AI-main\SafeRoute-AI-main\files\Backend')
raise SystemExit(pytest.main(['tests/test_route_comparison.py', '-q']))

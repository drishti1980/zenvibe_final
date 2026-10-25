import imp
import os
import sys


sys.path.insert(0, os.path.dirname(__file__))

wsgi = imp.load_source('wsgi', 'app_wsgi.py')
application = wsgi.application

# TECHORBYTE SHARED DEMO GUARD
import importlib.util as _tb_util
import sys as _tb_sys
_tb_root = '/home/utwsig55/public_html/demo_portal'
_tb_sys.path.insert(0, _tb_root)
_tb_spec = _tb_util.spec_from_file_location('_tb_shared_guard', _tb_root + '/demo_access.py')
_tb_guard = _tb_util.module_from_spec(_tb_spec)
_tb_spec.loader.exec_module(_tb_guard)
application = _tb_guard.protect_demo(application)

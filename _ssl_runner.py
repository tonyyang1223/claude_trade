"""
Wrapper: 在调用子脚本前 monkey-patch SSL context，绕过 sandbox runtime 过期证书。
用法: python _ssl_runner.py <script_path> [args...]
"""
import os
import ssl
import sys
import runpy

ssl._create_default_https_context = ssl._create_unverified_context

if len(sys.argv) < 2:
    print("usage: python _ssl_runner.py <script.py> [args...]")
    sys.exit(1)

script = os.path.abspath(sys.argv[1])
script_dir = os.path.dirname(script)
# 把脚本所在目录放到 sys.path 最前面，让 `from db import *` 这类相对导入生效
sys.path.insert(0, script_dir)
sys.argv = sys.argv[1:]  # 让子脚本看到自己的 argv
runpy.run_path(script, run_name="__main__")

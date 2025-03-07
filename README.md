Change the proxy settings before running `syzbot_crawl.py`:
```python
os.environ["http_proxy"] = "http://127.0.0.1:8001"
os.environ["https_proxy"] = "http://127.0.0.1:8001"
```
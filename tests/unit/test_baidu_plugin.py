from webis.plugins.sources.baidu_plugin import BaiduSearchPlugin
import logging

logging.basicConfig(level=logging.INFO)

plugin = BaiduSearchPlugin()
print("Testing Baidu Plugin...")
docs = list(plugin.fetch("Python 3.12 新特性", limit=3))
print(f"Fetched {len(docs)} docs")
for doc in docs:
    print(f"- {doc.meta.title}: {doc.meta.url}")

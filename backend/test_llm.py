"""
快速测试 qwen3.5-27b-fp8 接口连通性
用法：python test_llm.py
也可覆盖环境变量：OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL
"""
import os
import sys
import time
import json
import urllib.request
import urllib.error

BASE_URL = "http://103.239.152.247:8024/v1"
API_KEY  = "sk-X9f2mK8pI3qR7sTeeW5yZ0aB4cN6sp8h"
MODEL    = "gemma-4-31B-it-AWQ-8bit"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

def check_models():
    """GET /models —— 验证 URL + key 基本可达"""
    url = f"{BASE_URL}/models"
    req = urllib.request.Request(url, headers=HEADERS)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = time.time() - t0
            data = json.loads(resp.read())
            ids = [m["id"] for m in data.get("data", [])]
            print(f"[OK] GET /models  ({elapsed:.2f}s)")
            print(f"     可用模型: {ids}")
            if MODEL in ids:
                print(f"     [✓] {MODEL} 在列表中")
            else:
                print(f"     [!] {MODEL} 不在列表中，请确认模型名称")
    except urllib.error.HTTPError as e:
        print(f"[FAIL] GET /models  HTTP {e.code}: {e.reason}")
        print(f"       {e.read().decode(errors='replace')}")
    except Exception as e:
        print(f"[FAIL] GET /models  {type(e).__name__}: {e}")

def check_chat():
    """POST /chat/completions —— 验证模型推理是否正常"""
    url = f"{BASE_URL}/chat/completions"
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": "你好，请用一句话介绍自己。"}],
        "max_tokens": 64,
        "stream": False,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers=HEADERS, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.time() - t0
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            usage   = data.get("usage", {})
            print(f"[OK] POST /chat/completions  ({elapsed:.2f}s)")
            print(f"     回复: {content.strip()}")
            print(f"     Token 用量: {usage}")
    except urllib.error.HTTPError as e:
        print(f"[FAIL] POST /chat/completions  HTTP {e.code}: {e.reason}")
        print(f"       {e.read().decode(errors='replace')}")
    except Exception as e:
        print(f"[FAIL] POST /chat/completions  {type(e).__name__}: {e}")

def check_stream():
    """POST /chat/completions (stream) —— 验证流式输出"""
    url = f"{BASE_URL}/chat/completions"
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": "数到三。"}],
        "max_tokens": 32,
        "stream": True,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers=HEADERS, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            chunks = 0
            text   = ""
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                body = line[5:].strip()
                if body == "[DONE]":
                    break
                try:
                    delta = json.loads(body)["choices"][0]["delta"].get("content", "")
                    text += delta
                    chunks += 1
                except Exception:
                    pass
            elapsed = time.time() - t0
            print(f"[OK] POST /chat/completions (stream)  ({elapsed:.2f}s, {chunks} chunks)")
            print(f"     内容: {text.strip()}")
    except urllib.error.HTTPError as e:
        print(f"[FAIL] POST /chat/completions (stream)  HTTP {e.code}: {e.reason}")
        print(f"       {e.read().decode(errors='replace')}")
    except Exception as e:
        print(f"[FAIL] POST /chat/completions (stream)  {type(e).__name__}: {e}")

if __name__ == "__main__":
    print(f"目标服务: {BASE_URL}")
    print(f"模型:     {MODEL}")
    print(f"API Key:  {'(空)' if not API_KEY else API_KEY[:6] + '***'}")
    print("-" * 50)
    check_models()
    print()
    check_chat()
    print()
    check_stream()

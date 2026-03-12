import requests
import json
import sseclient
import threading
import queue
import time

base_url = "https://stock-mcp.pricetrade.top"


def send_and_receive(session_id, request_data, request_id=1):
    """发送请求并接收响应"""
    mcp_url = f"{base_url}/messages/?session_id={session_id}"

    # 发送请求
    resp = requests.post(mcp_url, json=request_data, timeout=15)
    if resp.status_code != 202:
        return f"Error: {resp.status_code}"

    # 监听响应 - 使用同一个 session
    try:
        sse_resp = requests.get(f"{base_url}/sse?session_id={session_id}", stream=True, timeout=30)
        sse_client = sseclient.SSEClient(sse_resp)

        for event in sse_client.events():
            if event.data:
                # 检查是否是消息事件
                if event.event == "message":
                    return event.data
                # 否则可能是新的 endpoint
                elif event.event == "endpoint":
                    new_session = event.data.split("session_id=")[1]
                    print(f"Got new session: {new_session}")
                    # 用新 session 监听
                    return send_and_receive(new_session, request_data, request_id)
                else:
                    print(f"Got event: {event.event} = {event.data[:100]}")
    except Exception as e:
        return f"Error: {e}"

    return None


# 1. 获取初始 session
print("Getting initial session...")
init_response = requests.get(f"{base_url}/sse", stream=True, timeout=15)
init_client = sseclient.SSEClient(init_response)

session_id = None
for event in init_client.events():
    if event.event == "endpoint":
        session_id = event.data.split("session_id=")[1]
        break

print(f"Session: {session_id}")

# 2. 发送 initialize
print("\nSending initialize...")
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"},
    },
}

result = send_and_receive(session_id, init_request)
print(f"Initialize result: {result[:500] if result else 'None'}")

if result:
    try:
        data = json.loads(result)
        print(f"\nParsed: {json.dumps(data, indent=2, ensure_ascii=False)[:3000]}")
    except:
        print(f"Raw: {result}")

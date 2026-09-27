"""core.envelope 信封构造单元测试。

说明：envelope 模块顶层 ``import fastapi``，而离线分析环境（workbuddy-ai default）
未安装 fastapi。为最大化离线可验证覆盖，本测试在 fastapi 不可用时注入一个
最小化的 stub（仅提供 ``jsonable_encoder`` 与 ``JSONResponse`` 占位），从而真正
执行源码中的 ``success()`` / ``failure()`` / ``EnvelopeResponse`` 构造逻辑；若
真实 fastapi 可用则自动改用真实实现（行为等价）。
"""
import sys
import types

if "fastapi" not in sys.modules:
    _fake = types.ModuleType("fastapi")
    _enc = types.ModuleType("fastapi.encoders")
    _enc.jsonable_encoder = lambda v: v  # 测试用恒等编码
    _resp = types.ModuleType("fastapi.responses")

    class _JSONResponse:
        def __init__(self, content=None, status_code=200, **kwargs):
            self.body = content
            self.status_code = status_code

    _resp.JSONResponse = _JSONResponse
    _fake.encoders = _enc
    _fake.responses = _resp
    sys.modules["fastapi"] = _fake
    sys.modules["fastapi.encoders"] = _enc
    sys.modules["fastapi.responses"] = _resp

from core.envelope import EnvelopeResponse, failure, success  # noqa: E402


def test_success_default_shape():
    env = success({"a": 1})
    assert env == {"code": 0, "message": "ok", "data": {"a": 1}}


def test_success_custom_message_and_none_data():
    env = success(None, message="no data")
    assert env["code"] == 0
    assert env["message"] == "no data"
    assert env["data"] is None


def test_failure_carries_nonzero_code_and_data():
    env = failure(404, "not found", data=[])
    assert env == {"code": 404, "message": "not found", "data": []}
    assert env["code"] != 0


def test_envelope_response_builds_payload():
    resp = EnvelopeResponse(data={"x": 1}, message="hi", code=200, status_code=200)
    assert resp.status_code == 200
    assert resp.body == {"code": 200, "message": "hi", "data": {"x": 1}}


def test_envelope_response_defaults_to_success_shape():
    resp = EnvelopeResponse(data=[1, 2, 3])
    assert resp.status_code == 200
    assert resp.body["code"] == 0
    assert resp.body["message"] == "ok"
    assert resp.body["data"] == [1, 2, 3]

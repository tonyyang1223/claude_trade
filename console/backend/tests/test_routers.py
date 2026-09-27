"""路由层结构守卫（AST 静态校验，不依赖 fastapi 运行时）。

锁定两条易复发、且**曾真实造成线上故障**的约定：

1. **处理函数名不得与导入的 service 同名**。
   反例：``routers/macro.py`` 曾写 ``from services.macro_svc import btc_dominance``
   同时又定义 ``async def btc_dominance()``；模块级定义覆盖了导入名，函数体里的
   ``btc_dominance()`` 变成递归调用自身 → 返回 coroutine → ``AttributeError`` →
   ``/api/macro/btc-dominance`` 恒返回 code=500（前端只会显示「—」而静默吞掉）。

2. **路由处理函数必须是同步 ``def``**。
   service 层调用阻塞型 ``src`` 模块（requests + 网络，实测单次 30–149s）。
   ``async def`` 会占住事件循环，把并发的其他面板请求全部串行化
   （已实测：首屏 3 个并发请求退化为串行）。
"""
import ast
import pathlib

ROUTERS_DIR = pathlib.Path(__file__).resolve().parents[1] / "routers"


def _route_handlers(tree: ast.Module):
    """产出模块顶层函数节点（路由处理函数都在顶层）。"""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _imported_names(tree: ast.Module) -> set:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                out.add(alias.asname or alias.name)
    return out


def test_router_files_exist():
    files = sorted(p.name for p in ROUTERS_DIR.glob("*.py") if p.name != "__init__.py")
    assert len(files) >= 8, f"路由文件数量异常: {files}"


def test_handler_name_does_not_shadow_imported_service():
    problems = []
    for path in sorted(ROUTERS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = _imported_names(tree)
        for fn in _route_handlers(tree):
            if fn.name in imported:
                problems.append(f"{path.name}::{fn.name}")
    assert not problems, (
        "处理函数名覆盖了同名导入，函数体将递归调用自身（曾致 /api/macro 恒 500）: "
        + ", ".join(problems)
    )


def test_route_handlers_are_sync():
    problems = []
    for path in sorted(ROUTERS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in _route_handlers(tree):
            if isinstance(fn, ast.AsyncFunctionDef):
                problems.append(f"{path.name}::{fn.name}")
    assert not problems, (
        "路由处理函数必须用同步 def（Starlette 会放入线程池）；async def 会因阻塞型 "
        "src 调用占住事件循环: " + ", ".join(problems)
    )

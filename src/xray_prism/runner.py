# -*- coding: utf-8 -*-
"""
Xray-Prism 进程管理层

负责启动、停止 Xray 子进程，并支持自动下载 Xray 内核。
"""

import logging
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Optional
import urllib.request
import tempfile

logger = logging.getLogger(__name__)

# Xray 下载配置
XRAY_VERSION = "v24.12.18"
XRAY_DOWNLOAD_BASE = f"https://github.com/XTLS/Xray-core/releases/download/{XRAY_VERSION}"


def get_xray_download_url() -> str:
    """获取当前平台的 Xray 下载链接"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # 架构映射
    arch_map = {
        "x86_64": "64",
        "amd64": "64",
        "x64": "64",
        "i386": "32",
        "i686": "32",
        "arm64": "arm64-v8a",
        "aarch64": "arm64-v8a",
    }
    
    arch = arch_map.get(machine, "64")
    
    if system == "windows":
        return f"{XRAY_DOWNLOAD_BASE}/Xray-windows-{arch}.zip"
    elif system == "linux":
        return f"{XRAY_DOWNLOAD_BASE}/Xray-linux-{arch}.zip"
    elif system == "darwin":
        if "arm" in machine:
            return f"{XRAY_DOWNLOAD_BASE}/Xray-macos-arm64-v8a.zip"
        return f"{XRAY_DOWNLOAD_BASE}/Xray-macos-64.zip"
    else:
        raise RuntimeError(f"不支持的操作系统: {system}")


def get_xray_executable_name() -> str:
    """获取 Xray 可执行文件名"""
    if platform.system().lower() == "windows":
        return "xray.exe"
    return "xray"


class XrayRunner:
    """Xray 进程管理器"""
    
    def __init__(
        self,
        xray_path: Optional[str] = None,
        project_dir: Optional[str] = None,
        process_info_file: Optional[str] = None,
        track_process: bool = True,
    ):
        """
        初始化 Xray 运行器
        
        Args:
            xray_path: 手动指定 xray 可执行文件路径
            project_dir: 项目目录，用于存放下载的 xray
            process_info_file: 进程元数据文件路径（可选）
            track_process: 是否启用跨进程元数据跟踪
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.xray_dir = self.project_dir / "bin"
        self.data_dir = self.project_dir / "data"
        self.track_process = track_process
        self.process_info_file = Path(process_info_file) if process_info_file else (self.data_dir / "xray_runner.json")
        self._xray_path = xray_path
        self._process: Optional[subprocess.Popen] = None

    def _normalize_path(self, path: Optional[str]) -> Optional[str]:
        """标准化路径，便于跨平台比较。"""
        if not path:
            return None

        normalized = str(Path(path).resolve(strict=False))
        if platform.system().lower() == "windows":
            return normalized.lower()
        return normalized

    def _read_process_metadata(self) -> Optional[dict]:
        """读取上次启动的 Xray 进程元数据。"""
        if not self.track_process:
            return None
        if not self.process_info_file.exists():
            return None

        try:
            with open(self.process_info_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取进程元数据失败: {e}")
            return None

    def _write_process_metadata(self, pid: int, xray_path: str, config_path: str) -> None:
        """保存当前启动的 Xray 进程元数据。"""
        if not self.track_process:
            return
        self.process_info_file.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "pid": pid,
            "xray_path": str(Path(xray_path).resolve(strict=False)),
            "config_path": str(Path(config_path).resolve(strict=False)),
        }
        with open(self.process_info_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _clear_process_metadata(self) -> None:
        """删除进程元数据文件。"""
        if not self.track_process:
            return
        try:
            if self.process_info_file.exists():
                self.process_info_file.unlink()
        except Exception as e:
            logger.warning(f"删除进程元数据失败: {e}")

    def _pid_exists(self, pid: int) -> bool:
        """检查进程是否存在。"""
        if pid <= 0:
            return False

        if platform.system().lower() == "windows":
            try:
                import ctypes
                from ctypes import wintypes

                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                STILL_ACTIVE = 259
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

                handle = kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION,
                    False,
                    pid
                )
                if not handle:
                    return False

                try:
                    exit_code = wintypes.DWORD()
                    if not kernel32.GetExitCodeProcess(
                        wintypes.HANDLE(handle),
                        ctypes.byref(exit_code)
                    ):
                        return False
                    return exit_code.value == STILL_ACTIVE
                finally:
                    kernel32.CloseHandle(wintypes.HANDLE(handle))
            except Exception:
                return False

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _get_process_executable(self, pid: int) -> Optional[str]:
        """获取进程可执行文件路径。"""
        system = platform.system().lower()

        if system == "linux":
            try:
                return str(Path(f"/proc/{pid}/exe").resolve(strict=True))
            except OSError:
                return None

        if system == "windows":
            try:
                import ctypes
                from ctypes import wintypes

                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

                handle = kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION,
                    False,
                    pid
                )
                if not handle:
                    return None

                try:
                    size = wintypes.DWORD(32768)
                    buffer = ctypes.create_unicode_buffer(size.value)
                    success = kernel32.QueryFullProcessImageNameW(
                        wintypes.HANDLE(handle),
                        0,
                        buffer,
                        ctypes.byref(size)
                    )
                    if not success:
                        return None
                    return buffer.value
                finally:
                    kernel32.CloseHandle(wintypes.HANDLE(handle))
            except Exception:
                return None

        return None

    def _get_process_cmdline(self, pid: int) -> Optional[list[str]]:
        """获取进程命令行参数。当前仅在 Linux 下启用更严格校验。"""
        if platform.system().lower() != "linux":
            return None

        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            return None

        parts = [part.decode("utf-8", errors="ignore") for part in raw.split(b"\0") if part]
        return parts or None

    def _get_tracked_process_pid(self) -> Optional[int]:
        """
        返回可安全接管的旧进程 PID。

        只有当 PID 仍然存在，且可执行文件与记录一致时才会返回。
        在 Linux 下还会进一步比对 config 路径，降低误杀风险。
        """
        if not self.track_process:
            return None
        metadata = self._read_process_metadata()
        if not metadata:
            return None

        pid = metadata.get("pid")
        if not isinstance(pid, int) or pid <= 0:
            self._clear_process_metadata()
            return None

        if not self._pid_exists(pid):
            self._clear_process_metadata()
            return None

        expected_exe = self._normalize_path(metadata.get("xray_path"))
        actual_exe = self._normalize_path(self._get_process_executable(pid))
        if not expected_exe or not actual_exe:
            return None

        if actual_exe != expected_exe:
            self._clear_process_metadata()
            return None

        expected_config = self._normalize_path(metadata.get("config_path"))
        cmdline = self._get_process_cmdline(pid)
        if expected_config and cmdline:
            normalized_cmdline = [self._normalize_path(arg) for arg in cmdline]
            if expected_config not in normalized_cmdline:
                logger.warning(f"检测到同名 Xray 进程但配置不匹配，跳过接管: PID {pid}")
                return None

        return pid

    def _terminate_pid(self, pid: int, timeout: int = 5) -> None:
        """按 PID 终止进程，兼容 Windows 和 Linux。"""
        if not self._pid_exists(pid):
            return

        logger.info(f"正在终止 Xray 进程 PID: {pid}")

        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return

        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._pid_exists(pid):
                return
            time.sleep(0.1)

        if hasattr(signal, "SIGKILL"):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                return

            deadline = time.time() + 2
            while time.time() < deadline:
                if not self._pid_exists(pid):
                    return
                time.sleep(0.1)

        raise TimeoutError(f"Xray 进程未能在限定时间内退出: PID {pid}")

    def _stop_tracked_process(self) -> bool:
        """停止由当前项目上次启动并记录在元数据中的 Xray 进程。"""
        tracked_pid = self._get_tracked_process_pid()
        if tracked_pid is None:
            return False

        self._terminate_pid(tracked_pid)
        self._clear_process_metadata()
        logger.info(f"已停止上次记录的 Xray 进程: PID {tracked_pid}")
        return True
    
    @property
    def xray_path(self) -> str:
        """获取 Xray 可执行文件路径"""
        if self._xray_path:
            return self._xray_path
        
        # 尝试查找 xray
        path = self.find_xray()
        if path:
            return path
        
        raise FileNotFoundError(
            "未找到 Xray 可执行文件。请使用 --xray-path 指定路径，"
            "或调用 download_xray() 自动下载。"
        )
    
    def find_xray(self) -> Optional[str]:
        """
        查找系统中的 Xray 可执行文件
        
        查找顺序:
        1. 项目目录下的 bin/ 文件夹
        2. 系统 PATH
        3. 常见安装路径
        
        Returns:
            Xray 可执行文件路径，未找到返回 None
        """
        exe_name = get_xray_executable_name()
        
        # 1. 检查项目 bin 目录
        local_path = self.xray_dir / exe_name
        if local_path.exists():
            logger.info(f"在项目目录找到 Xray: {local_path}")
            return str(local_path)
        
        # 2. 检查系统 PATH
        path_xray = shutil.which("xray")
        if path_xray:
            logger.info(f"在系统 PATH 找到 Xray: {path_xray}")
            return path_xray
        
        # 3. 检查常见安装路径
        common_paths = []
        system = platform.system().lower()
        
        if system == "windows":
            common_paths = [
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Xray" / exe_name,
                Path(os.environ.get("LOCALAPPDATA", "")) / "Xray" / exe_name,
            ]
        elif system == "linux":
            common_paths = [
                Path("/usr/local/bin/xray"),
                Path("/usr/bin/xray"),
                Path.home() / ".local" / "bin" / "xray",
            ]
        elif system == "darwin":
            common_paths = [
                Path("/usr/local/bin/xray"),
                Path("/opt/homebrew/bin/xray"),
            ]
        
        for path in common_paths:
            if path.exists():
                logger.info(f"在常见路径找到 Xray: {path}")
                return str(path)
        
        return None
    
    def download_xray(self, force: bool = False) -> str:
        """
        下载 Xray 到项目目录
        
        Args:
            force: 强制重新下载
            
        Returns:
            Xray 可执行文件路径
        """
        exe_name = get_xray_executable_name()
        target_path = self.xray_dir / exe_name
        
        if target_path.exists() and not force:
            logger.info(f"Xray 已存在: {target_path}")
            return str(target_path)
        
        # 创建目录
        self.xray_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取下载链接
        url = get_xray_download_url()
        logger.info(f"正在下载 Xray: {url}")
        
        # 下载到临时文件
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 使用 urllib 下载（避免额外依赖 requests）
            urllib.request.urlretrieve(url, tmp_path)
            logger.info("下载完成，正在解压...")
            
            # 解压
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(self.xray_dir)
            
            # 设置可执行权限（Linux/macOS）
            if platform.system().lower() != "windows":
                os.chmod(target_path, 0o755)
            
            logger.info(f"Xray 已安装到: {target_path}")
            self._xray_path = str(target_path)
            return str(target_path)
            
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def start(self, config_path: str) -> subprocess.Popen:
        """
        启动 Xray 进程
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Popen 进程对象
        """
        if self._process and self._process.poll() is None:
            logger.warning("Xray 已在运行，先停止现有进程")
            self.stop()
        else:
            # 服务重启后尝试接管并停止自己上次启动的 Xray，避免误伤其他实例。
            self._stop_tracked_process()
        
        xray = self.xray_path
        config = Path(config_path).absolute()
        
        if not config.exists():
            raise FileNotFoundError(f"配置文件不存在: {config}")
        
        cmd = [xray, "run", "-config", str(config)]
        logger.info(f"启动 Xray: {' '.join(cmd)}")
        
        # 启动进程，重定向输出
        creationflags = 0
        start_new_session = False
        if platform.system() == "Windows":
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0) |
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        else:
            start_new_session = True

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            start_new_session=start_new_session
        )
        
        self._write_process_metadata(self._process.pid, xray, str(config))
        logger.info(f"Xray 已启动，PID: {self._process.pid}")
        return self._process
    
    def stop(self) -> None:
        """停止 Xray 进程"""
        if self._process is None:
            if not self._stop_tracked_process():
                logger.debug("没有运行中的 Xray 进程")
            return
        
        if self._process.poll() is None:
            logger.info(f"正在停止 Xray 进程 (PID: {self._process.pid})")
            self._process.terminate()
            
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("进程未响应，强制终止")
                self._process.kill()
                self._process.wait()
        
        self._process = None
        self._clear_process_metadata()
        logger.info("Xray 已停止")
    
    def is_running(self) -> bool:
        """检查 Xray 是否正在运行"""
        if self._process is not None:
            if self._process.poll() is None:
                return True
            self._process = None

        return self._get_tracked_process_pid() is not None
    
    def get_output(self) -> tuple:
        """获取进程输出"""
        if self._process:
            return self._process.communicate()
        return (b"", b"")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

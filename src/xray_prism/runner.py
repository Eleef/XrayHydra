# -*- coding: utf-8 -*-
"""
Xray-Prism 进程管理层

负责启动、停止 Xray 子进程，并支持自动下载 Xray 内核。
"""

import logging
import os
import platform
import shutil
import subprocess
import sys
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
    
    def __init__(self, xray_path: Optional[str] = None, project_dir: Optional[str] = None):
        """
        初始化 Xray 运行器
        
        Args:
            xray_path: 手动指定 xray 可执行文件路径
            project_dir: 项目目录，用于存放下载的 xray
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.xray_dir = self.project_dir / "bin"
        self._xray_path = xray_path
        self._process: Optional[subprocess.Popen] = None
    
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
    
    def _cleanup_orphan_processes(self) -> None:
        """清理可能存在的僵尸 Xray 进程"""
        try:
            if platform.system().lower() == "windows":
                # Windows: 使用 taskkill 杀掉所有 xray.exe 进程
                subprocess.run(
                    ["taskkill", "/F", "/IM", "xray.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
                logger.debug("已清理遗留的 xray.exe 进程")
            else:
                # Linux/macOS: 使用 pkill
                subprocess.run(
                    ["pkill", "-9", "xray"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
                logger.debug("已清理遗留的 xray 进程")
        except Exception as e:
            # 如果清理失败也继续执行（可能没有遗留进程）
            logger.debug(f"清理遗留进程时出错（可忽略）: {e}")
    
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
        
        # 清理可能存在的僵尸进程（防止服务重启后的遗留进程）
        self._cleanup_orphan_processes()
        
        xray = self.xray_path
        config = Path(config_path).absolute()
        
        if not config.exists():
            raise FileNotFoundError(f"配置文件不存在: {config}")
        
        cmd = [xray, "run", "-config", str(config)]
        logger.info(f"启动 Xray: {' '.join(cmd)}")
        
        # 启动进程，重定向输出
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        
        logger.info(f"Xray 已启动，PID: {self._process.pid}")
        return self._process
    
    def stop(self) -> None:
        """停止 Xray 进程"""
        if self._process is None:
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
        logger.info("Xray 已停止")
    
    def is_running(self) -> bool:
        """检查 Xray 是否正在运行"""
        return self._process is not None and self._process.poll() is None
    
    def get_output(self) -> tuple:
        """获取进程输出"""
        if self._process:
            return self._process.communicate()
        return (b"", b"")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

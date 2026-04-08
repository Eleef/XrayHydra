#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Xray-Prism 主程序入口

将 VPN 订阅节点映射为本地独立端口，实现并发多 IP 出口。
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

load_dotenv()

from xray_prism.fetcher import fetch_subscription, FetchError
from xray_prism.parser import parse_subscription
from xray_prism.generator import ConfigGenerator
from xray_prism.proxy_runtime import build_proxy_address
from xray_prism.runner import XrayRunner
from xray_prism.tester import ProxyTester
from xray_prism.models import PortMapping


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )


def save_proxy_list(mappings, output_path: str, proxy_type: str = "http"):
    """
    保存代理列表文件
    
    Args:
        mappings: 端口映射列表
        output_path: 输出文件路径
        proxy_type: 代理类型 (http/socks5)
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Xray-Prism 代理列表\n")
        f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 代理协议: {proxy_type.upper()}\n")
        f.write(f"# 节点数量: {len(mappings)}\n")
        f.write("#" + "=" * 60 + "\n\n")
        
        for mapping in mappings:
            proxy_url = f"{proxy_type}://{build_proxy_address(mapping.local_port)}"
            f.write(f"# {mapping.node.name}\n")
            f.write(f"{proxy_url}\n\n")
        
        f.write("#" + "=" * 60 + "\n")
        f.write("# 格式: 协议://地址:端口\n")
        f.write(f"# 使用示例: curl -x http://{build_proxy_address(10000)} https://httpbin.org/ip\n")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Xray-Prism: 将订阅节点映射为本地独立端口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --url "https://example.com/subscribe" --test
  python main.py --file subscription.txt --port 20000
  python main.py --url "..." --xray-path /path/to/xray --test
        """
    )
    
    # 数据源
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--url", "-u",
        help="订阅链接 URL"
    )
    source_group.add_argument(
        "--file", "-f",
        help="本地订阅文件路径"
    )
    
    # 端口配置
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=10000,
        help="起始端口号 (默认: 10000)"
    )
    
    # Xray 配置
    parser.add_argument(
        "--xray-path",
        help="手动指定 Xray 可执行文件路径"
    )
    parser.add_argument(
        "--download-xray",
        action="store_true",
        help="自动下载 Xray 内核到项目目录"
    )
    
    # 测试配置
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="启动后自动运行连通性测试"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="测试超时时间 (秒, 默认: 5)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=20,
        help="最大并发测试线程数 (默认: 20)"
    )
    
    # 其他配置
    parser.add_argument(
        "--config-output", "-o",
        default="config.json",
        help="配置文件输出路径 (默认: config.json)"
    )
    parser.add_argument(
        "--inbound-type",
        choices=["http", "socks"],
        default="http",
        help="入站协议类型 (默认: http)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志"
    )
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="测试完成后保持 Xray 运行"
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    project_dir = Path(__file__).parent
    
    runner = None
    
    def signal_handler(sig, frame):
        """信号处理，确保优雅退出"""
        logger.info("\n收到中断信号，正在清理...")
        if runner:
            runner.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # ========== Step 1: 获取订阅 ==========
        logger.info("=" * 50)
        logger.info("Step 1: 获取订阅内容")
        logger.info("=" * 50)
        
        content = fetch_subscription(url=args.url, file=args.file)
        logger.info(f"获取到 {len(content)} 字节内容")
        
        # ========== Step 2: 解析节点 ==========
        logger.info("=" * 50)
        logger.info("Step 2: 解析代理节点")
        logger.info("=" * 50)
        
        nodes = parse_subscription(content)
        
        if not nodes:
            logger.error("未解析到任何有效节点！")
            sys.exit(1)
        
        logger.info(f"成功解析 {len(nodes)} 个节点")
        
        # 显示节点列表
        for i, node in enumerate(nodes[:10]):  # 只显示前10个
            logger.info(f"  [{i+1}] {node.name} ({node.protocol.value})")
        if len(nodes) > 10:
            logger.info(f"  ... 还有 {len(nodes) - 10} 个节点")
        
        # ========== Step 3: 生成配置 ==========
        logger.info("=" * 50)
        logger.info("Step 3: 生成 Xray 配置")
        logger.info("=" * 50)
        
        generator = ConfigGenerator(
            start_port=args.port,
            inbound_protocol=args.inbound_type
        )
        
        config_path = project_dir / args.config_output
        mappings = generator.generate_and_save(nodes, str(config_path))
        
        logger.info(f"端口范围: {args.port} - {args.port + len(nodes) - 1}")
        logger.info(f"配置文件: {config_path}")
        
        # 输出代理列表文件
        proxy_list_path = project_dir / "proxies.txt"
        save_proxy_list(mappings, str(proxy_list_path), args.inbound_type)
        logger.info(f"代理列表: {proxy_list_path}")
        
        # ========== Step 4: 启动 Xray ==========
        logger.info("=" * 50)
        logger.info("Step 4: 启动 Xray 内核")
        logger.info("=" * 50)
        
        runner = XrayRunner(
            xray_path=args.xray_path,
            project_dir=str(project_dir)
        )
        
        # 如果需要下载 Xray
        if args.download_xray:
            runner.download_xray()
        
        # 检查 Xray 是否存在
        try:
            xray_path = runner.xray_path
            logger.info(f"使用 Xray: {xray_path}")
        except FileNotFoundError:
            logger.warning("未找到 Xray，正在自动下载...")
            runner.download_xray()
        
        # 启动
        runner.start(str(config_path))
        
        # 等待初始化
        logger.info("等待 Xray 初始化 (3秒)...")
        time.sleep(3)
        
        if not runner.is_running():
            logger.error("Xray 启动失败！")
            stdout, stderr = runner.get_output()
            if stderr:
                logger.error(f"错误信息: {stderr.decode()[:500]}")
            sys.exit(1)
        
        logger.info("Xray 启动成功！")
        
        # ========== Step 5: 运行测试 ==========
        if args.test:
            logger.info("=" * 50)
            logger.info("Step 5: 运行连通性测试")
            logger.info("=" * 50)
            
            tester = ProxyTester(
                timeout=args.timeout,
                max_workers=args.workers
            )
            
            results = tester.test_all(
                mappings,
                proxy_type=args.inbound_type
            )
            
            # 打印结果表格
            print("\n" + tester.format_results(results))
        
        # ========== 保持运行或退出 ==========
        if args.keep_running or not args.test:
            logger.info("=" * 50)
            logger.info("Xray 正在运行，按 Ctrl+C 停止")
            logger.info("=" * 50)
            
            print(f"\n代理服务已启动:")
            print(f"  协议: {args.inbound_type.upper()}")
            print(f"  端口范围: {args.port} - {args.port + len(nodes) - 1}")
            print(f"  节点数量: {len(nodes)}")
            print(f"\n使用示例:")
            print(f"  curl -x {args.inbound_type}://127.0.0.1:{args.port} https://httpbin.org/ip")
            
            # 保持运行
            while runner.is_running():
                time.sleep(1)
        else:
            runner.stop()
            logger.info("测试完成，Xray 已停止")
        
    except FetchError as e:
        logger.error(f"获取订阅失败: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"文件错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n用户中断")
    except Exception as e:
        logger.exception(f"发生错误: {e}")
        sys.exit(1)
    finally:
        if runner:
            runner.stop()


if __name__ == "__main__":
    main()

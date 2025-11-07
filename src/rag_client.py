# -*- coding: utf-8 -*-
"""
@Time ： 2025/7/20 14:50
@Auth ： xiaolongtuan
@File ：rag_client.py
"""
# !/usr/bin/env python3
"""
RAG 配置翻译客户端
提供简单的API接口调用，用于进行网络设备配置翻译
"""
import requests
import json
import time
from typing import Dict, Any, Optional, List, Union


class RAGClient:
    def __init__(self, base_url: str = "http://10.112.19.133:6001"):
        """初始化客户端
        Args:
            base_url: API服务器地址，默认为http://10.112.19.133:6001
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def health_check(self) -> Dict[str, Any]:
        """健康检查
        Returns:
            Dict: 健康状态信息
        """
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def translate_config(self,
                         command: str,
                         source_vendor: str,
                         target_vendor: str,
                         config: str = "",
                         timeout: int = 120) -> Dict[str, Any]:
        """翻译配置命令
        Args:
            command: 要翻译的命令
            source_vendor: 源供应商（如cisco, huawei, juniper）
            target_vendor: 目标供应商（如cisco, huawei, juniper）
            config: 完整配置上下文（可选）
            timeout: 请求超时时间（秒）

        Returns:
            Dict: 翻译结果，包含以下字段：
                - success: 是否成功
                - answer: 翻译后的配置
                - source_explanation: 源命令解释
                - source_vendor: 源供应商
                - target_vendor: 目标供应商
                - original_command: 原始命令
                - performance: 性能统计
        """
        source_vendor = source_vendor.lower()
        target_vendor = target_vendor.lower()
        try:
            data = {
                "command": command,
                "config": config,
                "source_vendor": source_vendor,
                "target_vendor": target_vendor
            }

            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/query",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()

            # 添加客户端计算的总耗时
            elapsed_time = time.time() - start_time
            if "performance" not in result:
                result["performance"] = {}
            result["performance"]["client_total"] = elapsed_time

            return result
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"请求超时（{timeout}秒）",
                "source_vendor": source_vendor,
                "target_vendor": target_vendor,
                "original_command": command
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source_vendor": source_vendor,
                "target_vendor": target_vendor,
                "original_command": command
            }

    def get_config(self) -> Dict[str, Any]:
        """获取服务器配置

        Returns:
            Dict: 服务器配置信息
        """
        try:
            response = self.session.get(f"{self.base_url}/config")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def update_config(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新服务器配置

        Args:
            config_updates: 要更新的配置项

        Returns:
            Dict: 更新结果
        """
        try:
            response = self.session.post(
                f"{self.base_url}/config",
                json=config_updates,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}


def print_translation_result(result: Dict[str, Any]) -> None:
    """打印翻译结果

    Args:
        result: 翻译结果
    """
    if "error" in result:
        print(f"\n❌ 错误: {result['error']}")
        return

    if not result.get("success", False):
        print(f"\n❌ 翻译失败: {result.get('error', '未知错误')}")
        return

    print(f"\n✅ 翻译成功 ({result['source_vendor']} → {result['target_vendor']})")
    print(f"\n📝 原始命令: {result['original_command']}")

    print("\n🔍 源命令解释:")
    print(f"{result.get('source_explanation', '无解释')}")

    print("\n🔄 翻译结果:")
    print(f"{result.get('answer', '无结果')}")

    # 打印性能统计
    if "performance" in result:
        perf = result["performance"]
        print("\n⏱️ 性能统计:")
        for key, value in perf.items():
            print(f"  - {key}: {value:.2f}秒" if isinstance(value, (int, float)) else f"  - {key}: {value}")


def main():
    """主函数，提供命令行界面"""
    import argparse

    parser = argparse.ArgumentParser(description="RAGtifier配置翻译客户端")
    parser.add_argument("--url", default="http://10.112.19.133:6001", help="API服务器地址")
    parser.add_argument("--command", required=True, help="要翻译的命令")
    parser.add_argument("--source", required=True, help="源供应商（如cisco, huawei, juniper）")
    parser.add_argument("--target", required=True, help="目标供应商（如cisco, huawei, juniper）")
    parser.add_argument("--config", default="", help="完整配置上下文")
    parser.add_argument("--timeout", type=int, default=60, help="请求超时时间（秒）")

    args = parser.parse_args()

    client = RAGtifierClient(args.url)

    # 检查服务器健康状态
    health = client.health_check()
    if "error" in health:
        print(f"❌ 服务器连接失败: {health['error']}")
        return

    print(f"✅ 服务器连接成功: {args.url}")
    print(f"📡 支持的供应商: {', '.join(health.get('supported_vendors', []))}")

    # 执行翻译
    print(f"\n🔄 正在翻译: {args.command}")
    print(f"   {args.source} → {args.target}")

    result = client.translate_config(
        command=args.command,
        source_vendor=args.source,
        target_vendor=args.target,
        config=args.config,
        timeout=args.timeout
    )

    # 打印结果
    print_translation_result(result)


# 示例用法
def example():
    """示例用法"""
    client = RAGtifierClient("http://10.112.19.133:6001")

    # 检查服务器健康状态
    health = client.health_check()
    if "error" in health:
        print(f"❌ 服务器连接失败: {health['error']}")
        return

    print(f"✅ 服务器连接成功")
    print(f"📡 支持的供应商: {', '.join(health.get('supported_vendors', []))}")

    # 示例1: 时区配置翻译
    command = "clock timezone GMT add -6:00:00"
    config = """clock timezone GMT add -6:00:00
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0"""

    print(f"\n🔄 示例1 - 时区配置翻译: {command}")
    result = client.translate_config(
        command=command,
        source_vendor="cisco",
        target_vendor="huawei",
        config=config
    )
    print_translation_result(result)

    # 示例2: BGP配置翻译
    command = "maximum load-balancing ebgp 6"
    config = """router bgp 65001
 maximum load-balancing ebgp 6
 neighbor 192.168.1.2 remote-as 65002"""

    print(f"\n🔄 示例2 - BGP负载均衡配置翻译: {command}")
    result = client.translate_config(
        command=command,
        source_vendor="cisco",
        target_vendor="huawei",
        config=config
    )
    print_translation_result(result)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        main()  # 命令行模式
    else:
        example()  # 示例模式
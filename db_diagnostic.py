import subprocess
import json
import socket
import platform
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MacDNSDiagnostics:
    def __init__(self, host="db.cujvnutaucgrhleclmpq.supabase.co", port=5432):
        self.host = host
        self.port = port
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "tests": {}
        }

    def _get_system_info(self):
        return {
            "os": platform.system(),
            "os_version": platform.mac_ver()[0],
            "hostname": socket.gethostname()
        }

    def _run_command(self, command):
        try:
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def check_dns_cache(self):
        """DNSキャッシュの状態を確認"""
        logger.info("Checking DNS cache...")
        command = "sudo dscacheutil -statistics"
        self.results["tests"]["dns_cache"] = self._run_command(command)

    def check_dns_servers(self):
        """現在のDNSサーバー設定を確認"""
        logger.info("Checking DNS servers...")
        command = "networksetup -getdnsservers Wi-Fi"
        self.results["tests"]["dns_servers"] = self._run_command(command)

    def check_host_resolution(self):
        """ホスト名の解決をテスト"""
        logger.info(f"Testing host resolution for {self.host}...")
        try:
            ip = socket.gethostbyname(self.host)
            self.results["tests"]["host_resolution"] = {
                "success": True,
                "ip": ip
            }
        except socket.gaierror as e:
            self.results["tests"]["host_resolution"] = {
                "success": False,
                "error": str(e)
            }

    def check_network_interface(self):
        """ネットワークインターフェースの状態を確認"""
        logger.info("Checking network interface...")
        command = "networksetup -getinfo Wi-Fi"
        self.results["tests"]["network_interface"] = self._run_command(command)

    def run_dig(self):
        """digコマンドでDNS解決をテスト"""
        logger.info(f"Running dig for {self.host}...")
        command = f"dig {self.host} +short"
        self.results["tests"]["dig"] = self._run_command(command)

    def check_connectivity(self):
        """基本的な接続テスト"""
        logger.info(f"Testing connectivity to {self.host}:{self.port}...")
        try:
            socket.create_connection((self.host, self.port), timeout=5)
            self.results["tests"]["connectivity"] = {
                "success": True,
                "message": f"Successfully connected to {self.host}:{self.port}"
            }
        except Exception as e:
            self.results["tests"]["connectivity"] = {
                "success": False,
                "error": str(e)
            }

    def run_scutil_dns(self):
        """scutilでDNS設定を確認"""
        logger.info("Checking DNS configuration with scutil...")
        command = "scutil --dns"
        self.results["tests"]["scutil_dns"] = self._run_command(command)

    def run_all_tests(self):
        """全てのテストを実行"""
        logger.info("Starting all diagnostics tests...")
        
        self.check_dns_cache()
        self.check_dns_servers()
        self.check_host_resolution()
        self.check_network_interface()
        self.run_dig()
        self.check_connectivity()
        self.run_scutil_dns()
        
        return self.results

    def save_results(self, filename="mac_dns_diagnostics.json"):
        """結果をJSONファイルに保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {filename}")

    def print_summary(self):
        """テスト結果のサマリーを表示"""
        print("\n=== DNS Diagnostics Summary ===")
        for test_name, test_result in self.results["tests"].items():
            success = test_result.get("success", False)
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{test_name}: {status}")
            if not success and "error" in test_result:
                print(f"  Error: {test_result['error']}")

def main():
    diagnostics = MacDNSDiagnostics()
    diagnostics.run_all_tests()
    diagnostics.save_results()
    diagnostics.print_summary()

if __name__ == "__main__":
    main()
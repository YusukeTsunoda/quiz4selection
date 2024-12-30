import socket
import dns.resolver
import time
import json
from logging_utils import setup_logger
import subprocess
import platform

dns_logger = setup_logger('dns_diagnostics')

class DNSDiagnostics:
    def __init__(self, target_host):
        self.target_host = target_host
        self.logger = dns_logger
        
    def check_basic_dns(self):
        """基本的なDNS解決をチェック"""
        try:
            ip_address = socket.gethostbyname(self.target_host)
            self.logger.error(json.dumps({
                'event': 'dns_resolution',
                'host': self.target_host,
                'ip': ip_address,
                'status': 'success',
                'timestamp': time.time()
            }))
            return True
        except socket.gaierror as e:
            self.logger.error(json.dumps({
                'event': 'dns_resolution_error',
                'host': self.target_host,
                'error': str(e),
                'error_code': e.errno,
                'timestamp': time.time()
            }))
            return False

    def check_all_dns_servers(self):
        """利用可能なすべてのDNSサーバーをチェック"""
        try:
            resolver = dns.resolver.Resolver()
            nameservers = resolver.nameservers
            results = []
            
            for ns in nameservers:
                try:
                    resolver.nameservers = [ns]
                    answers = resolver.resolve(self.target_host, 'A')
                    results.append({
                        'nameserver': ns,
                        'status': 'success',
                        'ips': [str(rdata) for rdata in answers]
                    })
                except Exception as e:
                    results.append({
                        'nameserver': ns,
                        'status': 'error',
                        'error': str(e)
                    })
            
            self.logger.error(json.dumps({
                'event': 'dns_servers_check',
                'host': self.target_host,
                'results': results,
                'timestamp': time.time()
            }))
            
        except Exception as e:
            self.logger.error(json.dumps({
                'event': 'dns_servers_check_error',
                'host': self.target_host,
                'error': str(e),
                'timestamp': time.time()
            }))

    def run_network_diagnostics(self):
        """ネットワーク診断の実行"""
        os_type = platform.system().lower()
        
        # Ping テスト
        try:
            ping_param = '-n' if os_type == 'windows' else '-c'
            ping_cmd = ['ping', ping_param, '1', self.target_host]
            ping_result = subprocess.run(ping_cmd, capture_output=True, text=True)
            
            self.logger.error(json.dumps({
                'event': 'ping_test',
                'host': self.target_host,
                'success': ping_result.returncode == 0,
                'output': ping_result.stdout,
                'timestamp': time.time()
            }))
        except Exception as e:
            self.logger.error(json.dumps({
                'event': 'ping_test_error',
                'host': self.target_host,
                'error': str(e),
                'timestamp': time.time()
            }))

        # Traceroute テスト
        try:
            traceroute_cmd = ['tracert' if os_type == 'windows' else 'traceroute', self.target_host]
            traceroute_result = subprocess.run(traceroute_cmd, capture_output=True, text=True)
            
            self.logger.error(json.dumps({
                'event': 'traceroute_test',
                'host': self.target_host,
                'success': traceroute_result.returncode == 0,
                'output': traceroute_result.stdout,
                'timestamp': time.time()
            }))
        except Exception as e:
            self.logger.error(json.dumps({
                'event': 'traceroute_test_error',
                'host': self.target_host,
                'error': str(e),
                'timestamp': time.time()
            }))

    def run_full_diagnostics(self):
        """すべての診断を実行"""
        self.logger.error(json.dumps({
            'event': 'diagnostics_start',
            'host': self.target_host,
            'timestamp': time.time()
        }))
        
        self.check_basic_dns()
        self.check_all_dns_servers()
        self.run_network_diagnostics()
        
        self.logger.error(json.dumps({
            'event': 'diagnostics_complete',
            'host': self.target_host,
            'timestamp': time.time()
        })) 
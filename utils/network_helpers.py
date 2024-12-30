import socket
import dns.resolver
from dns_diagnostics import DNSDiagnostics
from logging_utils import setup_logger
import json
import time

network_logger = setup_logger('network_helpers')

def verify_dns_configuration(host):
    """DNS設定の検証とフォールバック処理"""
    diagnostics = DNSDiagnostics(host)
    
    # フォールバックDNSサーバーのリスト
    fallback_dns = [
        '8.8.8.8',  # Google DNS
        '1.1.1.1',  # Cloudflare DNS
        '208.67.222.222'  # OpenDNS
    ]
    
    # 基本的なDNS解決を試行
    if diagnostics.check_basic_dns():
        return True
        
    # 基本的な解決が失敗した場合、フォールバックDNSを試行
    resolver = dns.resolver.Resolver()
    original_nameservers = resolver.nameservers
    
    for dns_server in fallback_dns:
        try:
            resolver.nameservers = [dns_server]
            answers = resolver.resolve(host, 'A')
            
            network_logger.error(json.dumps({
                'event': 'fallback_dns_success',
                'host': host,
                'dns_server': dns_server,
                'resolved_ips': [str(rdata) for rdata in answers],
                'timestamp': time.time()
            }))
            
            # 成功した場合、このDNSサーバーを使用
            return True
            
        except Exception as e:
            network_logger.error(json.dumps({
                'event': 'fallback_dns_error',
                'host': host,
                'dns_server': dns_server,
                'error': str(e),
                'timestamp': time.time()
            }))
    
    # すべてのDNSサーバーが失敗した場合
    network_logger.error(json.dumps({
        'event': 'all_dns_failed',
        'host': host,
        'timestamp': time.time()
    }))
    
    return False

def check_network_connectivity(host, port):
    """ネットワーク接続性の確認"""
    try:
        # ソケット接続のタイムアウト設定
        socket.setdefaulttimeout(10)
        
        # DNSの検証
        if not verify_dns_configuration(host):
            return False
            
        # TCP接続の試行
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        
        if result == 0:
            network_logger.error(json.dumps({
                'event': 'connection_success',
                'host': host,
                'port': port,
                'timestamp': time.time()
            }))
            return True
        else:
            network_logger.error(json.dumps({
                'event': 'connection_error',
                'host': host,
                'port': port,
                'error_code': result,
                'timestamp': time.time()
            }))
            return False
            
    except Exception as e:
        network_logger.error(json.dumps({
            'event': 'connection_exception',
            'host': host,
            'port': port,
            'error': str(e),
            'timestamp': time.time()
        }))
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def run_connection_diagnostics(host, port):
    """接続診断の実行"""
    # DNS診断の実行
    diagnostics = DNSDiagnostics(host)
    diagnostics.run_full_diagnostics()
    
    # ネットワーク接続性の確認
    connection_result = check_network_connectivity(host, port)
    
    return connection_result 
import socket
import dns.resolver
from dns_diagnostics import DNSDiagnostics
from logging_utils import setup_logger
import json
import time
import os

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

def diagnose_supabase_connection(host, port=5432):
    """Supabase接続の診断を実行"""
    try:
        # DNS診断の実行
        diagnostics = DNSDiagnostics(host)
        diagnostics.run_full_diagnostics()
        
        # 環境変数の確認
        env_vars = {
            'DATABASE_URL': os.environ.get('DATABASE_URL'),
            'SUPABASE_URL': os.environ.get('SUPABASE_URL'),
            'VERCEL_ENV': os.environ.get('VERCEL_ENV')
        }
        
        network_logger.error(json.dumps({
            'event': 'environment_check',
            'database_url_exists': bool(env_vars['DATABASE_URL']),
            'supabase_url_exists': bool(env_vars['SUPABASE_URL']),
            'vercel_env': env_vars['VERCEL_ENV'],
            'timestamp': time.time()
        }))
        
        # データベースURLの解析
        if env_vars['DATABASE_URL']:
            from urllib.parse import urlparse
            parsed = urlparse(env_vars['DATABASE_URL'])
            
            # URLの形式チェック
            network_logger.error(json.dumps({
                'event': 'database_url_format',
                'scheme': parsed.scheme,
                'host': parsed.hostname,
                'port': parsed.port,
                'path': parsed.path,
                'timestamp': time.time()
            }))
            
            # ホスト名の形式チェック
            if parsed.hostname:
                parts = parsed.hostname.split('.')
                if len(parts) >= 3 and parts[0] == 'db':
                    project_ref = parts[1]
                    network_logger.error(json.dumps({
                        'event': 'hostname_validation',
                        'valid': True,
                        'project_ref': project_ref,
                        'domain': '.'.join(parts[2:]),
                        'timestamp': time.time()
                    }))
                else:
                    network_logger.error(json.dumps({
                        'event': 'hostname_validation',
                        'valid': False,
                        'hostname': parsed.hostname,
                        'expected_format': 'db.<project-ref>.supabase.co',
                        'timestamp': time.time()
                    }))
        
        # 接続テスト
        connection_result = check_network_connectivity(host, port)
        
        return {
            'dns_resolution': diagnostics.results if hasattr(diagnostics, 'results') else None,
            'connection_test': connection_result,
            'environment_vars': {
                'database_url_exists': bool(env_vars['DATABASE_URL']),
                'supabase_url_exists': bool(env_vars['SUPABASE_URL']),
                'vercel_env': env_vars['VERCEL_ENV']
            }
        }
        
    except Exception as e:
        network_logger.error(json.dumps({
            'event': 'supabase_diagnosis_error',
            'error': str(e),
            'timestamp': time.time()
        }))
        return None

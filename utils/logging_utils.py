import logging
import json
import time
import uuid
import os

def setup_logger(name, level=logging.INFO):
    """ロガーのセットアップ（標準出力のみ）"""
    logger = logging.getLogger(name)
    
    # すでに設定済みの場合は既存のロガーを返す
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    logger.propagate = False  # 親ロガーへの伝播を防止
    
    formatter = logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    # 標準出力へのハンドラを追加
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# 各種ロガーの設定
request_logger = setup_logger('request')
db_logger = setup_logger('database')
api_logger = setup_logger('api')
network_logger = setup_logger('network')
system_logger = setup_logger('system')

class NetworkLogger:
    def __init__(self):
        self.connections = {}
        self.logger = setup_logger('network.connections')

    def log_network_connection(self, host, port):
        """ネットワーク接続のロギング"""
        connection_id = str(uuid.uuid4())
        start_time = time.time()
        
        self.connections[connection_id] = {
            'host': host,
            'port': port,
            'start_time': start_time
        }
        
        self.logger.info(json.dumps({
            'event': 'connection_start',
            'connection_id': connection_id,
            'host': host,
            'port': port,
            'timestamp': time.time()
        }))
        
        return connection_id

    def log_connection_end(self, connection_id, status='success'):
        """ネットワーク接続終了のロギング"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            duration = time.time() - connection['start_time']
            
            self.logger.info(json.dumps({
                'event': 'connection_end',
                'connection_id': connection_id,
                'host': connection['host'],
                'port': connection['port'],
                'status': status,
                'duration_ms': duration * 1000,
                'timestamp': time.time()
            }))
            
            del self.connections[connection_id]

    def error(self, message):
        """エラーログの出力"""
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                message = {'message': message}
        
        message['timestamp'] = time.time()
        self.logger.error(json.dumps(message))

    def info(self, message):
        """情報ログの出力"""
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                message = {'message': message}
        
        message['timestamp'] = time.time()
        self.logger.info(json.dumps(message))

network_logger = NetworkLogger()

def log_system_metrics():
    """システムメトリクスのロギング"""
    try:
        import psutil
        
        metrics = {
            'event': 'system_metrics',
            'timestamp': time.time(),
            'metrics': {
                'cpu': {
                    'percent': psutil.cpu_percent(interval=1),
                    'count': psutil.cpu_count(),
                    'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                },
                'memory': psutil.virtual_memory()._asdict(),
                'disk': psutil.disk_usage('/')._asdict(),
                'network': {
                    'connections': len(psutil.net_connections()),
                    'stats': {nic: stats._asdict() for nic, stats in psutil.net_if_stats().items()}
                }
            }
        }
        
        system_logger.info(json.dumps(metrics))
        
    except Exception as e:
        system_logger.error(json.dumps({
            'event': 'system_metrics_error',
            'error': str(e),
            'timestamp': time.time()
        })) 
import logging
import json
import time
import uuid
import os

def setup_logger(name, level=logging.INFO):
    """ロガーのセットアップ（標準出力のみ）"""
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s'
    )

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 既存のハンドラをクリア
    logger.handlers = []

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
            'port': port
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
                'duration_ms': duration * 1000
            }))
            
            del self.connections[connection_id]

    def error(self, message):
        """エラーログの出力"""
        self.logger.error(message)

    def info(self, message):
        """情報ログの出力"""
        self.logger.info(message)

network_logger = NetworkLogger()

def log_system_metrics():
    """システムメトリクスのロギング"""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_logger.info(json.dumps({
            'event': 'system_metrics',
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent
        }))
    except Exception as e:
        system_logger.error(json.dumps({
            'event': 'system_metrics_error',
            'error': str(e)
        })) 
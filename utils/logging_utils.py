import logging
import json
import time
import uuid
import os
from logging.handlers import RotatingFileHandler

# ログディレクトリの作成
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

def setup_logger(name, log_file, level=logging.INFO):
    """ロガーのセットアップ"""
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s'
    )

    handler = RotatingFileHandler(
        os.path.join(log_dir, log_file),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    # 標準出力にも出力
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# 各種ロガーの設定
request_logger = setup_logger('request', 'request.log')
db_logger = setup_logger('database', 'database.log')
api_logger = setup_logger('api', 'api.log')
network_logger = setup_logger('network', 'network.log')
system_logger = setup_logger('system', 'system.log')

class NetworkLogger:
    def __init__(self):
        self.connections = {}

    def log_network_connection(self, host, port):
        """ネットワーク接続のロギング"""
        connection_id = str(uuid.uuid4())
        start_time = time.time()
        
        self.connections[connection_id] = {
            'host': host,
            'port': port,
            'start_time': start_time
        }
        
        network_logger.info(json.dumps({
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
            
            network_logger.info(json.dumps({
                'event': 'connection_end',
                'connection_id': connection_id,
                'host': connection['host'],
                'port': connection['port'],
                'status': status,
                'duration_ms': duration * 1000
            }))
            
            del self.connections[connection_id]

network_logger = NetworkLogger()

def log_system_metrics():
    """システムメトリクスのロギング"""
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
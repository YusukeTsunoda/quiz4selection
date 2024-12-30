import os
import sys
import socket
import dns.resolver
import psycopg2
import urllib.parse
import logging
import json
import ssl
from datetime import datetime
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VercelDatabaseDiagnostic:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "environment": {},
            "dns_check": {},
            "connection_details": {},
            "postgres_check": {},
            "overall_status": "pending"
        }
        
    def check_environment(self) -> None:
        """環境変数とVercel固有の設定を確認"""
        logger.info("環境変数の確認を開始")
        
        # 重要な環境変数の存在確認
        env_vars = [
            'POSTGRES_URL',
            'POSTGRES_PRISMA_URL',
            'POSTGRES_URL_NON_POOLING',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'NEXT_PUBLIC_SUPABASE_URL',
            'NEXT_PUBLIC_SUPABASE_ANON_KEY'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            # 機密情報を隠しつつ存在確認
            self.results["environment"][var] = {
                "exists": value is not None,
                "length": len(value) if value else 0
            }
        
        logger.info("環境変数チェック完了")

    def get_connection_details(self) -> Optional[Dict[str, Any]]:
        """接続情報を取得"""
        supabase_url = os.getenv('POSTGRES_URL') or os.getenv('DATABASE_URL')
        if not supabase_url:
            # フォールバック: Supabase URLから構築
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY', '')
            if supabase_url and supabase_key:
                parsed = urllib.parse.urlparse(supabase_url)
                project_ref = parsed.hostname.split('.')[0]
                supabase_url = f"postgresql://postgres:{supabase_key}@{project_ref}.supabase.co:5432/postgres"

        if not supabase_url:
            logger.error("データベースURLが見つかりません")
            return None

        try:
            parsed = urllib.parse.urlparse(supabase_url)
            host = parsed.hostname
            if '.supabase.co' in host:
                # Supabaseのホスト名の場合、db.プレフィックスを追加
                project_ref = host.split('.')[0]
                host = f"db.{project_ref}.supabase.co"
            
            if 'eyJ' in supabase_key:
                # サービスロールキーからパスワードを抽出
                split_key = supabase_key.split('.')
                if len(split_key) >= 2:
                    # 2番目のパートを取得してパスワードとして使用
                    import base64
                    try:
                        password = split_key[1]
                        # パディングを追加
                        password += "=" * (-len(password) % 4)
                        # base64デコード
                        decoded = base64.b64decode(password)
                        # UTF-8としてデコード
                        password = decoded.decode('utf-8')
                    except:
                        password = supabase_key
                else:
                    password = supabase_key
            else:
                password = supabase_key

            # 直接的な接続情報を構築
            connection_info = {
                "host": f"db.{project_ref}.supabase.co",
                "port": 5432,
                "database": "postgres",
                "user": "postgres",
                "password": password
            }

            self.results["connection_details"] = {
                "host": connection_info["host"],
                "port": connection_info["port"],
                "database": connection_info["database"],
                "has_password": bool(connection_info["password"])
            }

            return connection_info

            self.results["connection_details"] = {
                "host": connection_info["host"],
                "port": connection_info["port"],
                "database": connection_info["database"],
                "has_password": bool(connection_info["password"]),
                "password_length": len(supabase_key) if supabase_key else 0
            }

            return connection_info

            self.results["connection_details"] = {
                "host": connection_info["host"],
                "port": connection_info["port"],
                "database": connection_info["database"],
                "has_password": bool(connection_info["password"])
            }

            return connection_info
        except Exception as e:
            logger.error(f"接続情報の解析エラー: {str(e)}")
            return None

    def check_dns(self, hostname: str) -> None:
        """DNSの解決をテスト"""
        logger.info(f"DNS解決の確認を開始: {hostname}")
        
        try:
            answers = dns.resolver.resolve(hostname, 'A')
            self.results["dns_check"] = {
                "success": True,
                "ip_addresses": [str(rdata) for rdata in answers],
                "resolver": str(dns.resolver.get_default_resolver().nameservers[0])
            }
        except Exception as e:
            self.results["dns_check"] = {
                "success": False,
                "error": str(e)
            }

    def check_postgres_connection(self, connection_info: Dict[str, Any]) -> None:
        """PostgreSQL接続テスト"""
        logger.info("PostgreSQL接続の確認を開始")
        
        try:
            # 接続文字列を構築
            conn_str = (
                f"postgresql://{connection_info['user']}:{connection_info['password']}"
                f"@{connection_info['host']}:{connection_info['port']}"
                f"/{connection_info['database']}?sslmode=require"
            )
            
            # 接続を試行
            conn = psycopg2.connect(
                host=connection_info['host'],
                port=connection_info['port'],
                dbname=connection_info['database'],
                user=connection_info['user'],
                password=connection_info['password'],
                connect_timeout=10,
                sslmode='require'
            )
            
            # バージョン確認
            with conn.cursor() as cur:
                cur.execute('SELECT version();')
                version = cur.fetchone()[0]
            
            conn.close()
            
            self.results["postgres_check"] = {
                "success": True,
                "version": version
            }
            
        except Exception as e:
            self.results["postgres_check"] = {
                "success": False,
                "error": str(e)
            }

    def run_diagnostics(self) -> Dict[str, Any]:
        """すべての診断を実行"""
        logger.info("診断を開始")
        
        # 環境変数の確認
        self.check_environment()
        
        # 接続情報の取得
        connection_info = self.get_connection_details()
        if not connection_info:
            self.results["overall_status"] = "failed"
            return self.results
            
        # 各種チェックの実行
        self.check_dns(connection_info["host"])
        self.check_postgres_connection(connection_info)
        
        # 総合的な状態の評価
        all_checks = [
            self.results["dns_check"].get("success", False),
            self.results["postgres_check"].get("success", False)
        ]
        
        self.results["overall_status"] = "success" if all(all_checks) else "failed"
        
        return self.results

def main():
    diagnostic = VercelDatabaseDiagnostic()
    results = diagnostic.run_diagnostics()
    
    print("\n=== 診断結果 ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # 問題が見つかった場合の推奨事項
    if results["overall_status"] == "failed":
        print("\n=== 推奨される対処方法 ===")
        if not results["dns_check"].get("success"):
            print("- DNSの設定を確認してください")
            print("  - Supabaseのプロジェクト設定でホスト名が正しいか確認")
        if not results["postgres_check"].get("success"):
            print("- PostgreSQL接続の問題を確認してください")
            print("  - Supabaseのダッシュボードで接続情報を確認")
            print("  - データベースパスワードが正しいか確認")
            print("  - ネットワーク設定とIPの制限を確認")

if __name__ == "__main__":
    main()
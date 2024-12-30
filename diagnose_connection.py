import os
from utils.network_helpers import diagnose_supabase_connection
import json
from urllib.parse import urlparse

def get_supabase_host():
    """Supabaseのホスト名を環境変数から正しく取得"""
    database_url = os.environ.get('DATABASE_URL', '')
    supabase_url = os.environ.get('SUPABASE_URL', '')
    
    if database_url:
        # DATABASE_URLからホスト名を取得
        parsed = urlparse(database_url)
        if parsed.hostname:
            return parsed.hostname
    
    if supabase_url:
        # SUPABASE_URLからプロジェクトIDを取得し、ホスト名を構築
        parsed = urlparse(supabase_url)
        if parsed.hostname:
            project_id = parsed.hostname.split('.')[0]
            return f"db.{project_id}.supabase.co"
    
    # デフォルトのホスト名を返す
    return "db.cujvnutaucgrhleclmpq.supabase.co"

def main():
    """Supabase接続の診断を実行するメインスクリプト"""
    print("Starting Supabase connection diagnostics...")
    
    # 環境変数の表示（機密情報は除く）
    print("\nEnvironment Variables:")
    database_url = os.environ.get('DATABASE_URL', '')
    supabase_url = os.environ.get('SUPABASE_URL', '')
    print(f"DATABASE_URL exists: {bool(database_url)}")
    print(f"SUPABASE_URL exists: {bool(supabase_url)}")
    print(f"VERCEL_ENV: {os.environ.get('VERCEL_ENV', 'not set')}")
    
    if database_url:
        parsed = urlparse(database_url)
        print("\nDatabase URL Analysis:")
        print(f"Scheme: {parsed.scheme}")
        print(f"Host: {parsed.hostname}")
        print(f"Port: {parsed.port}")
        print(f"Path: {parsed.path}")
    
    # 正しいホスト名を取得
    host = get_supabase_host()
    print(f"\nTesting connection to: {host}")
    
    # 診断の実行
    results = diagnose_supabase_connection(host)
    
    if results:
        print("\nDiagnostic Results:")
        print("-" * 50)
        
        # DNS解決の結果
        if results['dns_resolution']:
            print("\nDNS Resolution:")
            print(json.dumps(results['dns_resolution'], indent=2))
        
        # 接続テストの結果
        print("\nConnection Test:")
        print(f"Success: {results['connection_test']}")
        
        # 環境変数の状態
        print("\nEnvironment Variables Status:")
        for key, value in results['environment_vars'].items():
            print(f"{key}: {value}")
            
        # 接続が失敗した場合の追加情報
        if not results['connection_test']:
            print("\nTroubleshooting Recommendations:")
            print("1. Verify your Supabase project is active")
            print("2. Check if the project ID in the connection URL is correct")
            print("3. Ensure your IP address is allowed in Supabase's network settings")
            print("4. Verify the database password in DATABASE_URL")
            print("5. Try using a different DNS server (e.g., 8.8.8.8 or 1.1.1.1)")
    else:
        print("\nDiagnostics failed to complete. Check the logs for details.")
    
    print("\nDiagnostics complete. Check the logs directory for detailed information.")

if __name__ == "__main__":
    main() 
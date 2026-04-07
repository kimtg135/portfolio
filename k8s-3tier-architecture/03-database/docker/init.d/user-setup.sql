-- 쇼핑몰 데이터베이스
CREATE DATABASE IF NOT EXISTS shop_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 복제 사용자
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED BY 'Repl_Secure_Pass_456';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';

-- 애플리케이션 사용자
CREATE USER IF NOT EXISTS 'shop_user'@'%' IDENTIFIED BY 'Shop_Pass_456';
GRANT ALL PRIVILEGES ON shop_db.* TO 'shop_user'@'%';

-- ProxySQL 모니터 사용자
CREATE USER IF NOT EXISTS 'proxysql'@'%' IDENTIFIED BY 'proxysql_pass';
GRANT USAGE ON *.* TO 'proxysql'@'%';

FLUSH PRIVILEGES;

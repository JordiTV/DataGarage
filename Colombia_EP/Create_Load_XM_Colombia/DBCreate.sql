/*
Database needs to be created.
MariaDB is used for this project.
In Ubuntu (as root):
# apt-get install mariadb-server
# mysql_secure_installation
*/

CREATE DATABASE EP_Colombia
CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

--Grant privileges to admin user, change 'admin' to user name in DB, needs to be created first:
GRANT ALL PRIVILEGES ON EP_Colombia.* TO 'admin'@'%'; 
--in case a 'watcher' user wants to be added:
GRANT SELECT ON EP_Colombia.* TO 'watcher'@'%';

--just in case...
Flush privileges;


/*To create users:
CREATE USER 'username'@'%' IDENTIFIED BY 'user'spassword';
*/

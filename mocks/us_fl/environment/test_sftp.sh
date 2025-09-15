#!/bin/bash
# Test SFTP connection and list files

expect << 'EOF'
spawn sftp -P 2222 test@localhost
expect "password:"
send "test\r"
expect "sftp>"
send "pwd\r"
expect "sftp>"
send "ls -la\r"
expect "sftp>"
send "ls -la doc/\r"
expect "sftp>"
send "ls -la doc/cor/\r"
expect "sftp>"
send "quit\r"
expect eof
EOF

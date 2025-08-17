# New Tools Added to EYN Python Toolkit

This document describes all the new tools and modules that have been added to enhance the EYN Python toolkit.

## 🗄️ Database Tools (`eyn db`)

SQLite database operations and utilities.

### Commands:

#### `eyn db query <db_path> <query>`
Execute SQL queries on a database.
```bash
eyn db query database.db "SELECT * FROM users LIMIT 5"
eyn db query database.db "SELECT COUNT(*) FROM users" --json
```

#### `eyn db tables <db_path>`
List all tables in a database.
```bash
eyn db tables database.db
eyn db tables database.db --json
```

#### `eyn db info <db_path> <table>`
Get table schema information.
```bash
eyn db info database.db users
eyn db info database.db users --json
```

#### `eyn db backup <db_path> <backup_path>`
Create a backup of a database.
```bash
eyn db backup database.db backup_$(date +%Y%m%d).db
```

#### `eyn db optimize <db_path>`
Optimize a database (VACUUM and ANALYZE).
```bash
eyn db optimize database.db
```

#### `eyn db export <db_path> <table> <csv_path>`
Export a table to CSV.
```bash
eyn db export database.db users users_export.csv
```

#### `eyn db import <db_path> <csv_path> <table>`
Import CSV data into a table.
```bash
eyn db import database.db users.csv users --create-table
```

---

## 🔐 Crypto Tools (`eyn crypto`)

Encryption, decryption, and cryptography utilities.

### Commands:

#### `eyn crypto encrypt-text <text> --key <key>`
Encrypt text using Fernet encryption.
```bash
eyn crypto encrypt-text "Hello World" --key "your-secret-key"
```

#### `eyn crypto decrypt-text <encrypted_text> --key <key>`
Decrypt text using Fernet encryption.
```bash
eyn crypto decrypt-text "gAAAAAB..." --key "your-secret-key"
```

#### `eyn crypto encrypt-file <input_file> <output_file> --key <key>`
Encrypt a file.
```bash
eyn crypto encrypt-file secret.txt secret.enc --key "your-secret-key"
```

#### `eyn crypto decrypt-file <input_file> <output_file> --key <key>`
Decrypt a file.
```bash
eyn crypto decrypt-file secret.enc secret_decrypted.txt --key "your-secret-key"
```

#### `eyn crypto generate-key`
Generate a new encryption key.
```bash
eyn crypto generate-key
```

#### `eyn crypto hash-password <password>`
Hash a password using PBKDF2.
```bash
eyn crypto hash-password "my-secure-password"
```

---

## 🌐 Network Tools (`eyn net`)

Network utilities and diagnostic tools.

### Commands:

#### `eyn net scan <host> [--start <port>] [--end <port>]`
Scan ports on a host.
```bash
eyn net scan localhost
eyn net scan 192.168.1.1 --start 80 --end 443
eyn net scan example.com --json
```

#### `eyn net dns <domain> [--type <record_type>]`
Perform DNS lookup.
```bash
eyn net dns google.com
eyn net dns google.com --type MX
eyn net dns google.com --type A --json
```

#### `eyn net reverse-dns <ip>`
Perform reverse DNS lookup.
```bash
eyn net reverse-dns 8.8.8.8
```

#### `eyn net ping <host> [--count <count>]`
Ping a host and get statistics.
```bash
eyn net ping google.com
eyn net ping 192.168.1.1 --count 10
eyn net ping example.com --json
```

#### `eyn net ssl <host> [--port <port>]`
Check SSL certificate information.
```bash
eyn net ssl google.com
eyn net ssl example.com --port 8443
eyn net ssl example.com --json
```

#### `eyn net whois <domain>`
Get WHOIS information for a domain.
```bash
eyn net whois google.com
```

---

## 📊 Analysis Tools (`eyn analysis`)

File and data analysis utilities.

### Commands:

#### `eyn analysis file-type <file_path>`
Detect file type using multiple methods.
```bash
eyn analysis file-type document.pdf
eyn analysis file-type image.jpg --json
```

#### `eyn analysis duplicates <directory> [--min-size <bytes>]`
Find duplicate files by content hash.
```bash
eyn analysis duplicates /path/to/photos
eyn analysis duplicates /path/to/files --min-size 1024
eyn analysis duplicates /path/to/files --json
```

#### `eyn analysis stats <directory>`
Get comprehensive file statistics.
```bash
eyn analysis stats /path/to/directory
eyn analysis stats /path/to/directory --json
```

#### `eyn analysis large-files <directory> [--min-size <mb>]`
Find large files in a directory.
```bash
eyn analysis large-files /path/to/directory
eyn analysis large-files /path/to/directory --min-size 500
eyn analysis large-files /path/to/directory --json
```

#### `eyn analysis integrity <file_path>`
Check file integrity using multiple hash algorithms.
```bash
eyn analysis integrity important_file.zip
eyn analysis integrity document.pdf --json
```

---

## 📝 Text Processing Tools (`eyn text`)

Advanced text processing and analysis utilities.

### Commands:

#### `eyn text extract-emails <text> [--file <file>]`
Extract email addresses from text.
```bash
eyn text extract-emails "Contact us at john@example.com or jane@test.com"
eyn text extract-emails "" --file emails.txt
eyn text extract-emails "Text with emails" --json
```

#### `eyn text extract-urls <text> [--file <file>]`
Extract URLs from text.
```bash
eyn text extract-urls "Visit https://example.com and http://test.com"
eyn text extract-urls "" --file webpage.html
eyn text extract-urls "Text with URLs" --json
```

#### `eyn text sentiment <text> [--file <file>]`
Analyze text sentiment.
```bash
eyn text sentiment "This is a great product! I love it!"
eyn text sentiment "" --file review.txt
eyn text sentiment "Text to analyze" --json
```

#### `eyn text keywords <text> [--file <file>] [--top <n>]`
Extract keywords from text.
```bash
eyn text keywords "This is a sample text for keyword extraction"
eyn text keywords "" --file document.txt --top 20
eyn text keywords "Text for keywords" --json
```

#### `eyn text summarize <text> [--file <file>] [--sentences <n>]`
Summarize text.
```bash
eyn text summarize "Long text to summarize..."
eyn text summarize "" --file long_document.txt --sentences 5
```

#### `eyn text clean <text> [--file <file>] [--no-punctuation] [--no-numbers]`
Clean and normalize text.
```bash
eyn text clean "Text to clean"
eyn text clean "" --file messy_text.txt --no-punctuation --no-numbers
```

---

## 🔧 Additional Features

### Progress Bars
All download operations now feature beautiful progress bars showing:
- Download progress percentage
- Transfer speed (B/s, KB/s, MB/s, etc.)
- Time remaining estimates
- File size information
- Visual progress bars with spinners

### Enhanced Error Handling
All new tools include comprehensive error handling with:
- Detailed error messages
- Graceful failure handling
- JSON output options for programmatic use
- Proper exit codes

### Cross-Platform Support
All tools work on:
- Windows
- macOS
- Linux

### Dependencies Added
- `cryptography` - For encryption/decryption
- `dnspython` - For DNS operations
- `python-magic` - For file type detection
- `playwright` - For web automation (already used)

---

## 🚀 Usage Examples

### Database Management
```bash
# Create a simple database and import data
eyn db query database.db "CREATE TABLE users (id INTEGER, name TEXT, email TEXT)"
eyn db import database.db users.csv users --create-table
eyn db backup database.db backup.db
```

### File Security
```bash
# Encrypt sensitive files
eyn crypto generate-key > secret.key
eyn crypto encrypt-file sensitive.txt sensitive.enc --key $(cat secret.key)
```

### Network Diagnostics
```bash
# Check network connectivity and services
eyn net ping google.com
eyn net scan localhost --start 22 --end 80
eyn net ssl github.com
```

### File Analysis
```bash
# Analyze file system and find issues
eyn analysis stats /home/user/documents
eyn analysis duplicates /home/user/photos --min-size 1024
eyn analysis large-files /home/user --min-size 100
```

### Text Processing
```bash
# Process and analyze text content
eyn text extract-emails "" --file contacts.txt
eyn text sentiment "" --file customer_reviews.txt
eyn text keywords "" --file article.txt --top 15
```

---

## 📋 Requirements

- Python 3.11+
- All dependencies are automatically installed with the package
- Some tools may require system utilities (ping, traceroute, whois) on Unix-like systems

## 🔄 Updates

These tools complement the existing EYN Python toolkit and follow the same design principles:
- Consistent CLI interface
- Rich console output
- JSON output options
- Comprehensive error handling
- Cross-platform compatibility
- Progress indicators where applicable

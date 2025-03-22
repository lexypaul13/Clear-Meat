#!/usr/bin/env python3
"""
Database security audit script for the MeatWise API.

This script performs security checks on the database configuration,
permissions, and structure to identify potential security issues.
"""

import argparse
import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import json
from datetime import datetime
import re

# Load environment variables
load_dotenv()

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DatabaseAuditor:
    """Class to perform security audits on the database."""
    
    def __init__(self, host, port, dbname, user, password):
        """Initialize with database connection parameters."""
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.conn = None
        self.issues = []
        self.passed = []
        
    def connect(self):
        """Establish a connection to the database."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            print(f"{Colors.GREEN}✓ Successfully connected to the database{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"{Colors.FAIL}✗ Failed to connect to the database: {e}{Colors.ENDC}")
            return False
    
    def disconnect(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print(f"{Colors.BLUE}Database connection closed{Colors.ENDC}")
    
    def run_query(self, query, params=None):
        """Run a query and return the results."""
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
            
            return []
        except Exception as e:
            print(f"{Colors.FAIL}Query error: {e}{Colors.ENDC}")
            print(f"Query: {query}")
            return None

    def add_issue(self, category, severity, description, recommendation):
        """Add a security issue to the list."""
        self.issues.append({
            "category": category,
            "severity": severity,
            "description": description,
            "recommendation": recommendation
        })
    
    def add_pass(self, category, description):
        """Add a passed check to the list."""
        self.passed.append({
            "category": category,
            "description": description
        })
        
    def check_postgres_version(self):
        """Check if PostgreSQL version is up to date."""
        print(f"\n{Colors.HEADER}Checking PostgreSQL version...{Colors.ENDC}")
        
        result = self.run_query("SELECT version();")
        if not result:
            return
            
        version_str = result[0]['version']
        print(f"Database version: {version_str}")
        
        # Extract version number
        match = re.search(r'PostgreSQL (\d+)\.(\d+)', version_str)
        if not match:
            self.add_issue(
                "Configuration", "Medium",
                "Could not determine PostgreSQL version",
                "Ensure you're running a supported and up-to-date PostgreSQL version"
            )
            return
            
        major_version = int(match.group(1))
        minor_version = int(match.group(2))
        
        if major_version < 12:
            self.add_issue(
                "Configuration", "High",
                f"PostgreSQL version {major_version}.{minor_version} is outdated",
                "Upgrade to PostgreSQL 14 or newer for better security features"
            )
        elif major_version < 14:
            self.add_issue(
                "Configuration", "Medium",
                f"PostgreSQL version {major_version}.{minor_version} is not the latest",
                "Consider upgrading to PostgreSQL 14 or newer"
            )
        else:
            self.add_pass(
                "Configuration",
                f"PostgreSQL version {major_version}.{minor_version} is recent"
            )
            print(f"{Colors.GREEN}✓ PostgreSQL version {major_version}.{minor_version} is recent{Colors.ENDC}")
    
    def check_user_permissions(self):
        """Check for excessive user permissions."""
        print(f"\n{Colors.HEADER}Checking user permissions...{Colors.ENDC}")
        
        # Check for superusers
        superusers = self.run_query("""
            SELECT usename, usesuper 
            FROM pg_user 
            WHERE usesuper = true;
        """)
        
        if superusers:
            for user in superusers:
                if user['usename'] not in ['postgres']:
                    self.add_issue(
                        "Permissions", "High",
                        f"User '{user['usename']}' has superuser privileges",
                        "Remove superuser privileges from users that don't require it"
                    )
                    print(f"{Colors.FAIL}✗ User '{user['usename']}' has superuser privileges{Colors.ENDC}")
            
            if len(superusers) > 1:
                print(f"{Colors.WARNING}! Multiple superusers found: {len(superusers)}{Colors.ENDC}")
            else:
                self.add_pass(
                    "Permissions",
                    "Appropriate number of superusers"
                )
                print(f"{Colors.GREEN}✓ Appropriate number of superusers{Colors.ENDC}")
        
        # Check for public schema permissions
        public_privs = self.run_query("""
            SELECT grantee, privilege_type
            FROM information_schema.role_table_grants 
            WHERE table_schema = 'public' AND grantee = 'PUBLIC';
        """)
        
        if public_privs:
            for priv in public_privs:
                if priv['privilege_type'] in ['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']:
                    self.add_issue(
                        "Permissions", "High",
                        f"PUBLIC role has {priv['privilege_type']} permission on public schema",
                        "Revoke excessive permissions from the PUBLIC role"
                    )
                    print(f"{Colors.FAIL}✗ PUBLIC role has {priv['privilege_type']} permission{Colors.ENDC}")
        else:
            self.add_pass(
                "Permissions",
                "No excessive PUBLIC permissions"
            )
            print(f"{Colors.GREEN}✓ No excessive PUBLIC permissions{Colors.ENDC}")
    
    def check_row_level_security(self):
        """Check if row level security is enabled on tables."""
        print(f"\n{Colors.HEADER}Checking row level security...{Colors.ENDC}")
        
        tables = self.run_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        
        if not tables:
            return
            
        for table in tables:
            table_name = table['table_name']
            rls_enabled = self.run_query("""
                SELECT relrowsecurity 
                FROM pg_class 
                WHERE relname = %s AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
            """, (table_name,))
            
            if not rls_enabled or not rls_enabled[0]['relrowsecurity']:
                self.add_issue(
                    "Row Level Security", "Medium",
                    f"Row Level Security not enabled on table '{table_name}'",
                    "Enable Row Level Security on all tables containing sensitive data"
                )
                print(f"{Colors.WARNING}! Table '{table_name}' does not have RLS enabled{Colors.ENDC}")
            else:
                # Check for RLS policies
                policies = self.run_query("""
                    SELECT polname 
                    FROM pg_policy 
                    WHERE polrelid = (SELECT oid FROM pg_class WHERE relname = %s 
                                      AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public'));
                """, (table_name,))
                
                if not policies:
                    self.add_issue(
                        "Row Level Security", "Medium",
                        f"Row Level Security enabled but no policies defined for table '{table_name}'",
                        "Define appropriate RLS policies"
                    )
                    print(f"{Colors.WARNING}! Table '{table_name}' has RLS enabled but no policies{Colors.ENDC}")
                else:
                    self.add_pass(
                        "Row Level Security",
                        f"Table '{table_name}' has RLS enabled with {len(policies)} policies"
                    )
                    print(f"{Colors.GREEN}✓ Table '{table_name}' has RLS enabled with {len(policies)} policies{Colors.ENDC}")
    
    def check_password_policies(self):
        """Check password policies."""
        print(f"\n{Colors.HEADER}Checking password policies...{Colors.ENDC}")
        
        # From Supabase config
        with open(".env") as f:
            env_content = f.read()
            
            # Check password length
            match = re.search(r'minimum_password_length\s*=\s*(\d+)', env_content)
            if not match:
                min_length = 6  # Default in Supabase
            else:
                min_length = int(match.group(1))
                
            if min_length < 8:
                self.add_issue(
                    "Authentication", "Medium",
                    f"Minimum password length is set to {min_length}, which is too short",
                    "Set minimum_password_length to at least 8 in Supabase configuration"
                )
                print(f"{Colors.WARNING}! Minimum password length is only {min_length}{Colors.ENDC}")
            else:
                self.add_pass(
                    "Authentication",
                    f"Minimum password length is set to {min_length}"
                )
                print(f"{Colors.GREEN}✓ Minimum password length is {min_length}{Colors.ENDC}")
            
            # Check password complexity
            match = re.search(r'password_requirements\s*=\s*"([^"]*)"', env_content)
            if not match or not match.group(1):
                self.add_issue(
                    "Authentication", "Medium",
                    "No password complexity requirements defined",
                    "Set password_requirements to 'lower_upper_letters_digits_symbols' in Supabase configuration"
                )
                print(f"{Colors.WARNING}! No password complexity requirements{Colors.ENDC}")
            else:
                requirements = match.group(1)
                if requirements != "lower_upper_letters_digits_symbols":
                    self.add_issue(
                        "Authentication", "Low",
                        f"Password complexity set to '{requirements}', which is not the strongest setting",
                        "Set password_requirements to 'lower_upper_letters_digits_symbols' for maximum security"
                    )
                    print(f"{Colors.WARNING}! Password complexity could be stronger: {requirements}{Colors.ENDC}")
                else:
                    self.add_pass(
                        "Authentication",
                        "Strong password complexity requirements configured"
                    )
                    print(f"{Colors.GREEN}✓ Strong password complexity requirements{Colors.ENDC}")
    
    def check_connection_pooling(self):
        """Check connection pooling configuration."""
        print(f"\n{Colors.HEADER}Checking connection pooling...{Colors.ENDC}")
        
        with open("supabase/config.toml") as f:
            config_content = f.read()
            
            # Check if connection pooling is enabled
            match = re.search(r'\[db\.pooler\]\s+enabled\s*=\s*(true|false)', config_content, re.DOTALL)
            if not match or match.group(1) == "false":
                self.add_issue(
                    "Configuration", "Low",
                    "Connection pooling is not enabled",
                    "Enable connection pooling for better resource management and security"
                )
                print(f"{Colors.WARNING}! Connection pooling is not enabled{Colors.ENDC}")
            else:
                self.add_pass(
                    "Configuration",
                    "Connection pooling is enabled"
                )
                print(f"{Colors.GREEN}✓ Connection pooling is enabled{Colors.ENDC}")
                
                # Check pooling mode
                match = re.search(r'pool_mode\s*=\s*"([^"]*)"', config_content)
                if match and match.group(1) == "transaction":
                    self.add_pass(
                        "Configuration",
                        "Connection pooling mode is set to transaction (recommended)"
                    )
                    print(f"{Colors.GREEN}✓ Connection pooling mode is transaction{Colors.ENDC}")
                else:
                    self.add_issue(
                        "Configuration", "Low",
                        "Connection pooling mode is not set to transaction",
                        "Set pool_mode to 'transaction' for better security isolation"
                    )
                    print(f"{Colors.WARNING}! Connection pooling mode is not optimal{Colors.ENDC}")
    
    def check_database_logging(self):
        """Check database logging configuration."""
        print(f"\n{Colors.HEADER}Checking database logging...{Colors.ENDC}")
        
        log_settings = self.run_query("""
            SELECT name, setting 
            FROM pg_settings 
            WHERE name IN (
                'log_statement', 
                'log_min_duration_statement', 
                'log_connections', 
                'log_disconnections'
            );
        """)
        
        if not log_settings:
            return
            
        log_config = {item['name']: item['setting'] for item in log_settings}
        
        # Check log_statement
        if log_config.get('log_statement') == 'none':
            self.add_issue(
                "Logging", "Medium",
                "SQL statement logging is disabled (log_statement=none)",
                "Set log_statement to 'mod' or 'all' to log modification queries or all queries"
            )
            print(f"{Colors.WARNING}! SQL statement logging is disabled{Colors.ENDC}")
        else:
            self.add_pass(
                "Logging",
                f"SQL statement logging is set to '{log_config.get('log_statement')}'"
            )
            print(f"{Colors.GREEN}✓ SQL statement logging is set to '{log_config.get('log_statement')}'{Colors.ENDC}")
        
        # Check log_min_duration_statement
        log_duration = log_config.get('log_min_duration_statement', '-1')
        if log_duration == '-1':
            self.add_issue(
                "Logging", "Low",
                "Slow query logging is disabled (log_min_duration_statement=-1)",
                "Set log_min_duration_statement to log queries that exceed a certain duration"
            )
            print(f"{Colors.WARNING}! Slow query logging is disabled{Colors.ENDC}")
        else:
            self.add_pass(
                "Logging",
                f"Slow query logging is enabled for queries > {log_duration}ms"
            )
            print(f"{Colors.GREEN}✓ Slow query logging is enabled for queries > {log_duration}ms{Colors.ENDC}")
        
        # Check connection logging
        if log_config.get('log_connections') != 'on':
            self.add_issue(
                "Logging", "Low",
                "Connection logging is disabled",
                "Enable log_connections for security monitoring"
            )
            print(f"{Colors.WARNING}! Connection logging is disabled{Colors.ENDC}")
        else:
            self.add_pass(
                "Logging",
                "Connection logging is enabled"
            )
            print(f"{Colors.GREEN}✓ Connection logging is enabled{Colors.ENDC}")
            
    def check_security_extensions(self):
        """Check security-related PostgreSQL extensions."""
        print(f"\n{Colors.HEADER}Checking security extensions...{Colors.ENDC}")
        
        extensions = self.run_query("""
            SELECT extname 
            FROM pg_extension;
        """)
        
        if not extensions:
            return
            
        extension_names = [ext['extname'] for ext in extensions]
        print(f"Installed extensions: {', '.join(extension_names)}")
        
        # Check for pgcrypto
        if 'pgcrypto' not in extension_names:
            self.add_issue(
                "Extensions", "Medium",
                "pgcrypto extension is not installed",
                "Install pgcrypto extension for cryptographic functions"
            )
            print(f"{Colors.WARNING}! pgcrypto extension is not installed{Colors.ENDC}")
        else:
            self.add_pass(
                "Extensions",
                "pgcrypto extension is installed"
            )
            print(f"{Colors.GREEN}✓ pgcrypto extension is installed{Colors.ENDC}")
            
        # Check for uuid-ossp
        if 'uuid-ossp' not in extension_names:
            self.add_issue(
                "Extensions", "Low",
                "uuid-ossp extension is not installed",
                "Install uuid-ossp extension for UUID generation"
            )
            print(f"{Colors.WARNING}! uuid-ossp extension is not installed{Colors.ENDC}")
        else:
            self.add_pass(
                "Extensions",
                "uuid-ossp extension is installed"
            )
            print(f"{Colors.GREEN}✓ uuid-ossp extension is installed{Colors.ENDC}")
    
    def check_database_backups(self):
        """Checks related to database backups."""
        print(f"\n{Colors.HEADER}Checking backup configuration...{Colors.ENDC}")
        print(f"{Colors.CYAN}Note: This is a manual check - please verify your backup policy{Colors.ENDC}")
        
        print("Recommended backup practices:")
        print("1. Regular automated backups (daily recommended)")
        print("2. Point-in-time recovery configuration")
        print("3. Backup encryption")
        print("4. Off-site backup storage")
        print("5. Regular backup restoration testing")
        
        self.add_issue(
            "Backup", "Information",
            "Database backup configuration requires manual verification",
            "Ensure regular encrypted backups with off-site storage and restoration testing"
        )
    
    def run_all_checks(self):
        """Run all security checks."""
        if not self.connect():
            return False
            
        print(f"\n{Colors.BOLD}{Colors.HEADER}Running Database Security Audit{Colors.ENDC}")
        print(f"{Colors.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"{Colors.CYAN}Database: {self.dbname} on {self.host}:{self.port}{Colors.ENDC}")
        print(f"{Colors.CYAN}User: {self.user}{Colors.ENDC}")
        
        try:
            self.check_postgres_version()
            self.check_user_permissions()
            self.check_row_level_security()
            self.check_password_policies()
            self.check_connection_pooling()
            self.check_database_logging()
            self.check_security_extensions()
            self.check_database_backups()
            
            return True
        except Exception as e:
            print(f"{Colors.FAIL}Error during audit: {str(e)}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.disconnect()
    
    def generate_report(self, output_file=None):
        """Generate a security audit report."""
        total_issues = len(self.issues)
        total_passed = len(self.passed)
        
        high_issues = sum(1 for issue in self.issues if issue['severity'] == 'High')
        medium_issues = sum(1 for issue in self.issues if issue['severity'] == 'Medium')
        low_issues = sum(1 for issue in self.issues if issue['severity'] == 'Low')
        info_issues = sum(1 for issue in self.issues if issue['severity'] == 'Information')
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}Database Security Audit Results{Colors.ENDC}")
        print(f"{Colors.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"Total checks passed: {Colors.GREEN}{total_passed}{Colors.ENDC}")
        print(f"Total issues found: {Colors.WARNING if total_issues > 0 else Colors.GREEN}{total_issues}{Colors.ENDC}")
        print(f"  High severity: {Colors.FAIL if high_issues > 0 else Colors.GREEN}{high_issues}{Colors.ENDC}")
        print(f"  Medium severity: {Colors.WARNING if medium_issues > 0 else Colors.GREEN}{medium_issues}{Colors.ENDC}")
        print(f"  Low severity: {Colors.CYAN if low_issues > 0 else Colors.GREEN}{low_issues}{Colors.ENDC}")
        print(f"  Informational: {Colors.BLUE}{info_issues}{Colors.ENDC}")
        
        # Print issues by severity
        if high_issues > 0:
            print(f"\n{Colors.BOLD}{Colors.FAIL}High Severity Issues:{Colors.ENDC}")
            for issue in self.issues:
                if issue['severity'] == 'High':
                    print(f"{Colors.FAIL}• {issue['category']}: {issue['description']}{Colors.ENDC}")
                    print(f"  {Colors.CYAN}Recommendation: {issue['recommendation']}{Colors.ENDC}")
        
        if medium_issues > 0:
            print(f"\n{Colors.BOLD}{Colors.WARNING}Medium Severity Issues:{Colors.ENDC}")
            for issue in self.issues:
                if issue['severity'] == 'Medium':
                    print(f"{Colors.WARNING}• {issue['category']}: {issue['description']}{Colors.ENDC}")
                    print(f"  {Colors.CYAN}Recommendation: {issue['recommendation']}{Colors.ENDC}")
        
        if low_issues > 0:
            print(f"\n{Colors.BOLD}{Colors.CYAN}Low Severity Issues:{Colors.ENDC}")
            for issue in self.issues:
                if issue['severity'] == 'Low':
                    print(f"{Colors.CYAN}• {issue['category']}: {issue['description']}{Colors.ENDC}")
                    print(f"  Recommendation: {issue['recommendation']}")
        
        if output_file:
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "host": self.host,
                    "port": self.port,
                    "name": self.dbname,
                    "user": self.user
                },
                "summary": {
                    "passed_checks": total_passed,
                    "total_issues": total_issues,
                    "high_issues": high_issues,
                    "medium_issues": medium_issues,
                    "low_issues": low_issues,
                    "info_issues": info_issues
                },
                "passed": self.passed,
                "issues": self.issues
            }
            
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
                
            print(f"\n{Colors.GREEN}Report saved to {output_file}{Colors.ENDC}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='PostgreSQL Database Security Audit Tool')
    parser.add_argument('--host', default=os.getenv('POSTGRES_SERVER', 'localhost'), help='Database host')
    parser.add_argument('--port', default=os.getenv('POSTGRES_PORT', '5432'), help='Database port')
    parser.add_argument('--dbname', default=os.getenv('POSTGRES_DB', 'postgres'), help='Database name')
    parser.add_argument('--user', default=os.getenv('POSTGRES_USER', 'postgres'), help='Database user')
    parser.add_argument('--password', default=os.getenv('POSTGRES_PASSWORD', ''), help='Database password')
    parser.add_argument('--output', help='Output file for JSON report')
    
    args = parser.parse_args()
    
    auditor = DatabaseAuditor(
        host=args.host,
        port=args.port,
        dbname=args.dbname,
        user=args.user,
        password=args.password
    )
    
    if auditor.run_all_checks():
        auditor.generate_report(args.output)
        
        # Return non-zero exit code if high severity issues exist
        high_issues = sum(1 for issue in auditor.issues if issue['severity'] == 'High')
        if high_issues > 0:
            return 1
    else:
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
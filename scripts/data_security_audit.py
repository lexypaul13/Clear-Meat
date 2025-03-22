#!/usr/bin/env python3
"""
Database data security audit script for the MeatWise API.

This script audits the database for potential security issues related to data storage,
including PII handling, sensitive data encryption, access patterns, etc.
"""

import argparse
import os
import sys
import psycopg2
import re
from psycopg2 import sql
from dotenv import load_dotenv
import json
from datetime import datetime
from tabulate import tabulate

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

class DataSecurityAuditor:
    """Class to perform data security audits on the database."""
    
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
        self.tables = []
        self.policies = []
        
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

    def add_issue(self, category, severity, description, recommendation, table=None):
        """Add a security issue to the list."""
        self.issues.append({
            "category": category,
            "severity": severity,
            "description": description,
            "recommendation": recommendation,
            "table": table
        })
    
    def add_pass(self, category, description, table=None):
        """Add a passed check to the list."""
        self.passed.append({
            "category": category,
            "description": description,
            "table": table
        })
        
    def collect_schema_info(self):
        """Collect information about the database schema."""
        print(f"\n{Colors.HEADER}Collecting schema information...{Colors.ENDC}")
        
        # Get tables
        tables = self.run_query("""
            SELECT 
                table_name,
                (SELECT count(*) FROM information_schema.columns 
                 WHERE table_schema = 'public' AND table_name = t.table_name) as column_count,
                obj_description(('"' || table_name || '"')::regclass, 'pg_class') as description
            FROM 
                information_schema.tables t 
            WHERE 
                table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY 
                table_name;
        """)
        
        if not tables:
            print(f"{Colors.WARNING}No tables found in public schema{Colors.ENDC}")
            return
            
        self.tables = tables
        print(f"{Colors.GREEN}Found {len(tables)} tables in the database{Colors.ENDC}")
        
        # Get RLS policies
        policies = self.run_query("""
            SELECT 
                schemaname, 
                tablename, 
                policyname, 
                roles, 
                cmd, 
                qual, 
                with_check
            FROM 
                pg_policies
            WHERE 
                schemaname = 'public'
            ORDER BY 
                tablename, policyname;
        """)
        
        if policies:
            self.policies = policies
            print(f"{Colors.GREEN}Found {len(policies)} row-level security policies{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}No row-level security policies found{Colors.ENDC}")

    def check_pii_columns(self):
        """Check for potentially unprotected PII data."""
        print(f"\n{Colors.HEADER}Checking for unprotected PII data...{Colors.ENDC}")
        
        pii_patterns = {
            'email': [r'email', r'e_mail', r'mail'],
            'name': [r'(^|_)name$', r'full_name', r'first_name', r'last_name', r'user_name'],
            'address': [r'address', r'street', r'city', r'state', r'zip', r'postal'],
            'phone': [r'phone', r'mobile', r'cell', r'telephone'],
            'id_numbers': [r'ssn', r'social_security', r'passport', r'national_id', r'tax_id', r'driver_license'],
            'financial': [r'credit_card', r'card_number', r'cvv', r'payment', r'bank_account'],
            'health': [r'health', r'medical', r'diagnosis', r'prescription', r'patient'],
            'biometric': [r'fingerprint', r'retina', r'facial', r'biometric'],
            'ip': [r'ip_address']
        }
        
        for table in self.tables:
            table_name = table['table_name']
            
            columns = self.run_query("""
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable,
                    column_default
                FROM 
                    information_schema.columns
                WHERE 
                    table_schema = 'public' AND table_name = %s
                ORDER BY 
                    ordinal_position;
            """, (table_name,))
            
            if not columns:
                continue
            
            pii_columns = []
            
            for column in columns:
                column_name = column['column_name'].lower()
                
                # Check if column name matches any PII pattern
                for pii_type, patterns in pii_patterns.items():
                    if any(re.search(pattern, column_name) for pattern in patterns):
                        pii_columns.append({
                            'column_name': column['column_name'],
                            'pii_type': pii_type,
                            'data_type': column['data_type'],
                            'is_nullable': column['is_nullable'],
                            'has_default': column['column_default'] is not None
                        })
                        break
            
            if not pii_columns:
                continue
                
            # Check if table has RLS policies
            has_rls = any(policy['tablename'] == table_name for policy in self.policies)
            
            for pii_column in pii_columns:
                issue_found = False
                
                # Check if table has RLS policies
                if not has_rls:
                    self.add_issue(
                        "PII Protection", 
                        "High", 
                        f"PII data '{pii_column['column_name']}' ({pii_column['pii_type']}) in table '{table_name}' is not protected by row-level security", 
                        "Implement row-level security policies for this table to protect PII data",
                        table_name
                    )
                    print(f"{Colors.FAIL}✗ PII column '{pii_column['column_name']}' in '{table_name}' not protected by RLS{Colors.ENDC}")
                    issue_found = True
                
                # For specific sensitive data types, check for encryption
                if pii_column['pii_type'] in ['id_numbers', 'financial', 'health', 'biometric']:
                    if pii_column['data_type'] in ['character varying', 'text', 'varchar']:
                        # Look for column comments indicating encryption
                        comment = self.run_query("""
                            SELECT pg_description.description
                            FROM pg_description
                            JOIN pg_class ON pg_description.objoid = pg_class.oid
                            JOIN pg_attribute ON pg_attribute.attrelid = pg_class.oid
                            WHERE pg_class.relname = %s
                            AND pg_attribute.attname = %s
                            AND pg_attribute.attnum = pg_description.objsubid
                        """, (table_name, pii_column['column_name']))
                        
                        is_encrypted = False
                        if comment and comment[0]['description']:
                            is_encrypted = bool(re.search(r'encrypt|hash|digest|secure', comment[0]['description'], re.I))
                        
                        if not is_encrypted:
                            self.add_issue(
                                "Data Encryption", 
                                "High", 
                                f"Sensitive {pii_column['pii_type']} data in column '{pii_column['column_name']}' in table '{table_name}' may not be encrypted", 
                                "Consider encrypting this sensitive data or storing only hashed values",
                                table_name
                            )
                            print(f"{Colors.FAIL}✗ Sensitive column '{pii_column['column_name']}' in '{table_name}' not encrypted{Colors.ENDC}")
                            issue_found = True
                
                if not issue_found:
                    protection_type = "row-level security" if has_rls else ""
                    self.add_pass(
                        "PII Protection", 
                        f"PII data '{pii_column['column_name']}' protected by {protection_type}", 
                        table_name
                    )
                    print(f"{Colors.GREEN}✓ PII column '{pii_column['column_name']}' in '{table_name}' is protected{Colors.ENDC}")
    
    def check_password_storage(self):
        """Check for proper password storage."""
        print(f"\n{Colors.HEADER}Checking password storage...{Colors.ENDC}")
        
        password_columns = []
        
        # Find potential password columns
        for table in self.tables:
            table_name = table['table_name']
            
            columns = self.run_query("""
                SELECT 
                    column_name, 
                    data_type, 
                    character_maximum_length
                FROM 
                    information_schema.columns
                WHERE 
                    table_schema = 'public' AND table_name = %s
                    AND (column_name LIKE '%password%' OR column_name LIKE '%hash%')
                ORDER BY 
                    ordinal_position;
            """, (table_name,))
            
            if not columns:
                continue
                
            for column in columns:
                password_columns.append({
                    'table_name': table_name,
                    'column_name': column['column_name'],
                    'data_type': column['data_type'],
                    'max_length': column['character_maximum_length']
                })
        
        if not password_columns:
            print(f"{Colors.BLUE}No password columns found{Colors.ENDC}")
            return
            
        for col in password_columns:
            issues_found = False
            
            # Check if column name suggests it's storing plain passwords
            if 'password' in col['column_name'].lower() and 'hash' not in col['column_name'].lower() and 'hashed' not in col['column_name'].lower():
                self.add_issue(
                    "Password Storage", 
                    "High", 
                    f"Column '{col['column_name']}' in table '{col['table_name']}' may be storing plain passwords", 
                    "Store only hashed passwords, never plain text passwords",
                    col['table_name']
                )
                print(f"{Colors.FAIL}✗ Column '{col['column_name']}' in '{col['table_name']}' may store plain passwords{Colors.ENDC}")
                issues_found = True
            
            # Check if the character length is too small for proper hashing
            if col['data_type'] in ['character varying', 'varchar', 'text'] and col['max_length'] is not None:
                if col['max_length'] < 60:
                    self.add_issue(
                        "Password Storage", 
                        "High", 
                        f"Password column '{col['column_name']}' in table '{col['table_name']}' has length {col['max_length']} which is too short for secure hashing", 
                        "Increase max length to at least 60 characters for bcrypt hashes",
                        col['table_name']
                    )
                    print(f"{Colors.FAIL}✗ Password column '{col['column_name']}' in '{col['table_name']}' is too short for secure hashing{Colors.ENDC}")
                    issues_found = True
            
            # Check for small sample of data to determine if it looks hashed
            if not issues_found:
                sample = self.run_query(f"""
                    SELECT {sql.Identifier(col['column_name']).as_string(self.conn)}
                    FROM {sql.Identifier(col['table_name']).as_string(self.conn)}
                    WHERE {sql.Identifier(col['column_name']).as_string(self.conn)} IS NOT NULL
                    LIMIT 1
                """)
                
                if sample and sample[0][col['column_name']]:
                    value = sample[0][col['column_name']]
                    
                    # Check if it looks like a bcrypt hash
                    if not (len(value) >= 60 and value.startswith('$2')):
                        # Check if it looks like a SHA/MD5 hash (hex characters only)
                        if not re.match(r'^[a-f0-9]{32,}$', value, re.I):
                            self.add_issue(
                                "Password Storage", 
                                "High", 
                                f"Password data in column '{col['column_name']}' in table '{col['table_name']}' may not be properly hashed", 
                                "Use strong hashing algorithms like bcrypt, Argon2, or PBKDF2",
                                col['table_name']
                            )
                            print(f"{Colors.FAIL}✗ Password data in '{col['column_name']}' in '{col['table_name']}' not properly hashed{Colors.ENDC}")
                            issues_found = True
            
            if not issues_found:
                self.add_pass(
                    "Password Storage", 
                    f"Password column '{col['column_name']}' appears to use secure storage", 
                    col['table_name']
                )
                print(f"{Colors.GREEN}✓ Password column '{col['column_name']}' in '{col['table_name']}' uses secure storage{Colors.ENDC}")
    
    def check_row_level_security(self):
        """Check for tables missing row-level security."""
        print(f"\n{Colors.HEADER}Checking row-level security...{Colors.ENDC}")
        
        # Tables that typically contain user-specific data
        sensitive_tables = []
        
        for table in self.tables:
            table_name = table['table_name']
            
            # Check if table name suggests user-specific data
            user_data_patterns = [
                r'user', r'profile', r'account', r'member', r'customer',
                r'order', r'transaction', r'payment', r'subscription',
                r'message', r'comment', r'post', r'address', r'preference',
                r'bookmark', r'favorite', r'history', r'log', r'session',
                r'document', r'product'
            ]
            
            if any(re.search(pattern, table_name, re.I) for pattern in user_data_patterns):
                sensitive_tables.append(table_name)
                continue
                
            # Check if table has user_id or similar columns
            columns = self.run_query("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                  AND (column_name LIKE '%user_id%' OR column_name LIKE '%owner%')
                ORDER BY ordinal_position;
            """, (table_name,))
            
            if columns:
                sensitive_tables.append(table_name)
        
        tables_with_rls = {policy['tablename'] for policy in self.policies}
        
        for table_name in sensitive_tables:
            if table_name not in tables_with_rls:
                self.add_issue(
                    "Row-Level Security", 
                    "High", 
                    f"Sensitive table '{table_name}' does not have row-level security policies", 
                    "Implement RLS policies to restrict data access to authorized users only",
                    table_name
                )
                print(f"{Colors.FAIL}✗ Sensitive table '{table_name}' missing RLS policies{Colors.ENDC}")
            else:
                # Check quality of RLS policies
                policies_for_table = [p for p in self.policies if p['tablename'] == table_name]
                
                has_select_policy = any(p['cmd'] == 'SELECT' or p['cmd'] == 'ALL' for p in policies_for_table)
                has_update_policy = any(p['cmd'] == 'UPDATE' or p['cmd'] == 'ALL' for p in policies_for_table)
                has_delete_policy = any(p['cmd'] == 'DELETE' or p['cmd'] == 'ALL' for p in policies_for_table)
                
                if not (has_select_policy and has_update_policy and has_delete_policy):
                    missing = []
                    if not has_select_policy: missing.append("SELECT")
                    if not has_update_policy: missing.append("UPDATE")
                    if not has_delete_policy: missing.append("DELETE")
                    
                    self.add_issue(
                        "Row-Level Security", 
                        "Medium", 
                        f"Table '{table_name}' is missing RLS policies for: {', '.join(missing)}", 
                        f"Add policies for {', '.join(missing)} operations",
                        table_name
                    )
                    print(f"{Colors.WARNING}! Table '{table_name}' missing RLS policies for: {', '.join(missing)}{Colors.ENDC}")
                else:
                    self.add_pass(
                        "Row-Level Security", 
                        f"Table has comprehensive RLS policies", 
                        table_name
                    )
                    print(f"{Colors.GREEN}✓ Table '{table_name}' has comprehensive RLS policies{Colors.ENDC}")
    
    def check_data_anonymization(self):
        """Check if data anonymization is used for PII in test data."""
        print(f"\n{Colors.HEADER}Checking data anonymization...{Colors.ENDC}")
        
        # Look for test/dev schemas
        schemas = self.run_query("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name LIKE '%test%' OR schema_name LIKE '%dev%'
            ORDER BY schema_name;
        """)
        
        if not schemas:
            print(f"{Colors.BLUE}No test/dev schemas found to check for data anonymization{Colors.ENDC}")
            return
            
        for schema in schemas:
            schema_name = schema['schema_name']
            
            # Get tables in this schema
            tables = self.run_query("""
                SELECT 
                    table_name
                FROM 
                    information_schema.tables
                WHERE 
                    table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY 
                    table_name;
            """, (schema_name,))
            
            if not tables:
                continue
                
            for table in tables:
                table_name = table['table_name']
                
                # Look for PII columns
                pii_columns = self.run_query("""
                    SELECT 
                        column_name
                    FROM 
                        information_schema.columns
                    WHERE 
                        table_schema = %s AND table_name = %s
                        AND (
                            column_name LIKE '%email%' OR
                            column_name LIKE '%name%' OR
                            column_name LIKE '%address%' OR
                            column_name LIKE '%phone%' OR
                            column_name LIKE '%ssn%' OR
                            column_name LIKE '%passport%' OR
                            column_name LIKE '%credit%' OR
                            column_name LIKE '%card%'
                        )
                    ORDER BY 
                        ordinal_position;
                """, (schema_name, table_name))
                
                if not pii_columns:
                    continue
                    
                # Check if there's any data in this table
                count = self.run_query(f"""
                    SELECT COUNT(*) as count
                    FROM {sql.Identifier(schema_name).as_string(self.conn)}.{sql.Identifier(table_name).as_string(self.conn)}
                    LIMIT 1
                """)
                
                if count and count[0]['count'] > 0:
                    for col in pii_columns:
                        column_name = col['column_name']
                        
                        # Sample some data to check if it looks real or anonymized
                        sample = self.run_query(f"""
                            SELECT {sql.Identifier(column_name).as_string(self.conn)}
                            FROM {sql.Identifier(schema_name).as_string(self.conn)}.{sql.Identifier(table_name).as_string(self.conn)}
                            WHERE {sql.Identifier(column_name).as_string(self.conn)} IS NOT NULL
                            LIMIT 3
                        """)
                        
                        if sample:
                            values = [s[column_name] for s in sample if s[column_name]]
                            
                            if values:
                                # Check if the data looks anonymized
                                looks_anonymized = all(
                                    re.search(r'anon|redacted|masked|xxx|test|dummy|fake', str(v), re.I) or
                                    re.match(r'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$', str(v)) # UUID pattern
                                    for v in values
                                )
                                
                                if not looks_anonymized:
                                    # For email addresses, check for common test domains
                                    if 'email' in column_name.lower():
                                        looks_anonymized = all(
                                            re.search(r'@(example|test|fake|dummy)\.(com|org|net|io)$', str(v), re.I)
                                            for v in values
                                        )
                                
                                if not looks_anonymized:
                                    self.add_issue(
                                        "Data Anonymization", 
                                        "Medium", 
                                        f"PII data in column '{column_name}' in test table '{schema_name}.{table_name}' may not be anonymized", 
                                        "Use data masking or synthetic data for test/development environments",
                                        f"{schema_name}.{table_name}"
                                    )
                                    print(f"{Colors.WARNING}! PII in '{column_name}' in test table '{schema_name}.{table_name}' not anonymized{Colors.ENDC}")
                                else:
                                    self.add_pass(
                                        "Data Anonymization", 
                                        f"PII data in '{column_name}' appears to be anonymized in test data", 
                                        f"{schema_name}.{table_name}"
                                    )
    
    def check_sensitive_data_audit_logging(self):
        """Check if sensitive data access is tracked with audit logging."""
        print(f"\n{Colors.HEADER}Checking audit logging for sensitive data...{Colors.ENDC}")
        
        # Look for audit log tables
        audit_tables = []
        for table in self.tables:
            table_name = table['table_name']
            if re.search(r'audit|log|history|change|event', table_name, re.I):
                audit_tables.append(table_name)
        
        if not audit_tables:
            self.add_issue(
                "Audit Logging", 
                "Medium", 
                "No audit log tables found for tracking sensitive data access", 
                "Implement audit logging to track access to sensitive data",
                None
            )
            print(f"{Colors.WARNING}! No audit log tables found{Colors.ENDC}")
            return
            
        # Check for sensitive tables that should be audited
        for table in self.tables:
            table_name = table['table_name']
            
            # Skip audit tables themselves
            if table_name in audit_tables:
                continue
                
            # Check if table likely contains sensitive data
            sensitive_patterns = [
                r'user', r'profile', r'personal', r'account', r'payment',
                r'financial', r'medical', r'health', r'patient', r'secret'
            ]
            
            if any(re.search(pattern, table_name, re.I) for pattern in sensitive_patterns):
                # Check if table is referenced in any audit log table
                audited = False
                
                for audit_table in audit_tables:
                    # Look for columns that might reference this table
                    columns = self.run_query("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = %s
                          AND (
                            column_name LIKE %s OR 
                            column_name LIKE 'table_name' OR 
                            column_name LIKE 'entity_type'
                          )
                        ORDER BY ordinal_position;
                    """, (audit_table, f"%{table_name}%"))
                    
                    if columns:
                        # Check for sample data that references this table
                        for col in columns:
                            sample = self.run_query(f"""
                                SELECT 1
                                FROM {sql.Identifier(audit_table).as_string(self.conn)}
                                WHERE {sql.Identifier(col['column_name']).as_string(self.conn)} = %s
                                   OR {sql.Identifier(col['column_name']).as_string(self.conn)} LIKE %s
                                LIMIT 1
                            """, (table_name, f"%{table_name}%"))
                            
                            if sample:
                                audited = True
                                break
                    
                    if audited:
                        break
                
                if not audited:
                    self.add_issue(
                        "Audit Logging", 
                        "Medium", 
                        f"Sensitive table '{table_name}' may not be covered by audit logging", 
                        "Implement audit logging for this table to track sensitive data access",
                        table_name
                    )
                    print(f"{Colors.WARNING}! Sensitive table '{table_name}' not covered by audit logging{Colors.ENDC}")
                else:
                    self.add_pass(
                        "Audit Logging", 
                        f"Table appears to be covered by audit logging", 
                        table_name
                    )
                    print(f"{Colors.GREEN}✓ Table '{table_name}' is covered by audit logging{Colors.ENDC}")
    
    def run_all_checks(self):
        """Run all data security checks."""
        if not self.connect():
            return False
            
        print(f"\n{Colors.BOLD}{Colors.HEADER}Running Database Data Security Audit{Colors.ENDC}")
        print(f"{Colors.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"{Colors.CYAN}Database: {self.dbname} on {self.host}:{self.port}{Colors.ENDC}")
        
        try:
            self.collect_schema_info()
            
            if not self.tables:
                print(f"{Colors.FAIL}No tables found to audit{Colors.ENDC}")
                return False
                
            self.check_pii_columns()
            self.check_password_storage()
            self.check_row_level_security()
            self.check_data_anonymization()
            self.check_sensitive_data_audit_logging()
            
            return True
        except Exception as e:
            print(f"{Colors.FAIL}Error during audit: {str(e)}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.disconnect()
    
    def generate_report(self, output_file=None):
        """Generate a data security audit report."""
        total_issues = len(self.issues)
        total_passed = len(self.passed)
        
        high_issues = sum(1 for issue in self.issues if issue['severity'] == 'High')
        medium_issues = sum(1 for issue in self.issues if issue['severity'] == 'Medium')
        low_issues = sum(1 for issue in self.issues if issue['severity'] == 'Low')
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}Database Data Security Audit Results{Colors.ENDC}")
        print(f"{Colors.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"Total tables audited: {Colors.BLUE}{len(self.tables)}{Colors.ENDC}")
        print(f"Total checks passed: {Colors.GREEN}{total_passed}{Colors.ENDC}")
        print(f"Total issues found: {Colors.WARNING if total_issues > 0 else Colors.GREEN}{total_issues}{Colors.ENDC}")
        print(f"  High severity: {Colors.FAIL if high_issues > 0 else Colors.GREEN}{high_issues}{Colors.ENDC}")
        print(f"  Medium severity: {Colors.WARNING if medium_issues > 0 else Colors.GREEN}{medium_issues}{Colors.ENDC}")
        print(f"  Low severity: {Colors.CYAN if low_issues > 0 else Colors.GREEN}{low_issues}{Colors.ENDC}")
        
        # Create summary by category
        issues_by_category = {}
        for issue in self.issues:
            category = issue['category']
            if category not in issues_by_category:
                issues_by_category[category] = {'High': 0, 'Medium': 0, 'Low': 0, 'Total': 0}
            
            issues_by_category[category][issue['severity']] += 1
            issues_by_category[category]['Total'] += 1
        
        # Print summary table
        if issues_by_category:
            print(f"\n{Colors.BOLD}Issues by Category:{Colors.ENDC}")
            table_data = []
            for category, counts in issues_by_category.items():
                table_data.append([
                    category, 
                    counts['High'],
                    counts['Medium'],
                    counts['Low'],
                    counts['Total']
                ])
            
            headers = ["Category", "High", "Medium", "Low", "Total"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Print issues by severity
        if high_issues > 0:
            print(f"\n{Colors.BOLD}{Colors.FAIL}High Severity Issues:{Colors.ENDC}")
            for issue in self.issues:
                if issue['severity'] == 'High':
                    table = f"[{issue['table']}] " if issue['table'] else ""
                    print(f"{Colors.FAIL}• {table}{issue['category']}: {issue['description']}{Colors.ENDC}")
                    print(f"  {Colors.CYAN}Recommendation: {issue['recommendation']}{Colors.ENDC}")
        
        if medium_issues > 0:
            print(f"\n{Colors.BOLD}{Colors.WARNING}Medium Severity Issues:{Colors.ENDC}")
            for issue in self.issues:
                if issue['severity'] == 'Medium':
                    table = f"[{issue['table']}] " if issue['table'] else ""
                    print(f"{Colors.WARNING}• {table}{issue['category']}: {issue['description']}{Colors.ENDC}")
                    print(f"  {Colors.CYAN}Recommendation: {issue['recommendation']}{Colors.ENDC}")
        
        if low_issues > 0:
            print(f"\n{Colors.BOLD}{Colors.CYAN}Low Severity Issues:{Colors.ENDC}")
            for issue in self.issues:
                if issue['severity'] == 'Low':
                    table = f"[{issue['table']}] " if issue['table'] else ""
                    print(f"{Colors.CYAN}• {table}{issue['category']}: {issue['description']}{Colors.ENDC}")
                    print(f"  Recommendation: {issue['recommendation']}")
        
        if output_file:
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "host": self.host,
                    "port": self.port,
                    "name": self.dbname
                },
                "summary": {
                    "tables_audited": len(self.tables),
                    "passed_checks": total_passed,
                    "total_issues": total_issues,
                    "high_issues": high_issues,
                    "medium_issues": medium_issues,
                    "low_issues": low_issues
                },
                "tables": [table['table_name'] for table in self.tables],
                "issues_by_category": issues_by_category,
                "passed": self.passed,
                "issues": self.issues
            }
            
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
                
            print(f"\n{Colors.GREEN}Report saved to {output_file}{Colors.ENDC}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='PostgreSQL Data Security Audit Tool')
    parser.add_argument('--host', default=os.getenv('POSTGRES_SERVER', 'localhost'), help='Database host')
    parser.add_argument('--port', default=os.getenv('POSTGRES_PORT', '5432'), help='Database port')
    parser.add_argument('--dbname', default=os.getenv('POSTGRES_DB', 'postgres'), help='Database name')
    parser.add_argument('--user', default=os.getenv('POSTGRES_USER', 'postgres'), help='Database user')
    parser.add_argument('--password', default=os.getenv('POSTGRES_PASSWORD', ''), help='Database password')
    parser.add_argument('--output', help='Output file for JSON report')
    
    args = parser.parse_args()
    
    auditor = DataSecurityAuditor(
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
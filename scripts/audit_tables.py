#!/usr/bin/env python3
"""
Database schema audit script for the MeatWise API.

This script audits the database schema looking for common issues
like missing indexes, missing constraints, poor column choices, etc.
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

class SchemaAuditor:
    """Class to perform schema audits on the database."""
    
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
        self.indexes = []
        self.constraints = []
        
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
        
        # Get indexes
        indexes = self.run_query("""
            SELECT 
                t.relname as table_name,
                i.relname as index_name,
                a.attname as column_name,
                ix.indisunique as is_unique,
                ix.indisprimary as is_primary,
                am.amname as index_type
            FROM 
                pg_index ix
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                JOIN pg_am am ON am.oid = i.relam
            WHERE 
                t.relkind = 'r' AND 
                t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            ORDER BY 
                t.relname, i.relname, a.attnum;
        """)
        
        if indexes:
            self.indexes = indexes
            print(f"{Colors.GREEN}Found {len(indexes)} indexes in the database{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}No indexes found{Colors.ENDC}")
        
        # Get constraints
        constraints = self.run_query("""
            SELECT 
                tc.table_name,
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name,
                ccu.table_name as foreign_table_name,
                ccu.column_name as foreign_column_name
            FROM 
                information_schema.table_constraints tc
                LEFT JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                LEFT JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
            WHERE 
                tc.table_schema = 'public'
            ORDER BY 
                tc.table_name, tc.constraint_name;
        """)
        
        if constraints:
            self.constraints = constraints
            print(f"{Colors.GREEN}Found {len(constraints)} constraints in the database{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}No constraints found{Colors.ENDC}")
    
    def check_primary_keys(self):
        """Check if all tables have primary keys."""
        print(f"\n{Colors.HEADER}Checking primary keys...{Colors.ENDC}")
        
        tables_with_pk = set()
        for constraint in self.constraints:
            if constraint['constraint_type'] == 'PRIMARY KEY':
                tables_with_pk.add(constraint['table_name'])
        
        for table in self.tables:
            table_name = table['table_name']
            if table_name in tables_with_pk:
                self.add_pass(
                    "Primary Keys", 
                    f"Table has a primary key", 
                    table_name
                )
                print(f"{Colors.GREEN}✓ Table '{table_name}' has a primary key{Colors.ENDC}")
            else:
                self.add_issue(
                    "Primary Keys", 
                    "High", 
                    f"Table '{table_name}' does not have a primary key", 
                    "Add a primary key to uniquely identify each row",
                    table_name
                )
                print(f"{Colors.FAIL}✗ Table '{table_name}' does not have a primary key{Colors.ENDC}")
    
    def check_foreign_keys(self):
        """Check for orphaned tables with no relationships."""
        print(f"\n{Colors.HEADER}Checking foreign keys...{Colors.ENDC}")
        
        tables_with_fk = set()
        tables_referenced_by_fk = set()
        
        for constraint in self.constraints:
            if constraint['constraint_type'] == 'FOREIGN KEY':
                tables_with_fk.add(constraint['table_name'])
                if constraint['foreign_table_name']:
                    tables_referenced_by_fk.add(constraint['foreign_table_name'])
        
        for table in self.tables:
            table_name = table['table_name']
            
            # Check tables with no relationships at all
            if (table_name not in tables_with_fk and 
                table_name not in tables_referenced_by_fk and
                table_name not in ('migrations', 'schema_migrations')):  # Exclude migration tables
                
                self.add_issue(
                    "Foreign Keys", 
                    "Medium", 
                    f"Table '{table_name}' has no relationships with other tables", 
                    "Consider if this table should have relationships with other tables",
                    table_name
                )
                print(f"{Colors.WARNING}! Table '{table_name}' is isolated with no relationships{Colors.ENDC}")
            else:
                self.add_pass(
                    "Foreign Keys", 
                    f"Table is properly connected in the schema", 
                    table_name
                )
    
    def check_indexes(self):
        """Check for potential missing indexes."""
        print(f"\n{Colors.HEADER}Checking indexes...{Colors.ENDC}")
        
        # Look for foreign keys without indexes
        indexed_columns = {}
        for index in self.indexes:
            table_name = index['table_name']
            column_name = index['column_name']
            
            if table_name not in indexed_columns:
                indexed_columns[table_name] = set()
            
            indexed_columns[table_name].add(column_name)
        
        for constraint in self.constraints:
            if constraint['constraint_type'] == 'FOREIGN KEY':
                table_name = constraint['table_name']
                column_name = constraint['column_name']
                
                if (table_name not in indexed_columns or 
                    column_name not in indexed_columns[table_name]):
                    
                    self.add_issue(
                        "Indexes", 
                        "Medium", 
                        f"Foreign key column '{column_name}' in table '{table_name}' is not indexed", 
                        f"Create an index on '{column_name}' to improve query performance",
                        table_name
                    )
                    print(f"{Colors.WARNING}! Foreign key '{column_name}' in '{table_name}' not indexed{Colors.ENDC}")
        
        # Check for tables with no indexes at all
        tables_with_indexes = {index['table_name'] for index in self.indexes}
        
        for table in self.tables:
            table_name = table['table_name']
            if table_name not in tables_with_indexes and table['column_count'] > 3:
                self.add_issue(
                    "Indexes", 
                    "Medium", 
                    f"Table '{table_name}' has no indexes but has {table['column_count']} columns", 
                    "Consider adding appropriate indexes for query optimization",
                    table_name
                )
                print(f"{Colors.WARNING}! Table '{table_name}' has no indexes{Colors.ENDC}")
    
    def check_timestamps(self):
        """Check for created_at and updated_at timestamp columns."""
        print(f"\n{Colors.HEADER}Checking timestamp columns...{Colors.ENDC}")
        
        for table in self.tables:
            table_name = table['table_name']
            
            columns = self.run_query("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            if not columns:
                continue
                
            column_names = {col['column_name'] for col in columns}
            has_created_at = 'created_at' in column_names
            has_updated_at = 'updated_at' in column_names
            
            if not has_created_at and table_name not in ('migrations', 'schema_migrations'):
                self.add_issue(
                    "Timestamps", 
                    "Low", 
                    f"Table '{table_name}' is missing a 'created_at' timestamp column", 
                    "Add a 'created_at' column with DEFAULT NOW() for auditing purposes",
                    table_name
                )
                print(f"{Colors.WARNING}! Table '{table_name}' missing 'created_at' column{Colors.ENDC}")
            
            if not has_updated_at and table_name not in ('migrations', 'schema_migrations'):
                self.add_issue(
                    "Timestamps", 
                    "Low", 
                    f"Table '{table_name}' is missing an 'updated_at' timestamp column", 
                    "Add an 'updated_at' column with a trigger to update on row changes",
                    table_name
                )
                print(f"{Colors.WARNING}! Table '{table_name}' missing 'updated_at' column{Colors.ENDC}")
            
            if has_created_at and has_updated_at:
                self.add_pass(
                    "Timestamps", 
                    f"Table has both created_at and updated_at columns", 
                    table_name
                )
    
    def check_constraints(self):
        """Check for tables with no constraints."""
        print(f"\n{Colors.HEADER}Checking constraints...{Colors.ENDC}")
        
        tables_with_constraints = {constraint['table_name'] for constraint in self.constraints}
        
        for table in self.tables:
            table_name = table['table_name']
            if table_name not in tables_with_constraints:
                self.add_issue(
                    "Constraints", 
                    "Medium", 
                    f"Table '{table_name}' has no constraints", 
                    "Add appropriate constraints (primary key, foreign keys, unique) for data integrity",
                    table_name
                )
                print(f"{Colors.WARNING}! Table '{table_name}' has no constraints{Colors.ENDC}")
            else:
                constraints_for_table = [c for c in self.constraints if c['table_name'] == table_name]
                self.add_pass(
                    "Constraints", 
                    f"Table has {len(constraints_for_table)} constraints", 
                    table_name
                )
    
    def check_column_nullability(self):
        """Check columns that shouldn't be nullable."""
        print(f"\n{Colors.HEADER}Checking column nullability...{Colors.ENDC}")
        
        for table in self.tables:
            table_name = table['table_name']
            
            columns = self.run_query("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            if not columns:
                continue
            
            for column in columns:
                column_name = column['column_name']
                is_nullable = column['is_nullable'] == 'YES'
                
                # Columns that typically shouldn't be nullable
                critical_columns = [
                    'name', 'email', 'user_id', 'product_id', 'order_id', 'price', 
                    'quantity', 'status', 'type', 'category'
                ]
                
                if is_nullable and any(
                    column_name == name or column_name.endswith('_' + name) 
                    for name in critical_columns
                ):
                    self.add_issue(
                        "Nullability", 
                        "Low", 
                        f"Column '{column_name}' in table '{table_name}' is nullable but should probably be required", 
                        f"Consider making '{column_name}' NOT NULL with a default value if appropriate",
                        table_name
                    )
                    print(f"{Colors.WARNING}! Column '{column_name}' in '{table_name}' should not be nullable{Colors.ENDC}")
    
    def check_data_types(self):
        """Check for appropriate data types."""
        print(f"\n{Colors.HEADER}Checking data types...{Colors.ENDC}")
        
        for table in self.tables:
            table_name = table['table_name']
            
            columns = self.run_query("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            if not columns:
                continue
            
            for column in columns:
                column_name = column['column_name']
                data_type = column['data_type']
                max_length = column['character_maximum_length']
                
                # Check text columns that could be too large
                if data_type == 'text' and (
                    column_name.endswith('_code') or 
                    column_name in ('code', 'sku', 'status', 'type', 'category')
                ):
                    self.add_issue(
                        "Data Types", 
                        "Low", 
                        f"Column '{column_name}' in table '{table_name}' uses TEXT type but might be better as VARCHAR", 
                        f"Consider using VARCHAR with appropriate length for '{column_name}'",
                        table_name
                    )
                    print(f"{Colors.WARNING}! Column '{column_name}' in '{table_name}' should use VARCHAR{Colors.ENDC}")
                
                # Check character columns that are too small
                if data_type == 'character varying' and max_length is not None:
                    if column_name == 'email' and max_length < 255:
                        self.add_issue(
                            "Data Types", 
                            "Low", 
                            f"Email column '{column_name}' in table '{table_name}' has max length {max_length} which may be too short", 
                            f"Increase max length to at least 255 characters",
                            table_name
                        )
                        print(f"{Colors.WARNING}! Email column '{column_name}' in '{table_name}' too short{Colors.ENDC}")
                    elif (column_name == 'password' or column_name == 'hashed_password') and max_length < 60:
                        self.add_issue(
                            "Data Types", 
                            "Medium", 
                            f"Password column '{column_name}' in table '{table_name}' has max length {max_length} which is too short for secure hashing", 
                            f"Increase max length to at least 60 characters for bcrypt hashes",
                            table_name
                        )
                        print(f"{Colors.WARNING}! Password column '{column_name}' in '{table_name}' too short{Colors.ENDC}")
    
    def run_all_checks(self):
        """Run all schema checks."""
        if not self.connect():
            return False
            
        print(f"\n{Colors.BOLD}{Colors.HEADER}Running Database Schema Audit{Colors.ENDC}")
        print(f"{Colors.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"{Colors.CYAN}Database: {self.dbname} on {self.host}:{self.port}{Colors.ENDC}")
        
        try:
            self.collect_schema_info()
            
            if not self.tables:
                print(f"{Colors.FAIL}No tables found to audit{Colors.ENDC}")
                return False
                
            self.check_primary_keys()
            self.check_foreign_keys()
            self.check_indexes()
            self.check_timestamps()
            self.check_constraints()
            self.check_column_nullability()
            self.check_data_types()
            
            return True
        except Exception as e:
            print(f"{Colors.FAIL}Error during audit: {str(e)}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.disconnect()
    
    def generate_report(self, output_file=None):
        """Generate a schema audit report."""
        total_issues = len(self.issues)
        total_passed = len(self.passed)
        
        high_issues = sum(1 for issue in self.issues if issue['severity'] == 'High')
        medium_issues = sum(1 for issue in self.issues if issue['severity'] == 'Medium')
        low_issues = sum(1 for issue in self.issues if issue['severity'] == 'Low')
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}Database Schema Audit Results{Colors.ENDC}")
        print(f"{Colors.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"Total tables audited: {Colors.BLUE}{len(self.tables)}{Colors.ENDC}")
        print(f"Total checks passed: {Colors.GREEN}{total_passed}{Colors.ENDC}")
        print(f"Total issues found: {Colors.WARNING if total_issues > 0 else Colors.GREEN}{total_issues}{Colors.ENDC}")
        print(f"  High severity: {Colors.FAIL if high_issues > 0 else Colors.GREEN}{high_issues}{Colors.ENDC}")
        print(f"  Medium severity: {Colors.WARNING if medium_issues > 0 else Colors.GREEN}{medium_issues}{Colors.ENDC}")
        print(f"  Low severity: {Colors.CYAN if low_issues > 0 else Colors.GREEN}{low_issues}{Colors.ENDC}")
        
        # Create summary by table
        issues_by_table = {}
        for issue in self.issues:
            table = issue['table'] or 'General'
            if table not in issues_by_table:
                issues_by_table[table] = {'High': 0, 'Medium': 0, 'Low': 0, 'Total': 0}
            
            issues_by_table[table][issue['severity']] += 1
            issues_by_table[table]['Total'] += 1
        
        # Print summary table
        if issues_by_table:
            print(f"\n{Colors.BOLD}Issues by Table:{Colors.ENDC}")
            table_data = []
            for table, counts in issues_by_table.items():
                table_data.append([
                    table, 
                    counts['High'],
                    counts['Medium'],
                    counts['Low'],
                    counts['Total']
                ])
            
            headers = ["Table", "High", "Medium", "Low", "Total"]
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
                "issues_by_table": issues_by_table,
                "passed": self.passed,
                "issues": self.issues
            }
            
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
                
            print(f"\n{Colors.GREEN}Report saved to {output_file}{Colors.ENDC}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='PostgreSQL Schema Audit Tool')
    parser.add_argument('--host', default=os.getenv('POSTGRES_SERVER', 'localhost'), help='Database host')
    parser.add_argument('--port', default=os.getenv('POSTGRES_PORT', '5432'), help='Database port')
    parser.add_argument('--dbname', default=os.getenv('POSTGRES_DB', 'postgres'), help='Database name')
    parser.add_argument('--user', default=os.getenv('POSTGRES_USER', 'postgres'), help='Database user')
    parser.add_argument('--password', default=os.getenv('POSTGRES_PASSWORD', ''), help='Database password')
    parser.add_argument('--output', help='Output file for JSON report')
    
    args = parser.parse_args()
    
    auditor = SchemaAuditor(
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
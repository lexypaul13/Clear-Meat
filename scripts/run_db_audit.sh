#!/bin/bash
# Database Audit Runner Script for MeatWise API
# This script runs both schema and data security audits

set -e

# Create reports directory if it doesn't exist
REPORTS_DIR="./audit_reports"
mkdir -p $REPORTS_DIR

# Get current timestamp for report filenames
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SCHEMA_REPORT="${REPORTS_DIR}/schema_audit_${TIMESTAMP}.json"
DATA_REPORT="${REPORTS_DIR}/data_security_audit_${TIMESTAMP}.json"
COMBINED_REPORT="${REPORTS_DIR}/full_audit_${TIMESTAMP}.html"

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    source .env
else
    echo "Warning: .env file not found. Using default database connection settings."
fi

# Set default database connection parameters
DB_HOST=${POSTGRES_SERVER:-"localhost"}
DB_PORT=${POSTGRES_PORT:-5432}
DB_NAME=${POSTGRES_DB:-"postgres"}
DB_USER=${POSTGRES_USER:-"postgres"}
DB_PASS=${POSTGRES_PASSWORD:-""}

# Print connection details (without password)
echo "Database connection: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Check if required Python packages are installed
echo "Checking dependencies..."
pip install -q psycopg2-binary python-dotenv tabulate jinja2

# Run schema audit
echo -e "\n==============================================" 
echo "RUNNING DATABASE SCHEMA AUDIT"
echo -e "==============================================\n" 
python scripts/audit_tables.py \
    --host "$DB_HOST" \
    --port "$DB_PORT" \
    --dbname "$DB_NAME" \
    --user "$DB_USER" \
    --password "$DB_PASS" \
    --output "$SCHEMA_REPORT"

# Store schema audit exit code
SCHEMA_RESULT=$?

# Run data security audit
echo -e "\n==============================================" 
echo "RUNNING DATABASE DATA SECURITY AUDIT"
echo -e "==============================================\n" 
python scripts/data_security_audit.py \
    --host "$DB_HOST" \
    --port "$DB_PORT" \
    --dbname "$DB_NAME" \
    --user "$DB_USER" \
    --password "$DB_PASS" \
    --output "$DATA_REPORT"

# Store data security audit exit code
DATA_RESULT=$?

# Generate combined HTML report
echo -e "\n==============================================" 
echo "GENERATING COMBINED HTML REPORT"
echo -e "==============================================\n" 

# Create HTML report using Python
cat > scripts/generate_report.py << 'EOF'
#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime
import jinja2

def generate_html_report(schema_report_file, data_report_file, output_file):
    # Load the JSON reports
    try:
        with open(schema_report_file, 'r') as f:
            schema_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading schema report: {e}")
        schema_data = {"error": str(e)}
    
    try:
        with open(data_report_file, 'r') as f:
            data_security_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading data security report: {e}")
        data_security_data = {"error": str(e)}
    
    # Prepare the template data
    template_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "schema_data": schema_data,
        "data_security_data": data_security_data,
        "schema_issues_count": sum(len(schema_data.get("issues", [])) for severity in ["High", "Medium", "Low"]),
        "data_issues_count": sum(len(data_security_data.get("issues", [])) for severity in ["High", "Medium", "Low"]),
    }
    
    # Create HTML template
    template_str = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MeatWise API Database Audit Report</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            h1, h2, h3, h4 {
                color: #2c3e50;
            }
            .report-header {
                background-color: #34495e;
                color: white;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .section {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
            }
            .summary-box {
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                margin-bottom: 20px;
            }
            .summary-item {
                flex: 1;
                min-width: 200px;
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .severity-high {
                color: #e74c3c;
                font-weight: bold;
            }
            .severity-medium {
                color: #f39c12;
                font-weight: bold;
            }
            .severity-low {
                color: #3498db;
                font-weight: bold;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }
            th, td {
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #34495e;
                color: white;
            }
            tr:nth-child(even) {
                background-color: #f2f2f2;
            }
            .issue-card {
                background-color: white;
                border-left: 5px solid #ddd;
                margin-bottom: 15px;
                padding: 15px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .high-issue {
                border-left-color: #e74c3c;
            }
            .medium-issue {
                border-left-color: #f39c12;
            }
            .low-issue {
                border-left-color: #3498db;
            }
            .recommendation {
                background-color: #eef8ff;
                padding: 10px;
                margin-top: 10px;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="report-header">
            <h1>MeatWise API Database Audit Report</h1>
            <p>Generated on: {{ timestamp }}</p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <div class="summary-box">
                <div class="summary-item">
                    <h3>Schema Audit</h3>
                    <p>Tables Audited: <strong>{{ schema_data.summary.tables_audited }}</strong></p>
                    <p>Total Issues: <strong>{{ schema_data.summary.total_issues }}</strong></p>
                    <p>High Severity: <span class="severity-high">{{ schema_data.summary.high_issues }}</span></p>
                    <p>Medium Severity: <span class="severity-medium">{{ schema_data.summary.medium_issues }}</span></p>
                    <p>Low Severity: <span class="severity-low">{{ schema_data.summary.low_issues }}</span></p>
                </div>
                <div class="summary-item">
                    <h3>Data Security Audit</h3>
                    <p>Tables Audited: <strong>{{ data_security_data.summary.tables_audited }}</strong></p>
                    <p>Total Issues: <strong>{{ data_security_data.summary.total_issues }}</strong></p>
                    <p>High Severity: <span class="severity-high">{{ data_security_data.summary.high_issues }}</span></p>
                    <p>Medium Severity: <span class="severity-medium">{{ data_security_data.summary.medium_issues }}</span></p>
                    <p>Low Severity: <span class="severity-low">{{ data_security_data.summary.low_issues }}</span></p>
                </div>
            </div>
        </div>

        <!-- Schema Audit Section -->
        <div class="section">
            <h2>Schema Audit Results</h2>
            
            {% if schema_data.summary.total_issues > 0 %}
                <h3>Issues by Table</h3>
                <table>
                    <tr>
                        <th>Table</th>
                        <th>High</th>
                        <th>Medium</th>
                        <th>Low</th>
                        <th>Total</th>
                    </tr>
                    {% for table, counts in schema_data.issues_by_table.items() %}
                    <tr>
                        <td>{{ table }}</td>
                        <td class="severity-high">{{ counts.High }}</td>
                        <td class="severity-medium">{{ counts.Medium }}</td>
                        <td class="severity-low">{{ counts.Low }}</td>
                        <td><strong>{{ counts.Total }}</strong></td>
                    </tr>
                    {% endfor %}
                </table>
                
                {% if schema_data.summary.high_issues > 0 %}
                <h3>High Severity Issues</h3>
                {% for issue in schema_data.issues %}
                    {% if issue.severity == "High" %}
                    <div class="issue-card high-issue">
                        <h4>{{ issue.category }}</h4>
                        <p>{{ issue.description }}</p>
                        <p><strong>Table:</strong> {{ issue.table }}</p>
                        <div class="recommendation">
                            <p><strong>Recommendation:</strong> {{ issue.recommendation }}</p>
                        </div>
                    </div>
                    {% endif %}
                {% endfor %}
                {% endif %}
                
                {% if schema_data.summary.medium_issues > 0 %}
                <h3>Medium Severity Issues</h3>
                {% for issue in schema_data.issues %}
                    {% if issue.severity == "Medium" %}
                    <div class="issue-card medium-issue">
                        <h4>{{ issue.category }}</h4>
                        <p>{{ issue.description }}</p>
                        <p><strong>Table:</strong> {{ issue.table }}</p>
                        <div class="recommendation">
                            <p><strong>Recommendation:</strong> {{ issue.recommendation }}</p>
                        </div>
                    </div>
                    {% endif %}
                {% endfor %}
                {% endif %}
                
                {% if schema_data.summary.low_issues > 0 %}
                <h3>Low Severity Issues</h3>
                {% for issue in schema_data.issues %}
                    {% if issue.severity == "Low" %}
                    <div class="issue-card low-issue">
                        <h4>{{ issue.category }}</h4>
                        <p>{{ issue.description }}</p>
                        <p><strong>Table:</strong> {{ issue.table }}</p>
                        <div class="recommendation">
                            <p><strong>Recommendation:</strong> {{ issue.recommendation }}</p>
                        </div>
                    </div>
                    {% endif %}
                {% endfor %}
                {% endif %}
            {% else %}
                <p>No schema issues found. Great job!</p>
            {% endif %}
        </div>

        <!-- Data Security Audit Section -->
        <div class="section">
            <h2>Data Security Audit Results</h2>
            
            {% if data_security_data.summary.total_issues > 0 %}
                <h3>Issues by Category</h3>
                <table>
                    <tr>
                        <th>Category</th>
                        <th>High</th>
                        <th>Medium</th>
                        <th>Low</th>
                        <th>Total</th>
                    </tr>
                    {% for category, counts in data_security_data.issues_by_category.items() %}
                    <tr>
                        <td>{{ category }}</td>
                        <td class="severity-high">{{ counts.High }}</td>
                        <td class="severity-medium">{{ counts.Medium }}</td>
                        <td class="severity-low">{{ counts.Low }}</td>
                        <td><strong>{{ counts.Total }}</strong></td>
                    </tr>
                    {% endfor %}
                </table>
                
                {% if data_security_data.summary.high_issues > 0 %}
                <h3>High Severity Issues</h3>
                {% for issue in data_security_data.issues %}
                    {% if issue.severity == "High" %}
                    <div class="issue-card high-issue">
                        <h4>{{ issue.category }}</h4>
                        <p>{{ issue.description }}</p>
                        <p><strong>Table:</strong> {{ issue.table }}</p>
                        <div class="recommendation">
                            <p><strong>Recommendation:</strong> {{ issue.recommendation }}</p>
                        </div>
                    </div>
                    {% endif %}
                {% endfor %}
                {% endif %}
                
                {% if data_security_data.summary.medium_issues > 0 %}
                <h3>Medium Severity Issues</h3>
                {% for issue in data_security_data.issues %}
                    {% if issue.severity == "Medium" %}
                    <div class="issue-card medium-issue">
                        <h4>{{ issue.category }}</h4>
                        <p>{{ issue.description }}</p>
                        <p><strong>Table:</strong> {{ issue.table }}</p>
                        <div class="recommendation">
                            <p><strong>Recommendation:</strong> {{ issue.recommendation }}</p>
                        </div>
                    </div>
                    {% endif %}
                {% endfor %}
                {% endif %}
                
                {% if data_security_data.summary.low_issues > 0 %}
                <h3>Low Severity Issues</h3>
                {% for issue in data_security_data.issues %}
                    {% if issue.severity == "Low" %}
                    <div class="issue-card low-issue">
                        <h4>{{ issue.category }}</h4>
                        <p>{{ issue.description }}</p>
                        <p><strong>Table:</strong> {{ issue.table }}</p>
                        <div class="recommendation">
                            <p><strong>Recommendation:</strong> {{ issue.recommendation }}</p>
                        </div>
                    </div>
                    {% endif %}
                {% endfor %}
                {% endif %}
            {% else %}
                <p>No data security issues found. Great job!</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>Recommendations Summary</h2>
            <p>Based on the audit results, here are the top recommendations:</p>
            <ol>
                {% set critical_issues = [] %}
                {% for issue in schema_data.issues + data_security_data.issues %}
                    {% if issue.severity == "High" and issue not in critical_issues %}
                        {% do critical_issues.append(issue) %}
                        <li><strong>{{ issue.category }}:</strong> {{ issue.recommendation }}</li>
                    {% endif %}
                {% endfor %}
                
                {% if critical_issues|length < 5 %}
                    {% for issue in schema_data.issues + data_security_data.issues %}
                        {% if issue.severity == "Medium" and issue not in critical_issues and critical_issues|length < 5 %}
                            {% do critical_issues.append(issue) %}
                            <li><strong>{{ issue.category }}:</strong> {{ issue.recommendation }}</li>
                        {% endif %}
                    {% endfor %}
                {% endif %}
                
                {% if critical_issues|length == 0 %}
                    <li>No critical issues found. Continue maintaining good database practices.</li>
                {% endif %}
            </ol>
        </div>

        <footer>
            <p>MeatWise API Database Audit - Generated using automated database audit tools</p>
            <p>For more details, see the JSON reports at: {{ schema_report_file }} and {{ data_report_file }}</p>
        </footer>
    </body>
    </html>
    """
    
    # Render the template
    template = jinja2.Template(template_str)
    html_content = template.render(
        timestamp=template_data["timestamp"],
        schema_data=schema_data,
        data_security_data=data_security_data,
        schema_report_file=schema_report_file,
        data_report_file=data_report_file
    )
    
    # Write the HTML file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"HTML report generated at: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python generate_report.py <schema_report.json> <data_report.json> <output.html>")
        sys.exit(1)
    
    schema_report = sys.argv[1]
    data_report = sys.argv[2]
    output_file = sys.argv[3]
    
    generate_html_report(schema_report, data_report, output_file)
EOF

# Make the script executable
chmod +x scripts/generate_report.py

# Generate the combined HTML report
python scripts/generate_report.py "$SCHEMA_REPORT" "$DATA_REPORT" "$COMBINED_REPORT"

# Report final status
echo -e "\n==============================================" 
echo "AUDIT COMPLETE"
echo -e "==============================================\n" 
echo "Reports generated:"
echo "1. Schema Audit:       $SCHEMA_REPORT"
echo "2. Data Security:      $DATA_REPORT"
echo "3. Combined Report:    $COMBINED_REPORT"
echo ""

# Open the report in the browser if on macOS or Linux with a desktop
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$COMBINED_REPORT"
elif [[ "$OSTYPE" == "linux-gnu"* ]] && command -v xdg-open > /dev/null; then
    xdg-open "$COMBINED_REPORT"
fi

# Determine final exit code
if [ $SCHEMA_RESULT -ne 0 ] || [ $DATA_RESULT -ne 0 ]; then
    echo "⚠️ Audit completed with issues. Please review the reports."
    exit 1
else
    echo "✅ Audit completed successfully with no high-severity issues."
    exit 0
fi 
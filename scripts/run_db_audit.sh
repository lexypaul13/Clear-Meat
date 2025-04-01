#!/bin/bash
# Database Audit Runner Script for MeatWise API
# This script runs the database security audit

set -e

# Create reports directory if it doesn't exist
REPORTS_DIR="./audit_reports"
mkdir -p $REPORTS_DIR

# Get current timestamp for report filenames
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATA_REPORT="${REPORTS_DIR}/data_security_audit_${TIMESTAMP}.json"
HTML_REPORT="${REPORTS_DIR}/security_audit_${TIMESTAMP}.html"

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
AUDIT_RESULT=$?

# Generate HTML report using Python
echo -e "\n==============================================" 
echo "GENERATING HTML REPORT"
echo -e "==============================================\n" 

# Create HTML report using Python
cat > scripts/generate_report.py << 'EOF'
#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime
import jinja2

def generate_html_report(data_report_file, output_file):
    # Load the JSON report
    try:
        with open(data_report_file, 'r') as f:
            data_security_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading data security report: {e}")
        data_security_data = {"error": str(e)}
    
    # Prepare the template data
    template_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_security_data": data_security_data,
        "data_issues_count": sum(len(data_security_data.get("issues", [])) for severity in ["High", "Medium", "Low"]),
    }
    
    # Create HTML template
    template_str = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MeatWise API Database Security Audit Report</title>
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
        </style>
    </head>
    <body>
        <div class="report-header">
            <h1>MeatWise API Database Security Audit Report</h1>
            <p>Generated on: {{ timestamp }}</p>
        </div>

        <div class="section">
            <h2>Audit Summary</h2>
            <div class="summary-box">
                <div class="summary-item">
                    <h3>Security Issues</h3>
                    <p>{{ data_issues_count }} issues found</p>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Data Security Issues</h2>
            
            {% for severity in ['High', 'Medium', 'Low'] %}
                <h3 class="severity-{{ severity.lower() }}">{{ severity }} Severity Issues ({{ data_security_data.issues[severity]|length }})</h3>
                
                {% if data_security_data.issues[severity]|length == 0 %}
                    <p>No {{ severity.lower() }} severity issues found.</p>
                {% else %}
                    {% for issue in data_security_data.issues[severity] %}
                        <div class="issue-card {{ severity.lower() }}-issue">
                            <h4>{{ issue.category }}</h4>
                            <p><strong>Description:</strong> {{ issue.description }}</p>
                            <p><strong>Recommendation:</strong> {{ issue.recommendation }}</p>
                            {% if issue.table %}
                                <p><strong>Table:</strong> {{ issue.table }}</p>
                            {% endif %}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endfor %}
        </div>

        <div class="section">
            <h2>Passed Checks</h2>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Description</th>
                    <th>Table</th>
                </tr>
                {% for check in data_security_data.passed %}
                    <tr>
                        <td>{{ check.category }}</td>
                        <td>{{ check.description }}</td>
                        <td>{{ check.table or '-' }}</td>
                    </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    
    # Render template
    template = jinja2.Template(template_str)
    html_content = template.render(**template_data)
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_report.py <data_report_file> <output_file>")
        sys.exit(1)
    
    data_report_file = sys.argv[1]
    output_file = sys.argv[2]
    
    generate_html_report(data_report_file, output_file)
EOF

# Execute the report generator
python scripts/generate_report.py "$DATA_REPORT" "$HTML_REPORT"

echo -e "\nAudit complete. Reports saved to:"
echo "- JSON: $DATA_REPORT"
echo "- HTML: $HTML_REPORT"

# Return appropriate exit code
if [ $AUDIT_RESULT -ne 0 ]; then
    echo "WARNING: Security audit completed with issues."
    exit $AUDIT_RESULT
fi

echo "SUCCESS: Security audit completed successfully."
exit 0 
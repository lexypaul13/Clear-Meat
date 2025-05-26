#!/bin/bash

# 🔄 MeatWise API Migration Script
# This script helps migrate your project to a new GitHub account and Supabase project

set -e  # Exit on any error

echo "🔄 MeatWise API Migration Script"
echo "================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if required tools are installed
check_dependencies() {
    print_info "Checking dependencies..."
    
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed"
        exit 1
    fi
    
    if ! command -v supabase &> /dev/null; then
        print_error "Supabase CLI is not installed"
        exit 1
    fi
    
    print_status "All dependencies are installed"
}

# Get user input for migration
get_migration_info() {
    echo ""
    print_info "Please provide the following information:"
    echo ""
    
    read -p "📝 New GitHub repository URL (e.g., https://github.com/username/meatwise-api.git): " NEW_REPO_URL
    read -p "🆔 New Supabase project ID: " NEW_PROJECT_ID
    read -p "🔗 New Supabase project URL: " NEW_SUPABASE_URL
    read -p "🔑 New Supabase anon key: " NEW_ANON_KEY
    read -p "🔐 New Supabase service role key: " NEW_SERVICE_KEY
    
    echo ""
    print_info "Migration Information:"
    echo "Repository: $NEW_REPO_URL"
    echo "Project ID: $NEW_PROJECT_ID"
    echo "Supabase URL: $NEW_SUPABASE_URL"
    echo ""
    
    read -p "❓ Is this information correct? (y/n): " CONFIRM
    if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
        print_error "Migration cancelled"
        exit 1
    fi
}

# Create backup of current state
create_backup() {
    print_info "Creating backup of current state..."
    
    # Backup environment file
    if [ -f ".env" ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        print_status "Environment file backed up"
    fi
    
    # Backup database
    if command -v supabase &> /dev/null; then
        supabase db dump --local > backup_migration_$(date +%Y%m%d_%H%M%S).sql
        print_status "Database backup created"
    fi
    
    # Create git backup branch
    git checkout -b backup-before-migration
    git add .
    git commit -m "backup: state before migration to personal account" || true
    git checkout main
    
    print_status "Backup completed"
}

# Update configuration files
update_configs() {
    print_info "Updating configuration files..."
    
    # Update .env file
    if [ -f ".env" ]; then
        # Create new .env with updated values
        cat > .env.new << EOF
# Updated Supabase Configuration for Personal Account
SUPABASE_URL=$NEW_SUPABASE_URL
SUPABASE_ANON_KEY=$NEW_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=$NEW_SERVICE_KEY

# Keep existing OAuth credentials (update these in Supabase dashboard)
$(grep "^GOOGLE_CLIENT_ID=" .env 2>/dev/null || echo "# GOOGLE_CLIENT_ID=your_google_client_id")
$(grep "^GOOGLE_CLIENT_SECRET=" .env 2>/dev/null || echo "# GOOGLE_CLIENT_SECRET=your_google_client_secret")
$(grep "^FACEBOOK_CLIENT_ID=" .env 2>/dev/null || echo "# FACEBOOK_CLIENT_ID=your_facebook_app_id")
$(grep "^FACEBOOK_CLIENT_SECRET=" .env 2>/dev/null || echo "# FACEBOOK_CLIENT_SECRET=your_facebook_app_secret")
$(grep "^APPLE_CLIENT_ID=" .env 2>/dev/null || echo "# APPLE_CLIENT_ID=your_apple_client_id")
$(grep "^SUPABASE_AUTH_EXTERNAL_APPLE_SECRET=" .env 2>/dev/null || echo "# SUPABASE_AUTH_EXTERNAL_APPLE_SECRET=your_apple_secret")
$(grep "^TWITTER_CLIENT_ID=" .env 2>/dev/null || echo "# TWITTER_CLIENT_ID=your_twitter_client_id")
$(grep "^TWITTER_CLIENT_SECRET=" .env 2>/dev/null || echo "# TWITTER_CLIENT_SECRET=your_twitter_client_secret")

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
EOF
        
        mv .env.new .env
        print_status "Environment file updated"
    fi
    
    # Update supabase config
    if [ -f "supabase/config.toml" ]; then
        sed -i.bak "s/project_id = .*/project_id = \"meatwise-api-production\"/" supabase/config.toml
        print_status "Supabase config updated"
    fi
    
    print_status "Configuration files updated"
}

# Setup git for migration
setup_git() {
    print_info "Setting up git for migration..."
    
    # Create migration branch
    git checkout -b migration-to-personal
    
    # Update remote origin
    git remote set-url origin $NEW_REPO_URL
    
    print_status "Git configured for migration"
}

# Commit and push changes
commit_and_push() {
    print_info "Committing and pushing changes..."
    
    # Add all changes
    git add .
    
    # Commit changes
    git commit -m "feat: migrate to personal account

- Updated Supabase configuration for new project
- Migrated OAuth provider settings
- Updated environment variables
- Prepared for production deployment

Migration completed on $(date)"
    
    # Push to new repository
    print_info "Pushing to new repository..."
    git push -u origin migration-to-personal
    
    print_status "Code pushed to new repository"
}

# Link to new Supabase project
link_supabase() {
    print_info "Linking to new Supabase project..."
    
    # Link to new project
    supabase link --project-ref $NEW_PROJECT_ID
    
    print_status "Linked to new Supabase project"
}

# Main migration function
run_migration() {
    echo ""
    print_info "Starting migration process..."
    echo ""
    
    check_dependencies
    get_migration_info
    create_backup
    update_configs
    setup_git
    commit_and_push
    link_supabase
    
    echo ""
    print_status "Migration completed successfully!"
    echo ""
    print_info "Next steps:"
    echo "1. 🔗 Go to your new GitHub repository: $NEW_REPO_URL"
    echo "2. 📊 Create a pull request to merge 'migration-to-personal' to 'main'"
    echo "3. 🗄️  Push database schema: supabase db push"
    echo "4. 📱 Update OAuth provider redirect URIs"
    echo "5. 🧪 Test your API endpoints"
    echo ""
    print_info "See migration_guide.md for detailed post-migration steps"
}

# Run migration
run_migration 
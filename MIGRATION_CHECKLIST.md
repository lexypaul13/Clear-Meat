# 📋 **Migration Checklist**

## ✅ **Pre-Migration (Completed)**
- [x] Database backup created (`backup_20250525_231338.sql`)
- [x] Migration guide created (`migration_guide.md`)
- [x] Migration script created (`migrate_to_personal.sh`)
- [x] Social auth simplified for Supabase built-in OAuth

## 🚀 **Migration Steps**

### **1. Create New Accounts/Projects**
- [ ] Create new GitHub repository on personal account
- [ ] Create new Supabase project on personal account
- [ ] Save new credentials (Project ID, URL, keys)

### **2. Run Migration Script**
```bash
./migrate_to_personal.sh
```

### **3. Manual Steps After Script**
- [ ] Create pull request on new GitHub repo
- [ ] Merge migration branch to main
- [ ] Push database schema: `supabase db push`
- [ ] Restore data from backup

### **4. Update OAuth Providers**
- [ ] Google Cloud Console - update redirect URI
- [ ] Facebook Developers - update redirect URI  
- [ ] Apple Developer - update return URL
- [ ] Twitter Developer - update callback URL

### **5. Test Everything**
- [ ] API endpoints working
- [ ] Authentication working
- [ ] Database queries working
- [ ] OAuth flows working
- [ ] Phone/SMS auth working

### **6. Production Setup**
- [ ] Update environment variables for production
- [ ] Configure custom domain (if applicable)
- [ ] Set up monitoring/logging
- [ ] Configure backups

### **7. Cleanup**
- [ ] Revoke old Supabase API keys
- [ ] Archive old GitHub repository
- [ ] Update any external references
- [ ] Document new URLs/endpoints

## 🆘 **Emergency Rollback**
If something goes wrong:
1. Keep old repository until migration verified
2. Restore from `.env.backup.*` files
3. Use `backup_20250525_231338.sql` to restore data
4. Switch back to old Supabase project

## 📞 **Support**
- Migration guide: `migration_guide.md`
- Social auth setup: `SOCIAL_AUTH_SETUP.md`
- Supabase docs: https://supabase.com/docs 
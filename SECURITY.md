# MeatWise API Security

This document outlines the security features and best practices implemented in the MeatWise API.

## Security Features

### Authentication & Authorization

- **JWT-based authentication**: Secure token-based authentication using JWTs
- **Role-Based Access Control (RBAC)**: Granular permission system with four role levels:
  - Basic: Regular users with limited permissions
  - Contributor: Can add and edit products and ingredients
  - Moderator: Can verify products and manage reports
  - Admin: Full access to all API features
- **Token expiration**: Configurable token expiration time

### Protection Against Common Attacks

- **XSS Protection**:
  - Content Security Policy headers
  - Input sanitization and validation
  - Proper output encoding

- **SQL Injection Protection**:
  - Parameterized queries using SQLAlchemy
  - Input validation and sanitization

- **CSRF Protection**:
  - Proper implementation of API authentication
  - Security headers

- **Rate Limiting**:
  - Configurable rate limiting by IP address
  - Protection against brute force attacks

- **Path Traversal Protection**:
  - Validation of URL paths to prevent directory traversal

### API Security

- **Security Headers**:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Strict-Transport-Security
  - Referrer-Policy
  - Permissions-Policy

- **Input Validation**:
  - Request body validation
  - Content type validation
  - Content length validation
  - Pattern blocking for known attack vectors

- **Error Handling**:
  - Secure error messages (no sensitive information)
  - Proper HTTP status codes

### Data Security

- **Password Security**:
  - bcrypt password hashing
  - Minimum password length requirements

- **Environment Configuration**:
  - No hardcoded secrets
  - Environment-based configuration with .env file
  - SECRET_KEY validation (minimum 32 characters)

- **Database Security**:
  - Row-Level Security in Supabase
  - Proper access control policies

## Security Checklist

- [x] Secure SECRET_KEY configuration
- [x] JWT token expiration and validation
- [x] Role-Based Access Control
- [x] Password hashing with bcrypt
- [x] Protection against XSS
- [x] Protection against SQL injection
- [x] Protection against CSRF
- [x] Rate limiting
- [x] Security headers
- [x] Input validation and sanitization
- [x] Environment-based configuration
- [x] Database security

## Reporting Security Issues

If you discover a security vulnerability, please send an email to security@meatwise.example.com. All security vulnerabilities will be promptly addressed.

Please do not disclose security vulnerabilities publicly until they have been addressed by our team. 
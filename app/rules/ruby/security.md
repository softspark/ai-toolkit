---
language: ruby
category: security
version: "1.0.0"
---

# Ruby Security

## Mass Assignment
- Use strong parameters in controllers: `params.require(:user).permit(:name, :email)`.
- Never use `params.permit!` or pass unsanitized params to `create`/`update`.
- Use `attr_readonly` for fields that should never be updated after creation.
- Audit `update_columns` and `update_attribute` usage (bypass validations).

## SQL Injection
- Use ActiveRecord query interface with parameterized conditions.
- Use `where(name: value)` hash syntax or `where("name = ?", value)` placeholders.
- Never interpolate user input into `where()` strings: `where("name = '#{input}'")`.
- Use `sanitize_sql_array` if building raw SQL fragments is unavoidable.
- Audit all `find_by_sql`, `execute`, and `Arel.sql` calls.

## XSS Prevention
- Rails auto-escapes ERB output with `<%= %>`. Never use `raw()` with user data.
- Use `sanitize()` helper for allowing limited HTML tags.
- Set `Content-Security-Policy` header in `config/initializers/content_security_policy.rb`.
- Use `content_tag` helper for safe HTML generation.
- Mark strings as `html_safe` only when content is guaranteed safe.

## CSRF Protection
- Use `protect_from_forgery with: :exception` in `ApplicationController`.
- Use `authenticity_token` in all forms (Rails includes it by default).
- Use `X-CSRF-Token` header for AJAX requests from JavaScript.
- Exempt only webhook endpoints from CSRF (with payload signature verification).

## Authentication
- Use Devise or `has_secure_password` for authentication.
- Use `bcrypt` for password hashing (included with `has_secure_password`).
- Implement account lockout after N failed login attempts.
- Use `SecureRandom.urlsafe_base64` for generating tokens.
- Store sessions server-side (Redis/database) instead of cookie store in production.

## Authorization
- Use Pundit or CanCanCan for authorization logic.
- Define policies per model: `class UserPolicy < ApplicationPolicy`.
- Check ownership in policies, not just role membership.
- Use `authorize @resource` in every controller action.
- Default deny: require explicit authorization for all actions.

## Secrets Management
- Use `Rails.application.credentials` for encrypted secrets.
- Use `EDITOR="vim" bin/rails credentials:edit` to manage secrets.
- Use per-environment credentials: `credentials/production.yml.enc`.
- Never commit `master.key` or `production.key` to version control.
- Use environment variables for CI/CD and containerized deployments.

## Dependency Security
- Run `bundle audit check --update` for known vulnerability scanning.
- Use `Dependabot` for automated dependency update PRs.
- Pin gem versions in `Gemfile`. Review `Gemfile.lock` changes carefully.
- Use `bundler-audit` in CI pipeline as a required check.
- Update Rails promptly when security patches are released.

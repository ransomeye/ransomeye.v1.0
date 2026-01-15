-- RansomEye v1.0 RBAC + UI Auth Schema Migration (DOWN)
-- Phase 4: Remove RBAC + refresh token schema

DROP TABLE IF EXISTS rbac_refresh_tokens;
DROP TABLE IF EXISTS rbac_permission_audit;
DROP TABLE IF EXISTS rbac_role_permissions;
DROP TABLE IF EXISTS rbac_user_roles;
DROP TABLE IF EXISTS rbac_users;

DROP TYPE IF EXISTS rbac_permission;
DROP TYPE IF EXISTS rbac_role;

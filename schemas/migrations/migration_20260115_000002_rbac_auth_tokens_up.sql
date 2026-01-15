-- RansomEye v1.0 RBAC + UI Auth Schema Migration (UP)
-- Phase 4: UI Authentication & RBAC enforcement foundation
-- Includes RBAC schema + refresh token store

-- RANSOMEYE_INCLUDE: ../../rbac/db/schema.sql

-- UI Backend RBAC grants (post-RBAC schema)
GRANT SELECT ON TABLE rbac_users TO ransomeye_ui;
GRANT SELECT ON TABLE rbac_user_roles TO ransomeye_ui;
GRANT SELECT ON TABLE rbac_role_permissions TO ransomeye_ui;
GRANT INSERT ON TABLE rbac_permission_audit TO ransomeye_ui;
GRANT INSERT, UPDATE ON TABLE rbac_refresh_tokens TO ransomeye_ui;

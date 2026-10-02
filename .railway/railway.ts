import { defineRailway, project } from "railway/iac";

/**
 * Grounded Studio private mode intentionally does not deploy runtime services
 * to Railway. Managed third-party hosting would receive uploaded documents
 * before the application could enforce its internal-network boundary.
 *
 * Keep this file only so existing Railway links fail safely and visibly.
 * Deploy Grounded Studio on an internal VM/k8s/Coolify host instead.
 */
export default defineRailway(() => {
  return project("grounded-studio-test", { resources: [] });
});
